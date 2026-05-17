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
import subprocess
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
            self.det_dir, self.rec_dir = self._validate_local_model_pair(self.det_dir, self.rec_dir)

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

    def _validate_local_model_pair(self, det_dir: str | None, rec_dir: str | None) -> tuple[str | None, str | None]:
        if not det_dir or not rec_dir:
            print("Local model path is missing, fallback to official models.")
            return None, None

        det_ok, det_msg = self._validate_model_dir(det_dir)
        rec_ok, rec_msg = self._validate_model_dir(rec_dir)
        if det_ok and rec_ok:
            return det_dir, rec_dir

        print("Local models are not usable, fallback to official models.")
        if not det_ok:
            print(f"Detection model invalid: {det_msg}")
        if not rec_ok:
            print(f"Recognition model invalid: {rec_msg}")
        return None, None

    def _validate_model_dir(self, model_dir: str) -> tuple[bool, str]:
        pdmodel = os.path.join(model_dir, "inference.pdmodel")
        pdiparams = os.path.join(model_dir, "inference.pdiparams")
        if not os.path.exists(pdmodel):
            return False, f"missing file: {pdmodel}"
        if not os.path.exists(pdiparams):
            return False, f"missing file: {pdiparams}"

        # Run predictor creation in a child process to avoid crashing the main process.
        check_cmd = [
            sys.executable,
            "-c",
            (
                "import paddle.inference as I; "
                f"cfg=I.Config(r'{pdmodel}', r'{pdiparams}'); "
                "cfg.disable_gpu(); "
                "I.create_predictor(cfg); "
                "print('ok')"
            ),
        ]
        try:
            proc = subprocess.run(
                check_cmd,
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            if proc.returncode != 0:
                stderr = (proc.stderr or "").strip()
                return False, f"predictor create failed: {stderr or 'unknown error'}"
            return True, "ok"
        except Exception as e:
            return False, str(e)

    def _has_required_infer_files(self, model_dir: str) -> tuple[bool, str]:
        """Fast file-level guard: local model is usable only with pdmodel + pdiparams."""
        if not model_dir or not os.path.isdir(model_dir):
            return False, f"missing directory: {model_dir}"
        pdmodel = os.path.join(model_dir, "inference.pdmodel")
        pdiparams = os.path.join(model_dir, "inference.pdiparams")
        if not os.path.isfile(pdmodel):
            return False, f"missing file: {pdmodel}"
        if not os.path.isfile(pdiparams):
            info_file = os.path.join(model_dir, "inference.pdiparams.info")
            if os.path.isfile(info_file):
                return False, (
                    f"missing file: {pdiparams} (found {info_file}; "
                    "this is metadata only, official inference needs real .pdiparams)"
                )
            return False, f"missing file: {pdiparams}"
        return True, "ok"

    def _prepare_model_dir(self, original_dir: str, prefix: str) -> str:
        """
        Check if the path contains non-ASCII characters. If so, copy to a temp ASCII path.
        """
        if not original_dir or not os.path.exists(original_dir):
            return None
        
        # Check for non-ASCII
        try:
            original_dir.encode('ascii')
            # Fast reject when inference.pdiparams is missing (including only .info case)
            ok, reason = self._has_required_infer_files(original_dir)
            if ok:
                return original_dir
            print(f"Local {prefix} model not ready, will fallback to official: {reason}")
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
            
            ok, reason = self._has_required_infer_files(target_dir)
            if ok:
                return target_dir
            print(f"Local {prefix} model not ready after copy, will fallback to official: {reason}")
            return None

    def _normalize_box(self, box: Any) -> list[list[float]] | None:
        """支持 Paddle 2.x 多边形、Paddle 3.x numpy 多边形与 [x1,y1,x2,y2] 矩形。"""
        if box is None:
            return None
        try:
            if isinstance(box, np.ndarray):
                box = box.tolist()
        except Exception:
            pass

        if isinstance(box, (list, tuple)) and len(box) == 4:
            if all(isinstance(v, (int, float, np.integer, np.floating)) for v in box):
                x1, y1, x2, y2 = (float(box[0]), float(box[1]), float(box[2]), float(box[3]))
                return [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]

        if not isinstance(box, (list, tuple)):
            return None
        normalized: list[list[float]] = []
        for pt in box:
            if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                try:
                    normalized.append([float(pt[0]), float(pt[1])])
                except (TypeError, ValueError):
                    return None
        return normalized if normalized else None

    def _extract_lines_from_result(self, result: Any) -> list[Dict[str, Any]]:
        """
        Normalize PaddleOCR outputs from different versions:
        - PaddleOCR 3.x: [OCRResult], OCRResult contains rec_texts/rec_scores
        - PaddleOCR 2.x legacy: [[(box, (text, score)), ...]]
        """
        lines: list[Dict[str, Any]] = []

        if not result:
            return lines

        first_item = result[0]

        # PaddleOCR 3.x result object behaves like a dict
        if hasattr(first_item, "get"):
            texts = first_item.get("rec_texts", []) or []
            scores = first_item.get("rec_scores", []) or []
            # In PaddleOCR 3.x, detection polygons are commonly exposed as rec_polys/dt_polys.
            polys = (
                first_item.get("rec_polys")
                or first_item.get("dt_polys")
                or []
            )
            rec_boxes = first_item.get("rec_boxes")
            for idx, text_raw in enumerate(texts):
                text = str(text_raw).strip() if text_raw is not None else ""
                if not text:
                    continue
                score = 1.0
                if idx < len(scores):
                    try:
                        score = float(scores[idx])
                    except (TypeError, ValueError):
                        score = 1.0
                item: Dict[str, Any] = {"words": text, "probability": score}
                box = None
                if idx < len(polys):
                    box = self._normalize_box(polys[idx])
                if not box and rec_boxes is not None:
                    try:
                        if len(rec_boxes) > idx:
                            box = self._normalize_box(rec_boxes[idx])
                    except (TypeError, IndexError):
                        pass
                if box:
                    item["location"] = box
                lines.append(item)
            return lines

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
                        item: Dict[str, Any] = {
                            "words": str(text),
                            "probability": float(score),
                        }
                        box = self._normalize_box(line[0])
                        if box:
                            item["location"] = box
                        lines.append(item)
                except (IndexError, TypeError, ValueError):
                    continue

        return lines

    def _build_feature_map(
        self,
        words_result: list[Dict[str, Any]],
        image_width: int,
        image_height: int,
        grid_size: int = 32,
    ) -> list[list[float]]:
        """
        Approximate attention/feature heatmap using detection polygons weighted by confidence.
        This serves as a practical visualization when direct internal CBAM tensors are unavailable.
        """
        heat = np.zeros((grid_size, grid_size), dtype=np.float32)
        if image_width <= 0 or image_height <= 0:
            return heat.tolist()
        for item in words_result:
            box = item.get("location")
            if not box:
                continue
            try:
                xs = [float(p[0]) for p in box]
                ys = [float(p[1]) for p in box]
                l = max(0.0, min(xs))
                r = min(float(image_width), max(xs))
                t = max(0.0, min(ys))
                b = min(float(image_height), max(ys))
                if r <= l or b <= t:
                    continue
                gx0 = int((l / image_width) * grid_size)
                gx1 = int(np.ceil((r / image_width) * grid_size))
                gy0 = int((t / image_height) * grid_size)
                gy1 = int(np.ceil((b / image_height) * grid_size))
                gx0, gy0 = max(gx0, 0), max(gy0, 0)
                gx1, gy1 = min(gx1, grid_size), min(gy1, grid_size)
                w = float(item.get("probability", 1.0))
                heat[gy0:gy1, gx0:gx1] += max(0.05, w)
            except Exception:
                continue
        m = float(heat.max())
        if m > 0:
            heat /= m
        return heat.tolist()

    async def ocr_general_basic(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Perform OCR using local PaddleOCR models.
        """
        try:
            # Convert bytes to numpy array for PaddleOCR
            image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            image_np = np.array(image)
            image_width, image_height = int(image.width), int(image.height)

            words_result: list[Dict[str, Any]] = []

            try:
                if hasattr(self.ocr, "predict"):
                    print("Using PaddleOCR predict API...")
                    result = self.ocr.predict(image_np)
                else:
                    print("Using traditional PaddleOCR ocr API...")
                    result = self.ocr.ocr(image_np)

                words_result = self._extract_lines_from_result(result)
            except Exception as e:
                print(f"Primary OCR API failed ({type(e).__name__}: {e}), trying alternative...")
                try:
                    if hasattr(self.ocr, "ocr"):
                        result = self.ocr.ocr(image_np)
                    else:
                        result = self.ocr.predict(image_np)
                    words_result = self._extract_lines_from_result(result)
                except Exception as final_e:
                    print(f"Final OCR fallback failed: {final_e}")
                    raise final_e

            if not words_result:
                print("OCR Result: No text found")
                return {
                    "words_result": [],
                    "feature_map": [],
                    "full_text": "",
                    "model_version": "local-PP-OCRv4",
                }

            full_text = "\n".join(
                [str(item.get("words", "")).strip() for item in words_result if item.get("words")]
            )
            print("--- OCR Result Start ---")
            print(full_text)
            print("--- OCR Result End ---")

            return {
                "words_result": words_result,
                "dt_boxes": [item["location"] for item in words_result if "location" in item],
                "feature_map": self._build_feature_map(words_result, image_width, image_height),
                "full_text": full_text,
                "model_version": "local-PP-OCRv4",
            }
        except Exception as e:
            print(f"Local OCR Error during inference: {e}")
            import traceback
            traceback.print_exc()
            raise e

local_ocr_provider = LocalOCRProvider()
