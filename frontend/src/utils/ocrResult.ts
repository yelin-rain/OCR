export interface OcrLine {
  words: string;
  probability: number;
  location?: number[][];
}

export type ParsedOcrResult =
  | { type: "empty" }
  | { type: "lines"; lines: OcrLine[]; fullText: string; raw: unknown }
  | { type: "text"; text: string; raw: unknown }
  | { type: "raw"; raw: unknown }
  | { type: "error" };

export function parseOcrResult(resultStr: string | null): ParsedOcrResult {
  if (!resultStr) {
    return { type: "empty" };
  }

  try {
    const data = JSON.parse(resultStr);

    if (Array.isArray(data.words_result)) {
      const lines = (data.words_result as Array<Record<string, unknown>>)
        .map((item) => {
          const words = String(item?.words ?? "").trim();
          if (!words) return null;
          const probability = Number(item?.probability ?? 1);
          const locationRaw = item?.location;
          const location =
            Array.isArray(locationRaw) &&
            locationRaw.every(
              (p) => Array.isArray(p) && p.length >= 2 && Number.isFinite(Number(p[0])) && Number.isFinite(Number(p[1])),
            )
              ? (locationRaw as number[][]).map((p) => [Number(p[0]), Number(p[1])])
              : undefined;
          return {
            words,
            probability: Number.isFinite(probability) ? probability : 1,
            location,
          } as OcrLine;
        })
        .filter((line): line is OcrLine => Boolean(line));
      const fullText =
        typeof data.full_text === "string" && data.full_text.trim()
          ? data.full_text
          : lines.map((line) => line.words).join("\n");
      return { type: "lines", lines, fullText, raw: data };
    }

    const aiStudioText = data.result?.layoutParsingResults?.[0]?.markdown?.text;
    if (typeof aiStudioText === "string" && aiStudioText.trim()) {
      return { type: "text", text: aiStudioText, raw: data };
    }

    if (typeof data.full_text === "string" && data.full_text.trim()) {
      return { type: "text", text: data.full_text, raw: data };
    }

    return { type: "raw", raw: data };
  } catch {
    return { type: "error" };
  }
}
