"""
CRNN / 文本识别后处理流水线：

1. 清理：去噪、Unicode 规范化、空白折叠
2. 正则规则化矫正：日期、手机号、身份证、金额、邮箱等结构化字段
3. 中文语料库语义矫正：短语映射 + 词表编辑距离（保守替换）

对上游拼接后的原始字符串处理，返回 (original_text, processed_text, corrections)。
"""

from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

_CORPUS_PATH = Path(__file__).resolve().parent.parent / "data" / "ocr_semantic_corpus.json"

# 控制字符与零宽字符
_CONTROL_AND_INVISIBLE = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\u200b-\u200f\u202a-\u202e\u2060\ufeff]"
)

# 日期：2024年3月8日 / 2024-3-8
_DATE_PATTERNS = [
    re.compile(r"(?P<y>\d{4})\s*年\s*(?P<m>\d{1,2})\s*月\s*(?P<d>\d{1,2})\s*日?"),
    re.compile(r"(?P<y>\d{4})[-/.](?P<m>\d{1,2})[-/.](?P<d>\d{1,2})"),
]

_NUMBER_TOKEN = re.compile(r"-?\d+(?:\.\d+)?")

# 手机号（大陆 11 位，允许分隔符）
_PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:\+?86[-\s]?)?(1[3-9]\d)[-\s]?(\d{4})[-\s]?(\d{4})(?!\d)"
)

# 18 位身份证（末位可为 X）
_ID_CARD_18 = re.compile(
    r"(?<!\d)(\d{6})(\d{8})(\d{3})(\d|X|x)(?!\d)"
)

# 金额：¥ / ￥ / RMB 前缀
_MONEY_PATTERN = re.compile(
    r"(?:¥|￥|RMB|rmb)\s*([0-9０-９]{1,3}(?:[,，][0-9０-９]{3})*(?:\.[0-9０-９]{1,2})?|[0-9０-９]+(?:\.[0-9０-９]{1,2})?)"
)

# 邮箱
_EMAIL_PATTERN = re.compile(
    r"([a-zA-Z0-9._%+-]+)\s*@\s*([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"
)

# 全角数字与标点 → 半角
_CHAR_CONFUSION = str.maketrans(
    {
        "０": "0", "１": "1", "２": "2", "３": "3", "４": "4",
        "５": "5", "６": "6", "７": "7", "８": "8", "９": "9",
        "．": ".", "，": ",", "：": ":", "（": "(", "）": ")",
        "－": "-", "／": "/",
    }
)

# 连续中文词段（用于语料库纠错）
_CJK_RUN = re.compile(r"[\u4e00-\u9fff]{2,8}")


@lru_cache(maxsize=1)
def _load_corpus() -> dict:
    if not _CORPUS_PATH.is_file():
        return {"phrase_fixes": [], "vocabulary": []}
    with _CORPUS_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _strip_and_remove_noise(text: str) -> str:
    t = text.strip()
    t = _CONTROL_AND_INVISIBLE.sub("", t)
    t = unicodedata.normalize("NFKC", t)
    t = re.sub(r"[^\S\r\n]+", " ", t)
    t = re.sub(r"[ \t]+", " ", t)
    lines = [ln.strip() for ln in t.splitlines()]
    return "\n".join(lines).strip()


def _pad_date_part(n: str, width: int) -> str:
    try:
        v = int(n)
        return str(v).zfill(width) if width == 2 else str(v).zfill(4)
    except ValueError:
        return n


def _edit_distance_one(a: str, b: str) -> bool:
    if a == b:
        return True
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    if la == lb:
        return sum(x != y for x, y in zip(a, b)) == 1
    if la > lb:
        a, b, la, lb = b, a, lb, la
    i = j = diff = 0
    while i < la and j < lb:
        if a[i] != b[j]:
            diff += 1
            if diff > 1:
                return False
            if la == lb:
                i += 1
                j += 1
            else:
                j += 1
        else:
            i += 1
            j += 1
    return diff + (lb - j) <= 1


