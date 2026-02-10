from PIL import Image, ImageEnhance, ImageOps
import io

class ImageProcessor:
    @staticmethod
    def process_image(image_bytes: bytes) -> bytes:
        """
        Process the image for better OCR results.
        1. Open image from bytes.
        2. Convert to grayscale.
        3. Simple enhancement (optional: contrast, sharpen).
        4. Resize if too large (optional optimization).
        5. Return bytes.
        """
        try:
            image = Image.open(io.BytesIO(image_bytes))
            
            # RGB
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 灰度图
            gray_image = ImageOps.grayscale(image)
            
            # 增加白边
            padding = 50
            enhanced_image = ImageOps.expand(gray_image, border=padding, fill='white')
            
            # 增强对比度
            enhancer = ImageEnhance.Contrast(enhanced_image)
            enhanced_image = enhancer.enhance(1.5)
            
            # 限制图片大小
            max_dimension = 4096
            if max(enhanced_image.size) > max_dimension:
                enhanced_image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
                
            # 导出bytes
            output = io.BytesIO()
            enhanced_image.save(output, format='JPEG', quality=95)
            
            return output.getvalue()
            
        except Exception as e:
            print(f"Image processing failed: {e}. Returning original bytes.")
            return image_bytes

image_processor = ImageProcessor()
