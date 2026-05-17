import React, { useCallback, useEffect, useRef, useState } from "react";
import { Image as ImageIcon } from "lucide-react";

import { cn } from "../../utils/utils";
import type { OcrLine } from "../../utils/ocrResult";
import {
  cropLineToDataUrl,
  drawAnnotatedDetection,
  lineAtPoint,
} from "../../utils/detectionImage";

interface DetectionImageStackProps {
  imageUrl: string;
  lines: OcrLine[];
  activeIndex: number | null;
  onActiveIndexChange: (index: number | null) => void;
}

export const DetectionImageStack: React.FC<DetectionImageStackProps> = ({
  imageUrl,
  lines,
  activeIndex,
  onActiveIndexChange,
}) => {
  const imageRef = useRef<HTMLImageElement | null>(null);
  const annotatedRef = useRef<HTMLCanvasElement | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [cropUrls, setCropUrls] = useState<(string | null)[]>([]);

  const linesWithBox = lines.filter((l) => l.location && l.location.length >= 4);
  const hasBoxes = linesWithBox.length > 0;

  const redrawAnnotated = useCallback(() => {
    const img = imageRef.current;
    const canvas = annotatedRef.current;
    if (!img || !canvas || !loaded) return;
    drawAnnotatedDetection(canvas, img, lines, activeIndex);
  }, [lines, activeIndex, loaded]);

  useEffect(() => {
    redrawAnnotated();
  }, [redrawAnnotated]);

  useEffect(() => {
    const img = imageRef.current;
    if (!img || !loaded) {
      setCropUrls([]);
      return;
    }
    setCropUrls(
      lines.map((line) =>
        line.location?.length ? cropLineToDataUrl(img, line.location) : null,
      ),
    );
  }, [lines, loaded, imageUrl]);

  const handleAnnotatedClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const img = imageRef.current;
    const canvas = annotatedRef.current;
    if (!img || !canvas) return;
    const rect = canvas.getBoundingClientRect();
    const idx = lineAtPoint(
      img,
      lines,
      e.clientX - rect.left,
      e.clientY - rect.top,
      rect.width,
      rect.height,
    );
    onActiveIndexChange(idx);
  };

  return (
    <div className="flex flex-col gap-3">
      <div>
        <p className="text-xs font-medium text-gray-500 mb-1.5">原图</p>
        <div className="rounded-xl border border-gray-200 bg-white p-2 flex justify-center">
          <img
            ref={imageRef}
            src={imageUrl}
            alt="原图"
            crossOrigin="anonymous"
            className="w-full max-h-[220px] object-contain"
            onLoad={() => setLoaded(true)}
          />
        </div>
      </div>

      <div>
        <p className="text-xs font-medium text-gray-500 mb-1.5">
          检测框标注
          {hasBoxes ? (
            <span className="text-gray-400 font-normal ml-1">
              （点击框或下方区域可选中）
            </span>
          ) : null}
        </p>
        <div
          className={cn(
            "rounded-xl border border-gray-200 bg-gray-50 p-2 flex justify-center min-h-[120px]",
            hasBoxes && "cursor-crosshair",
          )}
        >
          {loaded ? (
            <canvas
              ref={annotatedRef}
              className="max-h-[280px] w-full h-auto"
              onClick={handleAnnotatedClick}
              role="img"
              aria-label="检测框标注图"
            />
          ) : (
            <div className="flex items-center justify-center h-32 text-gray-400 text-sm">
              加载中…
            </div>
          )}
        </div>
        {!hasBoxes && loaded && (
          <p className="text-xs text-amber-600 mt-1">
            当前结果未包含检测框坐标，仅展示原图。
          </p>
        )}
      </div>

      {hasBoxes && (
        <div>
          <p className="text-xs font-medium text-gray-500 mb-1.5">框选区域</p>
          <div className="flex flex-wrap gap-2 max-h-[200px] overflow-y-auto p-2 rounded-xl border border-gray-200 bg-white">
            {lines.map((line, idx) => {
              const url = cropUrls[idx];
              if (!url) return null;
              const isActive = activeIndex === idx;
              return (
                <button
                  key={idx}
                  type="button"
                  onClick={() => onActiveIndexChange(isActive ? null : idx)}
                  className={cn(
                    "flex flex-col items-center gap-1 rounded-lg border p-1 transition-colors",
                    isActive
                      ? "border-red-400 bg-red-50 ring-1 ring-red-300"
                      : "border-gray-200 hover:border-cyan-400 hover:bg-cyan-50/50",
                  )}
                  title={line.words}
                >
                  <img
                    src={url}
                    alt={`区域 ${idx + 1}`}
                    className="max-h-16 max-w-[120px] object-contain bg-gray-50 rounded"
                  />
                  <span className="text-[10px] text-gray-600 max-w-[100px] truncate px-0.5">
                    {line.words || `#${idx + 1}`}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {!loaded && (
        <div className="flex items-center gap-2 text-gray-400 text-sm justify-center py-4">
          <ImageIcon className="w-5 h-5 opacity-40" />
          正在加载图片…
        </div>
      )}
    </div>
  );
};
