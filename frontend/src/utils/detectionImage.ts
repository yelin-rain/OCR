import type { OcrLine } from "./ocrResult";

export type BoxRect = {
  left: number;
  top: number;
  width: number;
  height: number;
};

export function normalizeRect(location: number[][]): BoxRect {
  const xs = location.map((p) => p[0]);
  const ys = location.map((p) => p[1]);
  const left = Math.min(...xs);
  const top = Math.min(...ys);
  const right = Math.max(...xs);
  const bottom = Math.max(...ys);
  return {
    left,
    top,
    width: Math.max(1, right - left),
    height: Math.max(1, bottom - top),
  };
}

export function lineAtPoint(
  image: HTMLImageElement,
  lines: OcrLine[],
  x: number,
  y: number,
  displayWidth: number,
  displayHeight: number,
): number | null {
  if (!image.naturalWidth || !image.naturalHeight) return null;
  const rx = x * (image.naturalWidth / displayWidth);
  const ry = y * (image.naturalHeight / displayHeight);
  for (let i = 0; i < lines.length; i += 1) {
    const box = lines[i].location;
    if (!box?.length) continue;
    const r = normalizeRect(box);
    if (
      rx >= r.left &&
      rx <= r.left + r.width &&
      ry >= r.top &&
      ry <= r.top + r.height
    ) {
      return i;
    }
  }
  return null;
}

/** 在 canvas 上绘制原图 + 检测框标注 */
export function drawAnnotatedDetection(
  canvas: HTMLCanvasElement,
  image: HTMLImageElement,
  lines: OcrLine[],
  activeIndex: number | null,
  maxDisplayWidth = 520,
): { scaleX: number; scaleY: number; displayWidth: number; displayHeight: number } {
  const ctx = canvas.getContext("2d");
  if (!ctx || !image.naturalWidth) {
    return { scaleX: 1, scaleY: 1, displayWidth: 0, displayHeight: 0 };
  }

  const scale = Math.min(1, maxDisplayWidth / image.naturalWidth);
  const displayWidth = Math.max(1, Math.floor(image.naturalWidth * scale));
  const displayHeight = Math.max(1, Math.floor(image.naturalHeight * scale));
  canvas.width = displayWidth;
  canvas.height = displayHeight;

  ctx.drawImage(image, 0, 0, displayWidth, displayHeight);
  const scaleX = displayWidth / image.naturalWidth;
  const scaleY = displayHeight / image.naturalHeight;

  lines.forEach((line, index) => {
    if (!line.location?.length) return;
    const r = normalizeRect(line.location);
    const isActive = index === activeIndex;
    const x = r.left * scaleX;
    const y = r.top * scaleY;
    const w = r.width * scaleX;
    const h = r.height * scaleY;

    if (isActive) {
      ctx.fillStyle = "rgba(6, 182, 212, 0.18)";
      ctx.fillRect(x, y, w, h);
    }
    ctx.strokeStyle = isActive ? "#ef4444" : "#06b6d4";
    ctx.lineWidth = isActive ? 2.5 : 1.5;
    ctx.strokeRect(x, y, w, h);

    if (w > 40 && h > 14) {
      const label = line.words.length > 12 ? `${line.words.slice(0, 12)}…` : line.words;
      ctx.font = "11px system-ui, sans-serif";
      const tw = ctx.measureText(label).width + 8;
      const lh = 16;
      ctx.fillStyle = isActive ? "rgba(239, 68, 68, 0.92)" : "rgba(6, 182, 212, 0.88)";
      ctx.fillRect(x, Math.max(0, y - lh), Math.min(tw, w), lh);
      ctx.fillStyle = "#fff";
      ctx.fillText(label, x + 4, Math.max(11, y - 4));
    }
  });

  return { scaleX, scaleY, displayWidth, displayHeight };
}

/** 按检测框裁剪区域，生成预览 data URL */
export function cropLineToDataUrl(
  image: HTMLImageElement,
  location: number[][],
  maxEdge = 96,
): string | null {
  if (!image.naturalWidth) return null;
  const r = normalizeRect(location);
  const pad = Math.max(2, Math.floor(Math.min(r.width, r.height) * 0.05));
  const sx = Math.max(0, Math.floor(r.left - pad));
  const sy = Math.max(0, Math.floor(r.top - pad));
  const sw = Math.min(image.naturalWidth - sx, Math.ceil(r.width + pad * 2));
  const sh = Math.min(image.naturalHeight - sy, Math.ceil(r.height + pad * 2));
  if (sw < 1 || sh < 1) return null;

  const scale = maxEdge / Math.max(sw, sh);
  const dw = Math.max(1, Math.floor(sw * scale));
  const dh = Math.max(1, Math.floor(sh * scale));

  const canvas = document.createElement("canvas");
  canvas.width = dw;
  canvas.height = dh;
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;
  ctx.drawImage(image, sx, sy, sw, sh, 0, 0, dw, dh);
  try {
    return canvas.toDataURL("image/png");
  } catch {
    return null;
  }
}
