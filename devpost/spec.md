---
doc: spec
status: approved
---

# Carve-Out Tutor (working title) — Technical Spec

## How This Works, In Plain Language

There are **two Python programs** running on your laptop, both built with **FastAPI** (a library that takes a browser request like "show me the cart" and runs the Python function that answers it).

1. **The tutor app** (`localhost:8000`). This is what the learner uses: the catalog, the project page and the learning workspace with the code editor, Hint, Submit and Run project buttons, and the ownership percentage. The pages are plain HTML with a bit of JavaScript, and the editor is CodeMirror, a ready-made code editor that runs in the browser.
2. **The 3D asset store** (`localhost:8001`). This is the practice project: log in, browse pictures of assets, a cart, a fake checkout, download links and a profile. The tutor starts it as a second server whenever the learner clicks **Run project**.

**The trick that makes carving work:** each piece the learner rebuilds is **its own file** in the store. Authentication is `store/pieces/auth.py` and cart behavior is `store/pieces/cart.py`. The rest of the store just calls the functions in those files without caring who wrote them. To carve a piece, the editor shows a **stub**: the same function names, inputs and return types, with empty bodies. The AI's original file is never touched.

**When the learner clicks Submit**, the tutor saves their code and runs **pytest** (Python's standard test tool) on it in a separate process with a time limit, then shows which tests passed. If all pass, their file becomes the official version of that piece.

**When the learner clicks Run project**, the tutor builds a fresh copy of the store. For each piece it uses the learner's file if it has passed, otherwise the AI's original. Then it restarts the store server and opens it in a new tab. That's why the store never breaks while someone is mid-round.

**The AI part** (hints, grading explanations, answering questions) is a call to **Groq's API** using the free `gpt-oss-120b` model. The tutor sends a message and gets text back. The tutor code uses the `openai` Python library because Groq accepts the same request format. Switching to Gemini later only changes two settings: the address and the key.

**Progress** (which round you're on, your unfinished code, which pieces passed) is saved in a small file, `data/progress.json`. Close the app, come back, and everything is where you left it.

**Why this shape:** It uses one language and runs on one laptop. There's only one outside service (Groq), there are no accounts, and nothing has to be deployed. Everything is aimed at proving the carve loop.

## The Core Journey Through the System
PRD ref: `prd.md > The Core Journey`.

1. **Opening.** The learner opens `localhost:8000`. The tutor serves `catalog.html`, which shows the 3D asset store card and a greyed-out "Bring your own idea — coming soon" card.
2. **Project page.** Clicking the card loads `project.html`: a description, **Run project** and **Start learning**.
3. **Run it first.** **Run project** → the browser calls `POST /api/run` → `runner.py` copies `store/` into `.run/store/`. No pieces have passed yet, so the originals stay. It stops any old store process, starts `uvicorn` on port 8001 and waits until the server answers → the browser opens `localhost:8001` in a new tab. The learner logs in, browses, adds items to the cart and checks out.
4. **Start round 1.** **Start learning** → `POST /api/round/start` → `progress.json` now says "round 1, piece `auth`" → the browser goes to `learn.html`.
5. **Task workspace.** `learn.html` calls `GET /api/state`. The tutor returns the task for `auth`: inputs and outputs, call sites, what breaks, and the reference code pulled live from the store files. It also returns the learner's saved draft, or the stub if there isn't one. The editor shows it.
6. **Work.** As the learner types, the browser autosaves with `PUT /api/code` (a couple of seconds after they stop typing). **Hint** → `POST /api/hint` with their code → `llm.py` asks Groq for a nudge with no solution code → the nudge appears in the tutor area.
7. **Submit.** `POST /api/submit` → `runner.py` copies their code into a temp folder as `auth.py` and runs `pytest tests/test_auth.py` there, with a 15-second limit.
   - **Fails:** The browser shows each test as ✓ or ✗ with its message. `llm.py` gets the failing tests (names and messages) plus the learner's code, and returns a hint aimed at the most important failure.
   - **Passes:** The code is saved to `data/learner/auth.py`, the piece is marked `passed` in `progress.json`, and the ownership % is recalculated and shown going up.
8. **Explain it.** The tutor area switches to the understanding check. The learner writes an explanation → `POST /api/explain` → Groq returns a score from 0 to 10, what was missing, and extra information. A low score gets a targeted hint and a retry, up to two times, and then the tutor gives the full explanation. The learner can also use **Ask** (`POST /api/ask`) for questions.
9. **See it working.** **Run project** again → this time `runner.py` puts `data/learner/auth.py` into `.run/store/pieces/auth.py` before starting the store. Logging in now runs the learner's code.
10. **Round 2.** **Next piece** → `POST /api/round/start` → piece `cart`. `auth` stays the learner's file forever. Steps 5–9 repeat, and the % rises again.

## Stack

| Piece | Choice | Why |
|---|---|---|
| Language | **Python 3.11+** | Your choice: one language for both programs. |
| Web framework | **FastAPI** ([docs](https://fastapi.tiangolo.com/)) + **Uvicorn** server ([docs](https://www.uvicorn.org/)) | Your choice: modern and popular. Store routes use plain `def` (not `async def`) so the code learners read stays simple. |
| Store pages | **Jinja2** templates ([FastAPI templates docs](https://fastapi.tiangolo.com/advanced/templates/)) | FastAPI is aimed at JSON, so HTML pages need a template engine. Jinja2 is the standard one. |
| Store login session | Starlette **SessionMiddleware** ([docs](https://www.starlette.io/middleware/#sessionmiddleware)), which needs `itsdangerous` | A signed cookie that remembers who's logged in and what's in the cart. |
| Form posts | `python-multipart` | FastAPI needs this to read HTML form submissions (login, add to cart). |
| Store database | **SQLite** through Python's built-in `sqlite3` ([docs](https://docs.python.org/3/library/sqlite3.html)) | A spreadsheet-like file the store reads and writes. No setup needed. |
| Tests | **pytest** ([docs](https://docs.pytest.org/)), with results read from its `--junitxml` report | The standard Python test tool. Its XML report gives per-test pass/fail with no extra plugin. |
| AI | **Groq** `openai/gpt-oss-120b` through the **`openai`** library ([Groq OpenAI-compat docs](https://console.groq.com/docs/openai)). Backup: **Gemini** through Google's OpenAI-compatible endpoint ([docs](https://ai.google.dev/gemini-api/docs/openai)) | Your choice: free API keys. The tradeoffs you accepted are rate limits, possible use of your data for training, and less reliable "no answer" behavior than top paid models. |
| Tutor front end | Plain HTML + JavaScript (`fetch` for API calls), no build step | Your choice: Python is the main code and the browser parts stay small. |
| Code editor | **CodeMirror 5** (`5.65.16`) from cdnjs ([docs](https://codemirror.net/5/)) | A real code editor (line numbers, Python highlighting, Tab key) from a single script tag with no build tooling. If the CDN fails to load, it falls back to a plain `<textarea>`. |

**To check on the first build step:** Groq's current free-tier rate limits and the exact model ID. Free-tier details change, and I haven't looked them up during this conversation.

## Where It Runs and How Someone Tries It

- **Runs:** locally on your laptop (WSL is fine). Two servers: the tutor on `localhost:8000` and the store on `localhost:8001`, which the tutor starts and stops itself.
- **Needs:** Python 3.11+ and a free Groq API key from [console.groq.com](https://console.groq.com).
- **Start:**
  ```bash
  python -m venv .venv && source .venv/bin/activate
  pip install -r requirements.txt
  export GROQ_API_KEY=your_key_here
  uvicorn tutor.app:app --port 8000
  ```
  Then open **http://localhost:8000**. On first start, the tutor creates the store database (`data/store.db`) with the one user and the assets.
- **Store login for the demo:** username `learner`, password `carve123` (shown on the project page).
- **Switching to Gemini:** set `LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/`, `LLM_MODEL=gemini-2.5-flash` and `LLM_API_KEY=<AI Studio key>`. The defaults point to Groq.
- **Starting over for a fresh demo recording:** delete the `data/` folder.
- **Submission:** a short demo video recorded locally, plus a public GitHub repo. No deployment. It's optional, and we can revisit it in `6-ship`.

## Look and Feel
Carried from `prd.md > Look and Feel` and `scope.md > Inspiration & Identity`.

- **Tutor app:** calm and learning-focused, like GeeksforGeeks. Light warm-neutral background, white panels, one accent color (a warm orange) for primary buttons and the ownership bar, and a green for passed tests. System sans-serif font for the interface and monospace in the editor. Generous spacing and only one main idea per screen. Small, quiet transitions (button hover, the % bar filling) and nothing flashy.
- **Workspace:** a two-column layout like Programiz. On the **left** are the task (inputs/outputs, call sites, what breaks), collapsible reference snippets and the tutor area (hints, feedback, explanation chat). On the **right** are the editor on top and test results/output below. A top bar shows the round, the piece name and the **ownership %** as a bar with a number, always visible. On narrow screens the columns stack.
- **Store:** like Sketchfab, a clean, image-led showcase. A grid of large picture cards with the asset name, type (model / animation / world) and price, plus a simple header with Cart, Profile and Log in/out. Light theme.
- **Interface copy:** short, encouraging and plain. For example: "Your code is running the login now."

## Components

### Store App
The practice project: FastAPI routes and Jinja2 templates. It calls `pieces.auth` and `pieces.cart` and never implements their logic itself.
Routes: `GET /` browse grid, `GET|POST /login`, `POST /logout`, `POST /cart/add/{id}`, `POST /cart/remove/{id}`, `GET /cart`, `POST /checkout` (logged in and cart not empty, otherwise redirect with a message), `GET /download/{purchase_id}`, `GET /profile`.
The database path comes from the `STORE_DB` environment variable, so purchases survive store restarts and rebuilds.
PRD ref: `prd.md > The 3D Asset Store`, `prd.md > States and Boundaries` (wrong login, empty cart).

### Carvable Piece: Authentication
`store/pieces/auth.py`, round 1.
- `hash_password(password: str) -> str` returns the SHA-256 hex digest.
- `check_login(username: str, password: str, users: dict[str, str]) -> bool` returns True only if the user exists and the hashed password matches (compared with `hmac.compare_digest`). It returns False for empty input.
- `is_logged_in(session: dict) -> bool` reports whether the session holds a username.

Call sites: `POST /login` (loads `users` from the database and stores the username in the session on success), `POST /checkout` and `GET /profile` (both use `is_logged_in`).
Breaks if wrong: anyone can check out, or the real user can't log in.
Tests: `tests/test_auth.py`, covering correct login, wrong password, unknown user, empty fields, hash stability, and logged-in/out sessions.
PRD ref: `prd.md > Carving a Piece`, `prd.md > The 3D Asset Store`.

### Carvable Piece: Cart Behavior
`store/pieces/cart.py`, round 2. The cart is a list of asset IDs kept in the session.
- `add_item(cart: list[int], asset_id: int) -> list[int]` returns a new list and ignores duplicates (you buy a digital asset once).
- `remove_item(cart: list[int], asset_id: int) -> list[int]` returns a new list. Removing a missing ID is a no-op.
- `cart_total(cart: list[int], prices: dict[int, float]) -> float` returns the sum rounded to 2 decimals. An empty cart totals 0.0.

Call sites: `POST /cart/add/{id}`, `POST /cart/remove/{id}`, `GET /cart`, `POST /checkout`.
Breaks if wrong: duplicate items, items that won't remove, or a wrong total at checkout.
Tests: `tests/test_cart.py`.
PRD ref: `prd.md > Carving a Piece`, `prd.md > The 3D Asset Store`.

### Piece Definitions
`tutor/pieces.py` holds a `PIECES` dict with one entry per piece (`auth`, `cart`, in round order). Each entry has: title, store file, stub code, test file, inputs/outputs text, call sites, what breaks, the "model explanation" used for grading, and a reference list of `(file, function name)`. The reference code is **pulled live** from the store files with Python's `ast` module, so it can never go stale. These are hand-written, not AI-generated.
PRD ref: `prd.md > Focused Task`, `prd.md > Carving a Piece`.

### Tutor Server
`tutor/app.py` serves the three pages and the JSON API:

| Endpoint | Does |
|---|---|
| `GET /api/state` | Current round, piece, task context, editor code (draft, or the stub if there's no draft), test results, check status and ownership %. |
| `POST /api/round/start` | Starts the next piece that hasn't passed. Ignored if a round is already open. |
| `PUT /api/code` | Autosaves the draft. |
| `POST /api/hint` | Returns a hint for the current code. |
| `POST /api/submit` | Runs the tests. On pass, swaps the code in, updates the %, and opens the understanding check. On fail, returns results plus a hint. |
| `POST /api/explain` | Grades an explanation and returns `{score, feedback, hint?, final_explanation?, done}`. |
| `POST /api/ask` | Answers a learner question about the piece. |
| `POST /api/run` | Assembles and (re)starts the store and returns its URL. |

PRD ref: `prd.md > Hints`, `prd.md > Tests and Swap-In`, `prd.md > Understanding Check`, `prd.md > Running the Project`.

### Test Runner and Store Launcher
`tutor/runner.py`.
- **`run_tests(piece, code)`:** writes the code to a temp folder as `<piece>.py`, then runs `pytest <test file> --junitxml=report.xml` as a subprocess with that folder first on `PYTHONPATH` and a 15-second timeout. It parses the XML report into `[{name, passed, message}]`. A timeout or syntax error counts as a failed result with the error message.
- **`run_store()`:** copies `store/` to `.run/store/`, overwrites each **passed** piece with `data/learner/<piece>.py`, stops the previous store process, and starts `uvicorn app:app --port 8001` in that folder. It polls the port for up to 10 seconds, then returns the URL or the last lines of the store's error output.
PRD ref: `prd.md > Running the Project`, `prd.md > Tests and Swap-In`, `prd.md > States and Boundaries`.

### AI Tutor (LLM)
`tutor/llm.py` is the only file that talks to Groq. It has three functions, each with its own instruction prompt:
- **`hint(piece, code, failing_tests=None)`:** "Nudge, never give code or the exact answer." It receives the task context and the learner's code. After a failed submit, it also gets the failing tests' names and messages, with passing tests marked as already done, so the hint targets what's actually broken. **Backstop:** any fenced code block in the reply is stripped before it's shown.
- **`grade(piece, explanation, attempt)`:** asks for JSON `{score: 0-10, missing, extra}` and compares against the piece's model explanation. Below 7 on attempt 1 or 2, it returns a targeted "you're missing something about X" hint. After the second miss, it returns the precise explanation.
- **`answer(piece, question, code)`:** answers a learner question in context. It may explain concepts but not hand over code for the carved functions.

Configured by environment variables (`LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`/`GROQ_API_KEY`), with Groq defaults.
PRD ref: `prd.md > Hints`, `prd.md > Understanding Check`.

### Progress and Ownership
`tutor/progress.py` loads and saves `data/progress.json` and computes ownership.
**Ownership %** = the learner's lines ÷ all lines, counting non-blank, non-comment lines across the store's `.py` files as they'd run (learner pieces swapped in). Templates, CSS and tests aren't counted. It starts at 0% and only goes up.
PRD ref: `prd.md > Ownership Percentage`, `prd.md > Saved Progress`.

### Tutor Pages
`tutor/pages/catalog.html`, `project.html`, `learn.html` + `tutor/static/style.css`, `learn.js`.
- **Catalog:** one real card and one disabled "coming soon" card.
- **Project page:** description, demo login, **Run project**, **Start learning**, or **Continue learning** if a round is in progress.
- **Workspace:** the layout from **Look and Feel**. `learn.js` loads `/api/state`, sets up CodeMirror (with a `<textarea>` fallback), autosaves, and wires Hint / Submit / Run project / Explain / Ask / Next piece. It shows a "thinking…" state while the AI responds.
PRD ref: `prd.md > Project Catalog`, `prd.md > Screens and Layout`.

## Data Model

| Data | Where it lives | Updated by | When you leave and come back |
|---|---|---|---|
| Store user (1 row: `learner`, password hash) | `data/store.db` → `users` | `seed` on first start | Unchanged |
| Assets (~8 rows: id, name, kind, price, image file) | `data/store.db` → `assets` | `seed` | Unchanged |
| Purchases (id, asset_id, bought_at) | `data/store.db` → `purchases` | `POST /checkout` | Still on the profile |
| Logged-in user, cart | Store session cookie | Login/logout, cart routes | Survives tab reloads. Cleared on logout or browser close (fine for a demo). |
| Tutor progress | `data/progress.json` | Tutor API | Restored exactly |
| Passed learner pieces | `data/learner/auth.py`, `cart.py` | `POST /api/submit` on pass | Kept permanently and used by every Run |

`progress.json` shape:
```json
{
  "current": "cart",
  "pieces": {
    "auth": {"status": "passed", "draft": "...", "last_results": [...],
             "check": {"attempts": 2, "best_score": 8, "done": true}},
    "cart": {"status": "in_progress", "draft": "...", "last_results": null,
             "check": {"attempts": 0, "best_score": null, "done": false}}
  }
}
```
`status` is `not_started`, `in_progress` or `passed`. Once a piece is `passed`, it never goes back (`prd.md > States and Boundaries`).

## File Structure

```
Build_with_Ai_Basics/
├── store/                      # The 3D asset store (practice project, FastAPI)
│   ├── app.py                  # Routes: browse, login/logout, cart, checkout, download, profile
│   ├── db.py                   # sqlite3 helpers + seed() (one user, ~8 assets)
│   ├── pieces/                 # The carvable pieces: AI originals, never edited by the tutor
│   │   ├── auth.py             # Round 1: hash_password, check_login, is_logged_in
│   │   └── cart.py             # Round 2: add_item, remove_item, cart_total
│   ├── templates/              # Jinja2 pages: base, browse, login, cart, profile
│   └── static/
│       ├── store.css           # Sketchfab-like image-led styling
│       └── assets/             # Asset pictures (labeled placeholders)
├── tests/
│   ├── test_auth.py            # Tests for the auth piece
│   └── test_cart.py            # Tests for the cart piece
├── tutor/                      # The tutor app (FastAPI, localhost:8000)
│   ├── app.py                  # Serves pages + /api/* endpoints
│   ├── pieces.py               # PIECES: stubs, task context, model explanations, references
│   ├── runner.py               # run_tests() via pytest; run_store() assemble + restart
│   ├── llm.py                  # hint / grade / answer through Groq (openai library)
│   ├── progress.py             # progress.json load/save + ownership %
│   ├── pages/                  # catalog.html, project.html, learn.html
│   └── static/                 # style.css, learn.js
├── data/                       # (gitignored) progress.json, learner/*.py, store.db
├── .run/                       # (gitignored) assembled store copy that actually runs
├── devpost/                    # Devpost learning workspace
├── requirements.txt            # fastapi, uvicorn, jinja2, itsdangerous, python-multipart, openai, pytest
├── .gitignore
└── README.md                   # How to run + demo walkthrough
```

## External Services and Dependencies

**Groq API** (the only outside service)
- Docs: https://console.groq.com/docs/openai, models: https://console.groq.com/docs/models
- Call: `OpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY).chat.completions.create(model="openai/gpt-oss-120b", messages=[{"role":"system",...},{"role":"user",...}])` → the text is in `choices[0].message.content`. For grading, ask for JSON and parse it, retrying once on bad JSON.
- Key: free from console.groq.com. Never committed. It's read from an environment variable.
- Cost/limits: free tier with per-minute and per-day request limits. **Verify the current limits in build step 1.** A two-round demo uses roughly 15–30 requests.
- Backup: Gemini via `https://generativelanguage.googleapis.com/v1beta/openai/` with an AI Studio key. Same code, different environment variables.

**CDN:** CodeMirror 5.65.16 from `cdnjs.cloudflare.com`, with a `<textarea>` fallback offline.

Everything else is a Python package installed locally (see **Stack**).

## Important Failure Modes

- **Groq is rate-limited, down or the key is missing** → the tutor area shows "The tutor is busy, try again in a minute." Tests, swap-in, Run project and the % still work, because none of them need the AI. Fix: wait, or switch to the Gemini environment variables.
- **The learner's code hangs or crashes** (infinite loop, syntax error, wrong import) → the 15-second pytest timeout or the error shows up as a failed test with its message. A hint is offered and nothing is swapped in.
- **The store won't start** (port 8001 busy, import error) → after 10 seconds the workspace shows "The store couldn't start" plus the last lines of its error output. This should be rare, since only code that passed the tests is ever swapped in.
- **The AI leaks a solution in a hint** → the prompt forbids it, and the server strips fenced code blocks as a backstop. Inline answers can still slip through. Check this while building the hints step.

## What Was Simplified and Why

- **Pieces are predefined, hand-written entries** instead of the AI choosing what to carve. This proves the learning loop without live code analysis. The fuller version would need the AI to find good carve points and generate stubs and tests.
- **The learner's code runs directly on your laptop** instead of inside a sandbox (an isolated container). It's acceptable because it's one learner on their own machine. A public version would need containers or a sandboxed runner.
- **Login is the store's own tiny auth** (one user, SHA-256, session cookie) instead of real accounts. The tutor itself has no accounts at all (`prd.md > Product Decisions`: one user).
- **Fake checkout and on-page download links**, as decided in the PRD. No payment or mail service.
- **Labeled placeholder pictures** instead of real 3D files (`prd.md > Deferred From the POC`).
- **Progress is stored in one JSON file** instead of a database, because there's one learner and one project.
- **The store restarts on every Run project** instead of hot-swapping code. It's simpler and always runs exactly the current code, at the cost of a couple of seconds' wait.

## Decisions and Open Issues

**Your choices**
- **Python for both programs**, with HTML and a little JavaScript in the browser.
- **FastAPI** for both, chosen over the Flask recommendation because it's modern and popular. Tradeoff accepted: store pages need Jinja2 and SessionMiddleware set up by hand.
- **Groq + GPT-OSS (free)**, with **Gemini as backup**. Tradeoffs accepted: rate limits, possible data use for training, weaker "no answer" reliability.
- **Run locally and record the demo**. No deployment, which carries over from scope.
- **The carve/test/swap approach** (one file per piece, stub in the editor, pytest in a subprocess, rebuild + restart the store on Run). You agreed to it as proposed.

**Implementation details derived from those choices:** plain `def` routes in the store, the exact function signatures, CodeMirror 5 with a textarea fallback, SQLite for the store, the JSON progress file, the 15-second test timeout, the "score below 7" retry threshold, and the ownership line-counting rule.

**One useful unknown:** When asked which part of the carve/test/swap approach felt least certain, you said it all worked for you. No genuine uncertainty was identified, so none is recorded here.

**Still open**
- **Round pieces:** Authentication, then cart behavior, carried over from `prd.md > Open Questions`. You can still swap them. The design works for any piece that lives in its own file.
- **Groq free-tier limits and model ID:** check in build step 1.
- **Asset pictures:** generated, labeled placeholders by default. Swap in CC0 images if you want a more Sketchfab-like feel.
- **Name and the "Programiz" editor reference:** carried over from the PRD. Neither blocks the build.
