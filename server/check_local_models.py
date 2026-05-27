import json
import os
import subprocess
import sys
from typing import Dict, Any

from app.core.config import settings


def _resolve_infer_files(model_dir: str) -> tuple[str | None, str | None, str | None]:
    pdiparams = os.path.join(model_dir, "inference.pdiparams")
    if not os.path.isfile(pdiparams):
        return None, None, None
    pdmodel = os.path.join(model_dir, "inference.pdmodel")
    if os.path.isfile(pdmodel):
        return pdmodel, pdiparams, "pdmodel"
    pdjson = os.path.join(model_dir, "inference.json")
    if os.path.isfile(pdjson):
        return pdjson, pdiparams, "json"
    return None, None, None


def _check_required_files(model_dir: str) -> Dict[str, Any]:
    model_file, pdiparams, fmt = _resolve_infer_files(model_dir)
    yml = os.path.join(model_dir, "inference.yml")
    return {
        "model_dir": model_dir,
        "exists": os.path.isdir(model_dir),
        "format": fmt,
        "model_file_exists": bool(model_file),
        "pdiparams_exists": os.path.exists(pdiparams) if pdiparams else False,
        "yml_exists": os.path.exists(yml),
        "model_file_path": model_file,
        "pdiparams_path": pdiparams,
    }


def _probe_predictor(model_file: str | None, pdiparams: str | None) -> Dict[str, Any]:
    if not (model_file and pdiparams and os.path.exists(model_file) and os.path.exists(pdiparams)):
        return {"ok": False, "reason": "missing required files"}

    cmd = [
        sys.executable,
        "-c",
        (
            "import paddle.inference as I; "
            f"cfg=I.Config(r'{model_file}', r'{pdiparams}'); "
            "cfg.disable_gpu(); "
            "I.create_predictor(cfg); "
            "print('ok')"
        ),
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if proc.returncode != 0:
            return {
                "ok": False,
                "returncode": proc.returncode,
                "stderr": (proc.stderr or "").strip(),
                "stdout": (proc.stdout or "").strip(),
            }
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "reason": str(e)}


def _check_single(name: str, model_dir: str) -> Dict[str, Any]:
    file_check = _check_required_files(model_dir)
    probe = _probe_predictor(file_check["model_file_path"], file_check["pdiparams_path"])
    return {
        "name": name,
        "files": file_check,
        "probe": probe,
    }


def main() -> int:
    det_report = _check_single("det", settings.DET_MODEL_DIR)
    rec_report = _check_single("rec", settings.REC_MODEL_DIR)

    report = {
        "ocr_provider": settings.OCR_PROVIDER,
        "use_local_models": settings.USE_LOCAL_MODELS,
        "det": det_report,
        "rec": rec_report,
    }

    print(json.dumps(report, ensure_ascii=False, indent=2))

    all_ok = det_report["probe"]["ok"] and rec_report["probe"]["ok"]
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
