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

CHOICE_MARKER_CHARS = "①②③④⑤⑥⑦⑧⑨⑩"
FULLWIDTH_DIGITS = {
    "０": "0", "１": "1", "２": "2", "３": "3", "４": "4",
    "５": "5", "６": "6", "７": "7", "８": "8", "９": "9",
}
CHOICE_LINE_RE = re.compile(
    r"^(?:[*\-]\s+)?\*{0,2}(?:([①-⑩])|([0-9０-９])[.．、\)）]?)\*{0,2}\s*(.*)$"
)
HEADING_NUMBER_RE = re.compile(r"^#{0,6}\s*第([0-9０-９]+)問")
ANSWER_PAREN_NUMBER_RE = re.compile(r"^[（(]\s*([0-9０-９])\s*[）)]\s*$")

KATAKANA_COMBO_RE = re.compile(r"^[アイウエオカキクケコ]{2,}$")
OX_LINE_RE = re.compile(
    r"^[ア-ン]\s*[-－：―]\s*[〇✕]"
    r"(?:\s*[、/／,，]?\s*[ア-ン]\s*[-－：―]\s*[〇✕])*$"
)
OX_TOKEN_RE = re.compile(r"([ア-ン])\s*[-－：―]\s*([〇✕])")


def normalize_choice_text(text: str) -> str:
    if KATAKANA_COMBO_RE.match(text):
        return "・".join(text)
    if OX_LINE_RE.match(text):
        tokens = OX_TOKEN_RE.findall(text)
        return "、".join(f"{letter}－{symbol}" for letter, symbol in tokens)
    return text


ANSWER_PAREN_GROUP_RE = re.compile(r"^(.*?)[（(](.+)[）)]\s*$")


def normalize_answer_text(answer: str) -> str:
    # The "answer" field often repeats the same combination text shown in
    # `choices` (e.g. "①（ア：〇 イ：〇...）"), just wrapped in a leading
    # marker and parentheses instead of standing alone. Normalize that
    # inner text the same way, so the back-of-card "正解：..." line never
    # shows a different separator style than the front-of-card choice it
    # restates.
    m = ANSWER_PAREN_GROUP_RE.match(answer)
    if not m:
        return answer
    prefix, inner = m.group(1), m.group(2)
    normalized_inner = normalize_choice_text(inner)
    if normalized_inner == inner:
        return answer
    return f"{prefix}（{normalized_inner}）"


def to_int(s: str) -> int:
    return int("".join(FULLWIDTH_DIGITS.get(ch, ch) for ch in s))


def normalize_title_line(line: str) -> str:
    s = normalize_label_line(line)
    s = re.sub(r"^[0-9０-９]+[\s　]+", "", s)
    return s


TITLE_NOISE_WORDS = {"設問", "問題"}


def extract_titles(text: str) -> list[str]:
    matches = list(BLOCK_START_RE.finditer(text))
    titles = []
    prev_end = 0
    last_title = ""
    for m in matches:
        gap = text[prev_end:m.start()]
        candidate = None
        for line in reversed(gap.splitlines()):
            s = line.strip()
            if s == "" or SEPARATOR_RE.match(s):
                continue
            # Per-choice explanation bullets ("* **ア：適切でない。**",
            # "* **①：適切である。**") are markdown list items and are the
            # most common non-blank line right before the next question's
            # heading when no new subsection title was actually given (i.e.
            # this and the previous question share one title). They must
            # not be mistaken for a title line, so bullet-prefixed lines
            # are never candidates, regardless of their own decoration.
            if re.match(r"^[*\-]\s", s):
                continue
            if BLOCK_START_RE.match(s):
                continue
            norm = normalize_label_line(s)
            if BOUNDARY_RE.match(norm) or norm in TITLE_NOISE_WORDS:
                continue
            if not re.match(r"^[#*]|^【", s):
                continue
            title_norm = normalize_title_line(s)
            if title_norm == "":
                continue
            candidate = title_norm
            break
        title = candidate if candidate is not None else last_title
        titles.append(title)
        last_title = title
        prev_end = m.start()
    return titles


def _marker_value(circled, digit):
    if circled:
        return CHOICE_MARKER_CHARS.index(circled) + 1
    d = FULLWIDTH_DIGITS.get(digit, digit)
    return int(d)


