"""
Comprehensive image analysis utilities.

Provides additional image analysis functions beyond BLIP-2 and CLIP:
- Image metadata extraction
- Image similarity comparison
- Batch image processing
- Image format conversion
- Image quality assessment
"""
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import logging
import asyncio

logger = logging.getLogger(__name__)


async def extract_detailed_image_metadata(image_path: Path) -> Dict[str, Any]:
    """
    Extract comprehensive metadata from an image file.
    
    Supports: JPG, JPEG, PNG, GIF, WEBP, BMP, HEIC, HEIF, TIFF, TIF, SVG, ICO
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Dictionary with detailed image metadata including:
        - dimensions (width, height)
        - format, mode, file_size
        - EXIF data (if available)
        - color palette (if applicable)
        - compression info
    """
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS
        
        # Handle HEIC/HEIF files
        suffix = image_path.suffix.lower()
        if suffix in [".heic", ".heif"]:
            try:
                from pillow_heif import register_heif_opener
                register_heif_opener()
            except ImportError:
                logger.warning("pillow-heif not installed. HEIC/HEIF support may be limited.")
        
        def _extract_sync():
            """Synchronous metadata extraction (runs in thread pool)."""
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")
                
                width, height = img.size
                format_name = img.format or "unknown"
                mode = img.mode
                file_size = image_path.stat().st_size
                
                metadata = {
                    "width": width,
                    "height": height,
                    "format": format_name,
                    "mode": mode,
                    "file_size": file_size,
                    "aspect_ratio": round(width / height, 2) if height > 0 else 0,
                    "total_pixels": width * height,
                    "source_path": str(image_path),
                    "file_type": "image"
                }
                
                # Extract EXIF data if available
                try:
                    exif_data = img.getexif()
                    if exif_data:
                        exif_dict = {}
                        for tag_id, value in exif_data.items():
                            tag = TAGS.get(tag_id, tag_id)
                            exif_dict[tag] = value
                        metadata["exif"] = exif_dict
                except Exception as e:
                    logger.debug(f"Could not extract EXIF data: {e}")
                
                # Extract additional info if available
                if hasattr(img, "info"):
                    metadata["image_info"] = img.info
                
                return metadata
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _extract_sync)
        
    except ImportError:
        logger.error("Pillow (PIL) not installed. Install with: pip install pillow")
        raise ImportError("Pillow not installed. Install with: pip install pillow")
    except Exception as e:
        logger.error(f"Error extracting metadata from {image_path}: {e}")
        raise


async def compare_images_similarity(
    image_path1: Path,
    image_path2: Path,
    embeddings_provider
) -> float:
    """
    Compare two images for similarity using CLIP embeddings.
    
    Args:
        image_path1: Path to first image
        image_path2: Path to second image
        embeddings_provider: CLIPImageEmbeddingsProvider instance
        
    Returns:
        Similarity score between 0 and 1 (1 = identical, 0 = completely different)
    """
    try:
        import numpy as np
        
        # Get embeddings for both images
        emb1 = await embeddings_provider.embed_image(image_path1)
        emb2 = await embeddings_provider.embed_image(image_path2)
        
        # Calculate cosine similarity
        emb1_np = np.array(emb1)
        emb2_np = np.array(emb2)
        
        # Normalize vectors
        norm1 = np.linalg.norm(emb1_np)
        norm2 = np.linalg.norm(emb2_np)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        emb1_norm = emb1_np / norm1
        emb2_norm = emb2_np / norm2
        
        # Cosine similarity
        similarity = np.dot(emb1_norm, emb2_norm)
        
        # Normalize to 0-1 range (cosine similarity is already -1 to 1, but typically 0 to 1)
        similarity = max(0.0, min(1.0, (similarity + 1) / 2))
        
        return float(similarity)
        
    except Exception as e:
        logger.error(f"Error comparing images: {e}")
        raise


async def batch_analyze_images(
    image_paths: List[Path],
    blip2_analyzer,
    generate_captions: bool = True
) -> List[Dict[str, Any]]:
    """
    Batch analyze multiple images with BLIP-2 and metadata extraction.
    
    Args:
        image_paths: List of paths to image files
        blip2_analyzer: BLIP2ImageAnalyzer instance
        generate_captions: Whether to generate captions (default: True)
        
    Returns:
        List of dictionaries, each containing:
        - image_path: Path to the image
        - metadata: Detailed image metadata
        - caption: Generated caption (if generate_captions=True)
        - analysis: Full analysis result
    """
    results = []
    
    for image_path in image_paths:
        try:
            # Extract metadata
            metadata = await extract_detailed_image_metadata(image_path)
            
            result = {
                "image_path": str(image_path),
                "metadata": metadata
            }
            
            # Generate caption if requested
            if generate_captions:
                try:
                    caption = await blip2_analyzer.generate_caption(image_path)
                    result["caption"] = caption
                    result["analysis"] = f"Image: {image_path.name}\nDimensions: {metadata['width']}x{metadata['height']}\nFormat: {metadata['format']}\nCaption: {caption}"
                except Exception as e:
                    logger.warning(f"Failed to generate caption for {image_path}: {e}")
                    result["caption"] = None
                    result["analysis"] = f"Image: {image_path.name}\nDimensions: {metadata['width']}x{metadata['height']}\nFormat: {metadata['format']}\nCaption generation failed: {e}"
            else:
                result["caption"] = None
                result["analysis"] = f"Image: {image_path.name}\nDimensions: {metadata['width']}x{metadata['height']}\nFormat: {metadata['format']}"
            
            results.append(result)
            
        except Exception as e:
            logger.error(f"Error analyzing image {image_path}: {e}")
            results.append({
                "image_path": str(image_path),
                "error": str(e),
                "metadata": None,
                "caption": None,
                "analysis": None
            })
    
    return results


