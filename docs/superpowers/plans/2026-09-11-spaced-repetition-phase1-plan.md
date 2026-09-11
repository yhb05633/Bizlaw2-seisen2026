# 間隔反復・検索練習 フェーズ1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Leitner-style spaced-repetition data layer (box 1–5, next-review-date scheduling) with a cross-chapter "今日の復習" queue, and a forced 3-way self-assessment (わからなかった/かろうじて正解/簡単だった) on the answer side that drives box updates — all additive, with zero changes to `cards.js`/`scripts/parse_cards.py` and zero changes to the existing ★/マスター/メモ features.

**Architecture:** Every new piece of state follows the exact pattern already used for stars/mastery/memo in this file: a `localStorage` key prefixed per card id, read/written through small get/set functions, with render functions that sync the DOM whenever the chapter list or a card is rendered. Unlike the existing per-card keys (which each hold one primitive value), the new SRS state is a single JSON object per card (`box`, `lastReviewedAt`, `nextReviewAt`, `streak`, `totalReviews`, `totalCorrect`) stored under one key, since it's several related fields updated together. "分野" for future interleaving reuses the existing `card.chapter`/`chapterTitle` — no new field.

**Tech Stack:** Same as the rest of the app — vanilla HTML/CSS/JS in `index.html`, `localStorage`, no external libraries, no build step.

## Global Constraints

- No changes to `cards.js` or `scripts/parse_cards.py` — this plan is frontend-only, all new state lives in `localStorage`.
- No external JS/CSS libraries, no build step.
- Do not modify the existing ★実施回数 / マスター / メモ / 成績 / スワイプ features' code paths — the new SRS system is purely additive alongside them (per the approved design spec, decision 2).
- Self-assessment (わからなかった/かろうじて正解/簡単だった) is always freely selectable and never constrained by the objective choice-correctness badge (per design spec, decision 3).
- The existing "選択肢を選ばないと解答ボタンが押せない" gating already satisfies the retrieval-practice requirement — do not add a separate free-text recall input.
- **A browser IS available in this environment for real verification**, at `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`. Every task's verification step must run an actual headless-Chrome check against a scratch copy of `index.html` (self-test `<script>` appended before `</body>`, results written into `document.title`, read back via `--dump-dom`) rather than only reasoning about the code, matching the technique used in `docs/superpowers/plans/2026-09-06-answer-button-memo-master-plan.md`.
- Reference design: `docs/superpowers/specs/2026-09-11-spaced-repetition-phase1-design.md`.

---

## File Structure

- `index.html` — the only file touched. Both tasks below modify its `<style>` block, its body markup, and its `<script>` block. No new files; the project stays single-file per its established convention.

---

## Task 1: SRSデータ層 + 「今日の復習」キュー

**Files:**
- Modify: `index.html`

**Interfaces:**
- Produces: `SRS_KEY_PREFIX`, `BOX_INTERVAL_DAYS`, `todayStr() -> 'YYYY-MM-DD'`, `addDays(dateStr, days) -> 'YYYY-MM-DD'`, `getSrs(id) -> {box, lastReviewedAt, nextReviewAt, streak, totalReviews, totalCorrect}`, `saveSrs(id, srs)`, `isDueToday(id) -> boolean`, `getDueCards(cardsArray) -> Array`, `startReviewQueue()`, `updateReviewQueueButton()`. Task 2 consumes `getSrs`, `saveSrs`, `todayStr`, `addDays`, `BOX_INTERVAL_DAYS`, `SRS_KEY_PREFIX` by these exact names.
- Consumes: `CARDS`, `currentCards`/`currentIndex`/`isFlipped`/`sessionResults` (existing globals), `showCardScreen()`, `showChapterScreen()`, `renderCard()`, `isMasterSkipEnabled`/`isMastered` (existing, unmodified).

- [ ] **Step 1: Add `.chapter-toolbar` wrapping support and the new button's markup**

Find in the `<style>` section:

```css
  .chapter-toolbar {
    display: flex;
    gap: 8px;
    padding: 0 16px 12px;
  }
  .chapter-toolbar button {
    flex: 1;
    padding: 10px;
    border-radius: 8px;
    border: 1px solid #d6d3d1;
    background: white;
    font-size: 0.9rem;
  }
  #btn-master-skip.active { background: #7c3aed; border-color: #7c3aed; color: white; }
```

Replace with:

