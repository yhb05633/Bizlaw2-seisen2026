"""Parses the ビジ法２精選 source text files into cards.js.

Source files live outside this repo and must never be modified by this
script. Chapter numbers/titles/counts come from the hardcoded CHAPTERS
table below, not from headings inside the source files (several files
have missing or wrong chapter headings).
"""
import json
import pathlib
import re

SOURCE_DIR = pathlib.Path(
    "/Volumes/Macmini M2PRO/専門スキル/法務書籍/Legalstudy2026/ビジ法検定_/ビジ法２精選"
)
OUTPUT_PATH = pathlib.Path(__file__).resolve().parent.parent / "cards.js"

CHAPTERS = [
    {"number": 1, "title": "企業取引・契約にかかわる法務", "count": 14},
    {"number": 2, "title": "企業財産の管理と法務", "count": 18},
    {"number": 3, "title": "企業間取引にかかわる法規制", "count": 9},
    {"number": 4, "title": "消費者との取引にかかわる法規制", "count": 12},
    {"number": 5, "title": "情報の管理と活用にかかわる法規制", "count": 3},
    {"number": 6, "title": "デジタル社会と法律", "count": 4},
    {"number": 7, "title": "広告・表示等に関する法規制", "count": 3},
    {"number": 8, "title": "金融・証券業等に関する法規制", "count": 4},
    {"number": 9, "title": "債権の担保", "count": 14},
    {"number": 10, "title": "債権の回収", "count": 9},
    {"number": 11, "title": "債務者の倒産への対応", "count": 9},
    {"number": 12, "title": "法的紛争等の予防と対応", "count": 18},
    {"number": 13, "title": "株式会社の組織と運営", "count": 34},
    {"number": 14, "title": "企業と従業員の関係", "count": 5},
    {"number": 15, "title": "企業活動と地域社会・行政等とのかかわり", "count": 5},
    {"number": 16, "title": "国際法務(渉外法務)", "count": 11},
]

BLOCK_START_RE = re.compile(r"^#{0,6}\s*第[0-9０-９]+問.*$", re.MULTILINE)
HEADING_LINE_RE = re.compile(r"^#{0,6}\s*第[0-9０-９]+問\s*[:：]?\s*(.*)$")
PAREN_RE = re.compile(r"[（(]([^）)]*)[）)]")
BOUNDARY_RE = re.compile(r"^(解答[・、]?解説|解答|正解)[:：]?\s*(.*)$")
ANSWER_VALUE_RE = re.compile(r"(?:正解|解答)[:：]\s*([^\n]+)")
SEPARATOR_RE = re.compile(r"^-{3,}$")


def normalize_label_line(line: str) -> str:
    s = line.strip()
    s = re.sub(r"^#+\s*", "", s)
    s = s.strip("*").strip()
    s = s.strip("【】").strip()
    return s


def split_into_question_blocks(text: str) -> list[str]:
    matches = list(BLOCK_START_RE.finditer(text))
    blocks = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        blocks.append(text[start:end].strip())
    return blocks


def parse_block(block_text: str) -> dict:
    lines = block_text.splitlines()
    heading_line = lines[0]
    body_lines = lines[1:]

    heading_match = HEADING_LINE_RE.match(heading_line.strip())
    rest = heading_match.group(1) if heading_match else ""
    paren_match = PAREN_RE.search(rest)
    exam_ref = paren_match.group(1).strip() if paren_match else ""

    boundary_idx = None
    inline_after = ""
    for i, line in enumerate(body_lines):
        norm = normalize_label_line(line)
        bm = BOUNDARY_RE.match(norm)
        if bm:
            boundary_idx = i
            inline_after = bm.group(2).strip()
            break

    if boundary_idx is None:
        raise ValueError(
            f"no answer/explanation boundary found in block: {heading_line!r}"
        )

    def is_question_noise(line: str) -> bool:
        norm = normalize_label_line(line)
        return norm in ("設問", "問題") or SEPARATOR_RE.match(line.strip()) is not None

    question_lines = body_lines[:boundary_idx]
    question_text = "\n".join(
        l for l in question_lines if not is_question_noise(l)
    ).strip()

    after_lines = body_lines[boundary_idx + 1 :]
    if inline_after:
        after_lines = [inline_after] + after_lines

    def is_explanation_noise(line: str) -> bool:
        norm = normalize_label_line(line)
        return norm == "解説" or SEPARATOR_RE.match(line.strip()) is not None

    explanation_source = [l for l in after_lines if not is_explanation_noise(l)]
    explanation_text = "\n".join(explanation_source).strip()

    answer_match = ANSWER_VALUE_RE.search(explanation_text)
    if answer_match:
        answer = answer_match.group(1).strip().strip("*").strip()
    else:
        answer = next((l.strip() for l in explanation_source if l.strip()), "")

    return {
        "examRef": exam_ref,
        "question": question_text,
        "answer": answer,
        "explanation": explanation_text,
    }
