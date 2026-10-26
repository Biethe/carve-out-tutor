# Calm Redesign, Part 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the real Carve-Out tutor the approved calm look and guided flow (a story on the first visit, "what do you want to build?", three questions, one next step at home, a guided workspace), using only what the app can already do: Polyvault and uploaded zips.

**Architecture:** The four tutor pages keep their routes and files (`/` is `catalog.html`, then `/interview`, `/project`, `/learn`) and are rewritten one at a time, in the order a learner meets them. Two new shared scripts carry what several pages show: `chip.js` (the mascot) and `story.js` (the first-visit story). The one stylesheet, `style.css`, is rebuilt from the prototype; the old one lives on as `old.css` only until the last page is converted. On the published site, the boot page (`web/index.html`) plays the story while browser Python loads. The server changes are small: skipping the questions, function descriptions in `GET /api/plan`, and some wording.

**Tech Stack:** Plain HTML, CSS and JS with no build step; FastAPI on Python 3.11+; CodeMirror 5.65.16, mermaid 11.4.1 and Phosphor icons 2.1.1 from the CDNs already in use; Google Fonts through `@import`; Pyodide on the published site. Playwright (installed on this machine, not a project dependency) drives the browser walk.

**Spec:** `docs/superpowers/specs/2026-10-25-calm-redesign-prototype.html`, the approved clickable prototype. Open it in a browser to see every screen move; `P:<line>` below means a line in that file. It simulates the whole flow with three sample apps. Part 1 builds its look and flow on the real app. Building an app from a typed idea is part 2 and out of scope.

## Global Constraints

- Copy: plain and human, sentence case, no em dashes or en dashes, no exclamation marks on screen, nothing that sounds like a slogan. Use the prototype's words wherever it has them, and the exact words given in the tasks for everything new. On-screen apostrophes are curly (’), as in the prototype.
- Look: light only. Colors come only from the tokens at P:10-39, copied exactly. No gradient anywhere except Chip's own body (P:451-466). Panels are plain `--surface` with a 1px `--line` border and a soft shadow.
- Type: Wix Madefor Display 500/600/700 for headings and Chip's words, Wix Madefor Text 400/500/600 for text, Geist Mono 400/500 for code. Shantell Sans and Atkinson Hyperlegible Mono stay loaded only as editor font choices.
- Motion: the prototype's easings (`--ease`, `--spring`) and keyframes. Motion only shows what happened or where to look. Under `prefers-reduced-motion: reduce`, the rule at P:427-429 stops it all, and every state change must still show.
- `.chip` now means Chip, the mascot. Small labels ("Coming soon", "Shown") use `.tag`.
- Links on the published site: `web/bridge.py` moves quoted root paths in HTML (`"/static/x"`, `"/project"`) under the site's path, but not `"/?..."` or `"/#..."`, so write `./?new`. Nothing in a `.js` file is rewritten: use relative URLs there (`api/state`, `learn`, `project`).
- Shared scripts are classic scripts that each expose one global (`Chip`, `Story`) and keep the rest inside an IIFE. Pages keep their own `$`, `api` and `esc`.
- Every API endpoint keeps working as it does today. No new libraries; `canvas-confetti` goes (the function flying into the counter replaces it).
- Every existing feature stays reachable: run the project, download it, delete an upload, the plan editor, any function in any order, hints, asking Chip, the check question, Clean, Files, Map, the code font, the bigger editor, paste blocking, voice.
- Git: work on branch `calm-redesign`, one commit per task, never push (a push to main publishes the site). Messages follow the repo's style, one plain sentence with no prefix, and end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- After adding or removing a file under `tutor/`, run `.venv/bin/python web/files.py` and commit `web/files.json` with it.

## Decisions for part 1 (my calls, for the user to confirm)

1. **Your own idea shows, marked "Coming soon".** The idea box stays first on the start page, as approved. Typing works and Chip reacts. "Build it" doesn't build yet: for a store-like idea Chip points to Polyvault; for anything else Chip says building new ideas is coming soon and points to Polyvault and "Bring my project". The story keeps its seven approved sentences, since part 2 delivers them.
2. **One example instead of four pills.** Only Polyvault exists, so the starters become one row, "Open Polyvault". The recipe box, habit tracker and bill splitter come back with part 2. The GitHub link field waits until the server can import from GitHub; zips work.
3. **No build screen yet.** Polyvault and uploads already exist, so choosing goes straight to the questions (first time) or home.
4. **The questions come after choosing**, as in the prototype: the project page sends a learner without a profile to `/interview`, and the questions end on home. "Skip these questions" saves an empty profile (Task 4).
5. **The voice stays.** The question is always on screen, Chip's recorded voice plays along, and Chip listens for yes or no, as today. Browsers block sound until the first click on a page, so the first question is silent and the voice joins in after the first answer. One sound button turns voice and listening off and on.
6. **Home steps:** "Answer 3 quick questions" (done), "Try the store" or "Try your app" (left out for uploads with nothing to run), then one step per function in the plan. The journey strip shows at most 9 steps around "You are here". Function steps say "Function N of M", the same numbers the workspace shows. "I've tried it" is remembered in this browser.
7. **"N of M yours"** counts passed functions out of all of the project's functions (28 for Polyvault). The ownership percentage by lines moves into the pill's tooltip.
8. **The workspace:** the Your task, Read first, Files and Map tabs become one task card with closed sections, so the editor and Chip stay in view. The draggable Chip window becomes the docked buddy panel. The function picker moves to home ("See the whole plan"). After a pass, the check question opens in the win sheet and `/api/explain` grades it as today.
9. **Themes go.** Paper, blueprint and chalkboard, and `theme.js`, are removed. The editor's font choice stays, with Geist Mono ("Classic mono") as the new default.

## Review Focus

1. **The published site.** A link or fetch that works on `localhost` but breaks under `/<repo>/web/tutor/`: a `/?` link, a root path in a `.js` file, a script the boot page can't reach. Expected: the whole flow works on the Pages build. Pinned by the site walk in Task 8.
2. **A returning learner.** Someone with a profile and progress opens the site again. Expected: no story, straight to home with the right next step; `New project` still reaches the start page; reloading the workspace comes back to it. Pinned in Tasks 2, 5 and 6.
3. **Uploads that aren't Polyvault.** A project with nothing to run, one that partly can't run in the browser, one whose next function needs the AI to prepare. Expected: no "Try your app" step and no "Open my app" for the first, the compatibility notes for the second, a plain error and a working button for the third. Pinned in Tasks 3 and 5.
4. **No AI available** (no key, or the demo proxy busy). Chip's plan suggestion, hints, answers, Clean and the check question all fail. Expected: Chip says so in plain words (pointing at Settings when there's no key), every button comes back, nothing spins forever. Pinned in Tasks 5, 6 and 7.
5. **Phone width, keyboard, reduced motion.** 390px wide, Tab and Esc only, `prefers-reduced-motion`. Expected: no sideways scrolling, the story scales down, the workspace stacks, the tour card and the win sheet fit, every action works from the keyboard with a visible focus ring, and with reduced motion nothing animates but every state still shows. Pinned by every task's phone walk, and in Task 7.

---

## File structure

| File | Its job after this plan |
|---|---|
| `tutor/static/style.css` | The one stylesheet, rebuilt: tokens, base, buttons, panels, top bar, Chip, then one section per screen, each with its own small-screen rules. |
| `tutor/static/chip.js` (new) | Chip: the SVG, eyes that follow the pointer, word-by-word speech, moods. |
| `tutor/static/story.js` (new) | The seven-beat first-visit story, drawn into any element. |
| `tutor/static/old.css` (temporary) | The old stylesheet, for pages not converted yet. Deleted in Task 8. |
| `tutor/static/theme.js` | Deleted in Task 8. `learn.js` sets the code font itself. |
| `tutor/static/settings.js` | Opens the Settings dialog from any `[data-open-settings]` button. |
| `tutor/static/compat.js` | The same verdicts, with tags instead of emoji. |
| `web/index.html` | The published boot page: the story while Python loads, then the tutor. |
| `tutor/pages/catalog.html` | The start page: the story (first local visit), "what do you want to build?", Polyvault, bring your project, your projects. |
| `tutor/pages/interview.html` | Three questions, then the profile view. |
| `tutor/pages/project.html` | Home: the next step, the journey, the whole plan. |
| `tutor/pages/learn.html`, `tutor/static/learn.js` | The guided workspace. |
| `tutor/app.py`, `tutor/onboarding.py`, `tutor/llm.py`, `tutor/overview.py` | Skipping the questions, descriptions in the plan, wording, the diagram's highlight color. |
| `tests/ui_walk.cjs` (new) | Walks the screens in a real browser and fails on wrong text, a missing element, a console error, a failed request, or a page that scrolls sideways. |
| `web/files.py` | Leaves `.cjs` files out, so the walk isn't loaded into browser Python. |
| `README.md` | The walkthrough and "start over" describe the new flow (Task 8). |

## How to run the checks

Define these once per shell, from the repo root. A local walk always starts a fresh tutor with no AI key, so nothing in it calls the AI and the "no AI" paths get exercised every time.

```bash
export SHOTS=/tmp/ui-walk CHROME=$HOME/.cache/ms-playwright/chromium-1246/chrome-linux64/chrome; mkdir -p $SHOTS
export NODE_PATH=$(npm root -g)/@playwright/cli/node_modules
walk() {  # walk <desktop|phone> <step...>: a fresh local tutor, then the walk
  pkill -f "uvicorn tutor.app:app --port 8765"; export TUTOR_DATA=$(mktemp -d)
  (LLM_API_KEY= GROQ_API_KEY= .venv/bin/uvicorn tutor.app:app --port 8765 >/dev/null 2>&1 &)
  until curl -s 127.0.0.1:8765/api/state >/dev/null; do sleep .3; done
  node tests/ui_walk.cjs http://127.0.0.1:8765/ "$@"
}
site() {  # site <desktop|phone> <step...>: the published build, served the way GitHub Pages serves it
  .venv/bin/python web/files.py >/dev/null; pkill -f "http.server 8020"; (python3 -m http.server 8020 >/dev/null 2>&1 &); sleep 1
  node tests/ui_walk.cjs http://127.0.0.1:8020/web/ "$@"
}
checks() { .venv/bin/python -m pytest -q && for f in tutor/static/*.js tests/ui_walk.cjs; do node --check "$f" || return 1; done; }
```

A walk prints `ok <step>` per step and exits 0, or prints `FAIL <reason>` and exits 1. Look at the screenshots in `$SHOTS` after each task: the walk catches what's broken, the screenshots show whether it looks like the prototype.

---

### Task 1: The new foundation and the boot loader

