# Upload Limits and Timeouts

## File Size Limits

- **Maximum file size**: 50 MB (configurable via `MAX_FILE_SIZE_MB` environment variable)
- **Minimum file size**: 1 byte (empty files are rejected)

## Supported File Formats

### Documents
- `.pdf` - PDF documents
- `.txt` - Plain text files
- `.md`, `.markdown` - Markdown files
- `.json` - JSON files
- `.csv` - CSV files
- `.docx` - Microsoft Word documents
- `.pptx` - Microsoft PowerPoint presentations

### Images
- `.jpg`, `.jpeg` - JPEG images
- `.png` - PNG images
- `.gif` - GIF images
- `.webp` - WebP images
- `.bmp` - Bitmap images
- `.heic`, `.heif` - HEIC/HEIF images
- `.tiff`, `.tif` - TIFF images
- `.svg` - SVG vector images
- `.ico` - Icon files

## Processing Timeouts

### Document Processing
- **Processing timeout**: 90 seconds
  - Includes: text extraction, chunking, embedding generation, vector store indexing
  - Large files (>10MB) may take longer
  - Complex images with analysis may take up to 90 seconds

### Image Analysis
- **Image analysis timeout**: 35 seconds
  - Includes: caption generation, CLIP embeddings, metadata extraction
  - Large images may take longer

### Request Timeouts
- **Upload endpoint timeout**: 100 seconds (middleware level)
  - This includes the full request processing time
  - If exceeded, the request is cancelled but document may still be processing

## Recommendations

1. **For large files (>10MB)**:
   - Consider splitting into smaller files
   - PDFs: Split into separate pages
   - Images: Compress before uploading

2. **For complex images**:
   - Processing may take 30-90 seconds
   - Be patient and refresh the page to check status
   - If timeout occurs, the document will be marked as FAILED

3. **If you get a timeout**:
   - Check the document status on the Documents page
   - If status is still INDEXING after 5 minutes, it will be automatically marked as FAILED
   - Try uploading a smaller version of the file

## Configuration

You can adjust limits by setting environment variables:

```bash
# Maximum file size in MB (default: 50)
MAX_FILE_SIZE_MB=100

# Allowed file extensions (comma-separated)
ALLOWED_FILE_EXTENSIONS=".pdf,.txt,.md,.jpg,.png"
```

## Error Messages

- **"File size exceeds maximum"**: File is larger than 50MB (or configured limit)
- **"File extension not allowed"**: File type is not in the supported list
- **"Processing timeout"**: Document took longer than 90 seconds to process
- **"Request timeout"**: The HTTP request exceeded 100 seconds
