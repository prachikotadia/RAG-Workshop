"""
CLIP-based image embeddings provider.

Provides image embeddings using CLIP model for multimodal RAG.
"""
from typing import List, Optional
import logging
from pathlib import Path
import numpy as np

logger = logging.getLogger(__name__)


class CLIPImageEmbeddingsProvider:
    """CLIP-based image embeddings provider."""
    
    def __init__(self, model_name: str = "openai/clip-vit-base-patch32", device: Optional[str] = None):
        """
        Initialize CLIP image embeddings provider.
        
        Args:
            model_name: HuggingFace model name for CLIP
            device: Device to run on ('cuda', 'cpu', or None for auto)
        """
        self.model_name = model_name
        self.device = device
        self._processor = None
        self._model = None
    
    def _get_model(self):
        """Lazy initialization of CLIP model."""
        if self._model is None:
            try:
                from transformers import CLIPProcessor, CLIPModel
                import torch
                
                # Auto-detect device if not specified
                if self.device is None:
                    self.device = "cuda" if torch.cuda.is_available() else "cpu"
                
                logger.info(f"Loading CLIP model: {self.model_name} on {self.device}")
                self._processor = CLIPProcessor.from_pretrained(self.model_name)
                self._model = CLIPModel.from_pretrained(self.model_name).to(self.device)
                self._model.eval()
                logger.info(f"CLIP model loaded successfully")
                
            except ImportError:
                raise ImportError(
                    "transformers and torch not installed. Install with: pip install transformers torch"
                )
        return self._processor, self._model
    
    async def embed_image(self, image_path: Path) -> List[float]:
        """
        Generate embedding for a single image.
        
        Supports all image formats: JPG, JPEG, PNG, GIF, WEBP, BMP, HEIC, HEIF, TIFF, TIF, SVG, ICO
        
        CRITICAL: Uses run_in_executor to prevent blocking the event loop.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            List of floats representing the image embedding vector
        """
        import asyncio
        from PIL import Image
        import torch
        
        processor, model = self._get_model()
        
        def _embed_sync():
            """Synchronous embedding generation (runs in thread pool to avoid blocking event loop)."""
            # Handle HEIC/HEIF files
            suffix = image_path.suffix.lower()
            if suffix in [".heic", ".heif"]:
                try:
                    from pillow_heif import register_heif_opener
                    register_heif_opener()
                except ImportError:
                    logger.warning(
                        "pillow-heif not installed. HEIC/HEIF support may be limited. "
                        "Install with: pip install pillow-heif"
                    )
            
            # Load and process image - convert to RGB for CLIP
            image = Image.open(image_path).convert("RGB")
            inputs = processor(images=image, return_tensors="pt").to(self.device)
            
            # Generate embedding
            with torch.no_grad():
                image_features = model.get_image_features(**inputs)
                embedding = image_features[0].cpu().numpy().tolist()
            
            return embedding
        
        try:
            loop = asyncio.get_event_loop()
            # CRITICAL: Run synchronous PyTorch operations in thread pool to avoid blocking event loop
            return await loop.run_in_executor(None, _embed_sync)
        except Exception as e:
            logger.error(f"Error embedding image {image_path}: {e}", exc_info=True)
            raise
    
    async def embed_images(self, image_paths: List[Path]) -> List[List[float]]:
        """
        Generate embeddings for multiple images.
        
        Args:
            image_paths: List of paths to image files
            
        Returns:
            List of embedding vectors (each is a list of floats)
        """
        embeddings = []
        for image_path in image_paths:
            embedding = await self.embed_image(image_path)
            embeddings.append(embedding)
        return embeddings

