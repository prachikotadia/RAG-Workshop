"""
Document parsers for extracting text from various file types.

Supports PDF, TXT, MD, and image files (JPG, PNG, GIF, etc.) with metadata extraction.
"""
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def extract_text_from_pdf(path: Path) -> Tuple[str, Dict[str, Any]]:
    """
    Extract text from a PDF file and return (full_text, metadata).
    
    Args:
        path: Path to the PDF file
    
    Returns:
        Tuple of (full_text, metadata_dict)
        Metadata includes: num_pages, source_path, file_type
    """
    try:
        import PyPDF2
    except ImportError:
        logger.error("PyPDF2 not installed. Install with: pip install PyPDF2")
        raise ImportError("PyPDF2 not installed. Install with: pip install PyPDF2")
    
    try:
        text = ""
        num_pages = 0
        with open(path, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)
            num_pages = len(pdf_reader.pages)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        
        metadata = {
            "num_pages": num_pages,
            "source_path": str(path),
            "file_type": "pdf"
        }
        
        return text.strip(), metadata
    except Exception as e:
        logger.error(f"Error parsing PDF {path}: {e}")
        raise ValueError(f"Failed to parse PDF: {str(e)}")


def extract_text_from_text_file(path: Path) -> Tuple[str, Dict[str, Any]]:
    """
    Extract text from a plain text or markdown file and return (full_text, metadata).
    
    Args:
        path: Path to the text/markdown file
    
    Returns:
        Tuple of (full_text, metadata_dict)
        Metadata includes: source_path, file_type
    """
    try:
        with open(path, "r", encoding="utf-8") as file:
            text = file.read()
        
        # Determine file type
        suffix = path.suffix.lower()
        file_type = "markdown" if suffix in [".md", ".markdown"] else "text"
        
        metadata = {
            "source_path": str(path),
            "file_type": file_type
        }
        
        return text, metadata
    except Exception as e:
        logger.error(f"Error parsing text file {path}: {e}")
        raise ValueError(f"Failed to parse text file: {str(e)}")


def extract_text_from_image(path: Path) -> Tuple[str, Dict[str, Any]]:
    """
    Extract metadata from an image file.

    For images, we store metadata (dimensions, format, etc.) as text.
    The actual image analysis will be done by CLIP/BLIP-2 when needed.
    
    Supports: JPG, JPEG, PNG, GIF, WEBP, BMP, HEIC, HEIF, TIFF, TIF, SVG, ICO

    Args:
        path: Path to the image file

    Returns:
        Tuple of (description_text, metadata_dict)
        Description text includes basic image info
        Metadata includes: width, height, format, file_size
    """
    try:
        from PIL import Image
        
        # For HEIC/HEIF files, try to load pillow-heif plugin
        suffix = path.suffix.lower()
        if suffix in [".heic", ".heif"]:
            try:
                from pillow_heif import register_heif_opener
                register_heif_opener()
                logger.debug(f"Registered HEIC/HEIF opener for {path}")
            except ImportError:
                logger.warning(
                    "pillow-heif not installed. HEIC/HEIF support may be limited. "
                    "Install with: pip install pillow-heif"
                )
        
        # Open and process image
        with Image.open(path) as img:
            # Convert to RGB if necessary (for formats like RGBA, P, etc.)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            
            width, height = img.size
            format_name = img.format or "unknown"
            mode = img.mode
            
            # Get file size
            file_size = path.stat().st_size
            
            # Create a basic description
            description = f"Image file: {path.name}\nDimensions: {width}x{height} pixels\nFormat: {format_name}\nColor mode: {mode}\nFile size: {file_size} bytes"
            
            metadata = {
                "width": width,
                "height": height,
                "format": format_name,
                "mode": mode,
                "file_size": file_size,
                "source_path": str(path),
                "file_type": "image"
            }
            
            return description, metadata
            
    except ImportError:
        logger.error("Pillow (PIL) not installed. Install with: pip install pillow")
        raise ImportError("Pillow not installed. Install with: pip install pillow")
    except Exception as e:
        logger.error(f"Error processing image {path}: {e}")
        raise ValueError(f"Failed to process image: {str(e)}")


def extract_text_from_file(path: Path) -> Tuple[str, Dict[str, Any]]:
    """
    Detect file type by suffix and route to the appropriate helper.

    Supported formats:
    - Documents: .pdf, .txt, .md, .markdown
    - Images: .jpg, .jpeg, .png, .gif, .webp, .bmp, .heic, .heif, .tiff, .tif, .svg, .ico
    
    Images are processed with CLIP (for embeddings) and BLIP-2 (for captioning).

    Args:
        path: Path to the file

    Returns:
        Tuple of (full_text, metadata_dict)

    Raises:
        ValueError: For unsupported file types
    """
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return extract_text_from_pdf(path)
    elif suffix in [".txt", ".text"]:
        return extract_text_from_text_file(path)
    elif suffix in [".md", ".markdown"]:
        return extract_text_from_text_file(path)
    elif suffix in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".heic", ".heif", ".tiff", ".tif", ".svg", ".ico"]:
        return extract_text_from_image(path)
    else:
        raise ValueError(
            f"Unsupported file type: {suffix}. "
            f"Supported: .pdf, .txt, .md, .jpg, .jpeg, .png, .gif, .webp, .bmp, .heic, .heif, .tiff, .tif, .svg, .ico"
        )

