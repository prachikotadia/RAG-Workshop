"""Validation utilities."""
import re
from pathlib import Path
from typing import List
from app.config import get_settings

settings = get_settings()


def validate_password(password: str) -> tuple[bool, str]:
    """
    Validate password strength.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if len(password) > 128:
        return False, "Password must be less than 128 characters"
    
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit"
    
    return True, ""


def validate_file_size(file_size: int) -> tuple[bool, str]:
    """
    Validate file size.
    
    Args:
        file_size: File size in bytes
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    max_size_bytes = settings.max_file_size_mb * 1024 * 1024
    if file_size > max_size_bytes:
        return False, f"File size exceeds maximum allowed size of {settings.max_file_size_mb}MB"
    
    if file_size == 0:
        return False, "File is empty"
    
    return True, ""


def validate_file_extension(filename: str) -> tuple[bool, str]:
    """
    Validate file extension.
    
    Args:
        filename: Name of the file
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not filename:
        return False, "Filename is required"
    
    file_ext = Path(filename).suffix.lower()
    allowed_extensions = [ext.strip() for ext in settings.allowed_file_extensions.split(",")]
    
    if file_ext not in allowed_extensions:
        return False, f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
    
    return True, ""


def validate_mime_type(content_type: str, filename: str) -> tuple[bool, str]:
    """
    Validate MIME type against file extension.
    
    Args:
        content_type: MIME type from upload
        filename: Name of the file
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # MIME type mapping
    mime_map = {
        ".pdf": ["application/pdf"],
        ".txt": ["text/plain"],
        ".md": ["text/markdown", "text/x-markdown"],
        ".markdown": ["text/markdown", "text/x-markdown"],
        # Image MIME types
        ".jpg": ["image/jpeg", "image/jpg"],
        ".jpeg": ["image/jpeg", "image/jpg"],
        ".png": ["image/png"],
        ".gif": ["image/gif"],
        ".webp": ["image/webp"],
        ".bmp": ["image/bmp", "image/x-ms-bmp"],
        ".heic": ["image/heic", "image/heif"],
        ".heif": ["image/heic", "image/heif"],
        ".tiff": ["image/tiff", "image/tif"],
        ".tif": ["image/tiff", "image/tif"],
        ".svg": ["image/svg+xml"],
        ".ico": ["image/x-icon", "image/vnd.microsoft.icon"],
    }
    
    file_ext = Path(filename).suffix.lower()
    allowed_mimes = mime_map.get(file_ext, [])
    
    if not allowed_mimes:
        # If no MIME mapping, just check extension
        return validate_file_extension(filename)
    
    # For images, be more lenient - check if it's any image type
    if file_ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".heic", ".heif", ".tiff", ".tif", ".svg", ".ico"]:
        if content_type.startswith("image/"):
            return True, ""
    
    if content_type not in allowed_mimes:
        return False, f"MIME type '{content_type}' does not match file extension '{file_ext}'. Expected: {', '.join(allowed_mimes)}"
    
    return True, ""