```css
  .chapter-toolbar {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    padding: 0 16px 12px;
  }
  .chapter-toolbar button {
    flex: 1;
    min-width: 140px;
    padding: 10px;
    border-radius: 8px;
    border: 1px solid #d6d3d1;
    background: white;
    font-size: 0.9rem;
  }
  #btn-master-skip.active { background: #7c3aed; border-color: #7c3aed; color: white; }
```

(The toolbar now holds 3 buttons instead of 2; `flex-wrap` + `min-width: 140px` makes it wrap to two rows on narrow phone widths instead of squeezing three buttons unreadably thin.)

- [ ] **Step 2: Add the `#btn-review-queue` button to the chapter toolbar**

Find:

```html
  <div class="chapter-toolbar">
    <button id="btn-master-skip"></button>
    <button id="btn-memo-list">メモ一覧</button>
  </div>
```

Replace with:

```html
  <div class="chapter-toolbar">
    <button id="btn-master-skip"></button>
    <button id="btn-review-queue"></button>
    <button id="btn-memo-list">メモ一覧</button>
  </div>
```

- [ ] **Step 3: Add the SRS data-layer functions**

Find:

```javascript
function setMemo(id, text) {
  try {
    if (text.trim() === '') {
      localStorage.removeItem(MEMO_KEY_PREFIX + id);
    } else {
      localStorage.setItem(MEMO_KEY_PREFIX + id, text);
    }
  } catch (e) {
    // ignore
  }
}

function escapeHtml(str) {
```

Replace with:

```javascript
function setMemo(id, text) {
  try {
    if (text.trim() === '') {
      localStorage.removeItem(MEMO_KEY_PREFIX + id);
    } else {
      localStorage.setItem(MEMO_KEY_PREFIX + id, text);
    }
  } catch (e) {
    // ignore
  }
}

const SRS_KEY_PREFIX = 'bizlaw2seisen:srs:';
const BOX_INTERVAL_DAYS = { 1: 0, 2: 3, 3: 7, 4: 14, 5: 30 };

function todayStr() {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function addDays(dateStr, days) {
  const [y, m, d] = dateStr.split('-').map(Number);
  const date = new Date(y, m - 1, d);
  date.setDate(date.getDate() + days);
  const yy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, '0');
  const dd = String(date.getDate()).padStart(2, '0');
  return `${yy}-${mm}-${dd}`;
}

function getSrs(id) {
  try {
    const raw = localStorage.getItem(SRS_KEY_PREFIX + id);
    if (raw) return JSON.parse(raw);
  } catch (e) {
    // ignore
  }
  return { box: 1, lastReviewedAt: null, nextReviewAt: todayStr(), streak: 0, totalReviews: 0, totalCorrect: 0 };
}

function saveSrs(id, srs) {
  try {
    localStorage.setItem(SRS_KEY_PREFIX + id, JSON.stringify(srs));
  } catch (e) {
    // ignore
  }
}

function isDueToday(id) {
  return getSrs(id).nextReviewAt <= todayStr();
}

function getDueCards(cardsArray) {
  return cardsArray.filter((c) => isDueToday(c.id));
}

function escapeHtml(str) {
```

- [ ] **Step 4: Add `startReviewQueue()` next to `startChapter()`**

Find:

```javascript
function startChapter(target) {
  let cards = target === 'all' ? CARDS : CARDS.filter((c) => c.chapter === target);
  if (isMasterSkipEnabled()) {
    cards = cards.filter((c) => !isMastered(c.id));
  }
  if (cards.length === 0) {
    alert(target === 'all' ? 'すべての問題がマスター済みです' : 'この章はすべてマスター済みです');
    return;
  }
  currentCards = cards;
  currentIndex = 0;
  isFlipped = false;
  sessionResults = {};
  showCardScreen();
  renderCard();
}
```

Replace with:

```javascript
function startChapter(target) {
  let cards = target === 'all' ? CARDS : CARDS.filter((c) => c.chapter === target);
  if (isMasterSkipEnabled()) {
    cards = cards.filter((c) => !isMastered(c.id));
  }
  if (cards.length === 0) {
    alert(target === 'all' ? 'すべての問題がマスター済みです' : 'この章はすべてマスター済みです');
    return;
  }
  currentCards = cards;
  currentIndex = 0;
  isFlipped = false;
  sessionResults = {};
  showCardScreen();
  renderCard();
}

function startReviewQueue() {
  const cards = getDueCards(CARDS);
  if (cards.length === 0) {
    alert('今日復習すべきカードはありません');
    return;
  }
  currentCards = cards;
  currentIndex = 0;
  isFlipped = false;
  sessionResults = {};
  showCardScreen();
  renderCard();
}
```

