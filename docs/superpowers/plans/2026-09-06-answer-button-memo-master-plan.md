# Answer Button / Memo / Mastery Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicit "解答を見る" button gated on choice selection, remove the できた/苦手 buttons, add a per-card "マスター" toggle with chapter-list mastery stats and a mastery-skip toggle, and add a per-card memo textarea with a jump-to-card memo list — all in `index.html`, no changes to the data pipeline.

**Architecture:** Every new piece of state (mastery, memo, mastery-skip preference) follows the exact pattern already used for できた/苦手 and star counts: a `localStorage` key prefixed per card id (or a single global key for the skip toggle), read/written through small get/set functions, with a render function that syncs the DOM to the stored state whenever a card (or the chapter list) is rendered. No `cards.js` schema changes.

**Tech Stack:** Same as the rest of the app — vanilla HTML/CSS/JS in `index.html`, `localStorage`, no external libraries.

## Global Constraints

- No external JS/CSS libraries.
- No changes to `scripts/parse_cards.py` or `cards.js` — this plan is frontend-only.
- All new persisted state uses `localStorage`, never a server; no cross-device sync.
- できた/苦手 must be fully removed: markup, CSS, JS functions, event listeners, and the `bizlaw2seisen:progress:` key prefix must no longer be read or written anywhere in the file. Existing stored values for that prefix are left alone (harmless orphaned data) — do not attempt to migrate or delete them.
- The existing "tap the card to flip" gesture must keep working exactly as before, with no selection requirement, for every task in this plan.
- **A browser IS available in this environment for real verification**, at `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`. Every task's verification step must use it (headless, via `--headless=new --disable-gpu --dump-dom` against a temporary copy of `index.html` with a small self-test `<script>` appended, dumping results into `document.title` the same way prior sessions on this project have done) rather than only reasoning about the code — a previous round of this project shipped a CSS bug (`.overlay { display: flex }` beating `[hidden]`) that static tracing missed entirely and only headless-Chrome testing caught.

---

## File Structure

- `index.html` — the only file touched. All five tasks below modify its `<style>` block, its body markup, and its `<script>` block.

---

## Task 1: Remove できた/苦手

**Files:**
- Modify: `index.html`

**Interfaces:**
- Removes: `PROGRESS_KEY_PREFIX`, `getProgress`, `setProgress`, `updateProgressButtons`, the `.progress-buttons` markup/CSS, and the `#btn-ok`/`#btn-ng` event listeners.
- No new interfaces — this is a pure removal, done first so later tasks never need to route around code that's about to disappear.

- [ ] **Step 1: Remove the `.progress-buttons` CSS rules**

Find this block in the `<style>` section and delete it entirely:

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

- [ ] **Step 2: Remove the `.progress-buttons` markup**

Find:

```html
  <div class="progress-buttons">
    <button id="btn-ng">苦手</button>
    <button id="btn-ok">できた</button>
  </div>
</div>
```

Replace with just:

```html
</div>
```

(This is the closing `</div>` of `#card-screen` — only the `.progress-buttons` div itself is removed.)

- [ ] **Step 3: Remove `PROGRESS_KEY_PREFIX`**

Find:

```javascript
const PROGRESS_KEY_PREFIX = 'bizlaw2seisen:progress:';
const STAR_KEY_PREFIX = 'bizlaw2seisen:stars:';
```

Replace with:

```javascript
const STAR_KEY_PREFIX = 'bizlaw2seisen:stars:';
```

- [ ] **Step 4: Remove `getProgress`, `setProgress`, `updateProgressButtons`**

Find:

```javascript
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
```

Replace with just:

```javascript
function getStarCount(id) {
```

- [ ] **Step 5: Remove the `updateProgressButtons` call in `renderCard()`**

Find:

```javascript
  document.getElementById('card').classList.toggle('flipped', isFlipped);
  updateProgressButtons(card.id);
  renderStarRow(card.id);
  updateResultBadge();
}
```

Replace with:

```javascript
  document.getElementById('card').classList.toggle('flipped', isFlipped);
  renderStarRow(card.id);
  updateResultBadge();
}
```

- [ ] **Step 6: Remove the `#btn-ok`/`#btn-ng` event listeners**

Find:

```javascript
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
```

