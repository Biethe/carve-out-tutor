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
