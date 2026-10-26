# Carve-Out Tutor

Understand how a big project works by rebuilding it yourself, one function at a time, while it keeps working.

You know how to write a script or a function, but a real system with hundreds of files is another thing: how the files glue together, how data flows, how it stays secure. Bring the source code of a project you want to understand (paste its GitHub link, or drop a zip), or pick a ready one. Carve-Out finds its pieces, and Chip, the tutor, takes one out at a time at your level. You write it back with hints, never the answer. Your piece passes when it behaves exactly like the original, so the project never breaks, and every piece you pass stays yours: a bar shows how much of the project is now your code.

**Languages:** Python, JavaScript, TypeScript, Java, C, C++, Rust, SQL, HTML and CSS. A piece is a function, a SQL table, view or query, a CSS rule, or an HTML section with an id.

**Ready projects:** Polyvault (a Python web store), the Tiny compiler ([jamiebuilds/the-super-tiny-compiler](https://github.com/jamiebuilds/the-super-tiny-compiler), CC BY 4.0), Field notes (an HTML, CSS and JavaScript list) and Corner shop (a SQL shop: customers, products, orders and the lines on each order).

Built for the Devpost *Build With AI: Basics* hackathon as a proof of concept.

## Use it in your browser

Open the published site (GitHub Pages) in any modern browser. Nothing to install: Python, the tests and the store all run inside the page with [Pyodide](https://pyodide.org/), and your progress is saved in that browser. No key is needed to try it: visitors without one use a shared demo through a small proxy (`demo-proxy/`, a Cloudflare Worker that keeps the key secret and only serves this site). For unlimited use, click the gear to add your own AI key: [Groq](https://console.groq.com/keys), [OpenRouter](https://openrouter.ai/settings/keys) and [Google Gemini](https://aistudio.google.com/apikey) all have free tiers. The key stays in your browser and goes only to that provider.

**What runs where:** Python, JavaScript, TypeScript, SQL, HTML and CSS run in the browser. Java, C, C++ and Rust are compiled and run on [Wandbox](https://wandbox.org), a free online compiler, so their code is sent there. The local tutor below uses your own compilers (`gcc`/`g++`, a JDK, `rustc`, and Node for JavaScript and TypeScript) and falls back to Wandbox when one is missing.

**How a piece is checked:** Python pieces use pytest tests. For other code, the AI writes a short check program that calls the function and prints one line per check. It's kept only if it runs on the original and an empty version fails it, and your version passes when every line matches the original's. SQL runs on SQLite and is compared table by table and row by row; CSS and HTML are compared declaration by declaration and element by element.

To try the browser version locally: `python web/files.py && python -m http.server 8020`, then open http://localhost:8020/web/.

## Run it locally with a server

You need Python 3.11+ and a free [Groq API key](https://console.groq.com/keys).

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
echo "GROQ_API_KEY=your_key_here" > .env     # git-ignored
uvicorn tutor.app:app --port 8000
```

Open **http://localhost:8000**. The store runs on `localhost:8001` and is started by the tutor. Store login: `learner` / `carve123`.

**Start over** (fresh demo): stop the server and delete the `data/` folder. To see the story again, open http://localhost:8000/?intro.

**Use Gemini instead of Groq:** put these in `.env`:
```
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
LLM_MODEL=gemini-2.5-flash
LLM_API_KEY=your_ai_studio_key
```

**Free-tier note:** Groq's free plan allows about 1,000 requests and 200,000 tokens a day for `gpt-oss-120b`. A full two-round demo uses a small part of that. If the limit runs out, the tutor says it's busy, and tests, Run project and the ownership bar keep working.

## Demo walkthrough

1. **The story.** On the first visit Chip tells what Carve-Out does in seven short steps, while Python loads in the background. Skip it any time.
2. **Which project do you want to understand?** Paste a GitHub link or drop a zip, or start from one that's ready: **Polyvault**, the **Tiny compiler**, **Field notes**, or **Corner shop**. Building a project from your own idea is marked coming soon.
3. **Three questions.** Yes or no, in Chip's voice, so the plan starts at the right level. You can skip them.
4. **Home** shows one next step: try the store first (login `learner` / `carve123`), then your first function. **See the whole plan** lists every step and lets you choose what you write.
5. **The workspace.** A short tour the first time. The task card says what the function must do; write it in the editor, **Get a hint** for a nudge, ask Chip anything. **Check my code** ticks each check.
6. **A pass.** Your function flies into the "yours" counter and runs inside the store from now on. Chip asks one question about it, then it's on to the next function.

Close the tutor at any point and start it again. Your plan, drafts and progress are all still there.

## How it works

```
web/              the standalone site: the main page, browser Python, the service worker
  bridge.py       runs tests, and serves the tutor and the store as web apps with no server
tutor/            the tutor app (FastAPI, :8000 locally; inside the browser on the site)
  app.py          pages + JSON API
  pieces.py       the carvable pieces, function by function: stubs, criteria, questions; assemble()
  langs.py        the other languages: finds their pieces, swaps yours in, checks it against the original
  runner.py       runs pytest on your code (separate process, 15s limit); assembles and restarts the store
  llm.py          hints, grading and answers via an OpenAI-compatible API (Groq by default)
  progress.py     data/progress.json + the ownership %
  static/examples/ the ready projects in other languages, as zips
store/            the practice project (FastAPI + Jinja2 + SQLite, :8001)
  pieces/         auth.py and cart.py: the AI's originals, never edited
tests/            the tests each piece must pass
  ui_walk.cjs     a walk through every screen in a real browser (Playwright), for checking the interface
```

Each piece is its own file, rebuilt one function at a time. When a function passes, it's swapped into the AI's file and saved to `data/learner/`. **Run project** copies the store to `.run/store/` with your file in place, then restarts it. Functions you haven't written yet keep running the original, so the store never breaks.

In the browser, the same tutor app runs inside Pyodide. A service worker passes the page's requests under `web/tutor/` and `web/run/` to it, tests run in a second Python worker that's replaced if code runs past 15 seconds, and progress lives in IndexedDB.

**Note:** with the local server, your code (and an uploaded project's C, Java or Rust) runs directly on your machine, not in a sandbox. On the site it runs inside the browser's sandbox; JavaScript checks run in a separate worker that only collects what the code prints.