- [ ] **Step 5: Refresh the queue button's count whenever the chapter screen is shown**

Find:

```javascript
function showChapterScreen() {
  document.getElementById('card-screen').hidden = true;
  document.getElementById('chapter-screen').hidden = false;
  renderChapterList();
}
```

Replace with:

```javascript
function showChapterScreen() {
  document.getElementById('card-screen').hidden = true;
  document.getElementById('chapter-screen').hidden = false;
  renderChapterList();
  updateReviewQueueButton();
}

function updateReviewQueueButton() {
  const count = getDueCards(CARDS).length;
  document.getElementById('btn-review-queue').textContent = `今日の復習（${count}）`;
}
```

- [ ] **Step 6: Wire the button's click listener**

Find:

```javascript
document.getElementById('btn-master-skip').addEventListener('click', () => {
  setMasterSkipEnabled(!isMasterSkipEnabled());
  updateMasterSkipButton();
});
```

Replace with:

```javascript
document.getElementById('btn-master-skip').addEventListener('click', () => {
  setMasterSkipEnabled(!isMasterSkipEnabled());
  updateMasterSkipButton();
});

document.getElementById('btn-review-queue').addEventListener('click', () => {
  startReviewQueue();
});
```

- [ ] **Step 7: Initialize the button's label on page load**

Find:

```javascript
renderChapterList();
updateMasterSkipButton();

if ('serviceWorker' in navigator) {
```

Replace with:

```javascript
renderChapterList();
updateMasterSkipButton();
updateReviewQueueButton();

if ('serviceWorker' in navigator) {
```

- [ ] **Step 8: Verify with real headless Chrome**

Create a scratch copy of the app (do not leave scratch files in the repo) and append a self-test script before `</body>`:

```bash
SCRATCH=$(mktemp -d)
cp index.html "$SCRATCH/scratch-index.html"
cp cards.js "$SCRATCH/cards.js"
python3 - "$SCRATCH/scratch-index.html" <<'PYEOF'
import sys
path = sys.argv[1]
html = open(path, encoding='utf-8').read()
script = '''
<script>
window.addEventListener('load', () => {
  const results = [];
  const check = (name, cond) => results.push(name + ':' + (cond ? 'PASS' : 'FAIL'));
  window.alert = () => {}; // real alert() blocks --dump-dom forever waiting for a dialog dismissal that never comes

  check('btn exists', !!document.getElementById('btn-review-queue'));
  check('initial label 172', document.getElementById('btn-review-queue').textContent === '\\u4eca\\u65e5\\u306e\\u5fa9\\u7fd2\\uff08172\\uff09');

  document.getElementById('btn-review-queue').click();
  check('navigates to card screen', document.getElementById('card-screen').hidden === false);
  check('queue has 172 cards', currentCards.length === 172);

  showChapterScreen();
  saveSrs('1-1', { box: 2, lastReviewedAt: new Date().toISOString(), nextReviewAt: addDays(todayStr(), 5), streak: 1, totalReviews: 1, totalCorrect: 1 });
  check('1-1 not due', isDueToday('1-1') === false);
  check('due count 171', getDueCards(CARDS).length === 171);
  showChapterScreen();
  check('label updates to 171', document.getElementById('btn-review-queue').textContent === '\\u4eca\\u65e5\\u306e\\u5fa9\\u7fd2\\uff08171\\uff09');

  CARDS.forEach((c) => saveSrs(c.id, { box: 2, lastReviewedAt: new Date().toISOString(), nextReviewAt: addDays(todayStr(), 5), streak: 0, totalReviews: 0, totalCorrect: 0 }));
  showChapterScreen();
  startReviewQueue();
  check('empty queue does not navigate', document.getElementById('card-screen').hidden === true);

  CARDS.forEach((c) => localStorage.removeItem('bizlaw2seisen:srs:' + c.id));

  document.title = results.join(' | ');
});
</script>
'''
html = html.replace('</body>', script + '</body>')
open(path, 'w', encoding='utf-8').write(html)
PYEOF
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu --virtual-time-budget=4000 --dump-dom "file://$SCRATCH/scratch-index.html" 2>/dev/null | grep -o '<title>[^<]*</title>'
rm -rf "$SCRATCH"
```

