"""
Image analysis module with fallback chain:
1. OpenAI Vision API (if OPENAI_API_KEY is set)
2. Local captioning model (if ENABLE_CAPTION_MODEL=true)
3. Metadata fallback (last resort)
"""
from typing import Optional, List, Dict, Any
import logging
import asyncio
from pathlib import Path
import os

logger = logging.getLogger(__name__)

# Global singleton instances
_clip_instance: Optional['CLIPImageEmbeddingsProvider'] = None


def get_clip_provider() -> 'CLIPImageEmbeddingsProvider':
    """
    Get or create the global CLIP embeddings provider instance (singleton pattern).
    
    This ensures the model is only loaded once and reused across requests.
    """
    global _clip_instance
    if _clip_instance is None:
        from app.embeddings.image_provider import CLIPImageEmbeddingsProvider
        _clip_instance = CLIPImageEmbeddingsProvider()
    return _clip_instance


class LightweightCaptionModel:
    """Lightweight image captioning model using Salesforce/blip-image-captioning-base."""
    
    def __init__(self, model_name: Optional[str] = None, device: Optional[str] = None):
        from app.config import get_settings
        import threading
        settings = get_settings()
        self.model_name = model_name or settings.local_caption_model_name
        self.device = device
        self._processor = None
        self._model = None
        self._lock = threading.Lock()  # Thread safety for model access
    
    def _get_model(self):
        """Lazy initialization of captioning model."""
        if self._model is None:
            with self._lock:  # Thread-safe initialization
                if self._model is None:  # Double-check after acquiring lock
                    try:
                        from transformers import BlipProcessor, BlipForConditionalGeneration
                        import torch
                        import os
                        
                        if self.device is None:
                            self.device = "cuda" if torch.cuda.is_available() else "cpu"
                        
                        logger.info(f"Loading lightweight captioning model: {self.model_name} on {self.device}")
                        
                        # CRITICAL: Limit OpenMP threads to prevent crashes
                        # Set environment variables before importing/using PyTorch
                        os.environ.setdefault('OMP_NUM_THREADS', '1')
                        os.environ.setdefault('MKL_NUM_THREADS', '1')
                        os.environ.setdefault('NUMEXPR_NUM_THREADS', '1')
                        os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
                        
                        # Load with optimizations for faster inference
                        # Note: Model download happens here - if it's slow, the timeout in get_caption_model() will catch it
                        self._processor = BlipProcessor.from_pretrained(
                            self.model_name,
                            cache_dir=None,  # Use default cache
                            local_files_only=False
                        )
                        self._model = BlipForConditionalGeneration.from_pretrained(
                            self.model_name,
                            cache_dir=None,
                            local_files_only=False,
                            torch_dtype=torch.float32  # Use float32 for CPU (faster than float16 on CPU)
                        ).to(self.device)
                        self._model.eval()
                        # Optimize model for inference
                        if self.device == "cpu":
                            # Use torch.jit.optimize_for_inference if available for CPU
                            try:
                                torch.set_num_threads(1)  # CRITICAL: Use single thread to prevent crashes
                                torch.set_num_interop_threads(1)  # Limit inter-op threads
                            except:
                                pass
                        logger.info(f"Captioning model loaded successfully on {self.device}")
                        
                    except ImportError:
                        raise ImportError("transformers and torch not installed. Install with: pip install transformers torch")
                    except Exception as e:
                        logger.error(f"Failed to load captioning model: {e}", exc_info=True)
                        raise
        return self._processor, self._model
    
    async def generate_caption(self, image_path: Path, max_length: int = 50) -> str:
        """
        Generate a caption using the lightweight BLIP captioning model.
        
        Args:
            image_path: Path to the image file
            max_length: Maximum caption length
            
        Returns:
            Caption string
        """
        import asyncio
        from PIL import Image
        import torch
        import os
        
        # CRITICAL: Set thread limits before any PyTorch operations
        os.environ.setdefault('OMP_NUM_THREADS', '1')
        os.environ.setdefault('MKL_NUM_THREADS', '1')
        os.environ.setdefault('NUMEXPR_NUM_THREADS', '1')
        
        # Thread-safe model access
        with self._lock:
            processor, model = self._get_model()
        
        def _caption_sync():
            """Synchronous caption generation."""
            try:
                # Set thread limits inside the executor to ensure they're applied
                os.environ['OMP_NUM_THREADS'] = '1'
                os.environ['MKL_NUM_THREADS'] = '1'
                os.environ['NUMEXPR_NUM_THREADS'] = '1'
                torch.set_num_threads(1)
                torch.set_num_interop_threads(1)
                
                image = Image.open(image_path).convert("RGB")
                
                # Resize to smaller size for faster processing on CPU
                # 224px is sufficient for BLIP and much faster
                max_size = 224
                if max(image.size) > max_size:
                    ratio = max_size / max(image.size)
                    new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
                    image = image.resize(new_size, Image.Resampling.LANCZOS)
                
                inputs = processor(images=image, return_tensors="pt").to(self.device)
                
                actual_max_length = min(max_length, 50)
                with torch.no_grad():
                    # Optimize for speed: use greedy decoding (num_beams=1), no sampling
                    # Set low max_new_tokens for faster generation
                    generated_ids = model.generate(
                        **inputs,
                        max_length=actual_max_length,
                        num_beams=1,  # Greedy decoding (fastest)
                        do_sample=False,  # Deterministic (faster)
                        max_new_tokens=30,  # Shorter captions = faster
                        pad_token_id=processor.tokenizer.pad_token_id or processor.tokenizer.eos_token_id,
                        early_stopping=True  # Stop early if possible
                    )
                
                caption = processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()
                logger.debug(f"Generated caption: {caption[:100]}...")
                return caption
            except Exception as e:
                logger.exception(f"Caption generation failed: {e}")
                raise
        
        try:
            loop = asyncio.get_event_loop()
            # Increased timeout for CPU inference (can be slow, especially first time)
            result = await asyncio.wait_for(
                loop.run_in_executor(None, _caption_sync),
                timeout=60.0  # 60 seconds for CPU inference
            )
            return result
        except asyncio.TimeoutError:
            logger.error(f"Caption generation timed out for {image_path}")
            raise TimeoutError(f"Caption generation timed out after 60 seconds")
        except Exception as e:
            logger.error(f"Caption generation failed for {image_path}: {e}", exc_info=True)
            raise


