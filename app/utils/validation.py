"""Validation utilities."""
import re
import logging
from pathlib import Path
from typing import List
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


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
    logger.debug(f"Validating file size: {file_size} bytes (max: {settings.max_file_size_mb}MB)")
    max_size_bytes = settings.max_file_size_mb * 1024 * 1024
    if file_size > max_size_bytes:
        error_msg = f"File size ({file_size / (1024*1024):.2f}MB) exceeds maximum allowed size of {settings.max_file_size_mb}MB"
        logger.warning(f"File size validation failed: {error_msg}")
        return False, error_msg
    
    if file_size == 0:
        error_msg = "File is empty (0 bytes)"
        logger.warning(f"File size validation failed: {error_msg}")
        return False, error_msg
    
    logger.debug(f"File size validation passed: {file_size} bytes")
    return True, ""


def validate_file_extension(filename: str) -> tuple[bool, str]:
    """
    Validate file extension.
    
    Args:
        filename: Name of the file
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    logger.debug(f"Validating file extension for: {filename}")
    if not filename:
        error_msg = "Filename is required"
        logger.warning(f"File extension validation failed: {error_msg}")
        return False, error_msg
    
    file_ext = Path(filename).suffix.lower()
    allowed_extensions = [ext.strip().lower() for ext in settings.allowed_file_extensions.split(",")]
    
    logger.debug(f"File extension: '{file_ext}', Allowed extensions: {allowed_extensions}")
    
    if file_ext not in allowed_extensions:
        error_msg = f"File extension '{file_ext}' is not allowed. Allowed types: {', '.join(sorted(allowed_extensions))}"
        logger.warning(f"File extension validation failed for '{filename}': {error_msg}")
        return False, error_msg
    
    logger.debug(f"File extension validation passed: {file_ext}")
    return True, ""


def validate_mime_type(content_type: str, filename: str) -> tuple[bool, str]:
    """
    Validate MIME type against file extension.
    
    BULLETPROOF: Never rejects files due to MIME type mismatch.
    Only logs warnings and allows the file to proceed.
    
    Args:
        content_type: MIME type from upload
        filename: Name of the file
    
    Returns:
        Tuple of (is_valid, error_message) - Always returns (True, "") for valid extensions
    """
    logger.debug(f"Validating MIME type for '{filename}': content_type='{content_type}'")
    
    if not content_type:
        logger.warning(f"MIME type validation: No content_type provided for '{filename}' - allowing file (extension-based validation)")
        return True, ""
    
    # MIME type mapping (comprehensive)
    mime_map = {
        ".pdf": ["application/pdf"],
        ".txt": ["text/plain", "text/plain; charset=utf-8"],
        ".md": ["text/markdown", "text/x-markdown", "text/plain"],
        ".markdown": ["text/markdown", "text/x-markdown", "text/plain"],
        # Image MIME types
        ".jpg": ["image/jpeg", "image/jpg", "image/x-jpeg"],
        ".jpeg": ["image/jpeg", "image/jpg", "image/x-jpeg"],
        ".png": ["image/png", "image/x-png"],
        ".gif": ["image/gif", "image/x-gif"],
        ".webp": ["image/webp"],
        ".bmp": ["image/bmp", "image/x-ms-bmp", "image/x-bmp"],
        ".heic": ["image/heic", "image/heif"],
        ".heif": ["image/heic", "image/heif"],
        ".tiff": ["image/tiff", "image/tif"],
        ".tif": ["image/tiff", "image/tif"],
        ".svg": ["image/svg+xml", "image/svg"],
        ".ico": ["image/x-icon", "image/vnd.microsoft.icon"],
        # New file types
        ".json": ["application/json", "text/json", "text/plain"],
        ".csv": ["text/csv", "application/csv", "text/plain", "application/vnd.ms-excel"],
        ".docx": ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/zip"],
        ".pptx": ["application/vnd.openxmlformats-officedocument.presentationml.presentation", "application/zip"],
    }
    
    file_ext = Path(filename).suffix.lower()
    allowed_mimes = mime_map.get(file_ext, [])
    
    # If no MIME mapping exists, just validate extension and allow
    if not allowed_mimes:
        logger.debug(f"No MIME mapping for extension '{file_ext}' - validating extension only")
        ext_valid, ext_error = validate_file_extension(filename)
        if not ext_valid:
            return False, ext_error
        # Extension is valid, allow regardless of MIME type
        logger.info(f"MIME type validation: No mapping for '{file_ext}' but extension is allowed - accepting file")
        return True, ""
    
    # For images, be very lenient - any image/* MIME type is acceptable
    image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".heic", ".heif", ".tiff", ".tif", ".svg", ".ico"]
    if file_ext in image_extensions:
        if content_type.startswith("image/"):
            logger.debug(f"MIME type validation passed: '{content_type}' matches image extension '{file_ext}'")
            return True, ""
        else:
            # MIME mismatch for image, but allow anyway (browsers sometimes send wrong MIME)
            logger.warning(f"MIME type mismatch for image '{filename}': expected image/*, got '{content_type}' - allowing file anyway (extension-based validation)")
            return True, ""
    
    # For Office documents, be lenient - they're often sent as application/zip
    office_extensions = [".docx", ".pptx"]
    if file_ext in office_extensions:
        if content_type in allowed_mimes or content_type == "application/zip" or content_type.startswith("application/vnd"):
            logger.debug(f"MIME type validation passed: '{content_type}' matches office extension '{file_ext}'")
            return True, ""
        else:
            logger.warning(f"MIME type mismatch for office document '{filename}': expected {allowed_mimes}, got '{content_type}' - allowing file anyway (extension-based validation)")
            return True, ""
    
    # For text files, be lenient
    text_extensions = [".txt", ".md", ".markdown", ".json", ".csv"]
    if file_ext in text_extensions:
        if content_type in allowed_mimes or content_type.startswith("text/"):
            logger.debug(f"MIME type validation passed: '{content_type}' matches text extension '{file_ext}'")
            return True, ""
        else:
            logger.warning(f"MIME type mismatch for text file '{filename}': expected {allowed_mimes}, got '{content_type}' - allowing file anyway (extension-based validation)")
            return True, ""
    
    # Check if MIME type matches
    if content_type in allowed_mimes:
        logger.debug(f"MIME type validation passed: '{content_type}' matches extension '{file_ext}'")
        return True, ""
    
    # MIME type doesn't match, but extension is valid - allow anyway (never reject)
    logger.warning(f"MIME type mismatch for '{filename}': extension '{file_ext}' expects {allowed_mimes}, got '{content_type}' - allowing file anyway (extension-based validation)")
    return True, ""

