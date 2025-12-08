"""
Real-time vision analysis using OpenAI's vision-capable models.

This module provides REAL image analysis by sending actual image bytes to vision models.
"""
import base64
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

# Global OpenAI client instance
_vision_client: Optional[OpenAI] = None


def get_vision_client(api_key: str) -> OpenAI:
    """Get or create OpenAI client for vision analysis."""
    global _vision_client
    if _vision_client is None:
        _vision_client = OpenAI(api_key=api_key)
    return _vision_client


async def analyze_image_with_vision(
    image_path: Path,
    question: Optional[str] = None,
    api_key: str = None,
    model: str = "gpt-4o-mini"
) -> Dict[str, Any]:
    """
    Perform REAL image analysis using OpenAI's vision-capable models.
    
    This function sends the actual image bytes to OpenAI's vision API and gets
    a detailed description of what's in the image.
    
    Args:
        image_path: Path to the image file
        question: Optional specific question about the image
        api_key: OpenAI API key
        model: Vision model to use (gpt-4o, gpt-4o-mini, gpt-4-vision-preview)
    
    Returns:
        Dictionary with:
        - description: Detailed multi-sentence description of the image
        - caption: Short 1-2 sentence caption
        - tags: List of key objects/tags
        - answer: Answer to specific question if provided
        - objects: Detected objects
        - colors: Detected colors
        - scene_type: Indoor/outdoor/etc
        - mood: Mood/atmosphere
    """
    import asyncio
    from PIL import Image
    import io
    
    if not api_key:
        raise ValueError("OpenAI API key is required for vision analysis")
    
    client = get_vision_client(api_key)
    
    def _analyze_sync():
        """Synchronous vision analysis (runs in thread pool)."""
        # Read and encode image
        with open(image_path, "rb") as image_file:
            image_bytes = image_file.read()
        
        # Encode to base64
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        # Determine image format from file extension
        image_format = image_path.suffix.lower().replace('.', '')
        if image_format == 'jpg':
            image_format = 'jpeg'
        elif image_format == '':
            # Try to detect from file content
            try:
                from PIL import Image
                with Image.open(image_path) as img:
                    image_format = img.format.lower() if img.format else 'jpeg'
            except:
                image_format = 'jpeg'  # Default fallback
        
        # Map to valid MIME types
        mime_type_map = {
            'jpeg': 'image/jpeg',
            'jpg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp',
            'bmp': 'image/bmp',
            'heic': 'image/heic',
            'heif': 'image/heif',
            'tiff': 'image/tiff',
            'tif': 'image/tiff',
        }
        mime_type = mime_type_map.get(image_format, 'image/jpeg')
        
        # Build prompt based on whether question is provided
        if question:
            # Specific question about the image
            prompt = f"""Analyze this image and answer the following question: {question}

Provide a detailed answer based on what you can actually see in the image. Be specific about:
- Objects visible (what they are, their colors, positions)
- People or animals (what they're doing, appearance, expressions)
- Environment (indoor/outdoor, time of day, setting)
- Actions or activities happening
- Colors and visual details
- Mood or atmosphere

Answer in natural, conversational language."""
        else:
            # General description request - optimized for structured extraction
            prompt = """Analyze this image in detail and provide a comprehensive description. Be very specific about:

1. **Main subjects and objects**: What are the primary elements? (e.g., "a single elephant in silhouette", "tall golden grass", "a large sun")
2. **Colors**: Be specific about color descriptions (e.g., "bright orange and yellow clouds", "golden grass", "dark silhouette")
3. **People or animals**: If present, describe what they look like, what they're doing, their expressions
4. **Actions**: What is happening? (e.g., "walking across", "swimming in", "standing near")
5. **Environment**: Indoor/outdoor? Time of day? (e.g., "open savannah", "sunset", "daytime", "night")
6. **Mood and atmosphere**: Describe the feeling (e.g., "peaceful", "dramatic", "majestic", "calm", "energetic")
7. **Spatial relationships**: What's in foreground vs background? Positions of elements
8. **Lighting**: Natural/artificial? Direction? Quality? (e.g., "warm golden light", "dramatic sunset lighting")

Write in natural, conversational language. Use 4-6 sentences. Be very specific and detailed about what you actually see."""
        
        # Prepare messages with image
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}"
                        }
                    }
                ]
            }
        ]
        
        # Call OpenAI vision API
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )
            
            analysis_text = response.choices[0].message.content
            
            # Check if OpenAI refused to analyze (content policy)
            refusal_phrases = [
                "i'm unable to assist",
                "i cannot",
                "i can't",
                "i'm not able",
                "unable to assist",
                "cannot analyze",
                "content policy",
                "safety guidelines",
                "i apologize, but",
                "i'm sorry, but i cannot"
            ]
            
            if any(phrase in analysis_text.lower() for phrase in refusal_phrases):
                logger.warning(f"OpenAI refused to analyze image {image_path.name} - likely content policy restriction")
                # Raise an exception to trigger fallback to local analysis
                raise ValueError(f"OpenAI content policy restriction: {analysis_text}")
            
            # Extract structured information from the analysis
            analysis_lower = analysis_text.lower()
            
            # Extract objects (common nouns)
            objects = []
            object_keywords = ["dog", "cat", "person", "people", "car", "tree", "building", "house",
                             "table", "chair", "book", "phone", "computer", "food", "water", "pool",
                             "sky", "cloud", "mountain", "beach", "road", "street", "window", "door",
                             "flower", "plant", "bird", "animal"]
            for keyword in object_keywords:
                if keyword in analysis_lower:
                    objects.append(keyword)
            
            # Extract colors
            colors = []
            color_keywords = ["red", "blue", "green", "yellow", "orange", "purple", "pink", "brown",
                            "black", "white", "gray", "grey", "beige", "tan", "gold", "silver",
                            "bright", "dark", "light"]
            for keyword in color_keywords:
                if keyword in analysis_lower:
                    colors.append(keyword)
            
            # Determine scene type
            scene_type = "unknown"
            if any(word in analysis_lower for word in ["indoor", "room", "inside", "interior", "building"]):
                scene_type = "indoor"
            elif any(word in analysis_lower for word in ["outdoor", "outside", "exterior", "nature", "landscape", "street", "park"]):
                scene_type = "outdoor"
            elif any(word in analysis_lower for word in ["water", "ocean", "sea", "beach", "pool", "lake"]):
                scene_type = "water/beach"
            
            # Extract mood
            mood = []
            mood_keywords = ["happy", "sad", "peaceful", "energetic", "calm", "dramatic", "bright", "dark",
                           "warm", "cool", "cheerful", "serious", "relaxing", "active"]
            for keyword in mood_keywords:
                if keyword in analysis_lower:
                    mood.append(keyword)
            
            # Generate short caption (first sentence or two)
            sentences = analysis_text.split('.')
            caption = '. '.join(sentences[:2]).strip()
            if not caption.endswith('.'):
                caption += '.'
            
            # Extract tags (key nouns and adjectives)
            tags = []
            words = analysis_text.split()
            for i, word in enumerate(words):
                if word.lower() in object_keywords or word.lower() in color_keywords:
                    if word.lower() not in tags:
                        tags.append(word.lower())
            
            return {
                "description": analysis_text,
                "caption": caption,
                "tags": list(set(tags))[:15],
                "answer": analysis_text if question else None,
                "objects": list(set(objects))[:20],
                "colors": list(set(colors))[:15],
                "scene_type": scene_type,
                "mood": list(set(mood))[:5],
                "analysis_source": "OpenAI Vision API",
                "model_used": model
            }
            
        except Exception as e:
            logger.error(f"Error calling OpenAI vision API: {e}", exc_info=True)
            raise
    
    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _analyze_sync)
    except Exception as e:
        logger.error(f"Error in vision analysis for {image_path}: {e}", exc_info=True)
        raise