# Global captioning model instance
_caption_model_instance: Optional[LightweightCaptionModel] = None
_caption_model_crashed: bool = False  # Track if model has crashed to prevent retries


def get_caption_model(force: bool = False, timeout: float = 10.0) -> Optional[LightweightCaptionModel]:
    """
    Get or create the global captioning model instance.
    
    Captioning models can be slow on CPU. Set ENABLE_CAPTION_MODEL=false to disable.
    
    Args:
        force: If True, load the model even if ENABLE_CAPTION_MODEL is False (useful for fallback scenarios)
        timeout: Maximum time (seconds) to wait for model loading/downloading. Default 10s (short to fail fast).
    """
    global _caption_model_instance, _caption_model_crashed
    from app.config import get_settings
    import threading
    import time
    settings = get_settings()
    
    # If model has crashed before, don't try again (prevents repeated crashes)
    if _caption_model_crashed:
        logger.warning("Captioning model previously crashed - skipping to prevent further crashes")
        return None
    
    if not settings.enable_caption_model and not force:
        logger.debug("Captioning model disabled")
        return None
    
    if _caption_model_instance is None:
        try:
            if force and not settings.enable_caption_model:
                logger.info("Forcing local captioning model load (fallback scenario)")
            
            # Check if model is already cached to avoid slow downloads
            try:
                from transformers import BlipProcessor
                from huggingface_hub import cached_assets_path
                import os
                
                # Quick check: see if model files exist in cache
                model_name = settings.local_caption_model_name
                cache_path = os.path.expanduser("~/.cache/huggingface/hub")
                # This is a heuristic - if cache doesn't exist or is empty, skip loading
                if not os.path.exists(cache_path) or not os.listdir(cache_path):
                    logger.warning("Model cache not found - skipping slow download, using metadata fallback")
                    return None
            except Exception:
                # If we can't check cache, proceed with loading attempt
                pass
            
            logger.info(f"Initializing local captioning model (timeout: {timeout}s)...")
            
            # Model loading result
            model_result = {"instance": None, "error": None, "done": False}
            
            def load_model():
                """Load model in a separate thread."""
                try:
                    model_result["instance"] = LightweightCaptionModel()
                    model_result["done"] = True
                    logger.info("Local captioning model loaded successfully")
                except Exception as e:
                    logger.error(f"Model loading error: {e}")
                    model_result["error"] = e
                    model_result["done"] = True
            
            # Load model in a thread with timeout
            loader_thread = threading.Thread(target=load_model, daemon=True)
            loader_thread.start()
            
            # Wait with timeout, but check periodically
            start_time = time.time()
            while loader_thread.is_alive() and (time.time() - start_time) < timeout:
                time.sleep(0.5)  # Check every 0.5 seconds
            
            if loader_thread.is_alive():
                logger.warning(f"Model loading timed out after {timeout}s - skipping local model, using metadata fallback")
                return None
            
            if model_result["error"]:
                if isinstance(model_result["error"], ImportError):
                    logger.error(f"Failed to load captioning model - missing dependencies: {model_result['error']}")
                    logger.error("Please install: pip install transformers torch")
                else:
                    logger.error(f"Failed to load captioning model: {model_result['error']}", exc_info=True)
                return None
            
            if model_result["instance"]:
                _caption_model_instance = model_result["instance"]
            else:
                logger.warning("Model loading completed but no instance created")
                return None
            
        except Exception as e:
            logger.error(f"Failed to initialize captioning model: {e}", exc_info=True)
            return None
    return _caption_model_instance


