export type ParsedOcrResult =
  | { type: "empty" }
  | { type: "words"; words: string[] }
  | { type: "text"; text: string }
  | { type: "raw"; raw: unknown }
  | { type: "error" };

interface WordsItem {
  words?: string;
}

export function parseOcrResult(resultStr: string | null): ParsedOcrResult {
  if (!resultStr) {
    return { type: "empty" };
  }

  try {
    const data = JSON.parse(resultStr);

    if (Array.isArray(data.words_result)) {
      const words = (data.words_result as WordsItem[])
        .map((item) => item?.words?.trim())
        .filter((word): word is string => Boolean(word));
      return { type: "words", words };
    }

    const aiStudioText = data.result?.layoutParsingResults?.[0]?.markdown?.text;
    if (typeof aiStudioText === "string" && aiStudioText.trim()) {
      return { type: "text", text: aiStudioText };
    }

    if (typeof data.full_text === "string" && data.full_text.trim()) {
      return { type: "text", text: data.full_text };
    }

    return { type: "raw", raw: data };
  } catch {
    return { type: "error" };
  }
}
