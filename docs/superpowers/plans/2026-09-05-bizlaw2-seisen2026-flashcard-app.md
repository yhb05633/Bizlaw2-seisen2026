# Bizlaw2-seisen2026 Flashcard App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Mac/iPhone flashcard web app for the 172-question "ビジ法２精選" question bank, using a Python script to normalize 16 inconsistently-formatted text files into a single data file.

**Architecture:** A one-time/rerunnable Python script (`scripts/parse_cards.py`) parses the 16 source `.txt` files into `cards.js` (a `CHAPTERS` + `CARDS` JS data file). A single-file static web app (`index.html`, inline CSS/JS) loads `cards.js` and renders a chapter-selection screen and a flip-card study screen. No build step, no external libraries, no server.

**Tech Stack:** Python 3 (stdlib only) for the data pipeline. Vanilla HTML/CSS/JS for the app. `localStorage` for per-device progress. PWA (`manifest.json` + `sw.js`) for "Add to Home Screen" on iPhone.

## Global Constraints

- No external JS/CSS libraries or frameworks — vanilla HTML/CSS/JS only, matching the sibling projects (`ビジ法2級`, `ビジ法3級模擬試験`).
- The source `.txt` files under `/Volumes/Macmini M2PRO/専門スキル/法務書籍/Legalstudy2026/ビジ法検定_/ビジ法２精選/` must never be modified by any script or task.
- Chapter number, chapter title, and expected question count come from the hardcoded table in the spec — never from headings inside the `.txt` files (several files have missing/incorrect chapter headings).
- Progress ("できた"/"苦手") is stored only in the browser's `localStorage`, keyed per card id. No server, no cross-device sync.
- No automated test framework is introduced for the frontend; frontend tasks are verified by manual checks in a browser, per the approved spec's testing policy.
- The parser is verified by an automated per-chapter question-count check against the table below — a mismatch is a hard failure (`SystemExit(1)`), not a warning.

### Chapter table (authoritative)

| number | title | count |
|---|---|---|
| 1 | 企業取引・契約にかかわる法務 | 14 |
| 2 | 企業財産の管理と法務 | 18 |
| 3 | 企業間取引にかかわる法規制 | 9 |
| 4 | 消費者との取引にかかわる法規制 | 12 |
| 5 | 情報の管理と活用にかかわる法規制 | 3 |
| 6 | デジタル社会と法律 | 4 |
| 7 | 広告・表示等に関する法規制 | 3 |
| 8 | 金融・証券業等に関する法規制 | 4 |
| 9 | 債権の担保 | 14 |
| 10 | 債権の回収 | 9 |
| 11 | 債務者の倒産への対応 | 9 |
| 12 | 法的紛争等の予防と対応 | 18 |
| 13 | 株式会社の組織と運営 | 34 |
| 14 | 企業と従業員の関係 | 5 |
| 15 | 企業活動と地域社会・行政等とのかかわり | 5 |
| 16 | 国際法務(渉外法務) | 11 |

Source files live at `NN.txt` (zero-padded, e.g. `01.txt`..`16.txt`) under `/Volumes/Macmini M2PRO/専門スキル/法務書籍/Legalstudy2026/ビジ法検定_/ビジ法２精選/`. File `NN.txt` corresponds to chapter number `NN`.

---

## File Structure

