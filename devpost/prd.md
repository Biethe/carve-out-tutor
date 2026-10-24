---
doc: prd
status: approved
---

# Carve-Out Tutor (working title): Product Requirements

A browser-based learning environment where a junior developer runs a finished Python web project (a small 3D asset store), then rebuilds two pieces of it with an AI tutor that gives hints but never the answer. Their own lines of code end up running inside the working store.
Source: `scope.md > The Unique Kernel`, `scope.md > Who It's For`.

## The Core Journey
Source: `scope.md > The Core Loop`, `scope.md > What "Working" Looks Like`.

1. **Opening:** The learner opens the app and sees a short intro and the project catalog. The catalog has one project, the 3D asset store, and a "Bring your own idea" option marked as coming soon.
2. **Project page:** They choose the 3D asset store and see a description of the project and what it does.
3. **Run it first:** They click Run and the finished store opens in another browser tab. They log in, browse assets, use the cart and check out, all without seeing any code.
4. **Start round 1:** They click the button to start learning. The tutor carves out the first piece, **authentication**, and opens its first function. A piece is rebuilt **one function at a time**.
5. **Task workspace:** They see one function: what it takes in and returns, and the criteria it must meet to pass. A separate **Read first** tab shows where it's called, what breaks if it's wrong, and only the code they need to read. The editor shows just that function, empty.
6. **Work:** They write the function. They can click **Hint** for a nudge, and ask the tutor about a library, a method or a concept at any time.
7. **Submit:** The tests run, and each criterion is marked passed or failed.
   - **Tests fail:** They see which criteria failed, and the tutor gives a hint focused on the most important one. Back to step 6.
   - **Tests pass:** Their function replaces the AI's in the store right away, and the ownership percentage goes up.
8. **One question:** The tutor asks one narrow question about that function. A weak answer gets a narrower follow-up question. (See **Understanding Check**.)
9. **Next function:** They move to the next function of the piece. Steps 5–8 repeat until the whole piece is theirs.
10. **See it working:** They run the store again in the other tab. It works the same, but now authentication is their code.
11. **Round 2:** The tutor keeps their authentication code and carves out **cart behavior**, again one function at a time. The ownership percentage keeps rising.

The proof is complete when two pieces are the learner's, the store still works end to end, and the ownership percentage shows their share.

## Screens and Layout

1. **Home / catalog:** A short intro and the catalog, with one real project card and one "Bring your own idea" card marked coming soon.
2. **Project page:** The description of the 3D asset store, what it does, a **Run project** button and a **Start learning** button.
3. **Learning workspace:** The main screen.
   - **Layout:** The task and references on one side, and the code editor with its output and test results on the other.
   - **Buttons:** **Hint**, **Submit** and **Run project**.
   - **Tutor area:** Where hints, feedback and the explanation conversation appear.
   - **Ownership percentage:** Always visible.
4. **The 3D asset store:** Opens in a separate browser tab when the learner runs the project (see **The 3D Asset Store**).

Keep it to one main idea per screen so the learner never gets lost.

## Look and Feel
- **Overall:** Light colors and generous spacing. Simple, very smooth and easy to navigate, with not too many things on a page at once. A few subtle effects, but not many.
- **Tutor app:** Calm, clear and learning-focused, like GeeksforGeeks.
- **Editor:** Like Programiz's online Python editor, with code on one side and output on the other. *(Assumption: "programs" meant Programiz. Confirm.)*
- **3D asset store:** Like Sketchfab: clean, image-led asset browsing in a showcase style.

## Features and Behavior

### Project Catalog
- The catalog shows the 3D asset store as the one available project, and "Bring your own idea" as a visible feature that is clearly marked coming soon and can't be clicked.
  - [ ] The catalog shows one project card that can be opened and one "coming soon" card.
  - [ ] Opening the project card shows its description, **Run project** and **Start learning**.

### Running the Project
Source: `scope.md > The POC Boundary`.
- **Run project** opens the 3D asset store in a separate browser tab, using whatever code is current: the AI's original code, plus any pieces the learner has completed.
  - [ ] Before any rounds, the store works fully in a new tab.
  - [ ] After each completed round, the store still works, and the learner's piece is the one running.

