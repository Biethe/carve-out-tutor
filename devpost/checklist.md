---
doc: checklist
status: approved
---

# Build Checklist

Build mode: fast

## Slices

- [x] **1. You can open the tutor, pick the 3D asset store, and run the finished store in a new tab**
  Becomes usable: `localhost:8000` shows the catalog (store card + disabled "Bring your own idea — coming soon"), the project page, and **Run project**, which opens the complete store on `localhost:8001`: log in, browse, cart, fake checkout, download link, profile.
  Why now: Everything else carves pieces out of this store, so it has to exist and work first. It also proves the riskiest plumbing early: the tutor copying the store into `.run/` and starting/stopping a second server.
  PRD ref: `prd.md > The Core Journey` (steps 1-3), `prd.md > Project Catalog`, `prd.md > Running the Project`, `prd.md > The 3D Asset Store`, `prd.md > States and Boundaries` (wrong login, empty cart)
  Spec ref: `spec.md > Store App`, `spec.md > Carvable Piece: Authentication`, `spec.md > Carvable Piece: Cart Behavior`, `spec.md > Test Runner and Store Launcher` (`run_store`), `spec.md > Tutor Pages` (catalog, project), `spec.md > Data Model`, `spec.md > File Structure`, `spec.md > Look and Feel`
  Build: Scaffold per the file structure (`requirements.txt`, `.gitignore` for `data/`, `.run/`, `.venv/`). Write the store: `db.py` with seed (one user, ~8 assets with labeled placeholder pictures), `pieces/auth.py`, `pieces/cart.py`, routes and Jinja2 templates in the Sketchfab-like style. Write `tests/test_auth.py` and `tests/test_cart.py` against the AI originals. Write the tutor's catalog and project pages and `POST /api/run` with `runner.run_store()`.
  Verify (mechanical): `pytest tests/` passes against the originals. Start the tutor, `curl` the catalog and project page, `POST /api/run`, then `curl` the store: wrong login shows an error, right login works, add/remove/total are correct, checkout with an empty cart is refused, checkout creates a purchase with a download link that shows on `/profile`. Calling `/api/run` twice restarts cleanly.
  Learner check: Open http://localhost:8000, click the store card, click **Run project**. In the new tab, try a wrong password, then log in as `learner` / `carve123`, add two assets, remove one, check out, and open your profile. Say whether the store looks and feels like the showcase you pictured.
  Commit: `Add 3D asset store and launch it from the tutor`

- [x] **2. You can do round 1: rebuild authentication, pass the tests, and see your code running the store**
  Becomes usable: **Start learning** opens the workspace: the task (inputs/outputs, call sites, what breaks, live reference code), a CodeMirror editor with the `auth` stub, autosave, **Submit** with per-test ✓/✗, and on pass your code becomes the store's login and the ownership % goes up. **Run project** now runs your `auth.py`. No AI yet.
  Why now: This is the unique kernel: carve, focused task, test, swap in, still working. It comes before the AI so the core loop is proven on its own, and the AI later only adds coaching on top.
  PRD ref: `prd.md > The Core Journey` (steps 4-7, 9), `prd.md > Carving a Piece`, `prd.md > Focused Task`, `prd.md > Tests and Swap-In`, `prd.md > Ownership Percentage`, `prd.md > Saved Progress`, `prd.md > States and Boundaries`
  Spec ref: `spec.md > Piece Definitions`, `spec.md > Tutor Server`, `spec.md > Test Runner and Store Launcher` (`run_tests`), `spec.md > Progress and Ownership`, `spec.md > Tutor Pages` (workspace), `spec.md > Data Model` (`progress.json`), `spec.md > Look and Feel` (workspace)
  Build: `tutor/pieces.py` with the `auth` entry (stub, task text, model explanation, references pulled with `ast`). `tutor/progress.py` (load/save, ownership line count). `runner.run_tests()` (temp folder, pytest subprocess, 15s timeout, junitxml parse). API: `/api/state`, `/api/round/start`, `/api/code`, `/api/submit`. `learn.html` + `learn.js` + workspace styling with the ownership bar.
  Verify (mechanical): Via the API: start round 1 → state shows the stub and 0%. Submit the stub → tests fail with messages, nothing swapped. Submit an infinite loop → timeout reported as a failure. Submit a correct solution → all pass, `data/learner/auth.py` exists, % > 0. `/api/run` → `.run/store/pieces/auth.py` is the learner's file and login still works. Restart the tutor → draft and % are restored.
  Learner check: Click **Start learning**. Read the task, write the three auth functions yourself in the editor, and click **Submit** until everything is green. Watch the % go up, then click **Run project** and log in to the store. That login is now your code.
  Commit: `Add round 1 carve loop: workspace, tests, swap-in, ownership`

