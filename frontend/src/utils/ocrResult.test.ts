import { describe, expect, it } from "vitest";

import { parseOcrResult } from "./ocrResult";

describe("parseOcrResult", () => {
  it("returns empty for null", () => {
    expect(parseOcrResult(null)).toEqual({ type: "empty" });
  });

  it("parses words_result format", () => {
    const input = JSON.stringify({
      words_result: [{ words: "hello" }, { words: "world" }],
    });
    expect(parseOcrResult(input)).toEqual({
      type: "words",
      words: ["hello", "world"],
    });
  });

  it("parses ai studio markdown text format", () => {
    const input = JSON.stringify({
      result: {
        layoutParsingResults: [{ markdown: { text: "line1\nline2" } }],
      },
    });
    expect(parseOcrResult(input)).toEqual({
      type: "text",
      text: "line1\nline2",
    });
  });

  it("falls back to full_text format", () => {
    const input = JSON.stringify({ full_text: "plain text content" });
    expect(parseOcrResult(input)).toEqual({
      type: "text",
      text: "plain text content",
    });
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