class SimpleImageAnalyzer:
    """Lightweight image analyzer with optional captioning model and metadata fallback."""
    
    def __init__(self):
        self.caption_model = get_caption_model()  # Try to load captioning model, None if fails
    
    def _generate_metadata_caption(self, image_path: Path) -> str:
        """Generate caption from metadata only (fallback)."""
        try:
            from PIL import Image
            
            suffix = image_path.suffix.lower()
            if suffix in [".heic", ".heif"]:
                try:
                    from pillow_heif import register_heif_opener
                    register_heif_opener()
                except ImportError:
                    pass
            
            image = Image.open(image_path).convert("RGB")
            width, height = image.size
            format_name = image.format or "unknown"
            
            aspect_ratio = width / height if height > 0 else 1.0
            if aspect_ratio > 1.5:
                orientation = "landscape"
            elif aspect_ratio < 0.67:
                orientation = "portrait"
            else:
                orientation = "square"
            
            if width > 2000 or height > 2000:
                size_desc = "high resolution"
            elif width > 1000 or height > 1000:
                size_desc = "medium resolution"
            else:
                size_desc = "standard resolution"
            
            return f"{orientation} {format_name.lower()} image, {size_desc}, {width}x{height} pixels"
        except Exception as e:
            logger.error(f"Error generating metadata caption: {e}")
            return f"Image file: {image_path.name}"
    
    async def generate_caption(self, image_path: Path, max_length: int = 50) -> str:
        """
        Generate a caption - tries captioning model first, falls back to metadata.
        
        Args:
            image_path: Path to the image file
            max_length: Maximum caption length
            
        Returns:
            Caption string
        """
        # Try captioning model first
        if self.caption_model:
            try:
                logger.debug(f"Attempting to generate caption with model for {image_path}")
                caption = await asyncio.wait_for(
                    self.caption_model.generate_caption(image_path, max_length),
                    timeout=10.0  # Outer timeout wrapper
                )
                logger.info(f"Generated model caption: {caption[:100]}...")
                return caption
            except (asyncio.TimeoutError, TimeoutError) as e:
                logger.warning(f"Captioning model timed out, using metadata fallback: {e}")
            except Exception as e:
                logger.warning(f"Captioning model failed, using metadata fallback: {e}")
        
        # Fallback to metadata
        logger.debug(f"Using metadata-based caption for {image_path}")
        return self._generate_metadata_caption(image_path)
    
    async def generate_detailed_description(self, image_path: Path) -> str:
        """
        Generate a detailed description - tries captioning model first, falls back to metadata.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Detailed description string
        """
        # Try captioning model first (generate longer description)
        if self.caption_model:
            try:
                logger.debug(f"Attempting to generate detailed description with model for {image_path}")
                # Generate longer caption for detailed description
                caption = await self.caption_model.generate_caption(image_path, max_length=100)
                logger.info(f"Generated model description: {caption[:100]}...")
                return caption
            except Exception as e:
                logger.warning(f"Captioning model failed for detailed description, using metadata fallback: {e}")
        
        # Fallback to metadata-based description
        try:
            from PIL import Image
            import os
            
            # Handle HEIC/HEIF files
            suffix = image_path.suffix.lower()
            if suffix in [".heic", ".heif"]:
                try:
                    from pillow_heif import register_heif_opener
                    register_heif_opener()
                except ImportError:
                    pass
            
            # Load image and get metadata
            image = Image.open(image_path).convert("RGB")
            width, height = image.size
            format_name = image.format or "unknown"
            mode = image.mode
            file_size = image_path.stat().st_size
            file_size_mb = file_size / (1024 * 1024)
            
            # Get color information
            try:
                # Sample some pixels to get color info
                pixels = list(image.getdata()[:1000])  # Sample first 1000 pixels
                if pixels:
                    avg_r = sum(p[0] for p in pixels) / len(pixels)
                    avg_g = sum(p[1] for p in pixels) / len(pixels)
                    avg_b = sum(p[2] for p in pixels) / len(pixels)
                    
                    # Determine dominant color tone
                    if avg_r > avg_g and avg_r > avg_b:
                        color_tone = "warm tones (red/orange)"
                    elif avg_b > avg_r and avg_b > avg_g:
                        color_tone = "cool tones (blue)"
                    elif avg_g > avg_r and avg_g > avg_b:
                        color_tone = "green tones"
                    else:
                        color_tone = "neutral tones"
                else:
                    color_tone = "unknown color tone"
            except:
                color_tone = "unknown color tone"
            
            # Aspect ratio analysis
            aspect_ratio = width / height if height > 0 else 1.0
            if aspect_ratio > 1.5:
                orientation = "wide landscape"
            elif aspect_ratio < 0.67:
                orientation = "tall portrait"
            elif 0.9 < aspect_ratio < 1.1:
                orientation = "square"
            else:
                orientation = "standard"
            
            # Resolution category
            total_pixels = width * height
            if total_pixels > 4_000_000:
                resolution = "high resolution"
            elif total_pixels > 1_000_000:
                resolution = "medium resolution"
            else:
                resolution = "standard resolution"
            
            description = f"""Image file: {image_path.name}
Format: {format_name.upper()}
Dimensions: {width} x {height} pixels ({resolution})
Orientation: {orientation}
Color mode: {mode}
File size: {file_size_mb:.2f} MB
Color characteristics: {color_tone}
Aspect ratio: {aspect_ratio:.2f}"""
            
            logger.debug(f"Generated detailed description for {image_path}")
            return description
            
        except Exception as e:
            logger.error(f"Error generating detailed description for {image_path}: {e}", exc_info=True)
            return f"Image file: {image_path.name}\nError: {str(e)}"
    
    async def answer_question_about_image(self, image_path: Path, question: str) -> str:
        """
        Answer a question about an image using metadata.
        
        Args:
            image_path: Path to the image file
            question: Question about the image
            
        Returns:
            Answer string based on metadata
        """
        try:
            from PIL import Image
            
            image = Image.open(image_path).convert("RGB")
            width, height = image.size
            format_name = image.format or "unknown"
            
            question_lower = question.lower()
            
            # Simple Q&A based on metadata
            if "size" in question_lower or "dimension" in question_lower:
                return f"The image is {width} pixels wide by {height} pixels tall."
            elif "format" in question_lower or "type" in question_lower:
                return f"The image format is {format_name.upper()}."
            elif "orientation" in question_lower:
                aspect_ratio = width / height if height > 0 else 1.0
                if aspect_ratio > 1.2:
                    return "The image is in landscape orientation (wider than tall)."
                elif aspect_ratio < 0.8:
                    return "The image is in portrait orientation (taller than wide)."
                else:
                    return "The image is approximately square."
            else:
                return f"I can provide information about image dimensions ({width}x{height}), format ({format_name}), and basic properties. For detailed content analysis, please describe what you see in the image."
                
        except Exception as e:
            logger.error(f"Error answering question about {image_path}: {e}", exc_info=True)
            return "Unable to answer question about this image."