- [x] **3. You can ask the tutor for a hint, and failed tests get a hint aimed at what broke**
  Becomes usable: **Hint** gives a nudge about your current code with no solution code. A failed **Submit** comes back with a hint focused on the most important failing test. If Groq is down or the key is missing, you see "The tutor is busy, try again in a minute" and everything else keeps working.
  Why now: The coaching is the second half of the kernel, and Groq is the only outside service, so its real behavior (model ID, limits, whether it leaks answers) should be checked before the understanding check also depends on it.
  PRD ref: `prd.md > The Core Journey` (steps 6-7), `prd.md > Hints`
  Spec ref: `spec.md > AI Tutor (LLM)` (`hint`), `spec.md > External Services and Dependencies`, `spec.md > Important Failure Modes`, `spec.md > Tutor Server` (`/api/hint`, `/api/submit`)
  Build: Check Groq's current model ID and free-tier limits. `tutor/llm.py` with config from env vars and `hint()` (task context, code, failing vs. passing tests, fenced-code stripping). Wire `/api/hint` and the failed-submit hint. "Thinking…" state and the tutor area in the workspace.
  Verify (mechanical): With a key: request a hint on the stub and on a half-right solution; confirm a reply arrives, contains no fenced code, and doesn't contain a complete function body. Submit code that fails only one test and confirm the hint mentions that test's concern. With the key unset: `/api/hint` returns the busy message and `/api/submit` still runs tests.
  Learner check: In round 1 (reset `data/` first if you already passed it), write a partial attempt, click **Hint**, then submit something that fails one test. Do the hints help without giving the answer away?
  Commit: `Add AI hints with failing-test focus`

- [x] **4. After passing, the tutor checks that you understood what you built**
  Becomes usable: Once tests pass, the tutor asks you to explain your code, scores it 0-10 with feedback and extra tips, gives up to two targeted hints and retries on a weak answer, and then the full explanation. **Ask** lets you question the tutor. A low score never removes your code or lowers the %.
  Why now: Completes one full round as the PRD describes, before repeating it for round 2.
  PRD ref: `prd.md > The Core Journey` (step 8), `prd.md > Understanding Check`
  Spec ref: `spec.md > AI Tutor (LLM)` (`grade`, `answer`), `spec.md > Tutor Server` (`/api/explain`, `/api/ask`), `spec.md > Data Model` (`check` in `progress.json`)
  Build: `grade()` with JSON parsing (retry once on bad JSON) and the attempt logic, `answer()`. `/api/explain` and `/api/ask`. Explanation and Ask UI in the tutor area, check state saved in progress.
  Verify (mechanical): After a pass, post a good explanation → score ≥ 7, done. Post a vague one three times → two hints, then a final explanation, done. `/api/ask` returns an answer. Ownership % and `data/learner/auth.py` unchanged throughout. Restart → check state restored.
  Learner check: After your tests pass, explain your login code in your own words. Try once badly on purpose to see the hint, and ask the tutor one question. Does the feedback feel fair and useful?
  Commit: `Add understanding check and Ask`