**Files:**
- Move: `tutor/static/style.css` to `tutor/static/old.css`, and point the `<link>` in `tutor/pages/{catalog,project,learn,interview}.html` at `/static/old.css`
- Create: `tutor/static/style.css`, `tutor/static/chip.js`, `tests/ui_walk.cjs`
- Modify: `web/index.html`, `web/files.py`, `web/files.json`

**Interfaces:**
- Produces `Chip.mount(root = document)`: fills every `[data-chip]` under `root` with Chip's SVG (P:710-728), once per element, and adds the shared `<defs>` (P:451-466) to the page once. It runs by itself on `DOMContentLoaded`; pages call it again for Chips they add later.
- Produces `Chip.say(el, text, chip?)`: replaces `el`'s content with `text`, revealed word by word (P:731-740: 55 ms a word, none under reduced motion). If `chip` is given, it gets `.talk` for `words × 55 + 450` ms.
- Produces `Chip.lookAt(chip, el | null)`: the eyes look at `el`'s centre; `null` goes back to following the pointer (P:741-767, including the idle glance).
- Produces `Chip.mood(chip, name, ms?)`: adds the class `name` (`talk`, `busy`, `think`, `happy`, `jump`), and removes it after `ms` if given.
- Produces these CSS classes for every later task: `chip` with sizes `xs sm md lg xl` and states `talk busy think happy hop jump`; `panel` and `panel raised` (the prototype's `glass` and `glass-strong`); `btn` with `primary ghost sm lg xl nudge` and `.go` arrows; `link`; `tag` with `good warn bad`; `top`, `brand`, `crumb`, `top-right`, `navb`; `own` with `bump`, and `ring`; `say` with `md sm`; `screen`; `status` with `error`; `gut`, `sr`, `muted`, `mono`.
- Produces `tests/ui_walk.cjs <url> <desktop|phone> <step...>` with the helpers `T()`, `see()`, `shot()`, `fail()` and the step `boot`. Later tasks add steps to its `STEPS` table.

- [ ] **Step 1: Branch, and commit the plan and its spec**

```bash
git switch -c calm-redesign
git add docs/superpowers
git commit -m "Plan the calm redesign of the tutor, with the approved prototype as its spec

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 2: Write the walk and its first step**

Create `tests/ui_walk.cjs`. The harness below is the contract every later step relies on; keep its helpers as they are.

```js
// Walks the tutor's screens in a real browser. It fails on wrong text, a missing element, a console error, a failed
// request, or a page that scrolls sideways, and saves a screenshot of every screen to $SHOTS. See the plan for how
// to start a fresh tutor first. Usage: node tests/ui_walk.cjs <url> <desktop|phone> <step...>
const { chromium } = require("playwright");
const { execFileSync } = require("child_process");

const [url, size, ...steps] = process.argv.slice(2);
const SHOTS = process.env.SHOTS || "/tmp/ui-walk";
const SITE = url.includes("/web/");  // the published build: the tutor runs inside the boot page's frame
let page;
const errors = [];
const fail = (why) => { throw new Error(why); };

// Where the tutor's pages are: the page itself, or the boot page's frame once Python has started.
async function T() {
  if (!SITE) return page.mainFrame();
  return (await page.waitForSelector("#tutor:not([hidden])", { timeout: 180000 })).contentFrame();
}
// Waits until `selector` is visible and, if `text` is given, until its text includes it.
async function see(where, selector, text, timeout = 15000) {
  const el = where.locator(selector).first();
  await el.waitFor({ state: "visible", timeout });
  for (const end = Date.now() + timeout; text !== undefined && !(await el.innerText()).includes(text);) {
    if (Date.now() > end) fail(`${selector} should say "${text}", it says "${await el.innerText()}"`);
    await page.waitForTimeout(200);
  }
  return el;
}
async function shot(where, name) {
  await page.waitForTimeout(800);  // let the entrance motion settle
  if (await where.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)) fail(`${name}: the page scrolls sideways`);
  await page.screenshot({ path: `${SHOTS}/${size}-${name}.png` });
}

async function boot() {  // the published site, a later visit: Chip waits with you while Python loads, then the tutor opens
  await page.evaluate(() => localStorage.setItem("seenStory", "1"));
  await page.reload();
  await see(page, "#boot-say", "Getting Python ready");
  if ((await page.locator("#boot-chip svg .pin").count()) !== 8) fail("Chip should have 8 pins");
  await page.mouse.move(5, 5);
  await page.waitForTimeout(300);
  if (!((await page.locator("#boot-chip").getAttribute("style")) || "").includes("--px")) fail("Chip's eyes should follow the pointer");
  await shot(page, "boot");
  await T();
}

const STEPS = { boot };

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROME || undefined });
  const view = size === "phone" ? { width: 390, height: 844 } : { width: 1280, height: 800 };
  const context = await browser.newContext({ viewport: view, reducedMotion: process.env.REDUCED ? "reduce" : "no-preference" });
  // With no key, the published build falls back to the shared demo AI. Block it: the walk never depends on the AI.
  if (SITE) await context.route(/workers\.dev/, (r) => r.abort());
  page = await context.newPage();
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => { if (m.type() === "error" && !m.text().startsWith("Failed to load resource")) errors.push(m.text()); });
  page.on("response", (r) => { if (r.status() >= 400 && !r.url().endsWith("favicon.ico")) errors.push(`${r.status()} ${r.url()}`); });
  await page.goto(url);
  for (const name of steps) {
    if (!STEPS[name]) fail(`no step called ${name}`);
    await STEPS[name]();
    if (errors.length) fail(`${name}: ${errors.join("\n")}`);
    console.log("ok", name);
  }
  await browser.close();
})().catch((e) => { console.error("FAIL", e.message); process.exit(1); });
```

`execFileSync` is there for Task 3's zip helper. In `web/files.py`, add `".cjs"` to the skipped suffixes (`{".db", ".pyc", ".cjs"}`).

- [ ] **Step 3: Run it and watch it fail**

Run: `site desktop boot`
Expected: `FAIL #boot-say should say "Getting Python ready"...` or a timeout on `#boot-say` (the old boot page has no such element).

- [ ] **Step 4: Move the old stylesheet aside**

`git mv tutor/static/style.css tutor/static/old.css`, then in the four pages change `href="/static/style.css"` to `href="/static/old.css"`. The old pages must look exactly as before; `web/index.html` moves to the new stylesheet in Step 6.

- [ ] **Step 5: Write the new `tutor/static/style.css` foundation**

