# Carve-Out Tutor

Learn to code by rebuilding real pieces of a project that already works.

The tutor gives you a finished Python web app (Polyvault, a small 3D asset store), cuts out one piece, and coaches you with hints, never the answer, until your code passes the tests and replaces the original. The store keeps working the whole time, and an ownership bar shows how much of it is now your code.

Built for the Devpost *Build With AI: Basics* hackathon as a proof of concept: one project, two rounds (authentication, then the cart).

## Use it in your browser

Open the published site (GitHub Pages) in any modern browser. Nothing to install: Python, the tests and the store all run inside the page with [Pyodide](https://pyodide.org/), and your progress is saved in that browser. No key is needed to try it: visitors without one use a shared demo through a small proxy (`demo-proxy/`, a Cloudflare Worker that keeps the key secret and only serves this site). For unlimited use, click the gear to add your own AI key: [Groq](https://console.groq.com/keys), [OpenRouter](https://openrouter.ai/settings/keys) and [Google Gemini](https://aistudio.google.com/apikey) all have free tiers. The key stays in your browser and goes only to that provider.

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
2. **What do you want to build?** Building from your own idea is coming soon; for now open **Polyvault**, or bring your own project as a .zip.
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
  runner.py       runs pytest on your code (separate process, 15s limit); assembles and restarts the store
  llm.py          hints, grading and answers via an OpenAI-compatible API (Groq by default)
  progress.py     data/progress.json + the ownership %
store/            the practice project (FastAPI + Jinja2 + SQLite, :8001)
  pieces/         auth.py and cart.py: the AI's originals, never edited
tests/            the tests each piece must pass
  ui_walk.cjs     a walk through every screen in a real browser (Playwright), for checking the interface
```

Each piece is its own file, rebuilt one function at a time. When a function passes, it's swapped into the AI's file and saved to `data/learner/`. **Run project** copies the store to `.run/store/` with your file in place, then restarts it. Functions you haven't written yet keep running the original, so the store never breaks.

In the browser, the same tutor app runs inside Pyodide. A service worker passes the page's requests under `web/tutor/` and `web/run/` to it, tests run in a second Python worker that's replaced if code runs past 15 seconds, and progress lives in IndexedDB.

**Note:** with the local server, your code runs directly on your machine, not in a sandbox. On the site it runs inside the browser's sandbox.
