#!/usr/bin/env python3
"""
将 PaddleOCR 训练产物导出为推理模型，并安装到本后端项目 inference_models 目录。

用法：

1) copy — 已有推理目录（含 inference.pdmodel + inference.pdiparams）：

   python scripts/export_paddleocr_models.py copy \\
     --det-source "D:/.../inference" \\
     --rec-source "D:/.../inference"

2) export — 在完整 PaddleOCR 仓库中调用 tools/export_model.py（注意 -o 必须为 key=value，
   本脚本已自动传入 Global.save_inference_dir 与 Global.pretrained_model）。

   python scripts/export_paddleocr_models.py export \\
     --paddleocr-root "D:/PaddlePaddle/PaddleOCR" \\
     --det-config "C:/.../modal/PaddleOCR/configs/det/det_r50_vd_db.yml" \\
     --rec-config "C:/.../modal/PaddleOCR/configs/rec/PP-OCRv4/ch_PP-OCRv4_rec_svtr_large.yml" \\
     --det-pretrained "C:/.../modal/PaddleOCR/output/db_resnet50_cbam/best_accuracy" \\
     --rec-pretrained "C:/.../modal/PaddleOCR/output/rec_rare_2/best_accuracy"

   若本机无 GPU，可加 --cpu-export（追加 Global.use_gpu=False）。

3) pick — 方案二：训练时若已在 yml 里配置 save_inference_dir，export_model.py 会把静态图
   写到「save_inference_dir/inference/」下。若你曾成功跑过导出，可直接从该目录安装，
   无需再克隆 PaddleOCR：

   python scripts/export_paddleocr_models.py pick \\
     --artifact-root "C:/.../modal/PaddleOCR" \\
     --det-yml "C:/.../modal/PaddleOCR/configs/det/det_r50_vd_db.yml" \\
     --rec-yml "C:/.../modal/PaddleOCR/configs/rec/PP-OCRv4/ch_PP-OCRv4_rec_svtr_large.yml"

安装目标默认：
  server/app/inference_models/det_db_resnet50_cbam
  server/app/inference_models/crnn_ctc_rare

完成后运行： python check_local_models.py
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def _server_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _default_det_target() -> Path:
    return _server_root() / "app" / "inference_models" / "det_db_resnet50_cbam"


def _default_rec_target() -> Path:
    return _server_root() / "app" / "inference_models" / "crnn_ctc_rare"


def _assert_inference_dir(label: str, src: Path) -> None:
    if not src.is_dir():
        raise SystemExit(f"{label}: 不是目录: {src}")
    pdiparams = src / "inference.pdiparams"
    if not pdiparams.is_file():
        raise SystemExit(f"{label}: 缺少 inference.pdiparams，目录: {src}")
    if not (src / "inference.pdmodel").is_file() and not (src / "inference.json").is_file():
        raise SystemExit(
            f"{label}: 缺少 inference.pdmodel 或 inference.json，目录: {src}"
        )


def _copy_tree_contents(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for name in os.listdir(src):
        s = src / name
        d = dst / name
        if s.is_file():
            shutil.copy2(s, d)
        elif s.is_dir():
            if d.exists():
                shutil.rmtree(d)
            shutil.copytree(s, d)


def cmd_copy(args: argparse.Namespace) -> int:
    det_src = Path(args.det_source).resolve()
    rec_src = Path(args.rec_source).resolve()
    _assert_inference_dir("检测", det_src)
    _assert_inference_dir("识别", rec_src)

    det_dst = Path(args.det_target).resolve() if args.det_target else _default_det_target()
    rec_dst = Path(args.rec_target).resolve() if args.rec_target else _default_rec_target()

    print(f"复制检测模型: {det_src} -> {det_dst}")
    _copy_tree_contents(det_src, det_dst)
    print(f"复制识别模型: {rec_src} -> {rec_dst}")
    _copy_tree_contents(rec_src, rec_dst)
    print("完成。请运行: python check_local_models.py")
    return 0


def _has_inference_pair(d: Path) -> bool:
    if not d.is_dir() or not (d / "inference.pdiparams").is_file():
        return False
    return (d / "inference.pdmodel").is_file() or (d / "inference.json").is_file()


def _find_inference_subdir(out_dir: Path, max_depth: int = 5) -> Path | None:
    """export_model.py 写入 save_inference_dir/inference/inference.*；也兼容浅层目录或异常布局。"""
    if not out_dir.is_dir():
        return None
    for c in (out_dir / "inference", out_dir):
        if _has_inference_pair(c):
            return c
    for dirpath, dirnames, _filenames in os.walk(out_dir):
        p = Path(dirpath)
        try:
            depth = len(p.relative_to(out_dir).parts)
        except ValueError:
            continue
        if depth > max_depth:
            dirnames.clear()
            continue
        if _has_inference_pair(p):
            return p
    return None


def _parse_save_inference_dir(yml_path: Path) -> Path:
    text = yml_path.read_text(encoding="utf-8")
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line.startswith("save_inference_dir:"):
            continue
        val = line.split(":", 1)[1].strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "'\"":
            val = val[1:-1]
        val = val.strip().rstrip("/\\")
        if val.startswith("./"):
            val = val[2:]
        return Path(val)
    raise SystemExit(f"未在配置文件中找到 save_inference_dir: {yml_path}")


def _resolve_pretrained_for_paddle(pretrained: Path, label: str) -> Path:
    """
    PaddleOCR load_model 使用「无前缀路径」：磁盘上通常是 xxx.pdparams，配置里写 xxx。
    用户既可传目录/best_accuracy，也可传 best_accuracy.pdparams。
    """
    p = pretrained.resolve()
    if p.is_file() and p.suffix == ".pdparams":
        return p.with_suffix("")
    if p.is_file():
        return p
    if p.is_dir():
        return p
    sibling = p.with_suffix(".pdparams")
    if sibling.is_file():
        return p
    raise SystemExit(
        f"{label}: 找不到权重。请传 checkpoint 前缀路径（如 .../best_accuracy），"
        f"或对应的 .pdparams 文件。已检查: {p} 与 {sibling}"
    )


def _run_export(
    paddleocr_root: Path,
    config_rel: str,
    pretrained: Path,
    out_dir: Path,
    label: str,
    *,
    cpu_export: bool,
    extra_opts: list[str],
) -> Path:
    export_py = paddleocr_root / "tools" / "export_model.py"
    if not export_py.is_file():
        raise SystemExit(f"未找到 {export_py}，请确认 --paddleocr-root 指向 PaddleOCR 仓库根目录")

    config_path = Path(config_rel)
    if not config_path.is_absolute():
        config_path = paddleocr_root / config_rel
    if not config_path.is_file():
        raise SystemExit(f"{label}: 配置文件不存在: {config_path}")

    pre_for_paddle = _resolve_pretrained_for_paddle(pretrained, label)

    out_dir.mkdir(parents=True, exist_ok=True)
    # tools/program.py 要求每个 -o 为 key=value；路径用 POSIX 避免 Windows 反斜杠被 yaml 误解析
    save_root = out_dir.resolve().as_posix()
    pre_str = pre_for_paddle.as_posix()
    use_pir = True  # Paddle 3.3 + MultiHead（rec_rare_2）在 Windows 上需 PIR 导出
    opts: list[str] = [
        f"Global.save_inference_dir={save_root}",
        f"Global.pretrained_model={pre_str}",
        f"Global.export_with_pir={'True' if use_pir else 'False'}",
    ]
    if cpu_export:
        opts.append("Global.use_gpu=False")
    for opt in extra_opts:
        if "=" not in opt:
            raise SystemExit(f"--extra-opt 须为 KEY=VAL 形式: {opt!r}")
        opts.append(opt)
    cmd = [sys.executable, str(export_py), "-c", str(config_path), "-o", *opts]
    env = os.environ.copy()
    if use_pir:
        env["FLAGS_enable_pir_api"] = "1"
    else:
        env.setdefault("FLAGS_enable_pir_api", "0")
    env.setdefault("FLAGS_enable_onednn", "0")
    env.setdefault("FLAGS_use_mkldnn", "0")
    print(f"[{label}] 执行: {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=str(paddleocr_root), env=env)
    if proc.returncode != 0:
        raise SystemExit(f"{label}: export_model.py 失败，退出码 {proc.returncode}")

    infer_dir = _find_inference_subdir(out_dir)
    if infer_dir is None:
        raise SystemExit(
            f"{label}: 导出后未找到 inference.pdmodel 与 inference.pdiparams。"
            f" 请检查目录 {out_dir}；若仅有 .pdiparams.info，多为导出中断或 Paddle 版本与仓库不一致。"
            f" 可尝试方案: python {Path(__file__).name} pick ..."
        )
    print(f"[{label}] 推理文件位于: {infer_dir}")
    return infer_dir


def cmd_export(args: argparse.Namespace) -> int:
    root = Path(args.paddleocr_root).resolve()
    if not root.is_dir():
        raise SystemExit(f"--paddleocr-root 无效: {root}")

    work = Path(args.work_dir).resolve()
    det_out = work / "det_export"
    rec_out = work / "rec_export"

    det_pt = Path(args.det_pretrained).resolve()
    rec_pt = Path(args.rec_pretrained).resolve()

    if args.skip_det and args.skip_rec:
        raise SystemExit("不能同时设置 --skip-det 与 --skip-rec")

    det_infer: Path | None = None
    rec_infer: Path | None = None
    if not args.skip_det:
        det_infer = _run_export(
            root,
            args.det_config,
            det_pt,
            det_out,
            "检测",
            cpu_export=args.cpu_export,
            extra_opts=args.extra_opt,
        )
    if not args.skip_rec:
        rec_infer = _run_export(
            root,
            args.rec_config,
            rec_pt,
            rec_out,
            "识别",
            cpu_export=args.cpu_export,
            extra_opts=args.extra_opt,
        )

    det_dst = Path(args.det_target).resolve() if args.det_target else _default_det_target()
    rec_dst = Path(args.rec_target).resolve() if args.rec_target else _default_rec_target()
    if det_infer is not None:
        _assert_inference_dir("检测(导出后)", det_infer)
        print(f"安装检测模型 -> {det_dst}")
        _copy_tree_contents(det_infer, det_dst)
    if rec_infer is not None:
        _assert_inference_dir("识别(导出后)", rec_infer)
        print(f"安装识别模型 -> {rec_dst}")
        _copy_tree_contents(rec_infer, rec_dst)
    print("完成。请运行: python check_local_models.py")
    return 0


def cmd_pick(args: argparse.Namespace) -> int:
    artifact = Path(args.artifact_root).resolve()
    if not artifact.is_dir():
        raise SystemExit(f"--artifact-root 无效: {artifact}")

    det_yml = Path(args.det_yml).resolve()
    rec_yml = Path(args.rec_yml).resolve()
    det_save = _parse_save_inference_dir(det_yml)
    rec_save = _parse_save_inference_dir(rec_yml)
    # export_model.py: os.path.join(Global.save_inference_dir, "inference")
    det_infer = (artifact / det_save / "inference").resolve()
    rec_infer = (artifact / rec_save / "inference").resolve()

    _assert_inference_dir("检测(pick)", det_infer)
    _assert_inference_dir("识别(pick)", rec_infer)

    det_dst = Path(args.det_target).resolve() if args.det_target else _default_det_target()
    rec_dst = Path(args.rec_target).resolve() if args.rec_target else _default_rec_target()
    print(f"安装检测模型: {det_infer} -> {det_dst}")
    _copy_tree_contents(det_infer, det_dst)
    print(f"安装识别模型: {rec_infer} -> {rec_dst}")
    _copy_tree_contents(rec_infer, rec_dst)
    print("完成。请运行: python check_local_models.py")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="导出/安装 PaddleOCR 推理模型到本后端")
    sub = parser.add_subparsers(dest="command", required=True)

    p_copy = sub.add_parser("copy", help="从已导出的推理目录复制到后端")
    p_copy.add_argument("--det-source", required=True, help="检测推理目录（含 pdmodel/pdiparams）")
    p_copy.add_argument("--rec-source", required=True, help="识别推理目录")
    p_copy.add_argument("--det-target", default=None, help="覆盖默认 det 安装路径")
    p_copy.add_argument("--rec-target", default=None, help="覆盖默认 rec 安装路径")
    p_copy.set_defaults(func=cmd_copy)

    p_exp = sub.add_parser("export", help="在本地 PaddleOCR 仓库中调用 tools/export_model.py 并安装")
    p_exp.add_argument("--paddleocr-root", required=True, help="PaddleOCR 仓库根目录")
    p_exp.add_argument("--det-config", required=True, help="检测训练/导出用 yml，相对 paddleocr-root 或绝对路径")
    p_exp.add_argument("--rec-config", required=True, help="识别 yml")
    p_exp.add_argument(
        "--det-pretrained",
        required=True,
        help="检测权重：.../best_accuracy（与 best_accuracy.pdparams 同目录）或直接传 .pdparams",
    )
    p_exp.add_argument(
        "--rec-pretrained",
        required=True,
        help="识别权重：同上",
    )
    p_exp.add_argument(
        "--work-dir",
        default=str(_server_root() / ".paddle_export_work"),
        help="导出临时目录",
    )
    p_exp.add_argument("--det-target", default=None)
    p_exp.add_argument("--rec-target", default=None)
    p_exp.add_argument("--skip-det", action="store_true", help="跳过检测模型导出/安装")
    p_exp.add_argument("--skip-rec", action="store_true", help="跳过识别模型导出/安装")
    p_exp.add_argument(
        "--cpu-export",
        action="store_true",
        help="追加 Global.use_gpu=False（无 GPU 或 CUDA 环境异常时使用）",
    )
    p_exp.add_argument(
        "--extra-opt",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="传给 export 的额外 -o 项，可多次指定",
    )
    p_exp.set_defaults(func=cmd_export)

    p_pick = sub.add_parser(
        "pick",
        help="从 yml 中 save_inference_dir 定位已导出的 inference/ 目录并复制到后端（方案二）",
    )
    p_pick.add_argument(
        "--artifact-root",
        required=True,
        help="训练工程根目录（与 yml 里相对路径一致，一般为含 output/ 的 PaddleOCR 目录）",
    )
    p_pick.add_argument("--det-yml", required=True, help="检测配置 yml 路径")
    p_pick.add_argument("--rec-yml", required=True, help="识别配置 yml 路径")
    p_pick.add_argument("--det-target", default=None)
    p_pick.add_argument("--rec-target", default=None)
    p_pick.set_defaults(func=cmd_pick)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