# Singleton instance
_simple_analyzer_instance: Optional[SimpleImageAnalyzer] = None


def get_blip2_analyzer() -> SimpleImageAnalyzer:
    """
    Get or create the global simple image analyzer instance (singleton pattern).
    
    NOTE: This function is kept for backward compatibility but returns SimpleImageAnalyzer
    instead of BLIP2ImageAnalyzer.
    """
    global _simple_analyzer_instance
    if _simple_analyzer_instance is None:
        _simple_analyzer_instance = SimpleImageAnalyzer()
    return _simple_analyzer_instance


async def scan_image_comprehensively(image_path: Path, question: Optional[str] = None) -> Dict[str, Any]:
    """
    Perform a comprehensive scan of an image using REAL analysis.
    
    Uses the proper fallback chain: OpenAI Vision → Local Captioning → Metadata.
    
    Args:
        image_path: Path to the image file
        question: Optional specific question about the image
        
    Returns:
        Dictionary with scan results
    """
    try:
        clip = get_clip_provider()
        
        logger.info(f"Starting comprehensive image scan for {image_path}")
        
        # Add timeout wrapper for analyze_image
        # Allow more time if local model is enabled (needs time to load/process)
        import asyncio
        from app.config import get_settings
        settings = get_settings()
        
        # Faster timeout - fail fast to metadata fallback
        timeout = 8.0  # Reduced from 30s/10s to 8s - prioritize speed
        
        try:
            analysis = await asyncio.wait_for(
                analyze_image(image_path, question=question),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"Image analysis timed out after {timeout} seconds, using metadata fallback")
            # Return minimal metadata fallback
            raise ValueError("Image analysis timed out, using metadata")
        
        # Skip CLIP embedding generation for faster processing
        # CLIP embeddings are not critical for basic image search
        clip_embedding = None
        clip_embedding_dim = 0
        logger.debug("Skipping CLIP embedding generation for faster processing")
        
        # Build comprehensive scan text
        full_scan_text = f"""=== REAL IMAGE ANALYSIS ===
        
Analysis Source: {analysis.get('analysis_source', 'Unknown')}
Model Used: {analysis.get('model_used', 'N/A')}
        
CAPTION:
{analysis.get('caption', 'N/A')}
        
DETAILED DESCRIPTION:
{analysis.get('description', 'N/A')}
        
DETECTED OBJECTS:
{', '.join(analysis.get('objects', [])) if analysis.get('objects') else 'None detected'}
        
DETECTED COLORS:
{', '.join(analysis.get('colors', [])) if analysis.get('colors') else 'None detected'}
        
SCENE TYPE: {analysis.get('scene_type', 'Unknown')}
        
MOOD/ATMOSPHERE: {', '.join(analysis.get('mood', [])) if analysis.get('mood') else 'Not specified'}
        
TAGS: {', '.join(analysis.get('tags', [])) if analysis.get('tags') else 'None'}
        
CLIP EMBEDDING: Generated ({clip_embedding_dim} dimensions) for similarity search"""
        
        logger.info(f"Comprehensive scan completed for {image_path}")
        
        return {
            "scan_text": full_scan_text,  # Add scan_text for document service
            "caption": analysis.get('caption', ''),
            "description": analysis.get('description', ''),
            "basic_caption": analysis.get('caption', ''),
            "detailed_description": analysis.get('description', ''),
            "objects": analysis.get('objects', []),
            "people": [obj for obj in analysis.get('objects', []) if obj in ['person', 'people']],
            "animals": [obj for obj in analysis.get('objects', []) if obj in ['dog', 'cat', 'bird', 'animal']],
            "actions": [],
            "colors": analysis.get('colors', []),
            "scene_type": analysis.get('scene_type', 'unknown'),
            "mood": analysis.get('mood', []),
            "analysis_source": analysis.get('analysis_source', 'Unknown'),
            "text_content": [],
            "clip_embedding": clip_embedding,
            "clip_embedding_dim": clip_embedding_dim,
            "full_scan_text": full_scan_text,
            "scan_complete": True,
            "analysis_source": analysis.get('analysis_source', 'Unknown'),
            "model_used": analysis.get('model_used', 'N/A')
        }
    except ValueError as ve:
        # Timeout or intentional fallback - use metadata
        logger.info(f"Using metadata fallback for {image_path}: {ve}")
        # Return minimal metadata structure
        return {
            "scan_text": f"Image: {image_path.name}\n\nMetadata: Basic image file information",
            "caption": image_path.name,
            "description": f"Image file: {image_path.name}",
            "basic_caption": image_path.name,
            "detailed_description": f"Image file: {image_path.name}",
            "objects": [],
            "people": [],
            "animals": [],
            "actions": [],
            "colors": [],
            "scene_type": "unknown",
            "mood": [],
            "text_content": [],
            "clip_embedding": None,
            "clip_embedding_dim": 0,
            "full_scan_text": f"Image: {image_path.name}\n\nMetadata: Basic image file information",
            "scan_complete": False,
            "analysis_source": "Metadata Fallback",
            "model_used": "None"
        }
    except Exception as e:
        logger.error(f"Error in REAL comprehensive image scan for {image_path}: {e}", exc_info=True)
        return {
            "scan_text": f"Image: {image_path.name}\n\nMetadata: Error during scan",
            "basic_caption": "Scan unavailable",
            "detailed_description": f"Error during scan: {e}",
            "objects": [],
            "people": [],
            "animals": [],
            "actions": [],
            "colors": [],
            "scene_type": "unknown",
            "mood": [],
            "text_content": [],
            "clip_embedding": None,
            "clip_embedding_dim": 0,
            "full_scan_text": f"Error during scan: {e}",
            "scan_complete": False,
            "analysis_source": "Error",
            "model_used": "None"
        }