def split_prompt_and_choices(question_text: str):
    lines = question_text.split("\n")
    nonblank = [(i, l) for i, l in enumerate(lines) if l.strip() != ""]

    marker_positions = []
    for pos, (_, line) in enumerate(nonblank):
        m = CHOICE_LINE_RE.match(line.strip())
        if m:
            marker_positions.append((pos, _marker_value(m.group(1), m.group(2))))

    run = []
    if marker_positions:
        last_nonblank_pos = len(nonblank) - 1
        if marker_positions[-1][0] == last_nonblank_pos:
            run = [marker_positions[-1]]
            for entry in reversed(marker_positions[:-1]):
                prev_pos, prev_val = run[-1]
                pos, val = entry
                if pos == prev_pos - 1 and val == prev_val - 1:
                    run.append(entry)
                else:
                    break
            run.reverse()
            if len(run) < 3 or run[0][1] != 1:
                run = []

    if run:
        start_nonblank_pos = run[0][0]
        start_line_idx = nonblank[start_nonblank_pos][0]
        prompt = "\n".join(lines[:start_line_idx]).strip()
        choices = []
        for pos, _ in run:
            line_idx, line = nonblank[pos]
            m = CHOICE_LINE_RE.match(line.strip())
            text = normalize_choice_text(m.group(3).strip().replace("**", ""))
            marker_val = _marker_value(m.group(1), m.group(2))
            marker_char = CHOICE_MARKER_CHARS[marker_val - 1]
            choices.append(f"{marker_char} {text}")
        return prompt, choices, False

    return question_text, [], True


def compute_answer_index(answer: str):
    stripped = answer.strip()
    m = CHOICE_LINE_RE.match(stripped)
    if m:
        return _marker_value(m.group(1), m.group(2)) - 1
    # Some source files (e.g. 02.txt) give the answer as a fullwidth-paren
    # arabic digit like "（2）" even though the question's own choices are
    # circled markers (①②③...). The digit is a 1-based choice position
    # either way, so it converts the same way as any other marker.
    m2 = ANSWER_PAREN_NUMBER_RE.match(stripped)
    if m2:
        return to_int(m2.group(1)) - 1
    return None


def normalize_label_line(line: str) -> str:
    s = line.strip()
    s = re.sub(r"^#+\s*", "", s)
    s = s.strip("*").strip()
    s = s.strip("【】").strip()
    return s


def _clean_value(s: str) -> str:
    return s.strip().strip("*").strip()


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

    num_match = HEADING_NUMBER_RE.match(heading_line.strip())
    question_number = to_int(num_match.group(1)) if num_match else None

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
        if norm == "解説" or SEPARATOR_RE.match(line.strip()) is not None:
            return True
        return re.match(r"^#{1,6}[\s　]", line.strip()) is not None

    explanation_source = [l for l in after_lines if not is_explanation_noise(l)]
    explanation_text = "\n".join(explanation_source).strip()

    answer_match = ANSWER_VALUE_RE.search(explanation_text)
    if answer_match:
        answer = _clean_value(answer_match.group(1))
    else:
        answer = next(
            (_clean_value(l) for l in explanation_source if l.strip()),
            "",
        )

    return {
        "examRef": exam_ref,
        "question": question_text,
        "answer": answer,
        "explanation": explanation_text,
        "questionNumber": question_number,
    }


def write_cards_js(cards: list[dict]) -> None:
    chapters_json = json.dumps(CHAPTERS, ensure_ascii=False, indent=2)
    cards_json = json.dumps(cards, ensure_ascii=False, indent=2)
    content = f"const CHAPTERS = {chapters_json};\n\nconst CARDS = {cards_json};\n"
    OUTPUT_PATH.write_text(content, encoding="utf-8")


def main() -> None:
    all_cards = []
    errors = []
    prose_count = 0
    unscored_count = 0

    for chapter in CHAPTERS:
        file_path = SOURCE_DIR / f"{chapter['number']:02d}.txt"
        text = file_path.read_text(encoding="utf-8")
        blocks = split_into_question_blocks(text)
        titles = extract_titles(text)

        if len(blocks) != chapter["count"]:
            errors.append(
                f"{file_path.name}: expected {chapter['count']} questions, "
                f"found {len(blocks)}"
            )

        for i, block in enumerate(blocks, start=1):
            try:
                parsed = parse_block(block)
            except ValueError as e:
                errors.append(f"{file_path.name} question {i}: {e}")
                continue

            title = titles[i - 1] if i - 1 < len(titles) else ""
            prompt, choices, is_prose = split_prompt_and_choices(parsed["question"])
            answer = normalize_answer_text(parsed["answer"])
            answer_index = compute_answer_index(answer)
            if is_prose:
                prose_count += 1
            if answer_index is None:
                unscored_count += 1

            all_cards.append(
                {
                    "id": f"{chapter['number']}-{i}",
                    "chapter": chapter["number"],
                    "chapterTitle": chapter["title"],
                    "questionNumber": parsed["questionNumber"] or i,
                    "title": title,
                    "examRef": parsed["examRef"],
                    "isProse": is_prose,
                    "prompt": prompt,
                    "choices": choices,
                    "answerIndex": answer_index,
                    "answer": answer,
                    "explanation": parsed["explanation"],
                }
            )

    if errors:
        print("パースに問題があります:")
        for e in errors:
            print(f"  - {e}")
        raise SystemExit(1)

    write_cards_js(all_cards)
    print(f"OK: {len(all_cards)} 問を書き出しました -> {OUTPUT_PATH}")
    print(f"  地の文表示(選択肢抽出不可)にフォールバックした問題数: {prose_count}")
    print(f"  正解位置を判定できなかった問題数(採点対象外): {unscored_count}")


if __name__ == "__main__":
    main()
