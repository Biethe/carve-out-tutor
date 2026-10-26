// Walks the tutor's screens in a real browser. It fails on wrong text, a missing element, a console error, a failed
// request, or a page that scrolls sideways, and saves a screenshot of every screen to $SHOTS. See
// docs/superpowers/plans/2026-10-25-calm-redesign.md ("How to run the checks") for starting a fresh tutor first.
// Usage: node tests/ui_walk.cjs <url> <desktop|phone> <step...>
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
// Like see(), for text that's in the page but hidden at this size (the crumb on phones).
async function has(where, selector, text, timeout = 15000) {
  for (const end = Date.now() + timeout; !((await where.locator(selector).first().textContent().catch(() => "")) || "").includes(text);) {
    if (Date.now() > end) fail(`${selector} should contain "${text}"`);
    await page.waitForTimeout(200);
  }
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
  // the status is hidden on phones (as in the prototype), so wait on its words, not on seeing it
  await page.waitForFunction(() => document.querySelector("#py")?.textContent.includes("Python is ready"), null, { timeout: 180000 });
  await page.click("#story-next");
  await T();
  if ((await page.evaluate(() => localStorage.getItem("seenStory"))) !== "1") fail("the story should be remembered");
  await page.evaluate(() => localStorage.removeItem("seenStory"));  // Skip works too
  await page.reload();
  await page.click("#skip-intro");
  await T();
}

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

async function quiz() {  // three yes/no questions after picking Polyvault; the walk answers yes, no, yes
  const t = await T();
  await see(t, "#build-text", "Polyvault is ready");
  await see(t, "#q-react", "Polyvault is ready. Three quick questions first.");
  await see(t, "#q-count", "Question 1 of 3");
  await see(t, "#q-text", "Have you written your own Python functions before?");
  // Chip speaks the first question right away, or, if the browser blocks sound, asks for a tap on the speaker.
  await t.waitForFunction(() => (window.played || []).some((src) => src.endsWith("/voice/python.wav"))
    || document.querySelector("#q-status").textContent.includes("Tap the speaker to hear Chip."), null, { timeout: 8000 });
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

async function home() {  // a new learner's home: try the store first, then the first function
  const t = await T();
  await has(t, "#h-project", "Polyvault");
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
  await t.click('a[aria-label="New project"]');
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
  await has(t, "#h-project", "mini");
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
  // Only the browser leaves connect out (its file can't load there); on your own computer it can be rebuilt too.
  if (SITE) await see(t, "#next-title", "Write area");
  await shot(t, "home-partial");
  await t.goto(new URL("./?new", t.url()).href);  // back to Polyvault for the steps after this one
  await t.click("#open-store");
  await t.waitForURL(/\/project/);
}

const WRONG = "def hash_password(password: str) -> str:\n    return password\n";
const RIGHT = 'import hashlib\n\n\ndef hash_password(password: str) -> str:\n    """Return the SHA-256 hex digest of the password."""\n    return hashlib.sha256(password.encode()).hexdigest()\n';
const type = (t, code) => t.evaluate((c) => document.querySelector(".CodeMirror").CodeMirror.setValue(c), code);
// Without a key, the local tutor tells you to add one in Settings; on the site the demo AI is blocked, so Chip is busy.
const NO_AI = SITE ? "busy" : "Settings";
async function workspace() {  // hash_password, first a wrong try
  const t = await T();
  if (!/\/learn/.test(t.url())) { await t.click('[data-act="write"]'); await t.waitForURL(/\/learn/); }
  await has(t, "#w-crumb", "Polyvault / hash_password");
  await see(t, "#w-step", "Function 1 of 6");
  if ((await t.locator("#w-checks li").count()) !== 2) fail("hash_password has two checks");
  await shot(t, "workspace");
  await t.fill("#chat-input", "What does sha256 do?");
  await t.click("#ask");
  await see(t, "#w-say", NO_AI);
  await type(t, WRONG);  // starting to type keeps Chip's answer on screen
  await page.waitForTimeout(400);
  if ((await t.locator("#w-asked").innerText()) !== "You asked: What does sha256 do?") fail("typing wiped Chip's answer");
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
  await see(t, '#w-checks li:last-child[data-state="pass"]');  // the checks tick one after another
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
  await has(t, "#w-crumb", "is_logged_in");
}

async function store() {  // Open my app: Polyvault starts in its own tab
  const t = await T();
  await t.goto(new URL("project", t.url()).href);
  const [tab] = await Promise.all([page.context().waitForEvent("page"), t.click("#run")]);
  for (let i = 0; i < 100 && !(await tab.title()).includes("Polyvault"); i++) await page.waitForTimeout(300);
  if (!(await tab.title()).includes("Polyvault")) fail("the store didn't open");
  await tab.close();
}

const STEPS = { boot, story, start, choose, quiz, skipquiz, profile, home, returning, upload, partial, workspace, pass, passed, tour, win, store };

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROME || undefined });
  const view = size === "phone" ? { width: 390, height: 844 } : { width: 1280, height: 800 };
  const context = await browser.newContext({ viewport: view, reducedMotion: process.env.REDUCED ? "reduce" : "no-preference" });
  // With no key, the published build falls back to the shared demo AI. Block it: the walk never depends on the AI.
  if (SITE) await context.route(/workers\.dev/, (r) => r.abort());
  // Remember which sounds the pages start playing, so the walk can tell whether Chip spoke.
  await context.addInitScript(() => {
    const play = HTMLMediaElement.prototype.play;
    HTMLMediaElement.prototype.play = function () { (window.played = window.played || []).push(this.src); return play.call(this); };
  });
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
