import json
import os
import subprocess
import sys
from typing import Dict, Any

from app.core.config import settings


def _check_required_files(model_dir: str) -> Dict[str, Any]:
    pdmodel = os.path.join(model_dir, "inference.pdmodel")
    pdiparams = os.path.join(model_dir, "inference.pdiparams")
    yml = os.path.join(model_dir, "inference.yml")
    return {
        "model_dir": model_dir,
        "exists": os.path.isdir(model_dir),
        "pdmodel_exists": os.path.exists(pdmodel),
        "pdiparams_exists": os.path.exists(pdiparams),
        "yml_exists": os.path.exists(yml),
        "pdmodel_path": pdmodel,
        "pdiparams_path": pdiparams,
    }


def _probe_predictor(pdmodel: str, pdiparams: str) -> Dict[str, Any]:
    if not (os.path.exists(pdmodel) and os.path.exists(pdiparams)):
        return {"ok": False, "reason": "missing required files"}

    cmd = [
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
    probe = _probe_predictor(file_check["pdmodel_path"], file_check["pdiparams_path"])
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
