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

const STEPS = { boot, story };

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
