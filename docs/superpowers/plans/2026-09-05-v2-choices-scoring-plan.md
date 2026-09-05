# Bizlaw2-seisen2026 v2 (選択肢・成績機能) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the existing flashcard app so every card has a uniform display (chapter/title header, no spoiler bold in choices, examRef at the bottom), lets the user select/toggle an answer choice (or, for "下線部" questions, an underlined span), tracks per-session correctness with a score overlay, gives each card a persistent 0-10 "star" attempt counter, and makes できた/苦手 togglable off.

**Architecture:** `scripts/parse_cards.py` gains a v2 schema: per-question `title` (extracted from the text between consecutive question headings), `questionNumber` (the literal heading number), `prompt`/`choices`/`isProse` (question text split into the setup text and a clean list of choice strings, or a prose fallback when choices can't be cleanly isolated), and `answerIndex` (0-based position of the correct choice, derived from the existing `answer` string). `index.html` is rewritten to consume this new shape: a persistent card header, choice/underline click-to-select, a session-scoped score tracker with an overlay, a per-card star counter, and toggle-off progress buttons.

**Tech Stack:** Same as v1 — Python 3 stdlib for the parser, vanilla HTML/CSS/JS for the app, `localStorage` for persistence, no external libraries.

## Global Constraints

- No external JS/CSS libraries — vanilla only, matching the existing app.
- Source `.txt` files must never be modified by the parser.
- Chapter number/title/count still come only from the hardcoded `CHAPTERS` table — unchanged from v1.
- Difficulty (難易度) is explicitly out of scope — do not add a difficulty field or display, even though earlier drafts considered it.
- Progress (できた/苦手), star counts, and answer choices persist only in `localStorage`, keyed per card id — no server, no cross-device sync.
- Session score resets every time `startChapter()` runs (opening a chapter or "すべて") — it is never persisted to `localStorage`.
- Questions where choices can't be cleanly isolated (the "下線部" `<u>`-tag questions, and the handful of irregular-format questions identified during design — see below) must gracefully fall back to prose display rather than guessing at a broken choice split. This fallback must be visible in the generated data (`isProse: true`), not silently mishandled.
- No automated frontend test framework — frontend tasks are verified by manual/static checks against the real generated data, per the existing project convention.

### Known exceptions to plan for explicitly

Verified once against the current real source data (results may shift slightly if the source `.txt` files are edited again before this plan is executed — the parser's own validation, not this list, is authoritative):

- **Prose-only questions (`isProse: true`, no discrete choices):** questions whose choices are inline `<u>...</u>` underlined spans within a paragraph rather than separate lines. Confirmed in chapters 1, 4, 9, 13, 15 (one question each).
- **Questions expected to fall back to prose display for structural reasons** (a trailing annotation line after the choices, or a choice whose text wraps onto a continuation line): at least chapter 2 question 10 and chapter 12 question 15. The parser's choice-extraction algorithm (Task 1) is deliberately conservative — it only extracts a clean choice list when every choice is exactly one line and the list runs to the very end of the question text — so it will correctly fall back to prose (`isProse: true`) for these without special-casing them by id.
- **Some questions use 6 choices (①〜⑥), not 5** (confirmed: chapter 8 question 1) — the parser must not hardcode a maximum of 5.
- **A few questions use plain arabic markers (`1．`〜`5．`) instead of circled digits** — the parser must recognize both.

---

## File Structure

- `scripts/parse_cards.py` — extended with title extraction, question-number extraction, and prompt/choices/isProse/answerIndex extraction. Same file as v1, no new files.
- `scripts/test_parse_cards.py` — extended with new unit tests for the new extraction functions.
- `cards.js` — regenerated with the new fields.
- `index.html` — rewritten (in place) to render the new schema and new interactions. Same single file as v1.

---

## Task 1: Parser v2 — title, question number, choices, isProse, answerIndex

**Files:**
- Modify: `scripts/parse_cards.py`
- Modify: `scripts/test_parse_cards.py`
- Modify (generated): `cards.js`

**Interfaces:**
- Produces: `extract_titles(text: str) -> list[str]`, `split_prompt_and_choices(question_text: str) -> tuple[str, list[str], bool]` (returns `(prompt, choices, is_prose)`), `compute_answer_index(answer: str) -> int | None`.
- Modifies: `parse_block` now also returns `"questionNumber": int` in its dict. `main()` now builds cards with the v2 field set below instead of the old flat `question` field.
- Produces (per-card schema in `cards.js`): `{id, chapter, chapterTitle, questionNumber, title, examRef, isProse, prompt, choices, answerIndex, answer, explanation}`. The old flat `question` field is removed — every consumer (the frontend, in Task 2) uses `prompt`/`choices`/`isProse` instead.

### Background the implementer needs

The current `scripts/parse_cards.py` (from v1) has these functions already, unchanged: `normalize_label_line`, `split_into_question_blocks`, `parse_block` (returns `examRef`/`question`/`answer`/`explanation`), `write_cards_js`, `main`. This task extends `parse_block` and adds new functions; it does not change the existing boundary-detection logic (`BOUNDARY_RE`, `ANSWER_VALUE_RE`, the question/answer split) at all.

**Title extraction:** every question in the real data is preceded by a short "title" line (a subsection heading, in wildly different raw formats depending on the chapter — `### タイトル`, `## タイトル`, `####　タイトル` with an ideographic space, or even a bare `**タイトル` with no closing asterisks and no `#` at all in one chapter). Rather than trying to match every heading-level variant, extract the title generically: for each question, look at the raw text *between the end of the previous question and the start of this question's heading* (the "gap"), and take the last non-blank, non-separator line in that gap, with `#`/`*`/`【】` decoration and any repeated exam-file numbering stripped. This was validated against all 172 real questions during design and found a title candidate for every single one (i.e., the "inherit previous question's title" fallback is a safety net that should not currently trigger, but must still be implemented for future data edits).

**Choice extraction:** most questions list their choices as 4-6 separate lines, each starting with a marker (circled `①`-`⑥`, or arabic `1.`-`6.`), optionally wrapped in `**bold**` (sometimes only the correct choice is bold — this is a real defect in the source data being fixed: choices must render identically regardless of source bolding). A small number of questions can't be cleanly split (see Global Constraints above) — for those, the whole question becomes `prompt` with `choices: []` and `isProse: true`, and the frontend (Task 2) displays it as continuous text (with real `<u>` underlines when present, made individually selectable).

**Answer index:** the existing `answer` field (e.g. `"④（ア－✕、イ－〇、ウ－〇、エ－✕）"` or `"③"` or `"1"`) always starts with the same kind of marker used by that question's choices. Parse just the leading marker to get a 1-based position, then convert to a 0-based index for comparing against the user's selected choice. If the leading token isn't a recognized marker, use `None` — the frontend must handle a `null` `answerIndex` by not attempting to score that card, without crashing.

- [ ] **Step 1: Add new constants and helper functions to `scripts/parse_cards.py`**

Add these near the existing constants (after `SEPARATOR_RE = re.compile(r"^-{3,}$")`):

```python
CHOICE_MARKER_CHARS = "①②③④⑤⑥⑦⑧⑨⑩"
FULLWIDTH_DIGITS = {
    "０": "0", "１": "1", "２": "2", "３": "3", "４": "4",
    "５": "5", "６": "6", "７": "7", "８": "8", "９": "9",
}
CHOICE_LINE_RE = re.compile(
    r"^(?:[*\-]\s+)?\*{0,2}(?:([①-⑩])|([0-9０-９])[.．、\)）]?)\*{0,2}\s*(.*)$"
)
HEADING_NUMBER_RE = re.compile(r"^#{0,6}\s*第([0-9０-９]+)問")


def to_int(s: str) -> int:
    return int("".join(FULLWIDTH_DIGITS.get(ch, ch) for ch in s))


def normalize_title_line(line: str) -> str:
    s = normalize_label_line(line)
    s = re.sub(r"^[0-9０-９]+[\s　]+", "", s)
    return s


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
            norm = normalize_title_line(s)
            if norm == "":
                continue
            candidate = norm
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
    if "<u>" in question_text:
        return question_text, [], True

    lines = question_text.split("\n")
    nonblank = [(i, l) for i, l in enumerate(lines) if l.strip() != ""]

    marker_positions = []
    for pos, (_, line) in enumerate(nonblank):
        m = CHOICE_LINE_RE.match(line.strip())
        if m:
            marker_positions.append((pos, _marker_value(m.group(1), m.group(2))))

    if not marker_positions:
        return question_text, [], True

    last_nonblank_pos = len(nonblank) - 1
    if marker_positions[-1][0] != last_nonblank_pos:
        return question_text, [], True

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
        return question_text, [], True

    start_nonblank_pos = run[0][0]
    start_line_idx = nonblank[start_nonblank_pos][0]

    prompt = "\n".join(lines[:start_line_idx]).strip()

    choices = []
    for pos, _ in run:
        line_idx, line = nonblank[pos]
        m = CHOICE_LINE_RE.match(line.strip())
        text = m.group(3).strip().replace("**", "")
        marker_val = _marker_value(m.group(1), m.group(2))
        marker_char = CHOICE_MARKER_CHARS[marker_val - 1]
        choices.append(f"{marker_char} {text}")

    return prompt, choices, False


def compute_answer_index(answer: str):
    m = CHOICE_LINE_RE.match(answer.strip())
    if not m:
        return None
    return _marker_value(m.group(1), m.group(2)) - 1
```

- [ ] **Step 2: Modify `parse_block` to also extract the question number**

Find this existing line in `parse_block`:

```python
    heading_match = HEADING_LINE_RE.match(heading_line.strip())
```

Immediately after the existing 4 lines that use `heading_match` (the block ending with `exam_ref = paren_match.group(1).strip() if paren_match else ""`), add:

```python
    num_match = HEADING_NUMBER_RE.match(heading_line.strip())
    question_number = to_int(num_match.group(1)) if num_match else None
```

Then find the `return` statement at the end of `parse_block`:

```python
    return {
        "examRef": exam_ref,
        "question": question_text,
        "answer": answer,
        "explanation": explanation_text,
    }
```

Replace it with:

```python
    return {
        "examRef": exam_ref,
        "question": question_text,
        "answer": answer,
        "explanation": explanation_text,
        "questionNumber": question_number,
    }
```

- [ ] **Step 3: Rewrite `main()` to build the v2 card shape**

Replace the entire `main()` function with:

```python
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
            answer_index = compute_answer_index(parsed["answer"])
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
                    "answer": parsed["answer"],
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
```

- [ ] **Step 4: Add unit tests to `scripts/test_parse_cards.py`**

Add these imports at the top (alongside the existing `from parse_cards import split_into_question_blocks, parse_block`):

```python
from parse_cards import (
    split_into_question_blocks,
    parse_block,
    extract_titles,
    split_prompt_and_choices,
    compute_answer_index,
)
```

Add a new test class:

```python
class TestExtractTitles(unittest.TestCase):
    def test_extracts_one_title_per_question_various_heading_styles(self):
        text = (
            "## 第１章 テスト\n\n"
            "### 行為能力\n"
            "#### 第1問（第45回 第3問 3-3）\n"
            "本文A\n\n"
            "##### 【解答・解説】\n"
            "**正解：①**\n\n"
            "---\n\n"
            "####　株主総会\n"
            "##### 第2問（第40回 第1問 1-1）\n"
            "本文B\n\n"
            "##### 【解答・解説】\n"
            "**正解：②**\n"
        )
        titles = extract_titles(text)
        self.assertEqual(titles, ["行為能力", "株主総会"])

    def test_falls_back_to_previous_title_when_missing(self):
        text = (
            "### 独占禁止法\n"
            "#### 第1問（第1回 第1問 1-1）\n"
            "本文A\n\n"
            "##### 【解答・解説】\n"
            "**正解：①**\n\n"
            "#### 第2問（第1回 第2問 2-1）\n"
            "本文B\n\n"
            "##### 【解答・解説】\n"
            "**正解：②**\n"
        )
        titles = extract_titles(text)
        self.assertEqual(titles, ["独占禁止法", "独占禁止法"])


class TestSplitPromptAndChoices(unittest.TestCase):
    def test_splits_clean_five_choice_question(self):
        question = (
            "次のア〜オのうち適切なものの組み合わせを選びなさい。\n\n"
            "ア．文A\n"
            "イ．文B\n\n"
            "① アイ\n"
            "② **アウ**\n"
            "③ アエ\n"
            "④ アオ\n"
            "⑤ イウ"
        )
        prompt, choices, is_prose = split_prompt_and_choices(question)
        self.assertFalse(is_prose)
        self.assertEqual(len(choices), 5)
        self.assertEqual(choices[0], "① アイ")
        self.assertEqual(choices[1], "② アウ")
        self.assertNotIn("*", choices[1])

    def test_supports_six_choices(self):
        lines = "\n".join(f"{c} 選択肢{c}" for c in "①②③④⑤⑥")
        question = "設問文\n\n" + lines
        prompt, choices, is_prose = split_prompt_and_choices(question)
        self.assertFalse(is_prose)
        self.assertEqual(len(choices), 6)

    def test_supports_arabic_markers(self):
        lines = "\n".join(f"{n}．選択肢{n}" for n in range(1, 6))
        question = "設問文\n\n" + lines
        prompt, choices, is_prose = split_prompt_and_choices(question)
        self.assertFalse(is_prose)
        self.assertEqual(len(choices), 5)
        self.assertTrue(choices[0].startswith("①"))

    def test_falls_back_to_prose_when_u_tag_present(self):
        question = "本文①<u>下線部分</u>と②<u>別の下線部分</u>です。"
        prompt, choices, is_prose = split_prompt_and_choices(question)
        self.assertTrue(is_prose)
        self.assertEqual(choices, [])
        self.assertEqual(prompt, question)

    def test_falls_back_to_prose_when_trailing_note_after_choices(self):
        question = (
            "設問文\n\n"
            "① アイ\n"
            "② アウ\n"
            "③ アエ\n\n"
            "※注記があります。"
        )
        prompt, choices, is_prose = split_prompt_and_choices(question)
        self.assertTrue(is_prose)
        self.assertEqual(choices, [])

    def test_falls_back_to_prose_when_choice_has_continuation_line(self):
        question = (
            "設問文\n\n"
            "① 甲「質問1」\n"
            "   乙「回答1」\n"
            "② 甲「質問2」\n"
            "   乙「回答2」\n"
            "③ 甲「質問3」\n"
            "   乙「回答3」"
        )
        prompt, choices, is_prose = split_prompt_and_choices(question)
        self.assertTrue(is_prose)
        self.assertEqual(choices, [])


class TestComputeAnswerIndex(unittest.TestCase):
    def test_circled_marker(self):
        self.assertEqual(compute_answer_index("④（ア－✕、イ－〇）"), 3)

    def test_bare_circled_marker(self):
        self.assertEqual(compute_answer_index("①"), 0)

    def test_arabic_marker(self):
        self.assertEqual(compute_answer_index("1"), 0)

    def test_unrecognized_returns_none(self):
        self.assertIsNone(compute_answer_index("該当なし"))
```

- [ ] **Step 5: Run the tests and confirm they pass**

Run: `python3 -m unittest scripts/test_parse_cards.py -v` (from the project root)
Expected: all tests pass (the 11 existing ones plus the new ones from Step 4).

- [ ] **Step 6: Regenerate the data against the real source files**

Run: `python3 scripts/parse_cards.py`
Expected: `OK: 172 問を書き出しました`, followed by the two new summary lines (prose-fallback count and unscored count). Record both numbers in your report — they are expected to be small (roughly 5-10 and 0-5 respectively, based on the design investigation), not large. If either number is much larger than expected, something is probably wrong with `split_prompt_and_choices` or `compute_answer_index` — investigate a few real fallback cases from the printed chapter/question errors before proceeding (there are none printed for prose/unscored counts specifically, so cross-reference by loading `cards.js` and filtering `CARDS.filter(c => c.isProse)` / `CARDS.filter(c => c.answerIndex === null)` to see which ids they are).

- [ ] **Step 7: Sanity-check the generated `cards.js`**

Load it with Python (`content = open('cards.js', encoding='utf-8').read(); ...; cards = json.loads(...)` as in prior tasks) and confirm:
- Every card has the keys `id, chapter, chapterTitle, questionNumber, title, examRef, isProse, prompt, choices, answerIndex, answer, explanation` (no leftover `question` key).
- No card has an empty `title`.
- For a card with `isProse: false`, `choices` has 3-6 entries and none contain a literal `*` character.
- For at least one card you identify as one of the known `<u>`-tag questions (search `cards.js` for `<u>` in the `prompt` field), confirm `isProse` is `true` and `choices` is `[]`.

- [ ] **Step 8: Commit**

```bash
git add scripts/parse_cards.py scripts/test_parse_cards.py cards.js
git commit -m "feat: add title/choices/isProse/answerIndex extraction (v2 schema)"
```

---

## Task 2: Frontend v2 — header, choice/prose selection, explanation formatting, toggle-off, star counter, scoring

**Files:**
- Modify: `index.html` (full-file rewrite of the card-related markup/CSS/JS — the chapter-list screen and PWA registration are unchanged from v1)

**Interfaces:**
- Consumes: the v2 `cards.js` shape from Task 1 (`prompt`, `choices`, `isProse`, `answerIndex`, `questionNumber`, `title`, plus the unchanged `chapter`, `chapterTitle`, `examRef`, `answer`, `explanation`).
- Produces: no new files; this is the final consumer of the v2 schema.

### What must change from the current `index.html`

The current file (from v1) has: a chapter-list screen (unchanged by this task), and a card-study screen with `#card` containing `.card-face.card-front` (with `#exam-ref`, `#question-text`) and `.card-face.card-back` (with `#answer-text`), a slider, prev/next buttons, できた/苦手 buttons, and a service-worker registration at the end of the script. This task replaces the entire card-study screen's markup, its CSS block, and essentially all of its JS below `renderChapterList()`, while preserving: the chapter-list screen's HTML/CSS/JS exactly as-is, and the service-worker registration exactly as-is (`navigator.serviceWorker.register('./sw.js').catch(() => {});`, at the very end of the script, after everything else).

Write the complete file below verbatim.

- [ ] **Step 1: Replace `index.html` with this complete content**

```html
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>ビジ法2級 精選フラッシュカード</title>
<link rel="manifest" href="manifest.json">
<link rel="apple-touch-icon" href="icon-180.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#1d4ed8">
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", sans-serif;
    background: #f5f5f4;
    color: #1c1917;
  }
  h1 { font-size: 1.1rem; padding: 16px; margin: 0; }
  #chapter-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 0 16px 16px;
  }
  .chapter-item {
    text-align: left;
    padding: 14px 16px;
    border-radius: 10px;
    border: 1px solid #d6d3d1;
    background: white;
    font-size: 1rem;
    cursor: pointer;
  }
  .chapter-item:active { background: #e7e5e4; }
  .toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    padding: 12px 16px;
  }
  .toolbar button {
    padding: 8px 12px;
    border-radius: 8px;
    border: 1px solid #d6d3d1;
    background: white;
  }
  #progress-label { flex: 1; text-align: center; font-size: 0.9rem; }
  #slider { width: calc(100% - 32px); margin: 0 16px 8px; }
  .nav-buttons {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    padding: 0 16px 16px;
  }
  .nav-buttons button {
    flex: 1;
    padding: 12px;
    border-radius: 8px;
    border: 1px solid #d6d3d1;
    background: white;
    font-size: 1rem;
  }
  .progress-buttons {
    display: flex;
    gap: 12px;
    padding: 0 16px 24px;
  }
  .progress-buttons button {
    flex: 1;
    padding: 12px;
    border-radius: 8px;
    border: 1px solid #d6d3d1;
    background: white;
    font-size: 1rem;
  }
  .progress-buttons button.active { color: white; }
  #btn-ok.active { background: #16a34a; border-color: #16a34a; }
  #btn-ng.active { background: #dc2626; border-color: #dc2626; }
  #card {
    margin: 0 16px 16px;
    border: 1px solid #d6d3d1;
    border-radius: 12px;
    background: white;
    overflow: hidden;
  }
  .card-header {
    padding: 14px 20px 0;
  }
  .chapter-line { font-size: 0.75rem; color: #78716c; }
  .question-line { font-size: 0.95rem; font-weight: bold; margin-top: 2px; }
  .card-face {
    padding: 12px 20px 20px;
    min-height: 220px;
    cursor: pointer;
  }
  .card-back { display: none; }
  #card.flipped .card-front { display: none; }
  #card.flipped .card-back { display: block; }
  .exam-ref { font-size: 0.8rem; color: #78716c; margin-top: 16px; }
  .tap-hint { font-size: 0.8rem; color: #a8a29e; margin-top: 16px; }
  #question-text p, #answer-text p { line-height: 1.6; margin: 0 0 10px; }
  #question-text ul, #answer-text ul { margin: 0 0 10px; padding-left: 1.4em; }
  #answer-text li { margin-bottom: 1em; }
  #answer-text li:last-child { margin-bottom: 0; }
  .choice {
    padding: 12px 14px;
    border: 1px solid #d6d3d1;
    border-radius: 8px;
    margin-bottom: 8px;
    font-size: 1rem;
    font-weight: normal;
    line-height: 1.5;
    cursor: pointer;
  }
  .choice.selected { background: #1c1917; color: white; border-color: #1c1917; }
  #question-text u.choice-span { cursor: pointer; text-decoration-thickness: 2px; }
  #question-text u.choice-span.selected { background: #1c1917; color: white; }
  .star-row-container {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 20px;
    border-top: 1px solid #e7e5e4;
  }
  .star-row { font-size: 1.05rem; letter-spacing: 2px; color: #d97706; }
  #btn-star-reset {
    font-size: 0.75rem;
    padding: 6px 10px;
    border-radius: 6px;
    border: 1px solid #d6d3d1;
    background: white;
  }
  .overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
  }
  .overlay-content {
    background: white;
    border-radius: 12px;
    padding: 20px;
    max-width: 400px;
    width: 100%;
    max-height: 80vh;
    overflow-y: auto;
  }
  .overlay-content h2 { margin-top: 0; font-size: 1.1rem; }
  .overlay-content ul { padding-left: 1.2em; }
  .overlay-content button {
    margin-top: 12px;
    width: 100%;
    padding: 12px;
    border-radius: 8px;
    border: 1px solid #d6d3d1;
    background: white;
  }
</style>
</head>
<body>
<div id="chapter-screen">
  <h1>ビジ法2級 精選フラッシュカード</h1>
  <div id="chapter-list"></div>
</div>
<div id="card-screen" hidden>
  <div class="toolbar">
    <button id="btn-back">← 章一覧</button>
    <span id="progress-label"></span>
    <button id="btn-score">成績を見る</button>
  </div>
  <input type="range" id="slider" min="1" max="1" value="1">
  <div id="card">
    <div class="card-header">
      <div class="chapter-line" id="header-chapter"></div>
      <div class="question-line" id="header-question"></div>
    </div>
    <div class="card-face card-front">
      <div id="question-text"></div>
      <div id="choices-container"></div>
      <div class="exam-ref" id="exam-ref"></div>
      <div class="tap-hint">タップして解答を見る</div>
    </div>
    <div class="card-face card-back">
      <div id="answer-text"></div>
    </div>
    <div class="star-row-container">
      <div class="star-row" id="star-row"></div>
      <button id="btn-star-reset">実施回数リセット</button>
    </div>
  </div>
  <div class="nav-buttons">
    <button id="btn-prev">前へ</button>
    <button id="btn-next">次へ</button>
  </div>
  <div class="progress-buttons">
    <button id="btn-ng">苦手</button>
    <button id="btn-ok">できた</button>
  </div>
</div>
<div class="overlay" id="score-overlay" hidden>
  <div class="overlay-content">
    <h2>成績</h2>
    <p id="score-summary"></p>
    <ul id="score-list"></ul>
    <button id="btn-score-close">閉じる</button>
  </div>
</div>

<script src="cards.js"></script>
<script>
function renderChapterList() {
  const container = document.getElementById('chapter-list');
  container.innerHTML = '';

  const allBtn = document.createElement('button');
  allBtn.className = 'chapter-item';
  allBtn.textContent = `すべて［${CARDS.length}問］`;
  allBtn.addEventListener('click', () => startChapter('all'));
  container.appendChild(allBtn);

  for (const ch of CHAPTERS) {
    const btn = document.createElement('button');
    btn.className = 'chapter-item';
    btn.textContent = `第${ch.number}章 ${ch.title}［${ch.count}問］`;
    btn.addEventListener('click', () => startChapter(ch.number));
    container.appendChild(btn);
  }
}

let currentCards = [];
let currentIndex = 0;
let isFlipped = false;
let selectedChoiceIndex = null;
let sessionResults = {};

const PROGRESS_KEY_PREFIX = 'bizlaw2seisen:progress:';
const STAR_KEY_PREFIX = 'bizlaw2seisen:stars:';
const MAX_STARS = 10;
const JUDGMENT_RE = /(最も)?(適切|正しい|誤り)(（[〇✕○×]）)?(である|でない|くない)?/;

function getChapterMeta(chapterNumber) {
  return CHAPTERS.find((c) => c.number === chapterNumber);
}

function getProgress(id) {
  try {
    return localStorage.getItem(PROGRESS_KEY_PREFIX + id) || '';
  } catch (e) {
    return '';
  }
}

function setProgress(id, status) {
  const current = getProgress(id);
  const next = current === status ? '' : status;
  try {
    if (next === '') {
      localStorage.removeItem(PROGRESS_KEY_PREFIX + id);
    } else {
      localStorage.setItem(PROGRESS_KEY_PREFIX + id, next);
    }
  } catch (e) {
    // localStorage unavailable (private mode, etc.) — ignore, state just won't persist
  }
  updateProgressButtons(id);
}

function updateProgressButtons(id) {
  const status = getProgress(id);
  document.getElementById('btn-ok').classList.toggle('active', status === 'ok');
  document.getElementById('btn-ng').classList.toggle('active', status === 'ng');
}

function getStarCount(id) {
  try {
    const raw = parseInt(localStorage.getItem(STAR_KEY_PREFIX + id), 10);
    return Number.isFinite(raw) ? Math.min(MAX_STARS, Math.max(0, raw)) : 0;
  } catch (e) {
    return 0;
  }
}

function incrementStarCount(id) {
  const current = getStarCount(id);
  if (current >= MAX_STARS) return;
  try {
    localStorage.setItem(STAR_KEY_PREFIX + id, String(current + 1));
  } catch (e) {
    // ignore
  }
  renderStarRow(id);
}

function resetStarCount(id) {
  try {
    localStorage.removeItem(STAR_KEY_PREFIX + id);
  } catch (e) {
    // ignore
  }
  renderStarRow(id);
}

function renderStarRow(id) {
  const count = getStarCount(id);
  const row = document.getElementById('star-row');
  let stars = '';
  for (let i = 0; i < MAX_STARS; i++) {
    stars += i < count ? '★' : '☆';
  }
  row.textContent = stars;
}

function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function formatText(text) {
  const lines = text.split('\n');
  let html = '';
  let inList = false;
  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (line === '') {
      if (inList) { html += '</ul>'; inList = false; }
      continue;
    }
    const isBullet = /^[*\-]\s+/.test(line);
    const isContinuation = !isBullet && inList && /^\s/.test(rawLine);
    const content = isBullet ? line.replace(/^[*\-]\s+/, '') : line;
    const withBold = escapeHtml(content).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    const withUnderline = withBold.replace(/&lt;u&gt;/g, '<u>').replace(/&lt;\/u&gt;/g, '</u>');
    if (isBullet) {
      if (!inList) { html += '<ul>'; inList = true; }
      html += `<li>${withUnderline}</li>`;
    } else if (isContinuation) {
      html = html.replace(/<\/li>$/, ` ${withUnderline}</li>`);
    } else {
      if (inList) { html += '</ul>'; inList = false; }
      html += `<p>${withUnderline}</p>`;
    }
  }
  if (inList) html += '</ul>';
  return html;
}

function formatExplanation(text) {
  const lines = text.split('\n').map((line) => {
    const stripped = line.replace(/\*\*/g, '');
    const bulletMatch = stripped.match(/^([*\-]\s+)(.*)$/);
    const prefix = bulletMatch ? bulletMatch[1] : '';
    const rest = bulletMatch ? bulletMatch[2] : stripped;
    const jm = rest.match(JUDGMENT_RE);
    if (jm && jm[0] && jm.index <= 20) {
      const before = rest.slice(0, jm.index);
      const after = rest.slice(jm.index + jm[0].length);
      return `${prefix}${before}**${jm[0]}**${after}`;
    }
    return prefix + rest;
  });
  return formatText(lines.join('\n'));
}

function stripLeadingAnswerLine(text, answer) {
  const lines = text.split('\n');
  let i = 0;
  while (i < lines.length && lines[i].trim() === '') i++;
  if (i < lines.length) {
    const normalized = lines[i].trim().replace(/^\*+|\*+$/g, '').trim();
    const answerNormalized = normalized.replace(/^正解[:：]\s*/, '');
    if (normalized === answer || answerNormalized === answer) {
      lines.splice(0, i + 1);
    }
  }
  return lines.join('\n');
}

function startChapter(target) {
  currentCards = target === 'all' ? CARDS : CARDS.filter((c) => c.chapter === target);
  currentIndex = 0;
  isFlipped = false;
  sessionResults = {};
  document.getElementById('chapter-screen').hidden = true;
  document.getElementById('card-screen').hidden = false;
  renderCard();
}

function renderHeader(card) {
  const meta = getChapterMeta(card.chapter);
  document.getElementById('header-chapter').textContent =
    `第${card.chapter}章 ${card.chapterTitle}（${meta ? meta.count : '?'}問）`;
  document.getElementById('header-question').textContent =
    `第${card.questionNumber}問　${card.title}`;
}

function renderChoices(card) {
  const container = document.getElementById('choices-container');
  container.innerHTML = '';

  if (card.isProse) {
    const spans = document.querySelectorAll('#question-text u');
    spans.forEach((span, idx) => {
      span.classList.add('choice-span');
      span.dataset.choiceIndex = String(idx);
      span.addEventListener('click', (e) => {
        e.stopPropagation();
        selectChoice(idx);
      });
    });
    updateChoiceSelectionUI();
    return;
  }

  card.choices.forEach((text, idx) => {
    const div = document.createElement('div');
    div.className = 'choice';
    div.textContent = text;
    div.dataset.choiceIndex = String(idx);
    div.addEventListener('click', (e) => {
      e.stopPropagation();
      selectChoice(idx);
    });
    container.appendChild(div);
  });
  updateChoiceSelectionUI();
}

function selectChoice(idx) {
  const card = currentCards[currentIndex];
  const isNewSelection = selectedChoiceIndex !== idx;
  selectedChoiceIndex = selectedChoiceIndex === idx ? null : idx;
  updateChoiceSelectionUI();
  if (isNewSelection && selectedChoiceIndex !== null) {
    incrementStarCount(card.id);
  }
}

function updateChoiceSelectionUI() {
  document.querySelectorAll('.choice, #question-text u.choice-span').forEach((el) => {
    const idx = Number(el.dataset.choiceIndex);
    el.classList.toggle('selected', idx === selectedChoiceIndex);
  });
}

function recordAnswerIfNeeded(card) {
  if (card.answerIndex === null || card.answerIndex === undefined) return;
  if (selectedChoiceIndex === null) return;
  sessionResults[card.id] = selectedChoiceIndex === card.answerIndex ? 'correct' : 'incorrect';
}

function renderCard() {
  const card = currentCards[currentIndex];
  selectedChoiceIndex = null;

  window.scrollTo(0, 0);
  document.getElementById('progress-label').textContent = `${currentIndex + 1} / ${currentCards.length}`;
  const slider = document.getElementById('slider');
  slider.min = 1;
  slider.max = currentCards.length;
  slider.value = currentIndex + 1;

  renderHeader(card);
  document.getElementById('question-text').innerHTML = formatText(card.prompt);
  renderChoices(card);
  document.getElementById('exam-ref').textContent = card.examRef;
  document.getElementById('answer-text').innerHTML =
    `<p><strong>正解：${escapeHtml(card.answer)}</strong></p>` +
    formatExplanation(stripLeadingAnswerLine(card.explanation, card.answer));
  document.getElementById('card').classList.toggle('flipped', isFlipped);
  updateProgressButtons(card.id);
  renderStarRow(card.id);
}

document.getElementById('card').addEventListener('click', () => {
  const card = currentCards[currentIndex];
  isFlipped = !isFlipped;
  if (isFlipped) {
    recordAnswerIfNeeded(card);
  }
  document.getElementById('card').classList.toggle('flipped', isFlipped);
});

document.getElementById('btn-star-reset').addEventListener('click', (e) => {
  e.stopPropagation();
  resetStarCount(currentCards[currentIndex].id);
});

document.getElementById('btn-back').addEventListener('click', () => {
  document.getElementById('card-screen').hidden = true;
  document.getElementById('chapter-screen').hidden = false;
});

function goNext() {
  if (currentIndex < currentCards.length - 1) {
    currentIndex++;
    isFlipped = false;
    renderCard();
  }
}

function goPrev() {
  if (currentIndex > 0) {
    currentIndex--;
    isFlipped = false;
    renderCard();
  }
}

document.getElementById('btn-next').addEventListener('click', (e) => {
  e.stopPropagation();
  goNext();
});
document.getElementById('btn-prev').addEventListener('click', (e) => {
  e.stopPropagation();
  goPrev();
});
document.getElementById('slider').addEventListener('input', (e) => {
  currentIndex = Number(e.target.value) - 1;
  isFlipped = false;
  renderCard();
});
document.getElementById('btn-ok').addEventListener('click', () => {
  setProgress(currentCards[currentIndex].id, 'ok');
});
document.getElementById('btn-ng').addEventListener('click', () => {
  setProgress(currentCards[currentIndex].id, 'ng');
});

function showScoreOverlay() {
  const entries = Object.entries(sessionResults);
  const correct = entries.filter(([, v]) => v === 'correct').length;
  const total = entries.length;
  document.getElementById('score-summary').textContent =
    total === 0 ? 'まだ回答していません' : `${total}問中${correct}問正解`;
  const list = currentCards
    .filter((c) => sessionResults[c.id])
    .map((c) => `<li>第${c.questionNumber}問（${c.title}）: ${sessionResults[c.id] === 'correct' ? '正解' : '不正解'}</li>`)
    .join('');
  document.getElementById('score-list').innerHTML = list;
  document.getElementById('score-overlay').hidden = false;
}

document.getElementById('btn-score').addEventListener('click', (e) => {
  e.stopPropagation();
  showScoreOverlay();
});
document.getElementById('btn-score-close').addEventListener('click', () => {
  document.getElementById('score-overlay').hidden = true;
});

renderChapterList();

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js').catch(() => {});
  });
}
</script>
</body>
</html>
```

- [ ] **Step 2: Verify against real data — static tracing (no browser available)**

Since there's no browser in this environment, verify by reading the real `cards.js` and hand-tracing (or scripting in Python/Node if available) each of the following against ACTUAL records, not synthetic examples:

1. Pick a normal (non-prose) card, e.g. chapter 1 question 1. Confirm: `renderHeader` would produce `"第1章 <chapterTitle from CHAPTERS>（<count>問）"` and `"第1問　<title>"`. Confirm `renderChoices` would produce one `.choice` div per entry in `choices`, each with plain (non-strong) text — grep `cards.js` for that card's `choices` array and confirm none contain `**`.
2. Pick a card with `isProse: true` (search `cards.js` for `"isProse": true`). Confirm its `prompt` contains `<u>` tags and that `formatText` (trace the regex) would preserve them as real `<u>` elements (not escaped) — this reuses the same underline-unescaping logic already validated in the v1 branch's final review.
3. Trace `compute_answer_index`-derived `answerIndex` against that same card's `choices` array for at least 2 cards: confirm `choices[answerIndex]` (when `answerIndex` is not null) is plausibly "the correct one" by cross-checking against the raw `answer` field's leading marker.
4. Trace `formatExplanation` against a real `explanation` string that starts with `**ア：誤り（✕）である。**` (chapter 1 or 2 have these) and confirm: (a) all raw `**` are stripped first, (b) the judgment phrase (here `誤り（✕）である`) is the ONLY thing re-wrapped in `**`, so it is the only `<strong>` in that line's output, (c) the rest of the sentence renders as plain text within the same `<li>`.
5. Trace `stripLeadingAnswerLine` + `formatExplanation` together end-to-end for one full card's `explanation`, confirming no leading duplicate "正解：" line survives and the per-item spacing CSS (`#answer-text li { margin-bottom: 1em; }`) will visibly separate each bullet.
6. Confirm `setProgress`'s toggle-off logic: calling it twice in a row with the same status argument should net out to `localStorage.removeItem` being called on the second call (trace the `current === status ? '' : status` logic by hand with `current` initialized from a fresh `getProgress` call).
7. Confirm `selectChoice`'s increment-on-new-selection-only logic by hand-tracing three consecutive calls: `selectChoice(0)` (should increment), `selectChoice(0)` again (should NOT increment — deselects), `selectChoice(1)` (should increment again).

Write the actual traced input/output (not just "should work") into your report for each of the 7 points above.

- [ ] **Step 3: Confirm nothing from the chapter-list screen or PWA registration was altered**

Diff your new `index.html` against the version in the previous commit for the `#chapter-screen` div and the final `if ('serviceWorker' in navigator) {...}` block — both must be byte-identical to before. If either changed, fix it — this task's scope is the card-study screen only.

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat: v2 card UI — header, choice/prose selection, scoring, star counter, toggle-off progress"
```