### The 3D Asset Store
The practice project the learner rebuilds piece by piece. It comes with a demo account (`learner`), and anyone can create more.
- **Sign up:** Create an account with a username and password (with a confirmation). Taken usernames, short passwords and mismatched confirmations show an error. After signing up, the new user logs in like anyone else.
- **Log in:** With any existing account. Wrong credentials show an error.
- **Browse assets:** Pictures standing in for 3D models, animations and worlds, stored in the store's database.
- **Cart:** Add items, remove items, and see the cart's contents and total.
- **Checkout:** Fake. No real payment happens.
- **Download link:** After checkout, the page shows a download link.
- **Profile:** Lists the assets *this user* bought, each with its download link. Users can't see or download each other's purchases.
  - [ ] A visitor who isn't logged in can't check out. Logging in with the right credentials works, and wrong credentials show an error.
  - [ ] A new user can sign up and then log in. Invalid or taken usernames, short passwords and mismatched confirmations are refused with a message.
  - [ ] Each user's profile shows only their own purchases.
  - [ ] Adding and removing items updates the cart's contents and total correctly.
  - [ ] After a fake checkout, a download link appears and the purchase is listed on the profile.

### Carving a Piece
Source: `scope.md > The Core Loop`.
- **Start learning** (round 1) and the start of round 2 each carve out one predefined piece: **authentication** first, then **cart behavior**.
- A piece is rebuilt **one function at a time**, in order. The editor shows only the current function as an empty stub, so the learner never faces several tasks at once.
  - [ ] The editor shows one stubbed function, and the rest of the project is untouched.
  - [ ] The next function opens only after the current one passes.

### Focused Task
- The task is split into two tabs so there's little to read at once:
  - **Your task:** the current function, what it takes in and returns, and the criteria it must meet to pass.
  - **Read first:** where it's called, what breaks in the store if it's wrong, and only the code needed to understand it.
  - [ ] The task tab shows one function and its pass criteria; the read tab shows call sites, consequences and references for that function only.
  - [ ] After Submit, each criterion is marked passed or failed.

### Hints
- The learner can ask for a hint at any time while coding. A hint is one short idea, ideally a question, and never gives the exact answer.
- After failed tests, hints focus on the most important thing the learner missed.
- **Ask the tutor:** at any time, the learner can ask about a library, a method, an attribute or a concept, and gets a short reference-style answer that never writes their function.
- **No log:** the tutor is a small button the learner can drag anywhere. It opens its own window, shows only the latest hint or answer, and clears when closed.
  - [ ] Clicking **Hint** gives a nudge related to the current piece that contains no complete solution code.
  - [ ] After failed tests, the hint addresses what a failing test is checking.

### Tests and Swap-In
- **Submit** runs the tests for the carved piece and shows the results.
- On pass, the learner's code becomes the running code for that piece, and the ownership percentage updates.
  - [ ] Failing code shows which tests failed, plus a hint, and the round stays open.
  - [ ] Passing code shows all tests passed, the learner's code is now what runs, and the percentage goes up.

### Understanding Check
- **After a function passes:** The tutor asks **one narrow question** about it (for example, "Why compare the hashes with hmac.compare_digest instead of ==?").
- **Feedback:** The tutor scores the answer, says what was missing, and adds one useful extra fact.
- **If the answer is weak:** The tutor asks a narrower follow-up question and the learner answers again. Answers are judged together, so adding detail never lowers the score. After two follow-ups, the tutor gives the full answer.
- **The function counts once the tests pass.** The question backs it up.
  - [ ] After passing, the learner gets one narrow question and a score with feedback.
  - [ ] A weak answer gets a narrower follow-up question and a retry, up to two, and then the full answer.
  - [ ] A later answer never scores lower than an earlier one.
  - [ ] A low score never removes the learner's code or lowers the percentage.

### Saved Progress
- Closing and reopening the app restores everything: completed pieces, the percentage, the current round, and in-progress code in the editor.
  - [ ] After closing mid-round and reopening, the same round is open with the learner's unfinished code still in the editor.
  - [ ] Completed pieces and the percentage are unchanged after reopening.

### Ownership Percentage
Source: `scope.md > The POC Boundary`.
- Always visible in the workspace. It shows the share of the project's lines of code written by the learner (the learner's lines ÷ total lines).
  - [ ] It starts at 0% and goes up after round 1, then again after round 2.