- `scripts/parse_cards.py` — the data pipeline: splits each source file into question blocks, parses each block into a record, validates counts, writes `cards.js`.
- `scripts/test_parse_cards.py` — unit tests for the parsing functions, run with `python3 -m unittest`.
- `cards.js` — generated output (git-tracked, since it's what the app loads; regenerate by rerunning the script).
- `index.html` — the app shell: chapter list screen + card study screen, inline `<style>` and `<script>`.
- `manifest.json`, `sw.js`, `icon-180.png`, `icon-192.png`, `icon-512.png` — PWA assets.
- `README.md`, `CLAUDE.md` — short docs for future maintenance, following the sibling projects' pattern.

---

## Task 1: Core parsing functions

**Files:**
- Create: `scripts/parse_cards.py`
- Test: `scripts/test_parse_cards.py`

**Interfaces:**
- Produces: `split_into_question_blocks(text: str) -> list[str]`, `parse_block(block_text: str) -> dict` with keys `examRef: str`, `question: str`, `answer: str`, `explanation: str`. Raises `ValueError` if no answer/explanation boundary is found in a block.

Real source files use several different ways of marking where a question ends and its answer/explanation begins. These were confirmed by inspecting the actual files:

1. `##### 【解答・解説】` heading, then a separate line `**正解：③（ア・エ・オ）**` (files 01, 02, 11, 13, 14, 15, 16).
2. `### 解答・解説` heading, then `**正解：③（ア・ウ・オ）**` (files 05, 06, 07, 08, 09).
3. Two separate headings, `### 解答` then the bare answer value, then `### 解説` then the explanation (file 10, and similar historic files).
4. Bold label on its own line, `**解答**`, then the bare answer value, then `**解説**`, then the explanation (file 03).
5. Bold label `**解答・解説**` then `**正解：③**` (file 04).
6. No markup at all: plain line `解答：⑤` followed by `【解説】` then explanation text (file 12).

- [ ] **Step 1: Write `scripts/parse_cards.py` with the core parsing functions**

```python
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
```

- [ ] **Step 2: Write `scripts/test_parse_cards.py`**

```python
import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from parse_cards import split_into_question_blocks, parse_block


class TestSplitIntoQuestionBlocks(unittest.TestCase):
    def test_splits_heading_style_blocks(self):
        text = (
            "## 第1章 テスト\n\n"
            "#### 第1問（第45回 第3問 3-3）\n"
            "本文A\n\n"
            "##### 【解答・解説】\n"
            "**正解：①**\n\n"
            "#### 第2問（第40回 第1問 1-1）\n"
            "本文B\n\n"
            "##### 【解答・解説】\n"
            "**正解：②**\n"
        )
        blocks = split_into_question_blocks(text)
        self.assertEqual(len(blocks), 2)
        self.assertTrue(blocks[0].startswith("#### 第1問"))
        self.assertTrue(blocks[1].startswith("#### 第2問"))

    def test_splits_plain_text_blocks_without_heading_markers(self):
        text = (
            "損害賠償責任\n\n"
            "第1問\n"
            "本文A\n\n"
            "解答：⑤\n\n"
            "【解説】\n"
            "説明A\n\n"
            "第2問\n"
            "本文B\n\n"
            "解答：①\n\n"
            "【解説】\n"
            "説明B\n"
        )
        blocks = split_into_question_blocks(text)
        self.assertEqual(len(blocks), 2)
        self.assertTrue(blocks[0].startswith("第1問"))
        self.assertTrue(blocks[1].startswith("第2問"))


class TestParseBlock(unittest.TestCase):
    def test_heading_kaitou_kaisetsu_style(self):
        block = (
            "#### 第1問（第45回 第3問 3-3）\n"
            "**設問**\n"
            "本文の質問です。\n\n"
            "##### 【解答・解説】\n"
            "**正解：③（ア・エ・オ）**\n\n"
            "* **ア：適切である。**説明その1\n"
        )
        result = parse_block(block)
        self.assertEqual(result["examRef"], "第45回 第3問 3-3")
        self.assertEqual(result["answer"], "③（ア・エ・オ）")
        self.assertIn("本文の質問です。", result["question"])
        self.assertNotIn("設問", result["question"])
        self.assertIn("説明その1", result["explanation"])

    def test_separate_kaitou_and_kaisetsu_headings(self):
        block = (
            "## 第1問（第45回 第10問 10-1）\n"
            "本文です。\n\n"
            "### 解答\n"
            "③\n\n"
            "### 解説\n"
            "説明文です。\n"
        )
        result = parse_block(block)
        self.assertEqual(result["answer"], "③")
        self.assertIn("説明文です。", result["explanation"])
        self.assertNotIn("解説", result["explanation"].split("\n")[0])

    def test_bold_kaitou_then_kaisetsu(self):
        block = (
            "#### 第1問（第48回 第2問 2-2）\n"
            "**設問**\n"
            "本文です。\n\n"
            "**解答**\n"
            "1\n\n"
            "**解説**\n"
            "1．説明です。\n"
        )
        result = parse_block(block)
        self.assertEqual(result["answer"], "1")
        self.assertIn("説明です。", result["explanation"])

    def test_bold_kaitou_kaisetsu_with_inline_seikai(self):
        block = (
            "### 第1問（第44回 第4問 41）\n"
            "**設問**\n"
            "本文です。\n\n"
            "**解答・解説**\n\n"
            "**正解：③**\n\n"
            "* a. 適切である：説明です。\n"
        )
        result = parse_block(block)
        self.assertEqual(result["answer"], "③")
        self.assertIn("説明です。", result["explanation"])

    def test_plain_text_no_markup(self):
        block = (
            "第1問\n"
            "本文です。\n\n"
            "解答：⑤\n\n"
            "【解説】\n"
            "説明です。\n"
        )
        result = parse_block(block)
        self.assertEqual(result["examRef"], "")
        self.assertEqual(result["answer"], "⑤")
        self.assertIn("説明です。", result["explanation"])

    def test_no_boundary_raises(self):
        block = "#### 第1問（第1回 第1問 1-1）\n本文だけで解答がありません。\n"
        with self.assertRaises(ValueError):
            parse_block(block)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run the tests and confirm they pass**

Run: `python3 -m unittest scripts/test_parse_cards.py -v` (from the project root)
Expected: all 8 tests PASS. If any fail, fix the regex/logic in `parse_cards.py` (not the test) until they pass — the test fixtures are transcribed from the real files' actual formats.

- [ ] **Step 4: Commit**

```bash
git add scripts/parse_cards.py scripts/test_parse_cards.py
git commit -m "feat: add core parsing functions for question/answer extraction"
```

---

## Task 2: Wire up main() and validate against real data

**Files:**
- Modify: `scripts/parse_cards.py` (append `main()` and `write_cards_js()`)
- Create (generated): `cards.js`

**Interfaces:**
- Consumes: `CHAPTERS`, `split_into_question_blocks`, `parse_block` from Task 1.
- Produces: running `python3 scripts/parse_cards.py` writes `cards.js` containing `const CHAPTERS = [...]` and `const CARDS = [...]`, where each card has keys `id, chapter, chapterTitle, examRef, question, answer, explanation`.

- [ ] **Step 1: Append `main()` and `write_cards_js()` to `scripts/parse_cards.py`**

```python
def write_cards_js(cards: list[dict]) -> None:
    chapters_json = json.dumps(CHAPTERS, ensure_ascii=False, indent=2)
    cards_json = json.dumps(cards, ensure_ascii=False, indent=2)
    content = f"const CHAPTERS = {chapters_json};\n\nconst CARDS = {cards_json};\n"
    OUTPUT_PATH.write_text(content, encoding="utf-8")


def main() -> None:
    all_cards = []
    errors = []

    for chapter in CHAPTERS:
        file_path = SOURCE_DIR / f"{chapter['number']:02d}.txt"
        text = file_path.read_text(encoding="utf-8")
        blocks = split_into_question_blocks(text)

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
            all_cards.append(
                {
                    "id": f"{chapter['number']}-{i}",
                    "chapter": chapter["number"],
                    "chapterTitle": chapter["title"],
                    "examRef": parsed["examRef"],
                    "question": parsed["question"],
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


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run against the real source files**

Run: `python3 scripts/parse_cards.py`

Expected: either `OK: 172 問を書き出しました -> .../cards.js`, or a list of `errors` naming the exact file and question index that failed.

- [ ] **Step 3: If there are errors, fix them**

For each reported error, open the named source file at the reported question index and check which of the six boundary styles listed in Task 1 it uses (or if it's a new variant). Common causes and fixes:

- **Count mismatch (found more blocks than expected):** a line elsewhere in the file starts with `第N問` at the beginning of a line (e.g. a stray reference). Search the file for `^第[0-9０-９]+問` with a text editor and check whether it's a real question heading or a false positive; if it's a false positive inside body text, that source file has an unusual line-start — this is a real data issue, flag it to the user rather than silently dropping it, since editing source files is out of scope for this script.
- **Count mismatch (found fewer blocks than expected):** a question heading uses a numbering style not covered by `BLOCK_START_RE` (e.g. full-width parenthesis numbering). Extend `BLOCK_START_RE`/`HEADING_LINE_RE` to cover the new style, add a corresponding unit test in `scripts/test_parse_cards.py`, and rerun.
- **`ValueError: no answer/explanation boundary found`:** the block uses a seventh answer-marking style not in `BOUNDARY_RE`. Add the new label variant to `BOUNDARY_RE`, add a unit test reproducing it, and rerun.

Keep iterating until `python3 scripts/parse_cards.py` reports `OK: 172 問`.

- [ ] **Step 4: Sanity-check the generated file**

Run: `node -e "require('./cards.js'); console.log(CHAPTERS.length, CARDS.length)"` if Node is available, or `python3 -c "import json,re; content=open('cards.js', encoding='utf-8').read(); print(content[:200])"` to eyeball the output. Confirm `CARDS.length` is 172 and the first record's `question`/`answer`/`explanation` fields look like readable Japanese text, not empty strings.

- [ ] **Step 5: Commit**

```bash
git add scripts/parse_cards.py cards.js
git commit -m "feat: generate cards.js from source files with count validation"
```

---

## Task 3: Chapter list screen

**Files:**
- Create: `index.html`

**Interfaces:**
- Consumes: `CHAPTERS` (array of `{number, title, count}`), `CARDS` (array of card objects) — both globals loaded from `cards.js`.
- Produces: a `#chapter-screen` div and a `#card-screen` div (initially hidden) in the DOM; a `startChapter(target)` JS function later tasks will call from chapter buttons (stubbed here to just log for now, replaced fully in Task 4).

- [ ] **Step 1: Write the HTML skeleton and chapter list rendering**

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
</style>
</head>
<body>
<div id="chapter-screen">
  <h1>ビジ法2級 精選フラッシュカード</h1>
  <div id="chapter-list"></div>
</div>
<div id="card-screen" hidden></div>

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

function startChapter(target) {
  console.log('startChapter called with', target);
}

renderChapterList();
</script>
</body>
</html>
```

- [ ] **Step 2: Manual verification**

Run: open `index.html` directly in a browser (double-click, or `open index.html` on Mac).
Expected: a page titled "ビジ法2級 精選フラッシュカード" listing "すべて［172問］" followed by 16 buttons reading "第1章 企業取引・契約にかかわる法務［14問］" through "第16章 国際法務(渉外法務)［11問］", each in the correct order with the correct counts from the table above. Open the browser console and click a chapter button — confirm `startChapter called with 1` (or `'all'`) is logged.

- [ ] **Step 3: Commit**

```bash
git add index.html
git commit -m "feat: add chapter list screen"
```

---

## Task 4: Card view rendering (flip, markdown-lite formatter)

**Files:**
- Modify: `index.html`

**Interfaces:**
- Consumes: `CARDS`, `CHAPTERS` globals; the `#card-screen` div and `startChapter(target)` stub from Task 3.
- Produces: `formatText(text: string) -> string` (HTML), `renderCard()`, replaces the `startChapter` stub with a full implementation that populates `currentCards`/`currentIndex` module-level variables later tasks (5, 6) will also use.

- [ ] **Step 1: Add the card screen markup**

Replace `<div id="card-screen" hidden></div>` with:

```html
<div id="card-screen" hidden>
  <div class="toolbar">
    <button id="btn-back">← 章一覧</button>
    <span id="progress-label"></span>
  </div>
  <div id="card">
    <div class="card-face card-front">
      <div id="exam-ref" class="exam-ref"></div>
      <div id="question-text"></div>
      <div class="tap-hint">タップして解答を見る</div>
    </div>
    <div class="card-face card-back">
      <div id="answer-text"></div>
    </div>
  </div>
</div>
```

- [ ] **Step 2: Add CSS for the card screen**

Append inside the existing `<style>` block:

```css
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
}
.toolbar button {
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid #d6d3d1;
  background: white;
}
#card {
  margin: 0 16px 16px;
  border: 1px solid #d6d3d1;
  border-radius: 12px;
  background: white;
  padding: 20px;
  min-height: 300px;
  cursor: pointer;
}
.card-back { display: none; }
#card.flipped .card-front { display: none; }
#card.flipped .card-back { display: block; }
.exam-ref { font-size: 0.8rem; color: #78716c; margin-bottom: 8px; }
.tap-hint { font-size: 0.8rem; color: #a8a29e; margin-top: 16px; }
#question-text p, #answer-text p { line-height: 1.6; margin: 0 0 10px; }
#question-text ul, #answer-text ul { margin: 0 0 10px; padding-left: 1.4em; }
```

- [ ] **Step 3: Add the formatter and card rendering JS**

Replace the `function startChapter(target) { console.log(...); }` stub with:

```javascript
let currentCards = [];
let currentIndex = 0;
let isFlipped = false;

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
    const content = isBullet ? line.replace(/^[*\-]\s+/, '') : line;
    const withBold = escapeHtml(content).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    if (isBullet) {
      if (!inList) { html += '<ul>'; inList = true; }
      html += `<li>${withBold}</li>`;
    } else {
      if (inList) { html += '</ul>'; inList = false; }
      html += `<p>${withBold}</p>`;
    }
  }
  if (inList) html += '</ul>';
  return html;
}

function startChapter(target) {
  currentCards = target === 'all' ? CARDS : CARDS.filter((c) => c.chapter === target);
  currentIndex = 0;
  isFlipped = false;
  document.getElementById('chapter-screen').hidden = true;
  document.getElementById('card-screen').hidden = false;
  renderCard();
}

function renderCard() {
  const card = currentCards[currentIndex];
  document.getElementById('progress-label').textContent = `${currentIndex + 1} / ${currentCards.length}`;
  document.getElementById('exam-ref').textContent = card.examRef;
  document.getElementById('question-text').innerHTML = formatText(card.question);
  document.getElementById('answer-text').innerHTML =
    `<p><strong>正解：${escapeHtml(card.answer)}</strong></p>` + formatText(card.explanation);
  document.getElementById('card').classList.toggle('flipped', isFlipped);
}

document.getElementById('card').addEventListener('click', () => {
  isFlipped = !isFlipped;
  document.getElementById('card').classList.toggle('flipped', isFlipped);
});

document.getElementById('btn-back').addEventListener('click', () => {
  document.getElementById('card-screen').hidden = true;
  document.getElementById('chapter-screen').hidden = false;
});
```

- [ ] **Step 4: Manual verification**

Run: open `index.html` in a browser.
Expected: clicking "第1章 ..." shows the card screen with "1 / 14" progress, the exam reference (e.g. "第45回 第3問 3-3"), and the formatted question text (paragraphs and bullet lists rendering correctly, no literal `**` visible). Tapping the card reveals "正解：③（ア・エ・オ）" plus the explanation, formatted the same way. Tapping again returns to the question. Clicking "← 章一覧" returns to the chapter list. Check a chapter known to use each boundary style (e.g. chapter 3, chapter 4, chapter 10, chapter 12) to confirm all render correctly.

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "feat: add card view with flip and markdown-lite formatting"
```

---

## Task 5: Navigation (prev/next, slider jump)

**Files:**
- Modify: `index.html`

**Interfaces:**
- Consumes: `currentCards`, `currentIndex`, `isFlipped`, `renderCard()` from Task 4.
- Produces: `goNext()`, `goPrev()`, slider `#slider` kept in sync with `currentIndex`.

- [ ] **Step 1: Add the slider and nav buttons to the card screen markup**

Insert into `#card-screen`, between the `.toolbar` div and `#card`:

```html
<input type="range" id="slider" min="1" max="1" value="1">
```

Append after the closing `</div>` of `#card` (still inside `#card-screen`):

```html
<div class="nav-buttons">
  <button id="btn-prev">前へ</button>
  <button id="btn-next">次へ</button>
</div>
```

- [ ] **Step 2: Add CSS**

```css
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
```

- [ ] **Step 3: Add navigation JS**

In `renderCard()`, after the existing `document.getElementById('progress-label')...` line, add:

```javascript
  const slider = document.getElementById('slider');
  slider.min = 1;
  slider.max = currentCards.length;
  slider.value = currentIndex + 1;
```

After `renderCard()`'s closing brace, add:

```javascript
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
```

- [ ] **Step 4: Manual verification**

Run: open `index.html`, enter a chapter.
Expected: "次へ" advances to the next card (question side, not flipped) and updates the slider position and "N / total" label; "前へ" goes back; dragging the slider jumps directly to that question number; "次へ" at the last card does nothing (no error in console); "前へ" at the first card does nothing.

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "feat: add prev/next navigation and slider jump"
```

---

## Task 6: Progress persistence (できた/苦手)

**Files:**
- Modify: `index.html`

**Interfaces:**
- Consumes: `currentCards`, `currentIndex`, `renderCard()` from Tasks 4-5.
- Produces: `getProgress(id)`, `setProgress(id, status)` backed by `localStorage`.

- [ ] **Step 1: Add the progress buttons to the markup**

Append after the `.nav-buttons` div (still inside `#card-screen`):

```html
<div class="progress-buttons">
  <button id="btn-ng">苦手</button>
  <button id="btn-ok">できた</button>
</div>
```

- [ ] **Step 2: Add CSS**

```css
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
```

- [ ] **Step 3: Add progress JS**

Add near the top of the script (after the `let isFlipped = false;` line):

```javascript
const PROGRESS_KEY_PREFIX = 'bizlaw2seisen:progress:';

function getProgress(id) {
  try {
    return localStorage.getItem(PROGRESS_KEY_PREFIX + id) || '';
  } catch (e) {
    return '';
  }
}

function setProgress(id, status) {
  try {
    localStorage.setItem(PROGRESS_KEY_PREFIX + id, status);
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
```

At the end of `renderCard()`, before its closing brace, add:

```javascript
  updateProgressButtons(card.id);
```

After the existing `slider.addEventListener('input', ...)` block, add:

```javascript
document.getElementById('btn-ok').addEventListener('click', () => {
  setProgress(currentCards[currentIndex].id, 'ok');
});
document.getElementById('btn-ng').addEventListener('click', () => {
  setProgress(currentCards[currentIndex].id, 'ng');
});
```

- [ ] **Step 4: Manual verification**

Run: open `index.html`, enter a chapter, click "できた" on the first card — the button should turn green/active. Click "次へ" then "前へ" back to that card — the "できた" state should still show as active (persisted). Reload the page entirely and re-enter the same chapter — the state should still be there (confirms `localStorage` persistence across reloads). Click "苦手" on the same card — it should switch to red/active and "できた" should turn off.

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "feat: add できた/苦手 progress tracking via localStorage"
```

---

## Task 7: PWA assets and docs

**Files:**
- Create: `manifest.json`, `sw.js`
- Copy: `icon-180.png`, `icon-192.png`, `icon-512.png` (from the `ビジ法2級` sibling project)
- Create: `README.md`, `CLAUDE.md`
- Modify: `index.html` (register the service worker)

- [ ] **Step 1: Copy icon files from the sibling project**

```bash
cp "../ビジ法2級/icon-180.png" ./icon-180.png
cp "../ビジ法2級/icon-192.png" ./icon-192.png
cp "../ビジ法2級/icon-512.png" ./icon-512.png
```

- [ ] **Step 2: Create `manifest.json`**

```json
{
  "name": "ビジネス実務法務検定2級 精選問題フラッシュカード",
  "short_name": "ビジ法2級精選",
  "start_url": "./index.html",
  "scope": "./",
  "display": "standalone",
  "background_color": "#f5f5f4",
  "theme_color": "#1d4ed8",
  "icons": [
    { "src": "icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

- [ ] **Step 3: Create `sw.js`**

```javascript
const CACHE_NAME = "bizlaw2-seisen2026-v1";
const ASSETS = [
  "./",
  "./index.html",
  "./cards.js",
  "./manifest.json",
  "./icon-180.png",
  "./icon-192.png",
  "./icon-512.png",
];

self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  event.respondWith(
    caches.match(event.request).then((cached) => {
      const network = fetch(event.request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
          return response;
        })
        .catch(() => cached);
      return cached || network;
    })
  );
});
```

- [ ] **Step 4: Register the service worker in `index.html`**

Add before the closing `</script>` of the main script block:

```javascript
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js');
  });
}
```

- [ ] **Step 5: Create `README.md`**

```markdown
# ビジ法2級 精選フラッシュカード

ビジネス実務法務検定2級の精選問題集(全16章・172問)を使った、Mac/iPhone向けフラッシュカードWebアプリ。

## 使い方

- Mac上でSafari/Chromeから `index.html` を直接開いて動作確認できる
- GitHub Pages で公開: https://yhb05633.github.io/Bizlaw2-seisen2026/
- iPhoneでは、上記URLをSafariで開き、共有メニューから「ホーム画面に追加」するとアプリのように使える(Service Workerによりオフライン動作)
- 学習の進捗(「できた」「苦手」マーク)は端末のlocalStorageに保存される(端末をまたいでは同期されない)

## データの更新

問題データは `/Volumes/Macmini M2PRO/専門スキル/法務書籍/Legalstudy2026/ビジ法検定_/ビジ法２精選/` の `01.txt`〜`16.txt` を元にしている。元データを修正した場合は以下を再実行して `cards.js` を作り直す:

\`\`\`bash
python3 scripts/parse_cards.py
\`\`\`
```

- [ ] **Step 6: Create `CLAUDE.md`**

```markdown
# CLAUDE.md

## プロジェクトの目的

ビジネス実務法務検定2級の精選問題集(全16章・172問)を使った、iPhone/Mac向けフラッシュカードWebアプリ。

## 構成

- `index.html` — 単一ファイルの静的Webアプリ(HTML/CSS/JS、外部依存なし)。`cards.js` を読み込んで表示する。
- `cards.js` — `scripts/parse_cards.py` が生成する問題データ(`CHAPTERS`, `CARDS`)。直接手編集しない。
- `scripts/parse_cards.py` — 元データ(`.txt`)から `cards.js` を生成するスクリプト。章番号・章タイトル・問題数はスクリプト内にハードコードされた表が正であり、元データの見出しには依存しない。
- ビルド不要。`index.html` をブラウザで開くだけで動作する。

## データを更新する場合

元の `.txt` を修正した後、`python3 scripts/parse_cards.py` を再実行して `cards.js` を作り直す。章ごとの問題数が想定と食い違う場合はエラーで停止するので、その章のファイルを確認する。

## 使い方

- Macでは `index.html` を直接開いて動作確認
- GitHub Pages で公開: https://yhb05633.github.io/Bizlaw2-seisen2026/
- iPhoneでは、上記URLをSafariで開き「ホーム画面に追加」でアプリのように使える
- 学習進捗はlocalStorageのみ、端末間の同期はしない
```

- [ ] **Step 7: Manual verification**

Run: open `index.html` in Chrome, open DevTools > Application > Service Workers, confirm the worker registers without errors. Reload with the network offline (DevTools > Network > Offline) and confirm the app still loads and works.

- [ ] **Step 8: Commit**

```bash
git add manifest.json sw.js icon-180.png icon-192.png icon-512.png README.md CLAUDE.md index.html
git commit -m "feat: add PWA assets and project docs"
```

---

## Task 8: Deploy (requires explicit go-ahead before pushing)

This task publishes the app publicly on GitHub Pages. **Do not run the `git remote add` / `git push` / `gh repo create` steps without confirming with the user first** — creating a public repo and pushing content is a visible, hard-to-reverse action.

- [ ] **Step 1: Confirm with the user** that they want to create the GitHub repo `Bizlaw2-seisen2026` now and push.
- [ ] **Step 2: Create the repo and push** (once confirmed)

```bash
gh repo create yhb05633/Bizlaw2-seisen2026 --public --source=. --remote=origin --push
```

- [ ] **Step 3: Enable GitHub Pages**

```bash
gh api repos/yhb05633/Bizlaw2-seisen2026/pages -X POST -f "source[branch]=main" -f "source[path]=/"
```

- [ ] **Step 4: Verify**

Wait a minute or two, then open `https://yhb05633.github.io/Bizlaw2-seisen2026/` in a browser and confirm the chapter list loads.

- [ ] **Step 5: On iPhone**, open the same URL in Safari, tap the Share icon, and tap "ホーム画面に追加".
