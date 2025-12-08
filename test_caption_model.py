#!/usr/bin/env python3
"""
Test script to verify local captioning model can be loaded.
"""
import sys
from pathlib import Path

print("Testing local captioning model...")
print("=" * 50)

# Test 1: Check dependencies
print("\n1. Checking dependencies...")
try:
    import transformers
    print(f"   ✓ transformers {transformers.__version__}")
except ImportError as e:
    print(f"   ✗ transformers not installed: {e}")
    print("   Install with: pip install transformers")
    sys.exit(1)

try:
    import torch
    print(f"   ✓ torch {torch.__version__}")
except ImportError as e:
    print(f"   ✗ torch not installed: {e}")
    print("   Install with: pip install torch")
    sys.exit(1)

# Test 2: Try to load the model
print("\n2. Testing model loading...")
try:
    from app.rag.image_analyzer import get_caption_model
    
    print("   Attempting to load model (this may take 30-60 seconds first time)...")
    model = get_caption_model(force=True)
    
    if model is None:
        print("   ✗ Model returned None - check logs above")
        sys.exit(1)
    
    print("   ✓ Model loaded successfully!")
    
    # Test 3: Try to generate a caption (if you have a test image)
    print("\n3. Model is ready to use!")
    print("   The model should now work automatically when OpenAI refuses.")
    
except Exception as e:
    print(f"   ✗ Failed to load model: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 50)
print("All tests passed! The local captioning model should work now.")
print("\nTo use it:")
print("1. Make sure your backend server is restarted")
print("2. Upload an image")
print("3. If OpenAI refuses, the local model will automatically be used")