- [x] **5. You can do round 2 on the cart, and close and reopen the app without losing anything**
  Becomes usable: **Next piece** carves cart behavior while your auth stays yours. The full loop repeats, the % rises again, and the store runs with both of your pieces. Closing mid-round and reopening restores the round, your draft, results and %. The project page says **Continue learning** when a round is open. README explains how to run and demo it.
  Why now: Round 2 is the proof that the loop repeats and ownership grows. By now it's mostly a new `PIECES` entry, so it comes last.
  PRD ref: `prd.md > The Core Journey` (step 10), `prd.md > Saved Progress`, `prd.md > Ownership Percentage`, `prd.md > States and Boundaries` (after round 2, closing and coming back)
  Spec ref: `spec.md > Piece Definitions` (`cart`), `spec.md > Tutor Server` (`/api/round/start`), `spec.md > Tutor Pages`, `spec.md > Where It Runs and How Someone Tries It`
  Build: `cart` entry in `PIECES`, **Next piece** button and an "all done" state after round 2, **Continue learning** on the project page, README with setup and demo walkthrough.
  Verify (mechanical): Script the whole journey via the API from an empty `data/`: round 1 pass → round 2 start → stub shown, auth still learner's → partial draft → restart the tutor → draft restored → pass → % higher than after round 1 → `/api/run` uses both learner files, and login, cart, checkout and profile all work on the store.
  Learner check: Click **Next piece**, start the cart functions, close the tutor server mid-way and start it again. Your draft should still be there. Finish the round and run the store: add, remove, check out. All of that is now your code.
  Commit: `Add round 2 (cart), resume, and README`

## Hands-on Checkpoints

- [x] Early usable behavior explored — after slice 2: you rebuild authentication yourself and run the store with your code, so feedback on the workspace can shape the AI slices. Feedback: smooth and comfortable, but the design is too basic; no hints yet was expected (slices 3-4). Design items moved to Final Review at the learner's request.
- [ ] Final kick-the-tires exploration and feedback completed

## Final Review

- [ ] Make the tutor pages more visually attractive. They're smooth but too plain (from the early checkpoint).
- [ ] A fuller projects/home page, with a richer description of the project. Clarify what "a whole page for the projects" means first.
- [ ] Home intro also mentions "bring your own idea" (coming soon), not only "start with a project that already works".
- [ ] Floating tutor: a small draggable button that opens its own scrollable window, replacing the fixed tutor panel. Clicking **Hint** opens it right away.
- [ ] Show only the latest hint, with no log. In the explanation stage, show only the explanation exchange.
- [ ] Grading takes earlier explanations into account, and adding detail never lowers the score (the learner got 6/10, then 3/10 after adding more).
- [ ] Passing criteria listed under each function in the task, marked ✓/✗ after Submit.
- [ ] Final review complete — feedback resolved and learner confirms ready to ship

## Code Tour and App Map

- [ ] Learning activity complete — guided route, focused alternative, prior practice connected, or brief recap
- [ ] Optional edit and transfer reflection addressed — offered/declined/already covered/not applicable as appropriate
- [ ] `devpost/app-map.html` generated from finished code, checked, and shown, including a project-grounded practice to reuse

Activity and evidence:
Route and stops:
Edit outcome:
Reflection:
Activity mode:

## Revisions

- Store database is created and seeded by the store itself on startup (`store/db.py > init`), not by the tutor — the store needs its tables whenever it starts, so this is simpler with the same result.
- The tutor stops the store in its FastAPI shutdown hook, not with `atexit` — the build found uvicorn re-raises the stop signal, which skips `atexit` and left the store running after the tutor quit.
- The practice store got a display name, "Polyvault" — the PRD only called it "the 3D asset store"; easy to rename.
- Hint rules made stricter (one function, next step only, no calls with arguments) and `reasoning_effort="low"` added. Live testing with `openai/gpt-oss-120b` showed the first prompt handed over nearly the whole solution (`hashlib.sha256(...).hexdigest()` plus all three functions), and the free tier's 8K tokens/minute needs short replies.
- The tutor also reads the API key from a git-ignored `.env` file, not only an exported variable, so the key survives new terminals.
- On a weak explanation that still has hints left, the tutor shows only the score and the hint, not the "what's missing" feedback. Live testing showed that feedback already spelled out the whole explanation, so the retry would be pointless. Feedback, extra tips and (if needed) the full explanation come once the check is done.
- **Next piece** appears as soon as the tests pass, with the explanation check offered alongside it rather than required first. If the AI were down, a required check would block round 2, and the PRD counts a round once the tests pass.
