import React from "react";
import { Tooltip } from "antd";
import { Check, Cpu, Sparkles } from "lucide-react";
import { cn } from "../utils/utils";

export type OcrModelMode = "official" | "custom";

interface ModelModeSwitchProps {
  value: OcrModelMode;
  onChange: (mode: OcrModelMode) => void;
  customAvailable: boolean;
  loading?: boolean;
  compact?: boolean;
  className?: string;
}

const MODES: Array<{
  id: OcrModelMode;
  label: string;
  hint: string;
  Icon: React.ComponentType<{ className?: string }>;
}> = [
  { id: "official", label: "官方", hint: "PP-OCRv4", Icon: Sparkles },
  { id: "custom", label: "自训练", hint: "rare_2", Icon: Cpu },
];

export const ModelModeSwitch: React.FC<ModelModeSwitchProps> = ({
  value,
  onChange,
  customAvailable,
  loading = false,
  compact = false,
  className,
}) => {
  const iconCls = compact ? "w-3 h-3" : "w-4 h-4";

  return (
    <div
      className={cn(
        "inline-flex rounded-lg border border-gray-200/90 shadow-sm backdrop-blur-sm",
        compact ? "p-0.5 bg-white/95" : "p-1 bg-gray-100/90",
        className,
      )}
      role="radiogroup"
      aria-label="识别模型"
    >
      {MODES.map((mode) => {
        const selected = value === mode.id;
        const disabled =
          loading || (mode.id === "custom" && !customAvailable);
        const { Icon } = mode;

        const button = (
          <button
            key={mode.id}
            type="button"
            role="radio"
            aria-checked={selected}
            disabled={disabled}
            onClick={(e) => {
              e.stopPropagation();
              if (!disabled) onChange(mode.id);
            }}
            className={cn(
              "relative flex items-center rounded-md font-medium transition-all duration-200",
              "focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 focus-visible:ring-offset-1",
              compact ? "gap-1 px-2 py-1 text-xs" : "gap-2 px-3 py-1.5 text-sm",
              selected
                ? "bg-blue-50 text-blue-700 ring-1 ring-blue-200/80"
                : "text-gray-600 hover:text-gray-800 hover:bg-gray-50",
              disabled && "opacity-45 cursor-not-allowed hover:bg-transparent",
            )}
          >
            <span
              className={cn(
                "flex items-center justify-center rounded-md shrink-0",
                compact ? "w-5 h-5" : "w-7 h-7",
                selected ? "bg-blue-100 text-blue-600" : "bg-gray-200/70 text-gray-500",
              )}
            >
              <Icon className={iconCls} />
            </span>
            <span className={cn(compact ? "leading-none" : "flex flex-col items-start leading-tight")}>
              <span className={compact ? "font-medium" : "text-xs font-semibold"}>
                {mode.label}
              </span>
              {!compact ? (
                <span className="text-[10px] font-normal text-gray-400">{mode.hint}</span>
              ) : null}
            </span>
            {selected && !compact ? (
              <Check className="w-3.5 h-3.5 text-blue-500 ml-0.5 shrink-0" aria-hidden />
            ) : null}
          </button>
        );

        if (mode.id === "custom" && !customAvailable) {
          return (
            <Tooltip
              key={mode.id}
              title="自训练模型未就绪，请检查 inference_models"
            >
              <span className="inline-flex">{button}</span>
            </Tooltip>
          );
        }

        return button;
      })}
    </div>
  );
};