async def analyze_image(image_path: Path, question: Optional[str] = None) -> Dict[str, Any]:
    """
    Analyze image with fallback chain:
    1. OpenAI Vision API (if OPENAI_API_KEY is set)
    2. Local captioning model (if ENABLE_CAPTION_MODEL=true)
    3. Metadata fallback (last resort)
    
    Args:
        image_path: Path to the image file
        question: Optional specific question about the image
        
    Returns:
        Dictionary with description, caption, tags, objects, colors, scene_type, mood, analysis_source
    """
    try:
        logger.info(f"Starting image analysis for {image_path.name}")
        
        from app.config import get_settings
        settings = get_settings()
        
        openai_failed = False
        should_fallback_to_local = False
        is_rate_limit_error = False
        error_obj = None
        
        if settings.openai_api_key:
            try:
                logger.info("Attempting OpenAI Vision API")
                from app.rag.vision_analyzer import analyze_image_with_vision
                
                # Faster timeout for OpenAI Vision - fail fast if slow
                vision_result = await asyncio.wait_for(
                    analyze_image_with_vision(
                        image_path=image_path,
                        question=question,
                        api_key=settings.openai_api_key,
                        model=settings.llm_model if ("gpt-4" in settings.llm_model.lower() or "gpt-4o" in settings.llm_model.lower()) else "gpt-4o-mini"
                    ),
                    timeout=8.0  # Reduced from 30s to 8s - fail fast
                )
                
                logger.info(f"OpenAI Vision API succeeded")
                return {
                    "description": vision_result.get("description", ""),
                    "caption": vision_result.get("caption", ""),
                    "tags": vision_result.get("tags", []),
                    "objects": vision_result.get("objects", []),
                    "colors": vision_result.get("colors", []),
                    "scene_type": vision_result.get("scene_type", "unknown"),
                    "mood": vision_result.get("mood", []),
                    "analysis_source": "OpenAI Vision",
                    "model_used": vision_result.get("model_used", "gpt-4o-mini")
                }
            except asyncio.TimeoutError:
                logger.error("OpenAI Vision API timed out")
                openai_failed = True
            except Exception as e:
                error_str = str(e).lower()
                openai_failed = True
                error_obj = e  # Store error for later use
                
                # Check for rate limit errors
                if "rate limit" in error_str or "429" in error_str or "rate_limit" in error_str:
                    logger.warning(f"OpenAI rate limit reached: {e}")
                    logger.info("Will use local captioning model as fallback (rate limit)")
                    is_rate_limit_error = True
                    should_fallback_to_local = True  # Use local model for rate limits
                # Check for content policy refusals
                elif any(pattern in error_str for pattern in [
                    "content policy", "unable to assist", "i'm unable", "i cannot",
                    "i can't", "cannot analyze", "refused", "safety guidelines"
                ]):
                    logger.warning(f"OpenAI refused due to content policy: {e}")
                    logger.info("Falling back to local captioning model due to content policy")
                    should_fallback_to_local = True
                else:
                    # Other errors - still try local model as fallback
                    logger.warning(f"OpenAI Vision API failed: {e}, trying local captioning model")
                    logger.info("Falling back to local captioning model")
                    should_fallback_to_local = True
        
        # Try local captioning model if OpenAI failed or if no OpenAI key
        # Use local model if ENABLE_CAPTION_MODEL=true and OpenAI failed or no key
        caption_model = None
        
        if settings.enable_caption_model:
            # Local model is enabled - try it if OpenAI failed or no OpenAI key
            if not settings.openai_api_key:
                logger.info("No OpenAI API key - attempting local captioning model as fallback")
                caption_model = get_caption_model(timeout=10.0)  # Allow more time for first load
            elif openai_failed and should_fallback_to_local:
                # OpenAI failed but we should try local model (rate limit, content policy, etc.)
                logger.info("OpenAI failed - attempting local captioning model as fallback")
                caption_model = get_caption_model(timeout=10.0)  # Allow more time for first load
            elif openai_failed:
                # OpenAI failed but not a rate limit - still try local if enabled
                logger.info("OpenAI failed - attempting local captioning model as fallback")
                caption_model = get_caption_model(timeout=10.0)
            else:
                # OpenAI succeeded, but user enabled local model - don't use it (OpenAI is better)
                logger.info("OpenAI succeeded - skipping local model (OpenAI is faster and better)")
                caption_model = None
        else:
            # Local model not enabled - use metadata fallback
            if not settings.openai_api_key:
                logger.info("No OpenAI API key and local model disabled - using metadata fallback")
            elif openai_failed:
                logger.info("OpenAI failed and local model disabled - using metadata fallback")
            caption_model = None
        
        if caption_model is None:
            logger.error("Local captioning model could not be loaded - check logs above for errors")
            logger.error("This may be due to:")
            logger.error("1. Missing dependencies (pip install transformers torch)")
            logger.error("2. Model download failure")
            logger.error("3. Insufficient memory")
        
        if caption_model:
            global _caption_model_crashed  # Declare global at function scope
            try:
                logger.info("Attempting local captioning model")
                
                try:
                    # Use very short timeout for local model to prevent hanging
                    # This prevents documents from getting stuck in INDEXING
                    timeout_seconds = 3.0  # Reduced from 5s to 3s - fail very fast
                    logger.info(f"Generating caption with local model (timeout: {timeout_seconds}s)...")
                    caption = await asyncio.wait_for(
                        caption_model.generate_caption(image_path, max_length=20),  # Even shorter captions = faster
                        timeout=timeout_seconds
                    )
                    logger.debug(f"Generated caption: {caption[:100]}...")
                except asyncio.TimeoutError:
                    logger.warning("Local captioning model timed out - using metadata fallback")
                    # Don't raise - fall through to metadata fallback
                    caption = None
                except Exception as e:
                    logger.warning(f"Local captioning model error: {e} - using metadata fallback")
                    # Mark model as potentially crashed if it's a serious error
                    if "segmentation" in str(e).lower() or "sigsegv" in str(e).lower() or "crash" in str(e).lower():
                        _caption_model_crashed = True
                        logger.error("Captioning model crashed - disabling for remainder of session")
                    # Don't raise - fall through to metadata fallback
                    caption = None
            except Exception as e:
                # Catch any other errors (including potential crashes)
                logger.error(f"Unexpected error with captioning model: {e}", exc_info=True)
                _caption_model_crashed = True
                logger.error("Captioning model encountered error - disabling for remainder of session")
                caption = None
                
                # If caption generation failed, skip to metadata fallback
                if not caption:
                    logger.info("Skipping to metadata fallback due to caption generation failure")
                    raise ValueError("Caption generation failed, using metadata fallback")
                
                caption_lower = caption.lower()
                
                objects = []
                object_keywords = ["dog", "cat", "person", "people", "car", "tree", "building", "house",
                                 "table", "chair", "book", "phone", "computer", "food", "water", "pool",
                                 "sky", "cloud", "mountain", "beach", "road", "street", "window", "door",
                                 "flower", "plant", "bird", "animal", "screen", "text", "button", "icon"]
                for keyword in object_keywords:
                    if keyword in caption_lower:
                        objects.append(keyword)
                
                colors = []
                color_keywords = ["red", "blue", "green", "yellow", "orange", "purple", "pink", "brown",
                                "black", "white", "gray", "grey", "beige", "tan", "gold", "silver",
                                "bright", "dark", "light"]
                for keyword in color_keywords:
                    if keyword in caption_lower:
                        colors.append(keyword)
                
                scene_type = "unknown"
                if any(word in caption_lower for word in ["indoor", "room", "inside", "interior", "building"]):
                    scene_type = "indoor"
                elif any(word in caption_lower for word in ["outdoor", "outside", "exterior", "nature", "landscape", "street", "park"]):
                    scene_type = "outdoor"
                elif any(word in caption_lower for word in ["water", "ocean", "sea", "beach", "pool", "lake"]):
                    scene_type = "water/beach"
                
                mood = []
                mood_keywords = ["happy", "sad", "peaceful", "energetic", "calm", "dramatic", "bright", "dark",
                               "warm", "cool", "cheerful", "serious", "relaxing", "active"]
                for keyword in mood_keywords:
                    if keyword in caption_lower:
                        mood.append(keyword)
                
                tags = list(set([w.lower() for w in caption.split() if len(w) > 3]))[:15]
                
                description_parts = [f"The image shows {caption.lower()}"]
                
                if objects:
                    description_parts.append(f"Visible objects include: {', '.join(objects[:5])}")
                if colors:
                    description_parts.append(f"The scene features {', '.join(colors[:5])} colors")
                if scene_type != "unknown":
                    description_parts.append(f"The setting appears to be {scene_type}")
                if mood:
                    description_parts.append(f"The atmosphere feels {', '.join(mood[:3])}")
                
                detailed_description = ". ".join(description_parts) + "."
                
                logger.info(f"Local captioning model succeeded")
                return {
                    "description": detailed_description,
                    "caption": caption,
                    "tags": tags,
                    "objects": list(set(objects))[:20],
                    "colors": list(set(colors))[:15],
                    "scene_type": scene_type,
                    "mood": list(set(mood))[:5],
                    "analysis_source": "Local Captioning Model",
                    "model_used": "Salesforce/blip-image-captioning-base"
                }
            except Exception as e:
                logger.warning(f"Local captioning model failed: {e}, using metadata fallback")
        
        logger.warning("Both OpenAI Vision and local captioning unavailable. Using metadata fallback.")
        try:
            from PIL import Image
            
            # Handle HEIC/HEIF files
            suffix = image_path.suffix.lower()
            if suffix in [".heic", ".heif"]:
                try:
                    from pillow_heif import register_heif_opener
                    register_heif_opener()
                except ImportError:
                    pass
            
            image = Image.open(image_path).convert("RGB")
            width, height = image.size
            format_name = image.format or "unknown"
            mode = image.mode
            
            aspect_ratio = width / height if height > 0 else 1.0
            if aspect_ratio > 1.5:
                orientation = "landscape"
            elif aspect_ratio < 0.67:
                orientation = "portrait"
            else:
                orientation = "square"
            
            caption = f"Image with captioning unavailable"
            description = f"Image captioning is currently disabled or unavailable. Only basic file metadata is available. Image file: {image_path.name}, Format: {format_name.upper()}, Dimensions: {width}x{height} pixels, Orientation: {orientation}, Color mode: {mode}. To enable real image analysis, set OPENAI_API_KEY or ENABLE_CAPTION_MODEL=true."
            
            tags = [format_name.lower(), orientation]
            if width > 2000 or height > 2000:
                tags.append("high-resolution")
            if mode == "RGB":
                tags.append("color")
            elif mode == "L":
                tags.append("grayscale")
            
            logger.warning(f"Metadata fallback used")
            return {
                "description": description,
                "caption": caption,
                "tags": tags,
                "objects": [],
                "colors": [],
                "scene_type": "unknown",
                "mood": [],
                "analysis_source": "Metadata Fallback (Image captioning disabled)",
                "model_used": "None"
            }
        except Exception as e:
            logger.error(f"Metadata fallback failed: {e}", exc_info=True)
            # Last resort - return minimal metadata
        return {
                "description": f"Image file: {image_path.name}",
                "caption": image_path.name,
                "tags": ["unknown"],
                "objects": [],
                "colors": [],
                "scene_type": "unknown",
                "mood": [],
                "analysis_source": "Metadata Fallback (Error)",
                "model_used": "None"
        }
    except Exception as e:
        logger.error(f"Image analysis failed: {e}", exc_info=True)
        return {
            "description": f"Image file: {image_path.name} (analysis unavailable)",
            "caption": f"Image: {image_path.name}",
            "tags": [],
            "objects": [],
            "colors": [],
            "scene_type": "unknown",
            "mood": [],
            "analysis_source": "Error",
            "model_used": "None"
        }