async def find_similar_images(
    query_image_path: Path,
    candidate_image_paths: List[Path],
    embeddings_provider,
    top_k: int = 5,
    threshold: float = 0.5
) -> List[Tuple[Path, float]]:
    """
    Find images similar to a query image using CLIP embeddings.
    
    Args:
        query_image_path: Path to the query image
        candidate_image_paths: List of candidate image paths to search
        embeddings_provider: CLIPImageEmbeddingsProvider instance
        top_k: Number of top similar images to return
        threshold: Minimum similarity threshold (0-1)
        
    Returns:
        List of tuples (image_path, similarity_score) sorted by similarity (highest first)
    """
    try:
        # Get query embedding
        query_emb = await embeddings_provider.embed_image(query_image_path)
        
        # Get embeddings for all candidates
        candidate_embs = await embeddings_provider.embed_images(candidate_image_paths)
        
        # Calculate similarities
        import numpy as np
        
        query_np = np.array(query_emb)
        query_norm = query_np / np.linalg.norm(query_np) if np.linalg.norm(query_np) > 0 else query_np
        
        similarities = []
        for i, cand_emb in enumerate(candidate_embs):
            cand_np = np.array(cand_emb)
            cand_norm = cand_np / np.linalg.norm(cand_np) if np.linalg.norm(cand_np) > 0 else cand_np
            
            similarity = np.dot(query_norm, cand_norm)
            similarity = max(0.0, min(1.0, (similarity + 1) / 2))
            
            if similarity >= threshold:
                similarities.append((candidate_image_paths[i], float(similarity)))
        
        # Sort by similarity (highest first) and return top_k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
        
    except Exception as e:
        logger.error(f"Error finding similar images: {e}")
        raise


def is_image_file(file_path: Path) -> bool:
    """
    Check if a file is an image based on its extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if the file is an image, False otherwise
    """
    image_extensions = {
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp",
        ".heic", ".heif", ".tiff", ".tif", ".svg", ".ico"
    }
    return file_path.suffix.lower() in image_extensions


def get_image_format_info(format_name: str) -> Dict[str, Any]:
    """
    Get information about an image format.
    
    Args:
        format_name: Image format name (e.g., "JPEG", "PNG")
        
    Returns:
        Dictionary with format information:
        - name: Format name
        - supports_transparency: Whether format supports transparency
        - supports_animation: Whether format supports animation
        - typical_use: Typical use case
    """
    format_info = {
        "JPEG": {
            "name": "JPEG",
            "supports_transparency": False,
            "supports_animation": False,
            "typical_use": "Photographs, web images"
        },
        "PNG": {
            "name": "PNG",
            "supports_transparency": True,
            "supports_animation": False,
            "typical_use": "Graphics, images with transparency"
        },
        "GIF": {
            "name": "GIF",
            "supports_transparency": True,
            "supports_animation": True,
            "typical_use": "Simple graphics, animations"
        },
        "WEBP": {
            "name": "WEBP",
            "supports_transparency": True,
            "supports_animation": True,
            "typical_use": "Modern web images, optimized compression"
        },
        "BMP": {
            "name": "BMP",
            "supports_transparency": False,
            "supports_animation": False,
            "typical_use": "Windows bitmap images"
        },
        "TIFF": {
            "name": "TIFF",
            "supports_transparency": True,
            "supports_animation": False,
            "typical_use": "High-quality images, printing"
        },
        "HEIC": {
            "name": "HEIC",
            "supports_transparency": True,
            "supports_animation": False,
            "typical_use": "Apple device images, efficient compression"
        },
        "HEIF": {
            "name": "HEIF",
            "supports_transparency": True,
            "supports_animation": False,
            "typical_use": "High Efficiency Image Format, modern standard"
        },
        "SVG": {
            "name": "SVG",
            "supports_transparency": True,
            "supports_animation": True,
            "typical_use": "Vector graphics, scalable images"
        }
    }
    
    return format_info.get(format_name.upper(), {
        "name": format_name,
        "supports_transparency": False,
        "supports_animation": False,
        "typical_use": "Unknown format"
    })