## States and Boundaries
- **First open:** The catalog appears, and the ownership percentage is 0%.
- **While a piece is carved out:** **Run project** keeps running the AI's original version of that piece until the learner's code passes, so the store never breaks while they work.
- **After a piece passes:** It is the learner's code permanently. It never reverts to the AI's version. If it later causes a bug, the learner comes back and fixes it, which is easier because they wrote it.
- **Empty or broken code submitted:** The tests fail and show the error or failing tests. A hint is offered, and nothing is swapped in.
- **Wrong login in the store:** An error message appears and the visitor stays logged out.
- **Empty cart:** The cart shows it's empty, and checkout isn't available.
- **After round 2:** Both pieces are the learner's, the store works end to end, and the percentage shows their final share.
- **Closing and coming back:** Nothing starts fresh. Finished pieces, the ownership percentage, the current round and any in-progress code are all still there, and the learner picks up where they left off.

## Product Decisions
- **One project:** The 3D asset store. Focus the effort on one great carve loop.
- **Two rounds, authentication then cart:** Both visibly change the store. These may still change.
- **A 3D asset store as the practice project:** A real kind of business, so it's a real-world product to understand from the inside.
- **Sign-up in the store:** Added during the final review so the learner can create users and check they can log in. New passwords are hashed by the learner's `hash_password`, and logins go through their `check_login`. The tutor itself still has no accounts.
- **Fake payment:** No real money moves.
- **Pictures instead of real 3D files:** The idea is shown without handling real assets.
- **Download link on the page, not by email:** This avoids connecting to an outside mail service.
- **Ownership is measured in lines of code:** Simple and visible.
- **One function at a time:** Each piece is split into its functions so the learner always has one small task (changed during the final review: one whole piece at once was too much to read and do).
- **Functions count once the tests pass:** One narrow question backs up the implementation. Weak answers get up to two narrower follow-ups, then the tutor gives the answer.
- **Hints never give the exact answer while coding.**
- **Progress persists:** Finished pieces, the percentage and in-progress work survive closing the app, so learners never start fresh.
- **A passed piece stays the learner's:** The AI's version runs only while a piece is unfinished. Once it passes, it's theirs for good, including fixing any bugs it causes later.
- **"Bring your own idea" is visible but coming soon.**

## What We're Building
- **Tutor screens:** The home/catalog page (one project plus a coming-soon card), the project page, and the learning workspace.
- **The store:** The 3D asset store with log-in, browsing, cart, fake checkout, on-page download links and a profile, opened in a separate tab by **Run project**.
- **The carve loop:** Carving, the focused task, hints, tests and swap-in, and the understanding check with hint retries.
- **Two rounds:** Authentication, then cart behavior.
- **The ownership percentage:** Always visible, measured in lines of code.

## Deferred From the POC
- **Sending download links by email:** Needs a mail service and credentials. The on-page link proves the flow.
- **Real payments:** Need a payment provider. They don't help prove the learning loop.
- **Real 3D files and viewers:** Pictures are enough to make the store believable.
- **A working "Bring your own idea":** Needs live generation of a project. It's shown, but disabled.

## Possible Later Enhancements
- **A bigger catalog:** About ten different kinds of web projects to choose from.
- **Bring your own idea, for real:** A Devpost-style interview, then the AI builds the project and carves it.
- **Many more rounds:** Until 40% or more of the project, and eventually the whole core, is the learner's.
- **More:** Games, mobile apps in a phone-sized preview, other languages and an in-browser terminal.
- **Accounts and saved progress** for learners anywhere in the world.

## Non-Goals
- **Detecting or blocking outside AI tools:** The rule can't be reliably enforced. The understanding check does that job instead (`scope.md > Explicitly Cut`).
- **Deployment for users worldwide:** Optional for the hackathon and not needed to prove the loop.
- **A full IDE:** No in-browser terminal and no editing arbitrary files outside the carved piece.
- **Generating the practice project live:** The store is prepared ahead of time.
- **Reverting a passed piece to the AI's code:** Once a piece passes, it stays the learner's.

## Open Questions
- **Round pieces:** Authentication, then cart behavior, may change. They can be confirmed during `4-spec` or the build.
- **Editor reference:** Confirm "programs" means Programiz. Can wait.
- **Name:** Is there a real name to replace "Carve-Out Tutor"? Can wait.
