import os

# IMPORTANT: set Paddle flags before importing paddle/paddleocr.
# In Windows + PaddleOCR3, oneDNN/PIR can trigger runtime NotImplementedError.
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["FLAGS_enable_onednn"] = "0"
os.environ["FLAGS_use_mkldnn"] = "0"

import sys
import numpy as np
from PIL import Image
import io
import shutil
import tempfile
import paddle
from paddleocr import PaddleOCR
from app.core.config import settings
from typing import Dict, Any

class LocalOCRProvider:
    def __init__(self):
        # PaddlePaddle C++ engine has issues with Chinese paths on Windows.
        # We'll copy the models to a temp ASCII path if the original path contains non-ASCII characters.
        self.det_dir = self._prepare_model_dir(settings.DET_MODEL_DIR, "det") if settings.USE_LOCAL_MODELS else None
        self.rec_dir = self._prepare_model_dir(settings.REC_MODEL_DIR, "rec") if settings.USE_LOCAL_MODELS else None

        if settings.USE_LOCAL_MODELS:
            print(f"Attempting to load local models from: {self.det_dir} and {self.rec_dir}")
        else:
            print("Using official high-accuracy models (PP-OCRv5). To use local models, set USE_LOCAL_MODELS=True in config.py")

        try:
            # Set internal paddle flags if possible
            try:
                import paddle
                # Force old executor
                paddle.set_flags({
                    "FLAGS_enable_pir_api": 0,
                    "FLAGS_enable_onednn": 0
                })
            except:
                pass

            # Initialize PaddleOCR with minimal arguments for maximum compatibility
            # Force PP-OCRv4 to avoid unstable PIR paths in 3.0
            if not self.det_dir:
                print("Initializing PaddleOCR with official PP-OCRv4 models...")
                self.ocr = PaddleOCR(
                    ocr_version='PP-OCRv4',
                    use_angle_cls=False,
                    lang='ch',
                    device='cpu',
                    engine='paddle',
                    enable_hpi=False,
                    enable_mkldnn=False,
                )
            else:
                print(f"Initializing PaddleOCR with local models from {self.det_dir}...")
                self.ocr = PaddleOCR(
                    text_detection_model_dir=self.det_dir,
                    text_recognition_model_dir=self.rec_dir,
                    use_textline_orientation=False,
                    lang='ch',
                    device='cpu',
                    engine='paddle',
                    enable_hpi=False,
                    enable_mkldnn=False,
                )
            print("PaddleOCR initialized successfully.")
        except Exception as e:
            print(f"Error initializing PaddleOCR: {e}")
            if self.det_dir or self.rec_dir:
                print("Falling back to official PP-OCRv4 models...")
                self.ocr = PaddleOCR(
                    ocr_version='PP-OCRv4',
                    lang='ch',
                    device='cpu',
                    engine='paddle',
                    enable_hpi=False,
                    enable_mkldnn=False,
                )
            else:
                raise e

    def _prepare_model_dir(self, original_dir: str, prefix: str) -> str:
        """
        Check if the path contains non-ASCII characters. If so, copy to a temp ASCII path.
        """
        if not original_dir or not os.path.exists(original_dir):
            return None
        
        # Check for non-ASCII
        try:
            original_dir.encode('ascii')
            # If successful, check for files
            if os.path.exists(os.path.join(original_dir, "inference.pdmodel")):
                return original_dir
            return None
        except UnicodeEncodeError:
            # Contains non-ASCII, copy to temp
            temp_root = os.path.join(tempfile.gettempdir(), "paddleocr_models")
            target_dir = os.path.join(temp_root, prefix)
            
            if not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)
            
            # Copy files if they exist and are different
            for item in os.listdir(original_dir):
                s = os.path.join(original_dir, item)
                d = os.path.join(target_dir, item)
                if os.path.isfile(s):
                    if not os.path.exists(d) or os.path.getsize(s) != os.path.getsize(d):
                        shutil.copy2(s, d)
            
            return target_dir if os.path.exists(os.path.join(target_dir, "inference.pdmodel")) else None

    def _extract_texts_from_result(self, result: Any) -> tuple[list[str], list[float]]:
        """
        Normalize PaddleOCR outputs from different versions:
        - PaddleOCR 3.x: [OCRResult], OCRResult contains rec_texts/rec_scores
        - PaddleOCR 2.x legacy: [[(box, (text, score)), ...]]
        """
        extracted_texts: list[str] = []
        rec_scores: list[float] = []

        if not result:
            return extracted_texts, rec_scores

        first_item = result[0]

        # PaddleOCR 3.x result object behaves like a dict
        if hasattr(first_item, "get"):
            texts = first_item.get("rec_texts", []) or []
            scores = first_item.get("rec_scores", []) or []
            extracted_texts = [str(t) for t in texts if t is not None and str(t).strip()]
            rec_scores = [float(s) for s in scores[: len(extracted_texts)]]
            # If score list length mismatches, pad with 1.0
            if len(rec_scores) < len(extracted_texts):
                rec_scores.extend([1.0] * (len(extracted_texts) - len(rec_scores)))
            return extracted_texts, rec_scores

        # PaddleOCR 2.x legacy structure
        if (
            isinstance(first_item, list)
            and len(first_item) > 0
            and isinstance(first_item[0], (list, tuple))
            and len(first_item[0]) > 1
        ):
            for line in first_item:
                try:
                    text = line[1][0]
                    score = line[1][1]
                    if text is not None and str(text).strip():
                        extracted_texts.append(str(text))
                        rec_scores.append(float(score))
                except (IndexError, TypeError, ValueError):
                    continue

        return extracted_texts, rec_scores

    async def ocr_general_basic(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Perform OCR using local PaddleOCR models.
        """
        try:
            # Convert bytes to numpy array for PaddleOCR
            image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            image_np = np.array(image)

            extracted_texts = []
            rec_scores = []

            try:
                if hasattr(self.ocr, "predict"):
                    print("Using PaddleOCR predict API...")
                    result = self.ocr.predict(image_np)
                else:
                    print("Using traditional PaddleOCR ocr API...")
                    result = self.ocr.ocr(image_np)

                extracted_texts, rec_scores = self._extract_texts_from_result(result)
            except Exception as e:
                print(f"Primary OCR API failed ({type(e).__name__}: {e}), trying alternative...")
                try:
                    if hasattr(self.ocr, "ocr"):
                        result = self.ocr.ocr(image_np)
                    else:
                        result = self.ocr.predict(image_np)
                    extracted_texts, rec_scores = self._extract_texts_from_result(result)
                except Exception as final_e:
                    print(f"Final OCR fallback failed: {final_e}")
                    raise final_e

            if not extracted_texts:
                print("OCR Result: No text found")
                return {"words_result": [], "full_text": ""}

            words_result = []
            for text, score in zip(extracted_texts, rec_scores):
                words_result.append({
                    "words": text,
                    "probability": float(score)
                })

            full_text = "\n".join(extracted_texts)
            print("--- OCR Result Start ---")
            print(full_text)
            print("--- OCR Result End ---")

            return {
                "words_result": words_result,
                "full_text": full_text
            }
        except Exception as e:
            print(f"Local OCR Error during inference: {e}")
            import traceback
            traceback.print_exc()
            raise e

local_ocr_provider = LocalOCRProvider()
