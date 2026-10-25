---
doc: scope
status: approved
---

# Carve-Out Tutor (working title — name TBD)

A browser-based AI tutor that hands you a working Python web project, cuts out one small piece, and coaches you, with hints but never the answer, until your own code replaces it and the page still works.

## The Unique Kernel
**You learn by rebuilding real pieces of a project that already works, and it keeps working the whole time.** The tutor carves out one small part, gives you only the context you need for it (inputs, outputs, where it's called, what breaks if it's wrong), and coaches you with hints. When your version passes the tests, it replaces the AI's code, and the tutor checks that you *understood* it, not just that the tests pass. Each round, a bigger share of the project is yours.

It's like learning to cook as a kid: mom does the meal, you peel the tomatoes and measure the flour, and you still get to taste the finished meal within the hour.

## Who It's For
Junior developers and beginners who know the basics of programming and want to build things. With coding agents, they could just prompt for a finished app and never learn how it works. Today they either let the AI do everything and learn nothing, or grind through tutorials that are cut off from anything they actually want to make.

## The Core Loop
1. The tutor shows the working web page, then carves out one piece of its code.
2. The learner sees a focused task: what this piece takes in and returns, where it's used, what breaks if it's wrong, and only the code around it that they need.
3. The learner writes code in the in-browser editor, runs the tests, and gets stuck along the way.
4. The tutor gives hints toward the goal, never the exact answer.
5. The tests pass. The learner's code replaces the AI's, and the page still runs.
6. The tutor asks a question about what they built, grades their explanation, fills in what's missing, and connects it to similar work they'll do in the future.
7. Next round, the tutor keeps their piece and carves out a different one.

**Why they come back:** Quick wins on a real, working product, and a visibly growing share of code that's theirs.

## Inspiration & Identity
- **Inspiration:** The learner's mom teaching them to cook through small, real steps on real meals.
- **Interview first:** The Devpost Build With AI flipped-interaction skills, where an agent interviews the learner before anything gets built.
- **Feel:** Focused and never overwhelming, one small piece at a time, everything on one page.

## Why This Matters to the Learner
"How can I keep what AI offers us, which is quick implementations, while still learning?" They want to become an AI engineer who can actually implement things, to understand how pieces of code fit together into a real product, and to learn more about agents along the way. They see this project as an agent itself.

## What "Working" Looks Like
A one-minute demo:
1. **Opening (~5 seconds):** A short intro to the project.
2. **The page:** The working Python web page appears. It was prepared ahead of time.
3. **The carve-out:** The tutor cuts out a piece and hands the learner a focused task.
4. **The learning:** The learner tries, gets stuck, gets hints, tries again, passes the tests, and answers the comprehension question.
5. **The payoff:** The page runs again, now with the learner's code inside it, written without the AI handing them the answer. The ownership score goes up.
6. **Round two:** A different piece, and the score goes up again. That's the proof they're learning.

## The POC Boundary
- **One project:** A single small Python web page, prepared ahead of time.
- **One page in the browser:** The task panel, a code editor, a way to run tests, and a preview of the running web page.
- **The carve loop:**
  - Pick a piece and cut it out.
  - Show the focused context.
  - Give hints without answers.
  - Run tests, swap in the learner's code, and re-run the page.
  - Ask the comprehension question and give graded feedback.
- **Rounds:** Two complete rounds, each on a different piece.
- **Ownership score:** The percentage of the project's lines of code that the learner wrote, always visible and rising as they contribute.
- **Opening:** A short intro in front of the prepared page. No live generation.
- **"Bring your own idea":** Shown as a feature of the product but not working in the PoC and not explored in the demo.
- **Standalone (added in the final review):** The whole product is a static web page on GitHub Pages. Python and tests run in the browser, the AI is called from the browser with the learner's own provider and key, and progress is saved in the browser. Nothing depends on the builder's computer.
- **Bring your own project (added in the final review):** Upload a working Python project as a zip (for example from GitHub) and download it back with your code inside. A web app runs live in the page. A project that can't run in a browser (it needs a game engine or a local machine) is checked with tests only.
- **Profile-based carving, up to 100% (added in the final review):** A short first-launch interview, spoken or typed, records what the learner says they can do. Every function can be carved. The learner's model finds the key spots, the profile decides what to leave to the original code, and a learner can choose to write everything. Claimed skills get spot-checked during the project, and the results are saved next to the claims.
- **Voice:** Speak to the tutor any time, especially in the interview and explanations.

## Later
- **Full interview:** A full Devpost-style interview (scope, PRD, spec) before the AI builds anything.
- **Project catalog:** About ten different kinds of web pages or websites for the learner to choose from.
- **Languages other than Python** for uploaded projects, and tests for JavaScript games.
- **Bring your own idea, for real:** The AI generates a working project from the learner's idea, then carves it.
- **More project types:** Games, mobile apps (shown in a phone-sized preview) and multi-page apps, plus more languages.
- **In-browser terminal:** For running arbitrary commands.
- **Accounts and sync:** Progress that follows the learner across devices. In the PoC, the downloaded zip is the way to move work.

## Explicitly Cut
- **Detecting or blocking outside AI tools:** The rule is that the learner doesn't paste solutions from other AI tools, but the app can't reliably enforce that. The comprehension check is the PoC's answer.
- **Deployment for users worldwide:** Optional for the hackathon and not needed to prove the loop.
