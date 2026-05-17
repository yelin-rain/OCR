from PIL import Image, ImageEnhance, ImageOps
import io

class ImageProcessor:
  PADDING = 50
  MAX_DIMENSION = 4096

  @staticmethod
  def map_location_to_original(
      location: list[list[float]],
      original_width: int,
      original_height: int,
      processed_width: int,
      processed_height: int,
  ) -> list[list[float]]:
      """
      OCR 在预处理图（灰度 + 白边 + 可选缩放）上推理，将检测框坐标映射回原图尺寸。
      """
      if not location or original_width <= 0 or original_height <= 0:
          return location

      padding = ImageProcessor.PADDING
      expanded_w = original_width + 2 * padding
      expanded_h = original_height + 2 * padding
      scale = min(1.0, ImageProcessor.MAX_DIMENSION / max(expanded_w, expanded_h))

      mapped: list[list[float]] = []
      for x, y in location:
          # 预处理图 -> 扩边后尺寸
          x_exp = float(x) / scale
          y_exp = float(y) / scale
          # 扩边后 -> 原图
          mapped.append([max(0.0, x_exp - padding), max(0.0, y_exp - padding)])
      return mapped

  @staticmethod
  def map_words_result_to_original(
      words_result: list,
      original_width: int,
      original_height: int,
      processed_width: int,
      processed_height: int,
  ) -> None:
      for item in words_result:
          if not isinstance(item, dict):
              continue
          loc = item.get("location")
          if isinstance(loc, list) and loc:
              item["location"] = ImageProcessor.map_location_to_original(
                  loc,
                  original_width,
                  original_height,
                  processed_width,
                  processed_height,
              )

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
            padding = ImageProcessor.PADDING
            enhanced_image = ImageOps.expand(gray_image, border=padding, fill='white')
            
            # 增强对比度
            enhancer = ImageEnhance.Contrast(enhanced_image)
            enhanced_image = enhancer.enhance(1.5)
            
            # 限制图片大小
            if max(enhanced_image.size) > ImageProcessor.MAX_DIMENSION:
                enhanced_image.thumbnail(
                    (ImageProcessor.MAX_DIMENSION, ImageProcessor.MAX_DIMENSION),
                    Image.Resampling.LANCZOS,
                )
                
            # 导出bytes
            output = io.BytesIO()
            enhanced_image.save(output, format='JPEG', quality=95)
            
            return output.getvalue()
            
        except Exception as e:
            print(f"Image processing failed: {e}. Returning original bytes.")
            return image_bytes

image_processor = ImageProcessor()