Replace with:

```javascript
document.getElementById('slider').addEventListener('input', (e) => {
  currentIndex = Number(e.target.value) - 1;
  isFlipped = false;
  renderCard();
});

function showScoreOverlay() {
```

- [ ] **Step 7: Verify with real headless Chrome**

Make a scratch copy of `index.html` (e.g. to a temp path — do not leave scratch copies in the repo), append a `<script>` before `</body>` that runs after `window.addEventListener('load', ...)`, calls `startChapter(1)`, and asserts: `document.getElementById('btn-ok')` is `null`, `document.getElementById('btn-ng')` is `null`, `document.querySelector('.progress-buttons')` is `null`, and that clicking the card (`document.getElementById('card').click()`) still flips it (`document.getElementById('card').classList.contains('flipped')` becomes `true`). Write the results into `document.title` and read them back with:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu --virtual-time-budget=3000 --dump-dom "file:///path/to/scratch-index.html" 2>/dev/null | grep -o '<title>[^<]*</title>'
```

Expected: all assertions true, confirming both the removal and that tap-to-flip is unaffected. Delete the scratch copy afterward.

- [ ] **Step 8: Commit**

```bash
git add index.html
git commit -m "$(cat <<'EOF'
Remove できた/苦手 progress buttons

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: 解答ボタン (answer button, gated on selection)

**Files:**
- Modify: `index.html`

**Interfaces:**
- Consumes: `selectedChoiceIndex`, `selectChoice`, `updateChoiceSelectionUI`, `recordAnswerIfNeeded`, `updateResultBadge`, `renderChoices` (all already defined).
- Produces: `flipToggle()` (replaces the inline logic that used to live directly in the `#card` click listener), `flipToAnswer()` (flips only forward, used by the new button), `updateAnswerButtonState()` (enables/disables `#btn-answer`) — later tasks do not depend on these, but must not remove them.

- [ ] **Step 1: Add the button's CSS**

Find:

```css
  .tap-hint { font-size: 0.8rem; color: #a8a29e; margin-top: 16px; }
```

Replace with:

```css
  .tap-hint { font-size: 0.8rem; color: #a8a29e; margin-top: 16px; }
  .answer-btn {
    display: block;
    width: 100%;
    margin-top: 16px;
    padding: 12px;
    border-radius: 8px;
    border: 1px solid #1c1917;
    background: #1c1917;
    color: white;
    font-size: 1rem;
    cursor: pointer;
  }
  .answer-btn:disabled {
    background: #e7e5e4;
    border-color: #d6d3d1;
    color: #a8a29e;
    cursor: not-allowed;
  }
```

- [ ] **Step 2: Add the button's markup**

Find:

```html
      <div class="tap-hint">タップして解答を見る</div>
    </div>
    <div class="card-face card-back">
```

Replace with:

```html
      <div class="tap-hint">タップして解答を見る</div>
      <button id="btn-answer" class="answer-btn">解答を見る</button>
    </div>
    <div class="card-face card-back">
```

- [ ] **Step 3: Replace the `#card` click listener with `flipToggle`/`flipToAnswer`, and add `updateAnswerButtonState`**

Find:

```javascript
document.getElementById('card').addEventListener('click', () => {
  const card = currentCards[currentIndex];
  isFlipped = !isFlipped;
  if (isFlipped) {
    recordAnswerIfNeeded(card);
    updateResultBadge();
  }
  document.getElementById('card').classList.toggle('flipped', isFlipped);
});
```

Replace with:

```javascript
function flipToggle() {
  const card = currentCards[currentIndex];
  isFlipped = !isFlipped;
  if (isFlipped) {
    recordAnswerIfNeeded(card);
    updateResultBadge();
  }
  document.getElementById('card').classList.toggle('flipped', isFlipped);
}

function flipToAnswer() {
  if (isFlipped) return;
  flipToggle();
}

function updateAnswerButtonState() {
  const hasSelectable = document.querySelectorAll('.choice, #question-text u.choice-span').length > 0;
  document.getElementById('btn-answer').disabled = hasSelectable && selectedChoiceIndex === null;
}

document.getElementById('card').addEventListener('click', () => {
  flipToggle();
});

document.getElementById('btn-answer').addEventListener('click', (e) => {
  e.stopPropagation();
  flipToAnswer();
});
```

