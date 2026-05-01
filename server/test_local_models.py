import os
import sys
import numpy as np
from PIL import Image
import io

# Add server to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.providers.local_ocr_provider import local_ocr_provider
import asyncio

async def test_inference():
    print("Testing with LocalOCRProvider...")
    
    try:
        # Create a dummy image
        img = np.zeros((640, 640, 3), dtype=np.uint8)
        img_pil = Image.fromarray(img)
        img_byte_arr = io.BytesIO()
        img_pil.save(img_byte_arr, format='PNG')
        image_bytes = img_byte_arr.getvalue()
        
        # Run inference
        print("Running inference via provider...")
        result = await local_ocr_provider.ocr_general_basic(image_bytes)
        print(f"Inference successful! Full text length: {len(result['full_text'])}")
        
    except Exception as e:
        print(f"Inference failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_inference())
