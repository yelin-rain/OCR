import { describe, expect, it } from "vitest";

import { parseOcrResult } from "./ocrResult";

describe("parseOcrResult", () => {
  it("returns empty for null", () => {
    expect(parseOcrResult(null)).toEqual({ type: "empty" });
  });

  it("parses words_result format", () => {
    const input = JSON.stringify({
      words_result: [{ words: "hello", probability: 0.9 }, { words: "world" }],
    });
    const output = parseOcrResult(input);
    expect(output.type).toBe("lines");
    if (output.type === "lines") {
      expect(output.lines.map((line) => line.words)).toEqual(["hello", "world"]);
    }
  });

  it("parses ai studio markdown text format", () => {
    const input = JSON.stringify({
      result: {
        layoutParsingResults: [{ markdown: { text: "line1\nline2" } }],
      },
    });
    const output = parseOcrResult(input);
    expect(output.type).toBe("text");
    if (output.type === "text") {
      expect(output.text).toBe("line1\nline2");
    }
  });

  it("falls back to full_text format", () => {
    const input = JSON.stringify({ full_text: "plain text content" });
    const output = parseOcrResult(input);
    expect(output.type).toBe("text");
    if (output.type === "text") {
      expect(output.text).toBe("plain text content");
    }
  });

  it("returns raw for unknown shape", () => {
    const input = JSON.stringify({ a: 1, b: 2 });
    const output = parseOcrResult(input);
    expect(output.type).toBe("raw");
  });

  it("returns error for invalid json", () => {
    expect(parseOcrResult("not-json")).toEqual({ type: "error" });
  });
});