def apply_regex_normalization(text: str) -> tuple[str, list[dict]]:
    """
    正则规则化矫正：日期、数字、手机、身份证、金额、邮箱。
    返回 (文本, 矫正记录列表)。
    """
    corrections: list[dict] = []

    def repl_date(m: re.Match) -> str:
        y = _pad_date_part(m.group("y"), 4)
        mo = _pad_date_part(m.group("m"), 2)
        d = _pad_date_part(m.group("d"), 2)
        try:
            yi, mi, di = int(y), int(mo), int(d)
            if not (1 <= mi <= 12 and 1 <= di <= 31 and 1900 <= yi <= 2100):
                return m.group(0)
        except ValueError:
            return m.group(0)
        normalized = f"{y}-{mo}-{d}"
        if normalized != m.group(0):
            corrections.append({
                "type": "regex_date",
                "from": m.group(0),
                "to": normalized,
            })
        return normalized

    out = text
    for pat in _DATE_PATTERNS:
        out = pat.sub(repl_date, out)

    def fix_num_segment(m: re.Match) -> str:
        seg = m.group(0)
        fixed = seg.translate(_CHAR_CONFUSION)
        if fixed != seg:
            corrections.append({"type": "regex_number", "from": seg, "to": fixed})
        return fixed

    out = _NUMBER_TOKEN.sub(fix_num_segment, out)

    def repl_phone(m: re.Match) -> str:
        normalized = f"{m.group(1)}{m.group(2)}{m.group(3)}"
        if m.group(0) != normalized:
            corrections.append({
                "type": "regex_phone",
                "from": m.group(0),
                "to": normalized,
            })
        return normalized

    out = _PHONE_PATTERN.sub(repl_phone, out)

    def repl_id(m: re.Match) -> str:
        normalized = (
            f"{m.group(1)}{m.group(2)}{m.group(3)}{m.group(4).upper()}"
        )
        if m.group(0) != normalized:
            corrections.append({
                "type": "regex_id_card",
                "from": m.group(0),
                "to": normalized,
            })
        return normalized

    out = _ID_CARD_18.sub(repl_id, out)

    def repl_money(m: re.Match) -> str:
        amount = m.group(1).translate(_CHAR_CONFUSION).replace(",", "").replace("，", "")
        normalized = f"¥{amount}"
        if m.group(0) != normalized:
            corrections.append({
                "type": "regex_money",
                "from": m.group(0),
                "to": normalized,
            })
        return normalized

    out = _MONEY_PATTERN.sub(repl_money, out)

    def repl_email(m: re.Match) -> str:
        normalized = f"{m.group(1)}@{m.group(2)}".lower()
        if m.group(0) != normalized:
            corrections.append({
                "type": "regex_email",
                "from": m.group(0),
                "to": normalized,
            })
        return normalized

    out = _EMAIL_PATTERN.sub(repl_email, out)

    def fix_o_in_digits(m: re.Match) -> str:
        s = m.group(0)
        if re.fullmatch(r"[0-9Oo]{4,}", s):
            fixed = s.replace("O", "0").replace("o", "0")
            if fixed != s:
                corrections.append({"type": "regex_digit_o", "from": s, "to": fixed})
            return fixed
        return s

    out = re.sub(r"[0-9Oo]{4,}", fix_o_in_digits, out)
    return out, corrections


def apply_semantic_correction(text: str) -> tuple[str, list[dict]]:
    """
    中文语料库语义矫正：短语精确替换 + 词表编辑距离 1 的保守纠错。
    """
    corpus = _load_corpus()
    corrections: list[dict] = []
    phrase_fixes: list[tuple[str, str]] = [
        (w, r) for w, r in corpus.get("phrase_fixes", []) if w and r and w != r
    ]
    phrase_fixes.sort(key=lambda x: len(x[0]), reverse=True)

    t = text
    for wrong, right in phrase_fixes:
        if wrong in t:
            t = t.replace(wrong, right)
            corrections.append({
                "type": "corpus_phrase",
                "from": wrong,
                "to": right,
            })

    vocab: set[str] = set(corpus.get("vocabulary", []))
    if not vocab:
        return t, corrections

    def repl_word(m: re.Match) -> str:
        word = m.group(0)
        if word in vocab:
            return word
        for candidate in vocab:
            if len(candidate) == len(word) and _edit_distance_one(word, candidate):
                corrections.append({
                    "type": "corpus_vocabulary",
                    "from": word,
                    "to": candidate,
                })
                return candidate
        return word

    t = _CJK_RUN.sub(repl_word, t)
    return t, corrections


def process_crnn_output(raw: str) -> tuple[str, str, list[dict]]:
    """
    完整后处理流水线。

    返回:
        original_text: 仅 strip 的原始拼接文本
        processed_text: 规则化 + 语义矫正后的文本
        corrections: 各步矫正记录（便于前端/论文展示）
    """
    original_text = raw.strip()

    s1 = _strip_and_remove_noise(raw)
    s2, regex_corrections = apply_regex_normalization(s1)
    s3, semantic_corrections = apply_semantic_correction(s2)
    processed_text = s3
    all_corrections = regex_corrections + semantic_corrections

    return original_text, processed_text, all_corrections


def join_words_result_to_raw_string(words_result: list | None) -> str:
    """从 Paddle 风格 words_result 拼成多行原始字符串。"""
    if not words_result or not isinstance(words_result, list):
        return ""
    lines: list[str] = []
    for item in words_result:
        if isinstance(item, dict):
            lines.append(str(item.get("words", "")))
    return "\n".join(lines)


def sync_words_result_with_processed(
    words_result: list,
    original_text: str,
    processed_text: str,
) -> None:
    """
    将后处理结果写回 words_result，使前端/导出与 processed_text 一致。
    单行或多行（行数一致）时按行对齐更新。
    """
    if not words_result or original_text == processed_text:
        return

    proc_lines = processed_text.split("\n")
    if len(words_result) == 1 and isinstance(words_result[0], dict):
        words_result[0]["words"] = processed_text.replace("\n", " ")
        return

    orig_lines = original_text.split("\n")
    if len(orig_lines) == len(proc_lines) == len(words_result):
        for item, text in zip(words_result, proc_lines):
            if isinstance(item, dict):
                item["words"] = text