Sections, in this order, ported from the prototype unless noted:
1. `@import` of Google Fonts: `Wix+Madefor+Display:wght@500;600;700`, `Wix+Madefor+Text:wght@400;500;600`, `Geist+Mono:wght@400;500`, `Shantell+Sans:ital,wght,BNCE,INFM@0,300..800,-100..100,0..100` and `Atkinson+Hyperlegible+Mono:wght@400;600`, with `display=swap`.
2. Tokens and base: P:10-49. Add `body { margin: 0; min-height: 100dvh; }`, `a { color: var(--accent-ink); }`, `h1, h2, h3 { font-family: var(--display); }`.
3. Panels: P:51-53, renamed `.panel` and `.panel.raised`.
4. Screens: instead of P:55-58's class toggling, `.screen { animation: screenIn .55s var(--ease) both; }` with `@keyframes screenIn { from { opacity: 0; transform: translateY(14px); filter: blur(4px); } }`, so a page or section eases in whenever it becomes visible, with no script. Keep fixed layers (dialogs, sheets, the tour) outside `.screen` elements.
5. Top bar, the ownership pill and its ring: P:60-74. Rename the prototype's `.status` (the Python status at the top of the story) to `.py-status`; `.status` is the status line in item 8. Under 760px, `.crumb` hides (P:443).
6. Buttons, links, pills: P:76-97. Add `.go { display: inline-block; }` (Phosphor's `<i>` arrows need it to move).
7. Tags (new): `.tag { display: inline-flex; align-items: center; height: 24px; padding: 0 9px; border-radius: 8px; background: var(--accent-soft); color: var(--accent-ink); font: 600 12.5px var(--text); white-space: nowrap; }`, `.tag.good { background: rgba(59, 138, 90, .12); color: var(--good-ink); }`, `.tag.warn { background: rgba(154, 106, 46, .14); color: var(--ink); }`, `.tag.bad { background: rgba(194, 85, 77, .12); color: var(--bad-ink); }`.
8. Status lines (new): `.status { margin: 0; min-height: 1.4em; font-size: 14.5px; color: var(--muted); white-space: pre-wrap; }`, `.status.error { color: var(--bad-ink); font: 400 13px/1.5 var(--mono); }`.
9. Chip and Chip's words: P:99-133, and under 760px the smaller `.say` sizes (P:440-441).
10. Motion: the keyframes at P:404-426 (leave out the unused `drift`) and the reduced-motion rule at P:427-429.

- [ ] **Step 6: Write `tutor/static/chip.js`**

Port P:710-767 into `const Chip = (() => { ...; return { mount, say, lookAt, mood }; })();`. The defs `<svg>` from P:451-466 is created by `mount` the first time it runs (one per document). Eye tracking follows the pointer on every Chip on the page, as in `lookAll`. File header comment: `// Chip, the tutor's mascot: a little microchip whose eyes follow you. Shared by every page.`

- [ ] **Step 7: The boot loader in `web/index.html`**

Head: drop `theme.js` and the Phosphor stylesheet; link `../tutor/static/style.css`; scripts `../tutor/static/chip.js` then `python.js`. Keep the inline style for `#tutor` (`position: fixed; inset: 0; width: 100%; height: 100%; border: 0;`) and replace the rest with `.boot { min-height: calc(100dvh - 70px); display: grid; place-content: center; justify-items: center; gap: 16px; text-align: center; }`. Remove `overflow: hidden` from `body` (the story in Task 2 must be able to scroll on short screens).

Body:
```html
<section id="boot" hidden>
  <header class="top gut"><span class="brand"><span class="chip xs" data-chip></span>Carve-Out</span></header>
  <main class="boot gut screen">
    <span class="chip lg busy" id="boot-chip" data-chip></span>
    <p class="say md" id="boot-say" role="status">Getting Python ready…</p>
    <p class="muted">Everything runs in your browser. The first visit downloads Python once, so it takes a little longer.</p>
    <button class="btn" id="boot-retry" hidden>Try again</button>
  </main>
</section>
<iframe id="tutor" title="Carve-Out Tutor" allow="microphone; autoplay" hidden></iframe>
```
Script: show `#boot`, then `Python.start()`. On success, open the tutor exactly as today (`frame.src = "tutor/" + location.hash.slice(1)`, and the same `onload` that hides `#boot`, keeps the address bar's hash in step and copies the title). On failure: `#boot-say` says `Python couldn’t start: <message>`, Chip loses `busy`, and `#boot-retry` shows and reloads the page.

- [ ] **Step 8: Run the checks**

Run: `.venv/bin/python web/files.py && checks && site desktop boot && site phone boot`
Expected: pytest passes as before, no `node --check` output, `ok boot` twice. Open `$SHOTS/desktop-boot.png`: the calm loader with Chip, and once Python is ready, the old catalog in the frame, looking exactly as it did.

- [ ] **Step 9: Commit**

```bash
git add tutor/static web tests/ui_walk.cjs tutor/pages
git commit -m "Lay the calm look's foundation: tokens, buttons, Chip as a microchip, and a boot loader that waits with you

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: The story, while Python loads

**Files:**
- Create: `tutor/static/story.js`
- Modify: `tutor/static/style.css` (a "Story" section), `web/index.html`, `web/files.json`, `tests/ui_walk.cjs` (step `story`)

**Interfaces:**
- Consumes: `Chip.mount`, `Chip.say`, `Chip.mood` (Task 1).
- Produces `Story.play(root, { python = false, onDone })`: draws the story (P:468-532) into `root`, starts at beat 1, and calls `onDone()` after the last beat's button or "Skip intro". Just before `onDone`, it sets `localStorage.seenStory = "1"` (inside try/catch).
- Produces `Story.seen()`: true if `localStorage.seenStory === "1"` (false if storage throws).
- Produces `Story.python(state)`: with `python: true`, the status at the top of the story (`<span class="py-status" id="py">`) shows a spinner and `Getting Python ready`; `"ready"` turns it into the green dot and `Python is ready`, `"failed"` into `Python couldn’t start` in `--bad-ink`. With `python: false` there is no status, and when no story is showing the call does nothing.

- [ ] **Step 1: Add the failing step**

```js
const BEATS = [
  "Hi, I’m Chip. Let’s build something you actually care about.",
  "It starts with your idea. Any idea.",
  "I build the whole app for you, and it already works.",
  "Inside, it’s made of small pieces of code called functions.",
  "We take one piece out, and you write it back. I give hints, never answers.",
  "Your piece goes back in, and the app keeps working on your code.",
  "Piece by piece, the app you dreamed up becomes yours.",
];
async function story() {  // the published site, first visit: the story plays while Python loads
  await see(page, "#story-say", BEATS[0]);
  if (!(await page.locator("#story-back").isDisabled())) fail("Back should be off on the first beat");
  await see(page, "#story-next", "Show me");
  await shot(page, "story-1");
  for (let i = 1; i < 7; i++) {
    await page.click("#story-next");
    await see(page, "#story-say", BEATS[i]);
  }
  await see(page, "#story-next", "What will you build?");
  await page.click("#story-back");
  await see(page, "#story-say", BEATS[5]);
  await page.keyboard.press("ArrowRight");
  await see(page, "#story-say", BEATS[6]);
  await shot(page, "story-7");
  await see(page, "#py", "Python is ready", 180000);
  await page.click("#story-next");
  await T();
  if ((await page.evaluate(() => localStorage.getItem("seenStory"))) !== "1") fail("the story should be remembered");
  await page.evaluate(() => localStorage.removeItem("seenStory"));  // Skip works too
  await page.reload();
  await page.click("#skip-intro");
  await T();
}
```
Add `story` to `STEPS`. Run `site desktop story`; expected: FAIL on `#story-say`.

- [ ] **Step 2: Write `tutor/static/story.js`**

Port the story markup (P:468-532, minus the `<section>` wrapper) as a template string, and its script (P:797-914): `STORY`, `PLAY`, `goBeat`, `clickAt`, `fitStage`, the Next and Back buttons, ArrowLeft and ArrowRight (only while `root` is visible and focus isn't in a field), and "Skip intro". The last beat's button and "Skip intro" call the finish path described in the interface. All timers clear on every beat change and on finish. Expose `const Story = (() => { ...; return { play, seen, python }; })();`.

- [ ] **Step 3: Story styles**

Add a "Story" section to `style.css`: P:135-231, with `.glass` and `.glass-strong` renamed as in Task 1, plus, under 760px, `.caption` (P:442), `.py-status` hidden (P:443) and `.story-nav` (P:444).

- [ ] **Step 4: Play it on the boot page**

`web/index.html` gains `<div id="intro"></div>` before `#boot` and `../tutor/static/story.js` after `chip.js`. The page script becomes:

```js
// First visit: the story plays while Python loads. Later visits: Chip waits with you. The tutor opens once both are done.
let ready = false, told = Story.seen(), failed = null;
const boot = document.getElementById("boot"), intro = document.getElementById("intro");
function next() {
  if (!told) return;
  intro.hidden = true;
  if (ready) return open();
  boot.hidden = false;
  if (failed) showFailure(failed);
}
if (told) next(); else Story.play(intro, { python: true, onDone() { told = true; next(); } });
Python.start().then(() => { ready = true; Story.python("ready"); next(); })
  .catch((err) => { failed = err; Story.python("failed"); next(); });
```
`open()` and `showFailure(err)` are Task 1's success and failure code, moved into functions.

- [ ] **Step 5: Run the checks**

Run: `.venv/bin/python web/files.py && checks && site desktop story boot && site phone story boot`
Expected: `ok story`, `ok boot` for both sizes. In `$SHOTS/phone-story-1.png` the stage is scaled down and nothing is cut off.

- [ ] **Step 6: Commit**

```bash
git add tutor/static web tests/ui_walk.cjs
git commit -m "Tell the story of what Carve-Out does while Python loads, one sentence at a time

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: The start page: "So, what do you want to build?"

**Files:**
- Rewrite: `tutor/pages/catalog.html`
- Modify: `tutor/static/style.css` ("Start page" and "Dialogs" sections), `tutor/static/settings.js`, `tutor/pages/project.html` (one line, until Task 5 rewrites it), `tests/ui_walk.cjs` (steps `start`, `choose`, helpers `makeZip` and `AREA`)

**Interfaces:**
- Consumes: `Chip`, `Story`, `Compat.verdict` (unchanged).
- Produces: any element with `data-open-settings` opens Settings (`settings.js`). While old pages remain, `settings.js` still adds its gear when a page has a `.theme-switch` and no `[data-open-settings]`; Task 8 removes that.
- Produces: `./?new` shows the start page even to a learner with a profile; `?intro` plays the story again. Every page's brand links to `/`, which sends a learner with a profile home.
- Produces upload cards `.p-mine[data-name]` with `a.btn` (Open), `[data-ask-delete]`, `.confirm`, `[data-delete]`, `[data-cancel]`, and the walk helpers `makeZip(name, files)` and `AREA` (one plain function), all reused by Task 5's walk.

- [ ] **Step 1: Add the failing steps**

```js
// A small project of your own, zipped the way GitHub zips a repository: one top folder named after it.
function makeZip(name, files) {
  const zip = `${SHOTS}/${name}.zip`;
  const entries = Object.fromEntries(Object.entries(files).map(([path, text]) => [`${name}/${path}`, text]));
  execFileSync(process.env.PYTHON || "python3", ["-c",
    "import json, sys, zipfile\nwith zipfile.ZipFile(sys.argv[1], 'w') as z:\n    for path, text in json.loads(sys.argv[2]).items(): z.writestr(path, text)",
    zip, JSON.stringify(entries)]);
  return zip;
}
const AREA = 'def area(width, height):\n    """Width times height."""\n    return width * height\n';
async function start() {  // a first local visit: the story plays on the start page, Skip goes to the choice
  await see(page, "#story-say", BEATS[0]);
  if (await page.locator("#py").count()) fail("no Python status when Python isn't loading");
  await page.click("#skip-intro");
  await see(page, "#c-say", "So, what do you want to build?");
  await shot(page, "choose");
}
async function choose() {  // the idea box reacts, Polyvault opens, a zip uploads and deletes
  const t = await T();
  await t.fill("#idea-in", "an online shop for posters");
  await see(t, "#c-say", "Good news: that one already exists. It’s called Polyvault");
  await t.click("#idea-go");
  await see(t, "#open-store.nudge");
  await t.fill("#idea-in", "a game about frogs");
  await see(t, "#c-say", "Ooh. Tell me a little more.");
  await t.click("#idea-go");
  await see(t, "#c-say", "I can’t build new ideas yet. That’s coming soon.");
  await t.click("#own-open");
  await see(t, "#c-say", "Your own code works too. Drop it in and I’ll find its pieces.");
  await t.setInputFiles("#zip-in", makeZip("mini", { "shapes.py": AREA }));
  await see(t, "#upload-result", "mini is ready");
  await see(t, '.p-mine[data-name="mini"]', "Python code, tests only");
  await shot(t, "uploaded");
  await t.click('.p-mine[data-name="mini"] [data-ask-delete]');
  await see(t, '.p-mine[data-name="mini"] .confirm', "Delete mini?");
  await t.click('.p-mine[data-name="mini"] [data-delete]');
  await t.locator('.p-mine[data-name="mini"]').waitFor({ state: "detached" });
  await t.click("#open-store");
  await t.waitForURL(/\/interview/);  // a new learner answers three questions first
}
```
Add both to `STEPS`. Run `walk desktop start choose`; expected: FAIL on `#story-say`.

- [ ] **Step 2: Settings from a button**

In `settings.js`: build the dialog as now, then wire every `[data-open-settings]` to the existing open handler. Create the gear and profile icons only when the page has a `.theme-switch` and no `[data-open-settings]` (old pages, until Task 8). Dialog markup: `<dialog class="sheet settings-dialog">` with the same fields and text, buttons `class="btn primary"` (Save) and `class="btn ghost"` (Cancel). Add a "Dialogs" section to `style.css`, shared by every dialog from here on (Settings now, the map in Task 6, the win sheet in Task 7): `dialog.sheet` is the prototype's sheet (P:390: `width: min(600px, calc(100% - 32px))`, padding 28px, radius 28px, `--surface`, `--shadow-xl`, no border, `color: var(--ink)`); `dialog.sheet::backdrop` is the dim at P:388 (`rgba(243, 244, 242, .72)` with an 8px blur); `dialog.sheet[open] { animation: sheetIn .55s var(--spring) both; }` with `@keyframes sheetIn { from { opacity: 0; transform: translateY(34px) scale(.98); } }`. In the Settings form, labels sit over 42px fields with a 1px `--line` border and 12px radius.

- [ ] **Step 3: Rewrite `catalog.html`**

Head: title `Carve-Out Tutor`, meta description unchanged, `/static/style.css`, the Phosphor stylesheet, and scripts `/static/chip.js`, `/static/story.js`, `/static/settings.js`, `/static/compat.js`.

Markup, top to bottom:
- `<div id="intro" hidden></div>` for the story.
- `<section id="choose" class="screen" hidden>` with a top bar: brand (`<a class="brand" href="/">` with an `xs` Chip and `Carve-Out`), and on the right `<a class="navb" href="/interview" id="to-profile" hidden>Profile</a>` and `<button class="navb" data-open-settings>Settings</button>`.
- `<main class="choose gut">`, following P:539-567 with these changes:
  - The greeting: `lg` Chip `#c-chip` and `#c-say`.
  - The idea form `#idea-form` (`panel raised`) with `#idea-in` (placeholder `Describe your idea in one sentence`) and a foot: `<span class="muted">Anything you’d use or enjoy.</span>`, then `<span class="tag">Coming soon</span>` and the primary `#idea-go` (`Build it` with a Phosphor `ph-arrow-right go`).
  - `<span class="muted">Or start from an app that already works</span>` and one `panel` row: the chest, lantern and boombox pictures (`/store-assets/chest.webp`, `lantern.webp`, `boombox.webp`, 48px squares on `--studio`, `alt=""`), `<b>Polyvault</b>`, `<span class="muted">An online store for 3D models, written in Python. 28 functions to rebuild.</span>`, and `<a class="btn" id="open-store" href="/project?open=store">Open Polyvault</a>`.
  - The own-project row (P:558-562) with the text `Bring your own code as a .zip, and learn on that.`, and the `#drop` panel with only the drop zone (no GitHub form), then `<p class="muted small">Only upload projects you trust. Chip checks for harmful code first, but no check catches everything.</p>` and `<div id="upload-result" role="status"></div>`.
  - `<section id="uploads" hidden>` with `<h2>Your projects</h2>` and a grid of `.p-mine` cards.

Script:
1. `const params = new URLSearchParams(location.search)`; fetch `api/profile`. With a finished profile and neither `new` nor `intro` in the query: `location.replace("project")`. Show `#to-profile` when the profile is done.
2. If `params.has("intro")`, or the profile isn't done and `!Story.seen()`: show `#intro` and `Story.play(intro, { onDone: choose })`. Otherwise `choose()`.
3. `choose()` hides `#intro`, shows `#choose`, and after 420 ms has Chip say `What do you want to build next?` when `params.has("new")`, else `So, what do you want to build?`. It focuses `#idea-in` only when `matchMedia("(pointer: fine)").matches` (no phone keyboard popping up).
4. The idea box: port the reactions from P:1153-1194 (`KNOWN`, `pickTemplate`, the `fired` set, `Ooh. Tell me a little more.`, `I can picture it already.`), with these reaction lines: store `Good news: that one already exists. It’s called Polyvault, and it’s ready to take apart.`, recipes `Yum. Recipe apps have great pieces to learn from.`, habits `Tracking habits teaches lists and dates. Good pick.`, money `Money apps teach careful math. Nice.` `#idea-go` is enabled from 4 characters. Submitting a store-like idea repeats the store line and adds `.nudge` to `#open-store`; any other idea says `I can’t build new ideas yet. That’s coming soon. For now, try Polyvault below, or bring your own code.` and nudges `#open-store` too. Chip looks at `#idea-in` while you type (`Chip.lookAt`, back after 1.5 s).
5. `#own-open` toggles `#drop` (`aria-expanded`) and, on opening, Chip says `Your own code works too. Drop it in and I’ll find its pieces.`
6. Upload, the list, Open and Delete: keep today's code from the old `catalog.html` (`upload`, `showUploads`, drag and drop, the delete confirm), with this copy: while it works, `#upload-result` says `Unpacking <file name> and checking it…` and Chip gets `busy`; a file that isn't a zip: `That’s not a .zip file.`; blocked: `Blocked. It won’t run:` plus the reasons; ready: `<name> is ready. <Compat.verdict>`. Card meta stays `<kind> · <n> function(s) in <m> file(s)`; the fit line is a tag: `full` is `tag good` "Runs in your browser", `partial` is `tag warn` "Partly runs in your browser", `none` is `tag bad` "Needs your own computer", blocked is `tag bad` "Blocked by the safety check". The confirm says `Delete <name>? Its files and your progress on it go too.` Open links to `project?open=<name>`. `#uploads` is hidden when there are none.

- [ ] **Step 4: Send new learners to the questions from the project page**

In the old `project.html`, after `ready` resolves: `ready.then(() => fetch("api/profile")).then((r) => r.json()).then((p) => { if (!p.done) location.replace("interview"); });`. Task 5 keeps this rule in the new home.

- [ ] **Step 5: Start page styles**

A "Start page" section in `style.css`: P:233-254 (minus `.gh` and `.pills`), the example row, the `.p-mine` grid (two columns from 640px, one below) and the inline `.confirm`, plus its small-screen rule `.idea textarea { font-size: 20px; }` under 760px.

- [ ] **Step 6: Run the checks**

Run: `checks && walk desktop start choose && walk phone start choose`
Expected: `ok start`, `ok choose` at both sizes. The old interview page opens at the end of `choose`.

- [ ] **Step 7: Commit**

```bash
git add tutor tests/ui_walk.cjs
git commit -m "Start with the learner's own idea: what do you want to build, Polyvault, or your own project

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Three questions, and the profile

**Files:**
- Rewrite: `tutor/pages/interview.html`
- Modify: `tutor/onboarding.py`, `tutor/app.py` (`finish_onboarding`), `tutor/static/style.css` ("Questions" and "Profile" sections), `tests/ui_walk.cjs` (steps `quiz`, `skipquiz`, `profile`)

**Interfaces:**
- Consumes: `Chip`, `Voice` (unchanged), `GET /api/onboarding`, `GET /api/profile`, `GET /api/project`, `POST /api/onboarding`, `POST /api/interview`, `/api/interview/restart`, `/api/interview/more`, `PUT /api/profile`.
- Produces: `POST /api/onboarding {answers: []}` saves a finished profile: level `beginner`, summary `Skipped the first questions.`, no claims, gaps or wants.
- Produces: the questions end on `project`. Element ids: `#quiz`, `#build-pill`, `#build-text`, `#q-count`, `#q-dots`, `#q-chip`, `#q-react`, `#q-text`, `#q-why`, `#q-yes`, `#q-no`, `#q-skip`, `#sound`, `#q-status`; `#profile`, `#p-level`, `#p-summary`, `#p-claims`, `#p-gaps`, `#p-wants`, `#home`, `#more`, `#redo`.

- [ ] **Step 1: Pin the skip in the onboarding self-check**

In `tutor/onboarding.py`'s `__main__` block add:
```python
    skipped = profile([])
    assert skipped["done"] and skipped["level"] == "beginner" and skipped["summary"] == "Skipped the first questions." and not skipped["claims"]
```
Run: `.venv/bin/python -m tutor.onboarding`
Expected: FAIL (`AssertionError`: the summary is `New to coding.`).

- [ ] **Step 2: Allow skipping**

`profile(answers)` returns `summary="Skipped the first questions."` when `answers` is empty. In `finish_onboarding`, refuse only when there are answers that don't start with `python`: `if (answers and answers[0][0] != "python") or not all(q in onboarding.QUESTIONS for q, _ in answers):`.
Run: `.venv/bin/python -m tutor.onboarding`
Expected: `onboarding ok, ... characters to record`.

- [ ] **Step 3: Add the failing walk steps**

```js
async function quiz() {  // three yes/no questions after picking Polyvault; the walk answers yes, no, yes
  const t = await T();
  await see(t, "#build-text", "Polyvault is ready");
  await see(t, "#q-react", "Polyvault is ready. Three quick questions first.");
  await see(t, "#q-count", "Question 1 of 3");
  await see(t, "#q-text", "Have you written your own Python functions before?");
  await shot(t, "quiz");
  await t.click("#sound");  // voice off, so the walk never waits on a microphone
  await t.click("#q-yes");
  await see(t, "#q-react", "Nice.");
  await see(t, "#q-text", "Have you built a web app with a login form?");
  await t.click("#q-no");
  await see(t, "#q-react", "No problem at all.");
  await see(t, "#q-text", "Have you saved data in a database before?");
  await t.focus("#q-yes");  // the last answer from the keyboard
  await page.keyboard.press("Enter");
  await see(t, "#q-react", "That’s all I need.");
  await t.waitForURL(/\/project/);
}
async function skipquiz() {  // the phone walk skips the questions
  const t = await T();
  await see(t, "#q-text", "Have you written your own Python functions before?");
  await shot(t, "quiz");
  await t.click("#q-skip");
  await t.waitForURL(/\/project/);
}
async function profile() {  // the profile the answers made (after quiz: yes, no, yes)
  const t = await T();
  await t.goto(new URL("interview", t.url()).href);
  await see(t, "#p-level", "You’re intermediate.");
  await see(t, "#p-claims", "Writing Python functions");
  await see(t, "#p-claims", "Saving data in a database");
  await see(t, "#p-gaps", "Web apps with a login");
  await shot(t, "profile");
  await t.click("#home");
  await t.waitForURL(/\/project/);
}
```
Run `walk desktop start choose quiz`; expected: FAIL on `#build-text`.

- [ ] **Step 4: Rewrite `interview.html`**

Head: title `Getting to know you | Carve-Out Tutor`; `style.css`, Phosphor; scripts `chip.js`, `settings.js`, `voice.js`. Top bar: brand and a Settings `navb`.

`#quiz` (`class="screen"`): the prototype's question screen (P:570-585): `#build-pill` with a full ring and `#build-text` = `<project> is ready`; `#q-count` and three `#q-dots`; `lg` Chip `#q-chip`; `#q-react`; `<h1 id="q-text">`; `#q-why` = `So I know where to start you.`; `#q-yes` (`btn primary xl`) and `#q-no` (`btn xl`); `#q-skip` (`link`) = `Skip these questions`; then a row with `#sound` (an icon button, `aria-pressed="true"`, `aria-label="Chip’s voice"`, Phosphor `ph-speaker-high` / `ph-speaker-slash`) and `<p class="status" id="q-status" role="status">`.

`#profile` (`class="screen"`): `<h1 id="p-level">` (`You’re <level>.`), `#p-summary`; `What you said you can do` with the note `These are claims for now. As you work, Chip will sometimes ask you to rebuild one of them, and mark it shown. Remove anything that isn’t right.` and `#p-claims` (skill, the quoted answer in `muted`, a tag `Shown` or `Claimed`, a remove button with `aria-label="Remove"`); `New to you` with `Good candidates for the parts you rebuild first.` and `#p-gaps`; `What you want to get better at` and `#p-wants`; empty lists say `Nothing yet.` Actions: `<a class="btn primary" id="home" href="/project">Back home</a>`, `#more` (`Improve my profile`), `#redo` (`link`, `Start over`).

Script: keep today's logic (`playLine`, `ask`, `listenFor`, `answer`, `aiNext`, `converse`, `showProfile`, the profile edits, restart, more questions, the clip preloading) with these changes:
- The project's name comes from `GET api/project` (`Polyvault` when `builtin`). On load: a finished profile shows `#profile`; otherwise `#quiz` asks `tree.first`, and `#q-react` says `<name> is ready. Three quick questions first.`
- The question text is always shown; the old talk/read switch and the wave go. Chip shows who's talking: `talk` while a clip or `Voice.speak` plays, `think` while the AI works.
- Voice: `sound` starts on, but Chip only speaks or listens after the learner's first click on this page (`unlocked`). Each answer plays its reaction clip (`yes`, `no`) and then the next question's clip, then, if `Voice.canListen`, listens: `#q-status` says `Listening. Say yes or no.` After one miss it plays `again` and says `Sorry, was that a yes or a no?`; after a second, `Click Yes or No.` `#sound` stops any clip, speech and listening when turned off; turned on, it unlocks and replays the current question.
- On screen, reactions are `Nice.`, `No problem at all.` and, after the last answer, `That’s all I need.`, with the `closing` clip, Chip `jump`, then `location.href = "project"` after 1500 ms (300 ms under reduced motion). Questions slide out and in as at P:1264-1277. Chip looks at Yes or No when hovered or focused (P:1311-1316).
- `#q-skip` posts `{answers: []}`, then goes to `project`.
- "Improve my profile" uses the same screen: `#build-pill`, `#q-dots` and `#q-why` hidden, `#q-count` = `Question <number> of <of>`, Chip's feedback in `#q-react`. Errors go in `#q-status`: without a key, `Improving your profile uses the AI. Add your key in Settings, then try again.`, otherwise the error; both with a `Try again` link button.

- [ ] **Step 5: Question and profile styles**

"Questions" section: P:256-269 plus `.build-pill` and the `#sound` row; "Profile" section: the lists as plain rows divided by 1px `--line`, remove buttons as 36px ghost icon buttons. Small screens: `.q-yn .btn.xl { min-width: 120px; }` under 760px.

- [ ] **Step 6: Run the checks**

Run: `checks && walk desktop start choose quiz profile && walk phone start choose skipquiz`
Expected: `ok` for every step. After the phone walk, `curl -s 127.0.0.1:8765/api/profile` shows `"summary": "Skipped the first questions."`.

- [ ] **Step 7: Commit**

```bash
git add tutor tests/ui_walk.cjs
git commit -m "Ask the three questions one at a time after picking a project, with Chip's voice and a way to skip

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Home, one next step

**Files:**
- Rewrite: `tutor/pages/project.html`
- Modify: `tutor/app.py` (`_functions`), `tutor/static/compat.js`, `tutor/static/style.css` ("Home", "Plan editor" and "Notices" sections), `tests/ui_walk.cjs` (steps `home`, `returning`, `upload`, `partial`)

**Interfaces:**
- Consumes: `Chip`, `runProject(statusEl)` (unchanged), `Compat`, `GET /api/plan` (rows now have `description`), `GET /api/state`, `GET /api/profile`, `POST /api/projects/{name}/open`, `GET /api/project`, `POST /api/plan/suggest`, `PUT /api/plan`, `POST /api/next`, `POST /api/open`, `GET /api/download`, `DELETE /api/projects/{name}`.
- Produces: `GET /api/plan` rows gain `"description"`, the card's description (a docstring for functions without a hand-written card, possibly empty).
- Produces: `localStorage["tried:" + info.name]` = `"1"` once the learner has tried the app (`info.name` is the project's folder name, `store` for Polyvault). The workspace's Home button links to `/project`.
- Produces element ids: `#h-project`, `#own` (with `.own-n`, `.own-t`, `.val`), `#home-chip`, `#home-say`, `#notice`, `#next`, `#next-visual`, `#next-step`, `#next-title`, `#next-text`, `#next-note`, `#next-actions` (buttons with `data-act` = `open-try`, `tried`, `write`, `run`, `plan`), `#next-status`, `#journey`, `#plan-note`, `#plan-toggle`, `#plan`, `#steps`, `#edit`, `#plan-summary`, `#suggest`, `#all`, `#plan-status`, `#switches`, `#run`, `#run-status`, `#download`, `#delete-area`, `#delete-ask`, `#delete-confirm`, `#delete-yes`, `#delete-no`.

- [ ] **Step 1: Descriptions in the plan**

Add `"description": f["description"]` to each row built in `_functions()`.
Run:
```bash
TUTOR_DATA=$(mktemp -d) .venv/bin/python -c "
from fastapi.testclient import TestClient
from tutor.app import app
rows = TestClient(app).get('/api/plan').json()['functions']
assert next(f for f in rows if f['name'] == 'hash_password')['description'].startswith('Turn the plain password'), rows[0]
print('ok')"
```
Expected: `ok` (fails with `KeyError: 'description'` before the change).

- [ ] **Step 2: Add the failing walk steps**

```js
async function home() {  // a new learner's home: try the store first, then the first function
  const t = await T();
  await see(t, "#h-project", "Polyvault");
  await see(t, "#own", "0 of 28 yours");
  await see(t, "#plan-note", "I couldn’t make you a plan just now.");  // the walk has no AI key
  await see(t, "#next-step", "Before you start");
  await see(t, "#next-title", "Try the store");
  await see(t, "#home-say", "You’re all set. First, have a play with the store.");
  if ((await t.locator("#journey .jn").count()) !== 8) fail("the journey: questions, try, six starter functions");
  if ((await t.locator("#journey .jn.now").count()) !== 1) fail("one You are here");
  await shot(t, "home-try");
  await t.click('[data-act="tried"]');
  await see(t, "#next-title", "Write hash_password");
  await see(t, "#next-step", "Function 1 of 6");
  await see(t, "#next-text", "Turn the plain password into its SHA-256 hash");
  await see(t, "#home-say", "Now the fun part. Your first function is hash_password.");
  await t.click("#plan-toggle");
  await see(t, "#steps");
  if ((await t.locator("#steps li").count()) !== 8) fail("the whole plan lists 8 steps");
  await shot(t, "home-plan");
  await t.click("#plan-toggle");
}
async function returning() {  // coming back: the start page sends you home, New project still reaches it
  const t = await T();
  await t.goto(new URL("./", t.url()).href);
  await t.waitForURL(/\/project/);
  await see(t, "#next-title", "Write hash_password");
  await t.click("text=New project");
  await see(t, "#c-say", "What do you want to build next?");
  await t.click("#open-store");
  await t.waitForURL(/\/project/);
}
async function upload() {  // your own project with nothing to run, whose function needs the AI to get ready
  const t = await T();
  await t.goto(new URL("./?new", t.url()).href);
  await t.click("#own-open");
  await t.setInputFiles("#zip-in", makeZip("mini", { "shapes.py": AREA }));
  await t.click('.p-mine[data-name="mini"] a.btn');
  await t.waitForURL(/\/project/);
  await see(t, "#h-project", "mini");
  await see(t, "#own", "0 of 1 yours");
  await see(t, "#next-title", "Write area");
  if ((await t.locator("#journey .jn").count()) !== 2) fail("no Try step for a project with nothing to run");
  if (await t.locator("#run").isVisible()) fail("nothing to open for a project with nothing to run");
  await t.click('[data-act="write"]');
  await see(t, "#next-status", "Settings");
  if (await t.locator('[data-act="write"]').isDisabled()) fail("Start writing should work again after the error");
  await shot(t, "home-upload");
  await t.click("#delete-ask");
  await t.click("#delete-yes");
  await t.waitForURL(/\?new/);
  await t.click("#open-store");
  await t.waitForURL(/\/project/);
}
async function partial() {  // your own project where one file needs a library browsers can't run
  const t = await T();
  await t.goto(new URL("./?new", t.url()).href);
  await t.click("#own-open");
  const db = "import psycopg2\n\n\ndef connect():\n    return psycopg2.connect('')\n";
  await t.setInputFiles("#zip-in", makeZip("duo", { "shapes.py": AREA, "db.py": db }));
  await see(t, "#upload-result", "Partly runs here", 60000);  // the check asks PyPI about psycopg2
  await see(t, '.p-mine[data-name="duo"]', "Partly runs in your browser");
  await t.click('.p-mine[data-name="duo"] a.btn');
  await t.waitForURL(/\/project/);
  await see(t, "#notice", "psycopg2");
  await see(t, "#own", "0 of 2 yours");
  await see(t, "#next-title", "Write area");  // connect is left out: its file can't load here
  await shot(t, "home-partial");
  await t.goto(new URL("./?new", t.url()).href);  // back to Polyvault for the steps after this one
  await t.click("#open-store");
  await t.waitForURL(/\/project/);
}
```
Run `walk desktop start choose quiz home`; expected: FAIL on `#h-project`.

- [ ] **Step 3: Rewrite `project.html`**

Head: title `Home | Carve-Out Tutor` (the script sets `<project> | Carve-Out Tutor`); `style.css`, Phosphor; scripts `chip.js`, `settings.js`, `run.js`, `compat.js`.

Top bar (P:604-614): brand linking to `/`; `<span class="crumb">/ <b id="h-project"></b></span>`; on the right the `#own` pill (`title` = `You wrote <ownership>% of the code, by lines.`), `<a class="btn sm" href="./?new">` with Phosphor `ph-plus` and `New project`, `<a class="navb" href="/interview">Profile</a>`, and a Settings `navb`.

Main (`class="home gut screen"`), following P:615-633: the greeting (`md` Chip, `#home-say`, class `say md`); `<div id="notice" class="panel notice" hidden>`; the `#next` card with `#next-status` (`class="status"`, `role="status"`) under `#next-actions`; `#journey`; `#plan-note` (`muted`, hidden); `#plan-toggle` (`See the whole plan` / `Hide the plan`, `aria-expanded`) and the `#plan` panel; then the foot links: `#run` (`Open my app`), `#download` (`Download with my code`), `#delete-area` with `#delete-ask` (`Delete this project`) and its confirm (`Delete <name>? Its files and your progress on it go too.`, `#delete-yes` Delete, `#delete-no` Cancel); and `<p class="status" id="run-status" role="status">`.

Inside `#plan`: `<ol id="steps" class="plan panel">` (styled like the prototype's `.plan`, P:329-339), then `<details id="edit"><summary>Change what you write</summary>` holding `#plan-summary`, `#suggest` (`Let Chip suggest from my profile`), `#all` (`Write everything`), `#plan-status`, and `#switches`: today's per-file switch list.

Loading, in order:
1. With `?open=<name>`: `POST api/projects/<name>/open`, then `history.replaceState(null, "", "project")`; without: `GET api/project`. An error replaces the main content with the error and `<a href="./?new">Back to the start</a>`. The answer is `info`; the project's display name is `Polyvault` when `info.builtin`, otherwise `info.name`, and it fills `#h-project` and the title.
2. `GET api/profile`; no finished profile: `location.replace("interview")`.
3. `GET api/plan` and `GET api/state`. If `plan.profile && !plan.suggested`: `#home-say` says `I’m reading your profile and the code to pick your first functions…`, Chip is `busy`, `#next` is hidden; then `POST api/plan/suggest`. On an error keep the plan, show `#plan-note` = `I couldn’t make you a plan just now. You can ask me again in the whole plan.`, and put the error in `#plan-status`.
4. Uploads only: `#notice` shows the compatibility box and the safety warnings exactly as today's project page builds them, without emoji; delete is offered.

The steps (one model for the journey, the card and the plan list):
```js
// Answer the questions (always done here), try the app if it runs, then the plan's functions in Chip's order.
function steps() {
  const tried = local("tried:" + info.name) === "1" || plan.functions.some((f) => f.status !== "not_started");
  const writing = plan.functions.filter((f) => f.mark === "write" && f.rank !== null && !f.blocked).sort((a, b) => a.rank - b.rank);
  return [
    { key: "quiz", title: "Answer 3 quick questions", text: "So Chip knows where to start.", done: true },
    ...(state.runs ? [{ key: "try", title: info.builtin ? "Try the store" : "Try your app", done: tried,
      text: info.builtin ? "Shop around Polyvault like a customer would. It’s the app you’re going to rebuild."
                    : "Click around your project like you would really use it. It’s the app you’re going to rebuild." }] : []),
    ...writing.map((f, i) => ({ key: f.key, fn: f, n: i + 1, of: writing.length, title: `Write ${f.name}`,
      text: (f.description || "").split("\n")[0] || `A function in ${f.file}.`, done: f.status === "passed" })),
  ];
}
// The step to show: a function you left half-written comes first, then the first step not done.
const current = (list) => list.find((s) => s.fn && `${s.fn.piece}.${s.fn.name}` === `${state.current}.${state.task?.name}` && s.fn.status === "in_progress")
  || list.find((s) => !s.done);
```
(`local(key)` reads `localStorage` inside try/catch.)

The card, by step:
- **try:** `#next-step` = `Before you start`. Visual: for Polyvault the mini store (P:1135-1136) with `/store-assets/chest.webp`, `lantern.webp`, `boombox.webp`; for an upload a mini window titled with the project's name. Actions `Open the store` (or `Open my app`, `data-act="open-try"`, primary) and `Skip for now` (`data-act="tried"`, ghost). `open-try` calls `runProject(#next-status)`, then the card shows `#next-note` (`Polyvault opens in a new tab. Log in as <b>learner</b>, password <b>carve123</b>.`, or for an upload `Your project opens in a new tab.`) and the one action `I’ve tried it` (`data-act="tried"`). `tried` stores the flag and moves on.
- **function:** `#next-step` = `Function <n> of <of>`; visual: a mini code card (P:1366-1367) with the file and `def <name>(…):` and a caret; action `Start writing`, or `Continue writing` when it's in progress (`data-act="write"`). It disables itself, says `Getting it ready…`, and posts `api/next`; an error goes in `#next-status`, and the button comes back; otherwise `location.href = "learn"`.
- **done** (there are functions to write and all have passed): `#next-step` = `Your plan is done`, `#next-title` = `Every function in your plan is yours.`, `#next-text` = `Open your app to see it run on your code, or add more functions to your plan.`, actions `Open my app` (`data-act="run"`, only if it runs) and `Add more functions` (`data-act="plan"`, opens `#plan` and `#edit`).
- **empty plan:** `#next-step` = `Nothing to write yet`, `#next-title` = `Pick what you want to write`, `#next-text` = `Choose a few functions in the plan below. Chip suggests the simplest ones first.`, action `Choose functions` (`data-act="plan"`).
- The card replays its entrance (`.in`, P:289-294) whenever its step changes.

Chip's line (`#home-say`): try `You’re all set. First, have a play with the store.` (an upload: `…with your app.`), after opening it `Take a few minutes in there. Come back when you’re done.`; a function you left half-written `Welcome back. You were writing <name>.`; the first function with nothing passed yet `Now the fun part. Your first function is <name>.`; a function right after one you passed `<previous> is yours. Next up is <name>.`; any other function `Next up is <name>.`; done `That’s your whole plan, written by you.`; empty `Your plan is empty right now.`

The journey (P:1396-1400) shows at most 9 steps:
```js
// A window of at most 9 steps around "You are here", so a long plan still fits on a phone.
// i is the current step's index, or the last step's once the plan is done.
const from = Math.max(0, Math.min(i - 2, list.length - 9)), shown = list.slice(from, from + 9);
```
When the window leaves steps out, `#journey` starts with `<span class="jmore">+<from></span>` and ends with `<span class="jmore">+<steps left after it></span>` (13px, `--muted`). Node tooltips are the step titles. `#journey` stays `aria-hidden`; `#steps` is the readable version.

`#steps` lists every step (done, now, next, P:1401-1404). Function rows are buttons that open that function: `POST api/open {key}`, then `learn`, with errors in `#plan-status`; this replaces the workspace's old picker.

The plan editor (`#edit`): today's `showPlan` switches, `#suggest`, `#all` and their handlers, in the new look (`I’ll write it`, `Keep`, `Local only`, `✓`, the reason in `muted`, a spot check as `tag` `Spot check: <claim>`). Every plan change re-renders the card, the journey, `#steps` and the pill.

The pill: `.own-n` = functions with status `passed`, `.own-t` = all functions, the ring at that share (`stroke-dashoffset = 44 - 44 * part`).

Foot: `#run` (hidden unless `state.runs`) calls `runProject(#run-status)`; `#download` keeps today's blob download; delete keeps today's confirm, then goes to `./?new`.

- [ ] **Step 4: `compat.js` without emoji**

`STATUS` becomes `{ "built in": ["good", "built in"], installable: ["good", "installs here"], "can't run in a browser": ["bad", "can’t run in a browser"], unknown: ["warn", "couldn’t check"] }`, and `libraries()` renders `<li><code>name</code> <span class="tag <kind>">label</span></li>`. `verdict()` is unchanged.

- [ ] **Step 5: Home styles**

"Home" section: P:279-340, plus `.jmore`; "Plan editor": today's switches restyled as `pill`s, `.on` for "I'll write it"; "Notices": `.notice` as a `panel` with 18px padding and 15px text. Small screens: P:436-439 for `.next`.

- [ ] **Step 6: Run the checks**

Run: `checks && walk desktop start choose quiz home returning upload partial && walk phone start choose skipquiz home`
Expected: `ok` for every step. Look at `$SHOTS/phone-home-try.png`: one column, the journey fits.

- [ ] **Step 7: Commit**

```bash
git add tutor tests/ui_walk.cjs
git commit -m "Home shows one next step, the journey around it, and the whole plan only when asked

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: The workspace

**Files:**
- Rewrite: `tutor/pages/learn.html`, `tutor/static/learn.js`
- Modify: `tutor/llm.py` (`NO_KEY`), `tutor/overview.py` (`YOURS`), `tutor/static/style.css` ("Workspace", "Editor", "Results", "Task details" sections), `tests/ui_walk.cjs` (steps `workspace`, `pass`, `passed`)

**Interfaces:**
- Consumes: `Chip`, `Voice`, `runProject`, `GET /api/state`, `GET /api/plan`, `PUT /api/code`, `POST /api/submit`, `/api/hint`, `/api/ask`, `/api/clean`, `/api/next`, `GET /api/overview`.
- Produces in `learn.js`, for Task 7: `buddy(content, { html = false, asked = "" })` shows Chip's latest words in the buddy panel: plain text through `Chip.say`, HTML set at once with a fade, and the learner's question above it as `You asked: <question>` when `asked` is given; `setOwn(n, total, bump)`; `onPass(res)`, called after a passing check that isn't a Clean retry; the state `project`, `fnName`, `passedCount`, `totalCount`, `check`, `allDone`, `runs`.
- Produces element ids: `#w-back`, `#w-crumb`, `#w-own`, `#run`, `#run-status`, `#w-main`, `#w-task`, `#w-step`, `#w-name`, `#w-sig`, `#w-desc`, `#w-checks`, `#w-used`, `#w-breaks`, `#w-refs`, `#files-details`, `#file-tree`, `#map-details`, `#map-view`, `#map-expand`, `#map-caption`, `#diagram`, `#map-dialog`, `#map-close`, `#diagram-big`, `#w-editor`, `#w-file`, `#code-font`, `#editor-size`, `#editor`, `#results`, `#submit`, `#hint`, `#clean`, `#next`, `#save-state`, `#w-buddy`, `#w-chip`, `#w-asked`, `#w-say`, `#ask-form`, `#chat-input`, `#ask`, `#tutor-mic`, `#speak-toggle`.

- [ ] **Step 1: Add the failing walk steps**

```js
const WRONG = "def hash_password(password: str) -> str:\n    return password\n";
const RIGHT = 'import hashlib\n\n\ndef hash_password(password: str) -> str:\n    """Return the SHA-256 hex digest of the password."""\n    return hashlib.sha256(password.encode()).hexdigest()\n';
const type = (t, code) => t.evaluate((c) => document.querySelector(".CodeMirror").CodeMirror.setValue(c), code);
// Without a key, the local tutor tells you to add one in Settings; on the site the demo AI is blocked, so Chip is busy.
const NO_AI = SITE ? "busy" : "Settings";
async function workspace() {  // hash_password, first a wrong try
  const t = await T();
  if (!/\/learn/.test(t.url())) { await t.click('[data-act="write"]'); await t.waitForURL(/\/learn/); }
  await see(t, "#w-crumb", "Polyvault / hash_password");
  await see(t, "#w-step", "Function 1 of 6");
  if ((await t.locator("#w-checks li").count()) !== 2) fail("hash_password has two checks");
  await shot(t, "workspace");
  await type(t, WRONG);
  await t.click("#submit");
  await see(t, '#w-checks li[data-state="fail"]');
  await see(t, "#results", "Not quite yet");
  await see(t, "#w-say", NO_AI);  // the hint after a failed check needs the AI
  await t.locator("#submit:not([disabled])").waitFor();
}
async function pass() {  // then the right code
  const t = await T();
  await type(t, RIGHT);
  await t.click("#submit");
  await see(t, '#w-checks li[data-state="pass"]');
  if ((await t.locator('#w-checks li[data-state="pass"]').count()) !== 2) fail("both checks should pass");
  await see(t, "#w-editor.ok");
  await see(t, "#w-own", "1 of 28 yours");
}
async function passed() {  // back on a function you passed: it's yours, the next one is a click away, Chip still helps
  const t = await T();
  await t.goto(t.url());
  await see(t, "#w-say", "hash_password is yours.");
  await see(t, "#save-state", "This function is yours now.");
  await see(t, "#next", "Next function");
  await t.fill("#chat-input", "What does encode do?");
  await t.click("#ask");
  await see(t, "#w-asked", "You asked: What does encode do?");
  await see(t, "#w-say", NO_AI);
  await t.click("#clean");
  await t.locator("#w-asked").waitFor({ state: "hidden" });  // Clean's reply replaced the answer
  await see(t, "#w-say", NO_AI);
  await t.locator("#clean:not([disabled])").waitFor();
}
```
Run `walk desktop start choose quiz home workspace`; expected: FAIL on `#w-crumb`.

- [ ] **Step 2: Wording on the server**

`llm.NO_KEY` = `"Add your AI key in Settings, at the top right. Groq gives free keys at console.groq.com."` `overview.YOURS` = `"rgba(61, 127, 119, 0.18)"` (the accent, see-through).
Run: `.venv/bin/python -m tutor.overview && checks`
Expected: its self-check passes and pytest passes.

- [ ] **Step 3: Rewrite `learn.html`**

Head: title `Workspace | Carve-Out Tutor`; CodeMirror's CSS, Phosphor, `style.css`; at the end of body CodeMirror and its Python mode, mermaid (deferred), `chip.js`, `settings.js`, `voice.js`, `run.js`, `learn.js`. No `theme.js`, no confetti.

Top bar (P:638-645): `<a class="btn ghost sm" id="w-back" href="/project">` with `ph-arrow-left` and `Home`; `#w-crumb`; on the right `#w-own` (the pill), `#run` (`btn sm`, `Open my app`) and a Settings `navb`. Under the bar, full width: `<p class="status gut" id="run-status" role="status">`.

`<main class="work gut screen" id="w-main">` with three cards (P:646-668):
- `#w-task` (`card panel raised`): `#w-step`, `<h1 id="w-name">`, `#w-sig`, `#w-desc`, `<h2 class="w-h">It passes when</h2>`, `#w-checks`; then closed `<details>`: `Where this code is used` (`#w-used`), `If it’s wrong` (`#w-breaks`), `Code to read` (`#w-refs`: one nested `details` per reference, its code in a `pre`), `Files in the project` (`#files-details`, `#file-tree`), `How data flows` (`#map-details`: `#map-view`, `#map-expand`, `#map-caption`, `#diagram`).
- `#w-editor` (`card panel raised`): a head with `#w-file`, `<span class="muted">Only this function. Imports go right above it.</span>`, then on the right `#code-font` (options `mono` `Classic mono`, `hand` `Handwritten`, `legible` `Extra readable`) and `#editor-size` (`ph-arrows-out`, `title="Make the editor taller"`); the body with `<textarea id="editor">`; `<div class="results" id="results" hidden>`; a foot with `#submit` (`btn primary`, `ph-check` and `Check my code`), `#hint` (`btn`, `Get a hint`), `#clean` (`btn`, `Clean`, hidden), `#next` (`btn primary`, `Next function` with `ph-arrow-right go`, hidden) and `#save-state` (`saved`).
- `#w-buddy` (`card panel raised`): `md` Chip `#w-chip`, then `<p class="muted small" id="w-asked" hidden>`, `<div class="say sm" id="w-say" aria-live="polite">`, and `#ask-form`: `#chat-input` (`placeholder="Ask me anything"`), `#ask` (`btn sm`, `Ask`), `#tutor-mic` (icon button, `ph-microphone`, hidden without `Voice.canListen`), `#speak-toggle` (icon button, `aria-pressed`, `ph-speaker-slash` / `ph-speaker-high`, `title="Read Chip’s replies out loud"`).

Then `<dialog class="sheet map-dialog" id="map-dialog">` (wider: `width: min(1100px, calc(100% - 32px))`) with `#map-close` and `#diagram-big`, as today.

- [ ] **Step 4: Rewrite `learn.js`**

Keep from today's file: `$`, `api`, `escapeHtml`, `PASTE_ALLOWED`, the CodeMirror setup with paste and drop blocking, `bigEditor` (toggling `editor-full` on `#w-main`), `formatReply`, the speak toggle and `say`, the mic (fills `#chat-input`, then asks), `loadOverview` (now run the first time `#files-details` or `#map-details` opens), `drawDiagram`, autosave, `#clean`, `#next`, `#run`. Drop: the floating window and its dragging, the tutor modes, the function picker, `celebrate`, the `themechange` listener.

Changes:
- First line: set `document.documentElement.dataset.codeFont` from `localStorage.codeFont`, default `mono`, before the editor is made; the select saves the choice as today.
- `drawDiagram` theme: `fontFamily: v("--text")`, `background: v("--surface")`, `primaryColor: v("--bg")`, `primaryTextColor: v("--ink")`, `primaryBorderColor: v("--muted")`, `lineColor: v("--muted")`, `edgeLabelBackground: v("--surface")`, `tertiaryColor: v("--surface")`. In `CAPTIONS.flow`, "the yellow column" and "the yellow band" become "the shaded column" and "the shaded band".
- Load: `GET api/state` (none open: `location.href = "project"`) and `GET api/plan` for the pill: `passedCount` = passed rows, `totalCount` = all rows, title = `You wrote <ownership>% of the code, by lines.` `#w-crumb` = `<project> / <b class="mono"><name></b>`, `#w-step` = `Function <step> of <total_steps>`, `#w-file` = the task's file, `#run` hidden unless `state.runs`. Checks render as `<li data-test="<test>" data-state="idle"><span class="ck" aria-hidden="true"></span><span>text</span></li>`. The buddy opens with `Your turn. Write <name> in the editor. I’ll be right here.`
- **Check my code:** every check goes to `data-state="run"`, Chip `busy`, the buddy says `Running the tests on your code…`, `#submit` and `#hint` are disabled. When `api/submit` answers, each check gets `pass` or `fail` from the results by test name, in order, 300 ms apart (0 under reduced motion). After the last one: an error answer shows in `#results` and the buttons come back; a pass calls `onPass(res)` (or, in a Clean retry, keeps today's Clean behavior and says `Cleaner, and still yours.`); a fail shakes `#w-editor` (`.bad` for 800 ms), says `Not yet. Here’s what to look at.`, shows `#results` (today's `showResults`, with `Not quite yet. Here’s what to look at:` and the failing tests' messages), brings the buttons back, and asks for the after-check hint (`getHint(true)`).
- **`onPass(res)`** (Task 7 adds the flight and the win sheet to it): `#w-editor` gets `.ok`, Chip `happy` and `jump`, the buddy says `It works. <name> now runs inside <project>.`, `#save-state` = `Saved. This version runs in your app now.`, `passedCount += 1` and `setOwn(passedCount, totalCount, true)`, then `afterPass()`.
- **`afterPass()`:** the editor is read-only, `#submit` and `#hint` disabled, `#clean` shown, `#next` shown unless `allDone`. With `allDone`, `#results` adds `That’s every function in your plan. Open your app to see <project> running on your code, or add more functions from home.`
- **Opening a passed function** (status `passed`): `afterPass()`, the buddy says `<name> is yours.`, `#save-state` = `This function is yours now.`
- **Hints, questions, Clean:** `getHint` and `#ask` put Chip in `think` until the reply, then `buddy(formatReply(reply), { html: true, asked })`; the buttons always come back. Clean's points and code show in the buddy; `#submit` reads `Check the cleaner version` while cleaning; `#save-state` says `Try a cleaner version`, and `Check to keep this version` after an edit.
- Paste blocked: `#save-state` = `No pasting here. Type it out.`

- [ ] **Step 5: Workspace styles**

"Workspace": P:342-379 (`.work`, `.task`, `.checks`, `.ck` states, `.editor`, `.ed-head`, `.ed-foot`, `.buddy`, `.ask`), leaving out the prototype's stand-in editor (`.ed-body`'s grid, `.gutter`, `#w-code`), which CodeMirror replaces; plus `.work.editor-full { grid-template-columns: minmax(0, 1fr); grid-template-areas: "editor" "buddy"; }` with the task card hidden, and P:431-434 for small screens. "Editor": `.CodeMirror` fills `.ed-body` on `#FAFBFA` with `font: 400 14px/24px var(--code-font)`; `--code-font` is `var(--mono)` by default, `"Shantell Sans", "Comic Sans MS", cursive` with `font-variation-settings: "INFM" 100, "BNCE" 25` and 15px for `hand`, `"Atkinson Hyperlegible Mono", ui-monospace, monospace` for `legible`; gutters `#FAFBFA` with a 1px `--line` border, line numbers `rgba(91, 103, 112, .7)` in Geist Mono 13px; the cursor 2px `--accent`; selection `--accent-soft`; tokens: keyword `--kw`, def `--fn`, string `--str`, number, builtin and meta `--ty`, comment `--muted` italic, everything else `--ink`, matching bracket `--good-ink`. "Results": 14px 18px padding above the foot, a 1px `--line` top border, a pass summary in `--good-ink` and a fail summary in `--bad-ink`, messages in `pre` on `--bg` (12.5px mono, `white-space: pre-wrap`). "Task details": `details` rows as at P:362-364, `pre` scrolls sideways inside its card, the file tree in 14px mono, the diagram scrolls inside its box, and the map dialog as a sheet.

- [ ] **Step 6: Run the checks**

Run: `checks && walk desktop start choose quiz home workspace pass passed && walk phone start choose skipquiz home workspace pass passed`
Expected: `ok` for every step. In `$SHOTS/phone-workspace.png` the cards stack: task, editor, Chip.

- [ ] **Step 7: Commit**

```bash
git add tutor tests/ui_walk.cjs
git commit -m "Write each function in a calm workspace with Chip docked beside the editor and the checks ticking one by one

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: The guided workspace: tour, reactions, the win

**Files:**
- Modify: `tutor/pages/learn.html` (the tour and win markup), `tutor/static/learn.js`, `tutor/static/style.css` ("Tour, win sheet, flyer" section), `tests/ui_walk.cjs` (steps `tour`, `win`)

**Interfaces:**
- Consumes from Task 6: `buddy`, `setOwn`, `onPass`, the state variables, the element ids. `POST /api/explain` returns `{error}` or `{score, done, hint?, feedback?, final_explanation?, extra?}`.
- Produces: `localStorage.seenTour` = `"1"` after the first tour. Element ids: `#shield`, `#coach`, `#coach-chip`, `#coach-count`, `#coach-say`, `#coach-skip`, `#coach-next`; `#win`, `#win-chip`, `#win-title`, `#win-sub`, `#win-note`, `#win-qa`, `#win-label`, `#win-q`, `#win-answer`, `#win-mic`, `#win-send`, `#win-skip`, `#win-reply`, `#win-after`, `#win-next`, `#win-home`, `#win-run`; `#answer-it` in the buddy.

- [ ] **Step 1: Add the failing walk steps**

```js
const TOUR = [
  "Start here. This is what your function has to do, and the checks it has to pass.",
  "Then write your code in here. Just this one function.",
  "When you think it works, press Check my code. I’ll run the tests for you.",
  "Stuck? I’m right here. Ask me anything, or ask for a hint.",
];
async function tour() {  // the first visit to the workspace: a four-stop tour, once
  const t = await T();
  await t.click('[data-act="write"]');
  await t.waitForURL(/\/learn/);
  await see(t, "#coach-say", TOUR[0]);
  await shot(t, "tour");
  if (size === "phone") {
    await page.keyboard.press("Escape");  // Esc ends it, like Skip the tour
  } else {
    for (let i = 0; i < 4; i++) {
      await see(t, "#coach-count", `${i + 1} of 4`);
      await see(t, "#coach-say", TOUR[i]);
      await see(t, ["#w-task", "#w-editor", "#submit", "#w-buddy"][i] + ".spot");
      await t.click("#coach-next");  // the last one says Got it
    }
  }
  await t.locator("#coach").waitFor({ state: "hidden" });
  await see(t, "#w-say", "Your turn. Take your time, I’m right here.");
  await type(t, "def hash_password(password: str) -> str:\n    h");
  await see(t, "#w-say", "Nice start. Take your time.");
  await t.goto(t.url());
  await page.waitForTimeout(1500);
  if (await t.locator("#coach").isVisible()) fail("the tour shows only once");
}
async function win() {  // the right code: the function flies into the counter, then one question
  const t = await T();
  await type(t, RIGHT);
  await t.click("#submit");
  if (!process.env.REDUCED) await see(t, ".flyer");
  await see(t, "#w-own", "1 of 28 yours");
  await see(t, "#win-title", "hash_password is yours.");
  await see(t, "#win-sub", "1 of 28 functions in Polyvault run your code now.");
  await see(t, "#win-q", "Why does the store keep a hash of the password instead of the password itself?");
  await shot(t, "win");
  await t.fill("#win-answer", "So nobody can read the real password.");
  await t.click("#win-send");
  await see(t, "#win-reply", NO_AI);  // grading needs the AI
  await t.locator("#win-send:not([disabled])").waitFor();
  await t.click("#win-skip");
  await see(t, "#win-next", "Next: is_logged_in");  // the starter plan's order: is_logged_in comes second
  await t.click("#win-next");
  await see(t, "#w-crumb", "is_logged_in");
}
```
Run `walk desktop start choose quiz home tour workspace win`; expected: FAIL on `#coach-say`.

- [ ] **Step 2: The tour**

Markup after `main`: `#shield` and the `#coach` card (P:671-676: `sm` Chip, `#coach-count`, `#coach-say` as `say sm`, `#coach-skip` `Skip the tour`, `#coach-next` `Next`). Script: port P:1595-1648 with the four stops `#w-task`, `#w-editor`, `#submit`, `#w-buddy` and the `TOUR` lines above; the count reads `<n> of 4`; the last button says `Got it`; focus moves to `#coach-next` at each stop, so Enter goes on; Esc ends it like Skip; it starts 950 ms after the first load when `localStorage.seenTour` isn't set, and sets it. Ending: `Your turn. Take your time, I’m right here.`, focus in the editor.

- [ ] **Step 3: Chip reacts to typing**

On editor changes while the function isn't passed: Chip looks at `#w-editor`, then back at the pointer after 1.6 s. The first change says `Nice start. Take your time.` The first time the code has a `return` and no `NotImplementedError`: `Looks close. Press Check my code when you’re ready.` After 25 s without typing while the code still has `NotImplementedError`: `Stuck? Press Get a hint and I’ll nudge you.` Each line once per visit.

- [ ] **Step 4: The flight and the win sheet**

`onPass(res)` gains, after Task 6's steps: the `.flyer` (P:1538-1555) from the editor to `#w-own`, with `setOwn` after it lands (no flight under reduced motion), then, 380 ms later, the win sheet.

Markup (P:678-692, as a dialog): `<dialog class="sheet win" id="win" aria-labelledby="win-title">`, opened with `showModal()`, which keeps focus inside it; in it `#win-chip` (`md happy`), `<h2 id="win-title">`, `#win-sub`, `<p id="win-note" hidden>`; the `#win-qa` form with `#win-label` (`One question before you move on.`), `<strong id="win-q">`, `#win-answer` (`placeholder="Answer in your own words"`), `#win-send` (`Send`, primary), `#win-mic` (icon button, only with `Voice.canListen`), `#win-skip` (`Skip`, ghost), and `<div id="win-reply" aria-live="polite">`; then `#win-after` with `#win-next` (primary), `#win-run` (`Open my app`, hidden) and `#win-home` (`Back home`, ghost).

Behavior:
- Title `<name> is yours.` Sub `<passedCount> of <totalCount> functions in <project> run your code now.`, plus ` That’s every function in your plan.` with `allDone`. With `res.shown_claim`, `#win-note` = `Spot check passed: you’ve shown “<claim>”. It’s marked in your profile.`
- No question (`check.question` empty) or already answered: straight to `#win-after`.
- Send: disabled while waiting, `#win-reply` says `Checking your answer…`, then `POST api/explain {explanation}`. An error shows in `#win-reply`, and Send comes back. A reply shows `<strong><score>/10.</strong>` and the formatted `hint` or `feedback`, then `Here’s the full answer: <final_explanation>` and `Good to know: <extra>` when given. Not `done`: the answer box empties, `#win-label` says `Try once more, in your own words.`, Send comes back. `done`: `check.done = true`, the form hides, `#win-after` shows.
- Skip: hide the form, show `#win-after`; the question stays open.
- `#win-next` = `Next: <name>`, where name is the plan's first function to write that hasn't passed, in Chip's order and skipping blocked ones (the one `api/next` opens). It's hidden with `allDone`, and then `#win-run` shows if `runs`. It posts `api/next`, then reloads. `#win-home` goes to `project`. Esc closes the sheet (the dialog's `cancel`); a question left unanswered then waits in the buddy.
- On opening, focus goes to `#win-answer` (or `#win-next`); the motion is the shared `dialog.sheet[open]` animation from Task 3.
- Back on a passed function whose question is still open: the buddy says `<name> is yours. One question about it is waiting.` and shows `#answer-it` (`btn sm`, `Answer it`), which opens the sheet at the question.

- [ ] **Step 5: Styles**

"Tour, win sheet, flyer": P:380 (`.spot`) and P:382-402, keeping `.shield`, `.coach-card`, `.win-top`, `.qa` and `.flyer`, and leaving out `.win`'s overlay and `.sheet` (the win sheet is a `dialog.sheet` from Task 3) and the toast.

- [ ] **Step 6: Run the checks**

Run: `checks && walk desktop start choose quiz home tour workspace win && walk desktop start choose quiz home tour workspace pass passed && walk phone start choose skipquiz home tour workspace win && REDUCED=1 walk desktop start choose quiz home tour workspace win`
Expected: `ok` for every step in all four walks. Then try the keyboard alone on the workspace: Tab reaches every button with a visible ring, and Esc ends the tour and closes the sheet.

- [ ] **Step 7: Commit**

```bash
git add tutor tests/ui_walk.cjs
git commit -m "Guide the first workspace visit, react to the learner's typing, and celebrate a pass with one question

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Finish: remove the old look, update the README, walk the published site

**Files:**
- Delete: `tutor/static/old.css`, `tutor/static/theme.js`
- Modify: `tutor/static/settings.js` (drop the gear fallback), `README.md`, `web/files.json`, `tests/ui_walk.cjs` (step `store`)

**Interfaces:**
- Consumes: everything above.
- Produces: the finished branch.

- [ ] **Step 1: Add the last walk step**

```js
async function store() {  // Open my app: Polyvault starts in its own tab
  const t = await T();
  await t.goto(new URL("project", t.url()).href);
  const [tab] = await Promise.all([page.context().waitForEvent("page"), t.click("#run")]);
  for (let i = 0; i < 100 && !(await tab.title()).includes("Polyvault"); i++) await page.waitForTimeout(300);
  if (!(await tab.title()).includes("Polyvault")) fail("the store didn't open");
  await tab.close();
}
```
Add it to `STEPS`.

- [ ] **Step 2: Remove what's left of the old look**

`git rm tutor/static/old.css tutor/static/theme.js`; remove the gear and profile-icon fallback from `settings.js` and its comment about adding a gear. Then:
Run: `grep -rn "old.css\|theme.js\|data-theme\|theme-switch\|ph-scissors\|confetti" tutor web`
Expected: no output.

- [ ] **Step 3: The README**

Rewrite "Demo walkthrough" for the new flow, in the README's voice, with no em dashes:
1. **The story.** On the first visit Chip tells what Carve-Out does in seven short steps, while Python loads in the background. Skip it any time.
2. **What do you want to build?** Building from your own idea is coming soon; for now open **Polyvault**, or bring your own project as a .zip.
3. **Three questions.** Yes or no, in Chip's voice, so the plan starts at the right level. You can skip them.
4. **Home** shows one next step: try the store first (login `learner` / `carve123`), then your first function. **See the whole plan** lists every step and lets you choose what you write.
5. **The workspace.** A short tour the first time. The task card says what the function must do; write it in the editor, **Get a hint** for a nudge, ask Chip anything. **Check my code** ticks each check.
6. **A pass.** Your function flies into the "yours" counter and runs inside the store from now on. Chip asks one question about it, then it's on to the next function.

In "Run it locally with a server", the "Start over" line becomes: `**Start over** (fresh demo): stop the server and delete the data/ folder. To see the story again, open http://localhost:8000/?intro.` In "How it works", mention `tests/ui_walk.cjs`: a walk through every screen in a real browser.

- [ ] **Step 4: The full checks, local and published**

Run:
```bash
.venv/bin/python web/files.py && checks \
  && walk desktop start choose quiz profile home returning upload partial tour workspace win \
  && walk desktop start choose quiz home tour workspace pass passed \
  && walk phone start choose skipquiz home tour workspace win \
  && REDUCED=1 walk desktop start choose quiz home tour workspace win \
  && site desktop story choose quiz home tour workspace win store boot \
  && site phone story choose skipquiz home tour workspace win
```
Expected: `ok` for every step. The `site` walks are the only proof that every path and file works on the published build (Review Focus 1).

- [ ] **Step 5: Look through every screenshot**

Open each file in `$SHOTS` next to the prototype. Check: the calm palette and no gradients, one primary button per screen, nothing cut off at phone width, Chip looks the same everywhere.

- [ ] **Step 6: Commit**

```bash
git add -A tutor web README.md tests/ui_walk.cjs
git commit -m "Retire the notebook look and themes, and describe the new flow in the README

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