- [ ] **Step 4: Call `updateAnswerButtonState()` from `renderCard()`**

Find:

```javascript
  renderHeader(card);
  document.getElementById('question-text').innerHTML = formatText(card.prompt, false);
  renderChoices(card);
  const noteEl = document.getElementById('choice-note');
```

Replace with:

```javascript
  renderHeader(card);
  document.getElementById('question-text').innerHTML = formatText(card.prompt, false);
  renderChoices(card);
  updateAnswerButtonState();
  const noteEl = document.getElementById('choice-note');
```

- [ ] **Step 5: Call `updateAnswerButtonState()` from `selectChoice()`**

Find:

```javascript
function selectChoice(idx) {
  const card = currentCards[currentIndex];
  const isNewSelection = selectedChoiceIndex !== idx;
  selectedChoiceIndex = selectedChoiceIndex === idx ? null : idx;
  updateChoiceSelectionUI();
  if (isNewSelection && selectedChoiceIndex !== null) {
    incrementStarCount(card.id);
  }
  updateResultBadge();
}
```

Replace with:

```javascript
function selectChoice(idx) {
  const card = currentCards[currentIndex];
  const isNewSelection = selectedChoiceIndex !== idx;
  selectedChoiceIndex = selectedChoiceIndex === idx ? null : idx;
  updateChoiceSelectionUI();
  if (isNewSelection && selectedChoiceIndex !== null) {
    incrementStarCount(card.id);
  }
  updateResultBadge();
  updateAnswerButtonState();
}
```

- [ ] **Step 6: Verify with real headless Chrome**

