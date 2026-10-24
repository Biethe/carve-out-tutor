# Carve-Out Tutor

Learn to code by rebuilding real pieces of a project that already works.

The tutor gives you a finished Python web app (Polyvault, a small 3D asset store), cuts out one piece, and coaches you with hints, never the answer, until your code passes the tests and replaces the original. The store keeps working the whole time, and an ownership bar shows how much of it is now your code.

Built for the Devpost *Build With AI: Basics* hackathon as a proof of concept: one project, two rounds (authentication, then the cart).

## Run it

You need Python 3.11+ and a free [Groq API key](https://console.groq.com/keys).

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
echo "GROQ_API_KEY=your_key_here" > .env     # git-ignored
uvicorn tutor.app:app --port 8000
```

Open **http://localhost:8000**. The store runs on `localhost:8001` and is started by the tutor. Store login: `learner` / `carve123`.

**Start over** (fresh demo): stop the server and delete the `data/` folder.

**Use Gemini instead of Groq:** put these in `.env`:
```
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
LLM_MODEL=gemini-2.5-flash
LLM_API_KEY=your_ai_studio_key
```

**Free-tier note:** Groq's free plan allows about 1,000 requests and 200,000 tokens a day for `gpt-oss-120b`. A full two-round demo uses a small part of that. If the limit runs out, the tutor says it's busy, and tests, Run project and the ownership bar keep working.

## Demo walkthrough

1. **Catalog → Polyvault → Run project.** The finished store opens in a new tab. Log in, add assets to the cart, check out, and see the download links on your profile.
2. **Start learning.** Round 1 carves out `store/pieces/auth.py`. The task panel shows what each function takes and returns, where it's called, what breaks if it's wrong, and the store code you need to read.
3. **Write, Hint, Submit.** Hints nudge without giving code. A failed submit shows ✓/✗ per test and a hint aimed at the failing test.
4. **Pass.** Your file replaces the original and the ownership bar goes up. Explain your code to the tutor: it scores you, gives up to two hints, then fills in what you missed. You can ask it questions too.
5. **Run project again.** The store's login is now your code.
6. **Next piece.** Round 2 carves out the cart (`store/pieces/cart.py`). Pass it and the bar rises again: login and cart are both yours.

Close the tutor at any point and start it again. Your round, draft and progress are all still there.

## How it works

```
tutor/            the tutor app (FastAPI, :8000)
  app.py          pages + JSON API
  pieces.py       the carvable pieces: stubs, task text, reference explanations
  runner.py       runs pytest on your code (separate process, 15s limit); assembles and restarts the store
  llm.py          hints, grading and answers via an OpenAI-compatible API (Groq by default)
  progress.py     data/progress.json + the ownership %
store/            the practice project (FastAPI + Jinja2 + SQLite, :8001)
  pieces/         auth.py and cart.py: the AI's originals, never edited
tests/            the tests each piece must pass
```

Each piece is its own file. When you pass, your code is saved to `data/learner/`, and **Run project** copies the store to `.run/store/` with your passed pieces swapped in, then restarts it. Pieces you haven't finished keep running the original, so the store never breaks.

**Note:** your code runs directly on your machine, not in a sandbox. That's fine for one learner locally, but not for a public deployment.