Expected: the title contains only `:PASS` entries (8 checks), no `:FAIL`. (The `\u...` escapes in the injected script are the literal Japanese label text `今日の復習（172）` / `今日の復習（171）` — written as escapes here only so this plan document stays ASCII-safe when quoted through the heredoc; the actual injected `<script>` can use the literal Japanese characters directly instead of escapes.)

- [ ] **Step 9: Commit**

```bash
git add index.html
git commit -m "$(cat <<'EOF'
Add SRS data layer and a cross-chapter 今日の復習 queue

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: 自己評価UI (検索練習) と box 更新の連動

**Files:**
- Modify: `index.html`

**Interfaces:**
- Consumes: `getSrs`, `saveSrs`, `todayStr`, `addDays`, `BOX_INTERVAL_DAYS` (Task 1, exact names), `currentCards`, `currentIndex`, `renderCard`.
- Produces: `applySelfAssessment(id, grade)` (`grade` is `'unknown' | 'barely' | 'easy'`), `formatDateLabel(dateStr) -> 'M/D'`, `renderSrsLabel(id)`. No later task in this plan depends on these (phase 2+ work is out of scope), but they're the natural extension points for the future confidence-rating/visualization phases.

- [ ] **Step 1: Add CSS for the self-assessment row and next-review label**

Find:

```css
  .master-btn.active { background: #7c3aed; border-color: #7c3aed; color: white; }
```

Replace with:

```css
  .master-btn.active { background: #7c3aed; border-color: #7c3aed; color: white; }
  .self-assessment {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin: 0 0 8px;
  }
  .assess-btn {
    flex: 1;
    min-width: 100px;
    padding: 10px 6px;
    border-radius: 8px;
    border: 1px solid #d6d3d1;
    background: white;
    font-size: 0.85rem;
    cursor: pointer;
  }
  .next-review-label {
    font-size: 0.75rem;
    color: #78716c;
    margin: 0 0 12px;
    min-height: 1em;
  }
```

- [ ] **Step 2: Add the self-assessment buttons and next-review label to the card back**

Find:

```html
    <div class="card-face card-back">
      <div id="answer-result"></div>
      <button id="btn-master" class="master-btn">マスター</button>
      <div id="answer-text"></div>
```

Replace with:

```html
    <div class="card-face card-back">
      <div id="answer-result"></div>
      <div class="self-assessment">
        <button class="assess-btn" data-grade="unknown">わからなかった</button>
        <button class="assess-btn" data-grade="barely">かろうじて正解</button>
        <button class="assess-btn" data-grade="easy">簡単だった</button>
      </div>
      <div id="next-review-label" class="next-review-label"></div>
      <button id="btn-master" class="master-btn">マスター</button>
      <div id="answer-text"></div>
```

- [ ] **Step 3: Add `applySelfAssessment`, `formatDateLabel`, `renderSrsLabel`**

Find:

```javascript
function getDueCards(cardsArray) {
  return cardsArray.filter((c) => isDueToday(c.id));
}

function escapeHtml(str) {
```

Replace with:

```javascript
function getDueCards(cardsArray) {
  return cardsArray.filter((c) => isDueToday(c.id));
}

function applySelfAssessment(id, grade) {
  const srs = getSrs(id);
  let newBox = srs.box;
  if (grade === 'unknown') {
    newBox = 1;
  } else if (grade === 'easy') {
    newBox = Math.min(5, srs.box + 1);
  }
  srs.box = newBox;
  srs.lastReviewedAt = new Date().toISOString();
  srs.nextReviewAt = addDays(todayStr(), BOX_INTERVAL_DAYS[newBox] ?? 1);
  srs.totalReviews += 1;
  srs.streak = grade === 'unknown' ? 0 : srs.streak + 1;
  if (grade !== 'unknown') srs.totalCorrect += 1;
  saveSrs(id, srs);
}

function formatDateLabel(dateStr) {
  const parts = dateStr.split('-');
  return `${Number(parts[1])}/${Number(parts[2])}`;
}

function renderSrsLabel(id) {
  const srs = getSrs(id);
  document.getElementById('next-review-label').textContent =
    srs.lastReviewedAt ? `次回復習: ${formatDateLabel(srs.nextReviewAt)}` : '';
}

function escapeHtml(str) {
```

- [ ] **Step 4: Call `renderSrsLabel()` from `renderCard()`**

Find:

```javascript
  renderStarRow(card.id);
  updateMasterButton(card.id);
  document.getElementById('memo-input').value = getMemo(card.id);
  updateResultBadge();
}
```

Replace with:

```javascript
  renderStarRow(card.id);
  updateMasterButton(card.id);
  renderSrsLabel(card.id);
  document.getElementById('memo-input').value = getMemo(card.id);
  updateResultBadge();
}
```

- [ ] **Step 5: Wire the self-assessment buttons' click listener**

Find:

```javascript
document.getElementById('btn-master').addEventListener('click', (e) => {
  e.stopPropagation();
  const id = currentCards[currentIndex].id;
  setMastered(id, !isMastered(id));
  updateMasterButton(id);
});
```

Replace with:

```javascript
document.getElementById('btn-master').addEventListener('click', (e) => {
  e.stopPropagation();
  const id = currentCards[currentIndex].id;
  setMastered(id, !isMastered(id));
  updateMasterButton(id);
});

document.querySelector('.self-assessment').addEventListener('click', (e) => {
  e.stopPropagation();
  const btn = e.target.closest('.assess-btn');
  if (!btn) return;
  const id = currentCards[currentIndex].id;
  applySelfAssessment(id, btn.dataset.grade);
  renderSrsLabel(id);
});
```

- [ ] **Step 6: Verify with real headless Chrome**

```bash
SCRATCH=$(mktemp -d)
cp index.html "$SCRATCH/scratch-index.html"
cp cards.js "$SCRATCH/cards.js"
python3 - "$SCRATCH/scratch-index.html" <<'PYEOF'
import sys
path = sys.argv[1]
html = open(path, encoding='utf-8').read()
script = '''
<script>
window.addEventListener('load', () => {
  const results = [];
  const check = (name, cond) => results.push(name + ':' + (cond ? 'PASS' : 'FAIL'));

  startChapter(1);
  flipToAnswer();
  check('label empty before grading', document.getElementById('next-review-label').textContent === '');

  const easyBtn = document.querySelectorAll('.assess-btn')[2];
  easyBtn.click();
  let srs = getSrs('1-1');
  check('easy sets box 2', srs.box === 2);
  check('easy sets nextReviewAt +3d', srs.nextReviewAt === addDays(todayStr(), 3));
  check('easy totalReviews 1', srs.totalReviews === 1);
  check('easy totalCorrect 1', srs.totalCorrect === 1);
  check('easy streak 1', srs.streak === 1);
  check('label shows next review', document.getElementById('next-review-label').textContent === ('\\u6b21\\u56de\\u5fa9\\u7fd2: ' + formatDateLabel(addDays(todayStr(), 3))));
  check('still flipped after easy', document.getElementById('card').classList.contains('flipped') === true);

  const unknownBtn = document.querySelectorAll('.assess-btn')[0];
  unknownBtn.click();
  srs = getSrs('1-1');
  check('unknown resets box to 1', srs.box === 1);
  check('unknown sets nextReviewAt today', srs.nextReviewAt === todayStr());
  check('unknown totalReviews 2', srs.totalReviews === 2);
  check('unknown totalCorrect unchanged', srs.totalCorrect === 1);
  check('unknown resets streak', srs.streak === 0);

  const barelyBtn = document.querySelectorAll('.assess-btn')[1];
  barelyBtn.click();
  srs = getSrs('1-1');
  check('barely keeps box 1', srs.box === 1);
  check('barely totalReviews 3', srs.totalReviews === 3);
  check('barely totalCorrect 2', srs.totalCorrect === 2);
  check('barely streak 1', srs.streak === 1);
  check('still flipped after barely', document.getElementById('card').classList.contains('flipped') === true);

  check('1-1 due today after grading', isDueToday('1-1') === true);
  check('due cards include 1-1', getDueCards(CARDS).some((c) => c.id === '1-1') === true);

  localStorage.removeItem('bizlaw2seisen:srs:1-1');

  document.title = results.join(' | ');
});
</script>
'''
html = html.replace('</body>', script + '</body>')
open(path, 'w', encoding='utf-8').write(html)
PYEOF
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu --virtual-time-budget=4000 --dump-dom "file://$SCRATCH/scratch-index.html" 2>/dev/null | grep -o '<title>[^<]*</title>'
rm -rf "$SCRATCH"
```

Expected: the title contains only `:PASS` entries (20 checks), no `:FAIL`. (The `\u...` escape is the literal Japanese label prefix `次回復習: ` — written as an escape here only so this plan document stays ASCII-safe; the actual injected `<script>` can use the literal characters directly.)

- [ ] **Step 7: Commit**

```bash
git add index.html
git commit -m "$(cat <<'EOF'
Add 3段階自己評価 UI and wire it to Leitner box updates

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```