Using the same scratch-copy + injected self-test-script approach as Task 1, verify against a REAL card from `cards.js` (e.g. chapter 1's first card, which has real `choices`):
1. After `startChapter(1)` and `renderCard()`, `document.getElementById('btn-answer').disabled` is `true` (no selection yet).
2. Click a `.choice` div (`document.querySelectorAll('.choice')[0].click()`), then confirm `document.getElementById('btn-answer').disabled` is `false`.
3. Click `#btn-answer` and confirm `document.getElementById('card').classList.contains('flipped')` is `true`.
4. From the flipped state, click `#btn-answer` again and confirm the card is STILL flipped (does not flip back — `flipToAnswer` only moves forward).
5. Click `#card` (the tap gesture) and confirm it now flips back to the front (`flipped` class removed) even though nothing about selection changed — proving tap-to-flip still works unconditionally.
6. Separately, load a card known to have NO discrete choices structurally-fallback-free at this point in the app's history — since both structural fallbacks (2-10, 12-15) were already fixed in an earlier round, every one of the 172 cards now has at least one selectable element (either `.choice` divs or `.choice-span` underlines). Instead, verify the "no selectable elements" branch defensively: temporarily set `currentCards[currentIndex].choices = []` and `currentCards[currentIndex].isProse = false` via the console before calling `renderChoices`/`updateAnswerButtonState`, and confirm `#btn-answer.disabled` is `false` in that synthetic case (the safety net for future data).

- [ ] **Step 7: Commit**

```bash
git add index.html
git commit -m "$(cat <<'EOF'
Add 解答ボタン gated on choice selection

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: マスターボタン (mastery toggle on the answer card)

**Files:**
- Modify: `index.html`

**Interfaces:**
- Produces: `MASTER_KEY_PREFIX`, `isMastered(id) -> boolean`, `setMastered(id, value)`, `updateMasterButton(id)`. Task 4 (chapter-list stats, mastery-skip filter) and Task 5 (none directly, but shares the pattern) depend on `isMastered`/`setMastered` existing with these exact names and signatures.

- [ ] **Step 1: Add the button's markup to the answer (back) card**

Find:

```html
    <div class="card-face card-back">
      <div id="answer-result"></div>
      <div id="answer-text"></div>
    </div>
```

Replace with:

```html
    <div class="card-face card-back">
      <div id="answer-result"></div>
      <button id="btn-master" class="master-btn">マスター</button>
      <div id="answer-text"></div>
    </div>
```

- [ ] **Step 2: Add the button's CSS**

Find:

```css
  #answer-result.incorrect { color: #dc2626; }
```

Replace with:

```css
  #answer-result.incorrect { color: #dc2626; }
  .master-btn {
    display: block;
    width: 100%;
    margin: 0 0 12px;
    padding: 10px;
    border-radius: 8px;
    border: 1px solid #d6d3d1;
    background: white;
    font-size: 0.95rem;
    cursor: pointer;
  }
  .master-btn.active { background: #7c3aed; border-color: #7c3aed; color: white; }
```

- [ ] **Step 3: Add `MASTER_KEY_PREFIX`, `isMastered`, `setMastered`, `updateMasterButton`**

Find:

```javascript
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
```

Replace with:

```javascript
function renderStarRow(id) {
  const count = getStarCount(id);
  const row = document.getElementById('star-row');
  let stars = '';
  for (let i = 0; i < MAX_STARS; i++) {
    stars += i < count ? '★' : '☆';
  }
  row.textContent = stars;
}

const MASTER_KEY_PREFIX = 'bizlaw2seisen:master:';

function isMastered(id) {
  try {
    return localStorage.getItem(MASTER_KEY_PREFIX + id) === '1';
  } catch (e) {
    return false;
  }
}

function setMastered(id, value) {
  try {
    if (value) {
      localStorage.setItem(MASTER_KEY_PREFIX + id, '1');
    } else {
      localStorage.removeItem(MASTER_KEY_PREFIX + id);
    }
  } catch (e) {
    // ignore
  }
}

function updateMasterButton(id) {
  document.getElementById('btn-master').classList.toggle('active', isMastered(id));
}

function escapeHtml(str) {
```

- [ ] **Step 4: Call `updateMasterButton()` from `renderCard()`**

Find:

```javascript
  document.getElementById('card').classList.toggle('flipped', isFlipped);
  renderStarRow(card.id);
  updateResultBadge();
}
```

Replace with:

```javascript
  document.getElementById('card').classList.toggle('flipped', isFlipped);
  renderStarRow(card.id);
  updateMasterButton(card.id);
  updateResultBadge();
}
```

- [ ] **Step 5: Add the click listener**

Find:

```javascript
document.getElementById('btn-star-reset').addEventListener('click', (e) => {
  e.stopPropagation();
  resetStarCount(currentCards[currentIndex].id);
});

document.getElementById('btn-back').addEventListener('click', () => {
```

Replace with:

```javascript
document.getElementById('btn-star-reset').addEventListener('click', (e) => {
  e.stopPropagation();
  resetStarCount(currentCards[currentIndex].id);
});

document.getElementById('btn-master').addEventListener('click', (e) => {
  e.stopPropagation();
  const id = currentCards[currentIndex].id;
  setMastered(id, !isMastered(id));
  updateMasterButton(id);
});

document.getElementById('btn-back').addEventListener('click', () => {
```

- [ ] **Step 6: Verify with real headless Chrome**

Using the scratch-copy technique: `startChapter(1)`, flip to the back (`flipToAnswer()` or `document.getElementById('card').click()`), confirm `document.getElementById('btn-master').classList.contains('active')` is `false` initially. Click `#btn-master`, confirm it becomes `true` AND `localStorage.getItem('bizlaw2seisen:master:1-1')` is `'1'`. Click it again, confirm it becomes `false` and the `localStorage` key is removed (`localStorage.getItem(...)` is `null`). Also confirm clicking `#btn-master` does NOT flip the card back to front (`e.stopPropagation()` working) — check `classList.contains('flipped')` is still `true` after the click.

- [ ] **Step 7: Commit**

```bash
git add index.html
git commit -m "$(cat <<'EOF'
Add マスター toggle button on the answer card

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: 章一覧のマスター表示 + マスタースキップ

**Files:**
- Modify: `index.html`

**Interfaces:**
- Consumes: `isMastered(id)` from Task 3.
- Produces: `masteryStats(cardsArray) -> {mastered, total, pct}`, `isMasterSkipEnabled()`, `setMasterSkipEnabled(value)`, `updateMasterSkipButton()`. `startChapter(target)` is modified in place (same name/signature, callers unaffected).

- [ ] **Step 1: Add the mastery-skip toggle button's markup**

Find:

```html
<div id="chapter-screen">
  <h1>ビジ法2級 精選フラッシュカード</h1>
  <div id="chapter-list"></div>
</div>
```

Replace with:

```html
<div id="chapter-screen">
  <h1>ビジ法2級 精選フラッシュカード</h1>
  <div class="chapter-toolbar">
    <button id="btn-master-skip"></button>
  </div>
  <div id="chapter-list"></div>
</div>
```

- [ ] **Step 2: Add CSS for the chapter-item mastery line and the toolbar**

Find:

```css
  .chapter-item:active { background: #e7e5e4; }
```

Replace with:

```css
  .chapter-item:active { background: #e7e5e4; }
  .chapter-item-title { display: block; }
  .chapter-item-master { display: block; font-size: 0.75rem; color: #78716c; margin-top: 2px; }
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

- [ ] **Step 3: Rewrite `renderChapterList()` to show mastery stats**

Find:

```javascript
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
```

Replace with:

```javascript
function masteryStats(cardsArray) {
  const total = cardsArray.length;
  const mastered = cardsArray.filter((c) => isMastered(c.id)).length;
  const pct = total === 0 ? 0 : Math.round((mastered / total) * 100);
  return { mastered, total, pct };
}

function renderChapterList() {
  const container = document.getElementById('chapter-list');
  container.innerHTML = '';

  const allStats = masteryStats(CARDS);
  const allBtn = document.createElement('button');
  allBtn.className = 'chapter-item';
  allBtn.innerHTML =
    `<span class="chapter-item-title">すべて［${CARDS.length}問］</span>` +
    `<span class="chapter-item-master">マスター ${allStats.mastered}/${allStats.total}（${allStats.pct}%）</span>`;
  allBtn.addEventListener('click', () => startChapter('all'));
  container.appendChild(allBtn);

  for (const ch of CHAPTERS) {
    const chapterCards = CARDS.filter((c) => c.chapter === ch.number);
    const stats = masteryStats(chapterCards);
    const btn = document.createElement('button');
    btn.className = 'chapter-item';
    btn.innerHTML =
      `<span class="chapter-item-title">第${ch.number}章 ${ch.title}［${ch.count}問］</span>` +
      `<span class="chapter-item-master">マスター ${stats.mastered}/${stats.total}（${stats.pct}%）</span>`;
    btn.addEventListener('click', () => startChapter(ch.number));
    container.appendChild(btn);
  }
}
```

- [ ] **Step 4: Add the mastery-skip toggle state and its listener**

Find:

```javascript
let currentCards = [];
let currentIndex = 0;
```

Replace with:

```javascript
const MASTER_SKIP_KEY = 'bizlaw2seisen:masterSkipEnabled';

function isMasterSkipEnabled() {
  try {
    return localStorage.getItem(MASTER_SKIP_KEY) === '1';
  } catch (e) {
    return false;
  }
}

function setMasterSkipEnabled(value) {
  try {
    if (value) {
      localStorage.setItem(MASTER_SKIP_KEY, '1');
    } else {
      localStorage.removeItem(MASTER_SKIP_KEY);
    }
  } catch (e) {
    // ignore
  }
}

function updateMasterSkipButton() {
  const enabled = isMasterSkipEnabled();
  const btn = document.getElementById('btn-master-skip');
  btn.textContent = enabled ? 'マスタースキップ: ON' : 'マスタースキップ: OFF';
  btn.classList.toggle('active', enabled);
}

document.getElementById('btn-master-skip').addEventListener('click', () => {
  setMasterSkipEnabled(!isMasterSkipEnabled());
  updateMasterSkipButton();
});

let currentCards = [];
let currentIndex = 0;
```

- [ ] **Step 5: Apply the skip filter in `startChapter`**

Find:

```javascript
function startChapter(target) {
  currentCards = target === 'all' ? CARDS : CARDS.filter((c) => c.chapter === target);
  currentIndex = 0;
  isFlipped = false;
  sessionResults = {};
  document.getElementById('chapter-screen').hidden = true;
  document.getElementById('card-screen').hidden = false;
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
    alert('この章はすべてマスター済みです');
    return;
  }
  currentCards = cards;
  currentIndex = 0;
  isFlipped = false;
  sessionResults = {};
  document.getElementById('chapter-screen').hidden = true;
  document.getElementById('card-screen').hidden = false;
  renderCard();
}
```

- [ ] **Step 6: Initialize the toggle button's label on page load**

Find:

```javascript
renderChapterList();

if ('serviceWorker' in navigator) {
```

Replace with:

```javascript
renderChapterList();
updateMasterSkipButton();

if ('serviceWorker' in navigator) {
```

- [ ] **Step 7: Verify with real headless Chrome**

Using the scratch-copy technique:
1. On load, confirm `document.getElementById('btn-master-skip').textContent` is `'マスタースキップ: OFF'`.
2. Confirm each chapter button's `innerHTML` contains a `マスター 0/N（0%）` line matching that chapter's real question count from `CHAPTERS` (e.g. chapter 1 should show `マスター 0/14（0%）`), and the "すべて" button shows `マスター 0/172（0%）`.
3. Mark one real card as mastered directly: `setMastered('1-1', true)`. Re-call `renderChapterList()` and confirm chapter 1's button now shows `マスター 1/14（7%）` (`Math.round(1/14*100)` = 7) and "すべて" shows `マスター 1/172（1%）`.
4. Click `#btn-master-skip` to enable it, confirm the label flips to `'マスタースキップ: ON'` and `localStorage.getItem('bizlaw2seisen:masterSkipEnabled')` is `'1'`.
5. With skip enabled and `1-1` mastered, call `startChapter(1)` and confirm `currentCards` does NOT contain the card with id `'1-1'` (`currentCards.some(c => c.id === '1-1')` is `false`) but still has the other 13 chapter-1 cards.
6. As an edge case, mark ALL of chapter 1's cards as mastered (`CARDS.filter(c => c.chapter === 1).forEach(c => setMastered(c.id, true))`), then call `startChapter(1)` again with skip still enabled, and confirm it does NOT navigate to the card screen (`document.getElementById('card-screen').hidden` stays `true`) — the empty-result guard fired. Since `alert()` blocks in a real browser, either stub `window.alert` to a no-op that records it was called before triggering this step, or confirm via the `hidden` check alone if the headless run doesn't block on it. Clean up (`unset`/remove the test's `localStorage` mastery keys) at the end of the self-test script so the assertions are order-independent if re-run.

- [ ] **Step 8: Commit**

```bash
git add index.html
git commit -m "$(cat <<'EOF'
Add mastery stats to the chapter list and a mastery-skip toggle

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: メモ機能 (per-card memo + jump-to-card memo list)

**Files:**
- Modify: `index.html`

**Interfaces:**
- Consumes: `escapeHtml`, `startChapter`'s underlying navigation pattern, `renderCard`, `CARDS`.
- Produces: `MEMO_KEY_PREFIX`, `getMemo(id) -> string`, `setMemo(id, text)`, `showMemoOverlay()`. No other task depends on these.

- [ ] **Step 1: Add the memo textarea to the answer (back) card**

Find:

```html
    <div class="card-face card-back">
      <div id="answer-result"></div>
      <button id="btn-master" class="master-btn">マスター</button>
      <div id="answer-text"></div>
    </div>
```

Replace with:

```html
    <div class="card-face card-back">
      <div id="answer-result"></div>
      <button id="btn-master" class="master-btn">マスター</button>
      <div id="answer-text"></div>
      <div class="memo-container">
        <label for="memo-input" class="memo-label">メモ</label>
        <textarea id="memo-input" class="memo-input" placeholder="この問題のポイントをメモ..."></textarea>
      </div>
    </div>
```

- [ ] **Step 2: Add the "メモ一覧" button next to the mastery-skip toggle**

Find:

```html
  <div class="chapter-toolbar">
    <button id="btn-master-skip"></button>
  </div>
```

Replace with:

```html
  <div class="chapter-toolbar">
    <button id="btn-master-skip"></button>
    <button id="btn-memo-list">メモ一覧</button>
  </div>
```

- [ ] **Step 3: Add the memo overlay markup**

Find:

```html
<div class="overlay" id="score-overlay" hidden>
  <div class="overlay-content">
    <h2>成績</h2>
    <p id="score-summary"></p>
    <ul id="score-list"></ul>
    <button id="btn-score-reset">成績をリセット</button>
    <button id="btn-score-close">閉じる</button>
  </div>
</div>

<script src="cards.js"></script>
```

Replace with:

```html
<div class="overlay" id="score-overlay" hidden>
  <div class="overlay-content">
    <h2>成績</h2>
    <p id="score-summary"></p>
    <ul id="score-list"></ul>
    <button id="btn-score-reset">成績をリセット</button>
    <button id="btn-score-close">閉じる</button>
  </div>
</div>
<div class="overlay" id="memo-overlay" hidden>
  <div class="overlay-content">
    <h2>メモ一覧</h2>
    <ul id="memo-list"></ul>
    <button id="btn-memo-close">閉じる</button>
  </div>
</div>

<script src="cards.js"></script>
```

- [ ] **Step 4: Add memo CSS**

Find:

```css
  .overlay-content button {
    margin-top: 12px;
    width: 100%;
    padding: 12px;
    border-radius: 8px;
    border: 1px solid #d6d3d1;
    background: white;
  }
```

Replace with:

```css
  .overlay-content button {
    margin-top: 12px;
    width: 100%;
    padding: 12px;
    border-radius: 8px;
    border: 1px solid #d6d3d1;
    background: white;
  }
  .memo-container { margin-top: 16px; }
  .memo-label { display: block; font-size: 0.8rem; color: #78716c; margin-bottom: 4px; }
  .memo-input {
    width: 100%;
    min-height: 80px;
    padding: 10px;
    border-radius: 8px;
    border: 1px solid #d6d3d1;
    font-size: 16px;
    font-family: inherit;
    resize: vertical;
    box-sizing: border-box;
  }
  .memo-item { margin-bottom: 12px; list-style: none; }
  .memo-item:last-child { margin-bottom: 0; }
  .memo-item-title { font-weight: bold; font-size: 0.85rem; margin-bottom: 4px; cursor: pointer; }
  .memo-item-text { font-size: 0.85rem; color: #44403c; white-space: pre-line; cursor: pointer; }
```

The `font-size: 16px` on `.memo-input` is required, not cosmetic — iOS Safari auto-zooms the page when a focused text input has a computed font size under 16px, which is jarring inside an installed PWA.

- [ ] **Step 5: Add `MEMO_KEY_PREFIX`, `getMemo`, `setMemo`**

Find:

```javascript
function updateMasterButton(id) {
  document.getElementById('btn-master').classList.toggle('active', isMastered(id));
}

function escapeHtml(str) {
```

Replace with:

```javascript
function updateMasterButton(id) {
  document.getElementById('btn-master').classList.toggle('active', isMastered(id));
}

const MEMO_KEY_PREFIX = 'bizlaw2seisen:memo:';

function getMemo(id) {
  try {
    return localStorage.getItem(MEMO_KEY_PREFIX + id) || '';
  } catch (e) {
    return '';
  }
}

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

- [ ] **Step 6: Populate the textarea in `renderCard()`**

Find:

```javascript
  document.getElementById('card').classList.toggle('flipped', isFlipped);
  renderStarRow(card.id);
  updateMasterButton(card.id);
  updateResultBadge();
}
```

Replace with:

```javascript
  document.getElementById('card').classList.toggle('flipped', isFlipped);
  renderStarRow(card.id);
  updateMasterButton(card.id);
  document.getElementById('memo-input').value = getMemo(card.id);
  updateResultBadge();
}
```

- [ ] **Step 7: Wire up the textarea's listeners**

Find:

```javascript
document.getElementById('btn-master').addEventListener('click', (e) => {
  e.stopPropagation();
  const id = currentCards[currentIndex].id;
  setMastered(id, !isMastered(id));
  updateMasterButton(id);
});

document.getElementById('btn-back').addEventListener('click', () => {
  document.getElementById('card-screen').hidden = true;
  document.getElementById('chapter-screen').hidden = false;
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

document.getElementById('memo-input').addEventListener('click', (e) => {
  e.stopPropagation();
});
document.getElementById('memo-input').addEventListener('input', (e) => {
  setMemo(currentCards[currentIndex].id, e.target.value);
});

document.getElementById('btn-back').addEventListener('click', () => {
  document.getElementById('card-screen').hidden = true;
  document.getElementById('chapter-screen').hidden = false;
});
```

- [ ] **Step 8: Add `showMemoOverlay()` and its listeners, including jump-to-card**

Find:

```javascript
document.getElementById('btn-score-reset').addEventListener('click', () => {
  sessionResults = {};
  showScoreOverlay();
});

renderChapterList();
updateMasterSkipButton();

if ('serviceWorker' in navigator) {
```

Replace with:

```javascript
document.getElementById('btn-score-reset').addEventListener('click', () => {
  sessionResults = {};
  showScoreOverlay();
});

function showMemoOverlay() {
  const withMemo = CARDS.filter((c) => getMemo(c.id).trim() !== '');
  const list = withMemo
    .map((c) => `<li class="memo-item" data-card-id="${c.id}"><div class="memo-item-title">第${c.chapter}章 第${c.questionNumber}問（${escapeHtml(c.title)}）</div><div class="memo-item-text">${escapeHtml(getMemo(c.id))}</div></li>`)
    .join('');
  document.getElementById('memo-list').innerHTML = list || '<li>メモはまだありません</li>';
  document.getElementById('memo-overlay').hidden = false;
}

document.getElementById('btn-memo-list').addEventListener('click', () => {
  showMemoOverlay();
});
document.getElementById('btn-memo-close').addEventListener('click', () => {
  document.getElementById('memo-overlay').hidden = true;
});
document.getElementById('memo-list').addEventListener('click', (e) => {
  const item = e.target.closest('.memo-item');
  if (!item) return;
  const cardId = item.dataset.cardId;
  const card = CARDS.find((c) => c.id === cardId);
  if (!card) return;
  document.getElementById('memo-overlay').hidden = true;
  document.getElementById('chapter-screen').hidden = true;
  document.getElementById('card-screen').hidden = false;
  currentCards = CARDS.filter((c) => c.chapter === card.chapter);
  currentIndex = currentCards.findIndex((c) => c.id === cardId);
  sessionResults = {};
  isFlipped = true;
  renderCard();
});

renderChapterList();
updateMasterSkipButton();

if ('serviceWorker' in navigator) {
```

- [ ] **Step 9: Verify with real headless Chrome**

Using the scratch-copy technique, against real data:
1. On load, click `#btn-memo-list` and confirm `document.getElementById('memo-list').innerHTML` contains `'メモはまだありません'` (no memos exist yet).
2. Close the overlay (`#btn-memo-close`), navigate to a real card in a DIFFERENT chapter than chapter 1 (e.g. `startChapter(3)`, `currentIndex = 0`, `renderCard()`), type into the memo: `document.getElementById('memo-input').value = 'テストメモ'; document.getElementById('memo-input').dispatchEvent(new Event('input'))`. Confirm `localStorage.getItem('bizlaw2seisen:memo:3-1')` equals `'テストメモ'`.
3. Navigate away (`startChapter(1)`), then open the memo list (`showMemoOverlay()`), confirm the list now contains one `<li class="memo-item" data-card-id="3-1">` with `テストメモ` in its text and the correct chapter/question/title header.
4. Click that memo-item's title element (`document.querySelector('.memo-item[data-card-id="3-1"] .memo-item-title').click()` — dispatch a real click so it bubbles to the delegated listener on `#memo-list`) and confirm: `document.getElementById('memo-overlay').hidden` is `true`, `document.getElementById('card-screen').hidden` is `false`, `currentCards[currentIndex].id` is `'3-1'`, and `document.getElementById('card').classList.contains('flipped')` is `true` (jumped straight to the answer side).
5. Confirm clicking inside `#memo-input` does not flip the card: with the card currently flipped (from step 4), click `#memo-input` (`document.getElementById('memo-input').click()`) and confirm `flipped` class is still present (a genuine `.click()` on a textarea does dispatch a real click event that would bubble without `stopPropagation()` — this is the exact regression `e.stopPropagation()` in Step 7 prevents).
6. Clean up the test memo (`setMemo('3-1', '')`) at the end of the self-test script.

- [ ] **Step 10: Commit**

```bash
git add index.html
git commit -m "$(cat <<'EOF'
Add per-card memo textarea and a jump-to-card memo list

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```
