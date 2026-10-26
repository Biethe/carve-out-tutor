// The workspace: one function's task, the editor, and Chip docked beside them.
let codeFont = null;
try { codeFont = localStorage.getItem("codeFont"); } catch {}
document.documentElement.dataset.codeFont = codeFont || "mono";  // before the editor is made, so it never jumps

const $ = (id) => document.getElementById(id);
const api = (method, url, body) =>
  fetch(url, { method, headers: { "Content-Type": "application/json" }, body: body && JSON.stringify(body) })
    .then(r => r.json()).catch(() => ({ error: "The tutor couldn’t be reached. Try again in a moment." }));  // never a stuck button
const RM = matchMedia("(prefers-reduced-motion: reduce)").matches;

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// Pasting is allowed only while building the tutor on your own machine. The public site always blocks it.
const PASTE_ALLOWED = ["localhost", "127.0.0.1"].includes(location.hostname);

// CodeMirror from the CDN, or the plain textarea if it didn't load (offline).
let editor;
if (window.CodeMirror) {
  editor = CodeMirror.fromTextArea($("editor"), {
    mode: "python", lineNumbers: true, indentUnit: 4, dragDrop: PASTE_ALLOWED,
    extraKeys: { Tab: cm => cm.execCommand(cm.somethingSelected() ? "indentMore" : "insertSoftTab") },
  });
  // Typing only: pasted or dropped text never reaches the editor.
  editor.on("beforeChange", (_, change) => {
    if (!PASTE_ALLOWED && (change.origin === "paste" || change.origin === "drop")) { change.cancel(); noPaste(); }
  });
} else {
  const ta = $("editor");
  if (!PASTE_ALLOWED) for (const ev of ["paste", "drop"]) ta.addEventListener(ev, e => { e.preventDefault(); noPaste(); });
  editor = { getValue: () => ta.value, setValue: v => (ta.value = v), on: (_, fn) => ta.addEventListener("input", fn), setOption() {} };
}

// The editor can take the whole workspace width, for longer code. Esc puts the task card back.
function bigEditor(on) {
  $("w-main").classList.toggle("editor-full", on);
  $("editor-size").setAttribute("aria-pressed", on);
  $("editor-size").title = on ? "Back to normal size (Esc)" : "Make the editor taller";
  $("editor-size").firstElementChild.className = "ph-bold " + (on ? "ph-arrows-in" : "ph-arrows-out");
  editor.refresh?.();  // CodeMirror re-measures after its box changes size
}
// The code font, chosen right on the editor: classic mono (default), handwritten or extra readable. Kept in this browser.
$("code-font").value = document.documentElement.dataset.codeFont;
$("code-font").onchange = () => {
  document.documentElement.dataset.codeFont = $("code-font").value;
  try { localStorage.setItem("codeFont", $("code-font").value); } catch {}
  document.fonts.ready.then(() => editor.refresh?.());  // CodeMirror re-measures once the new font has loaded
};
$("editor-size").onclick = () => bigEditor($("editor-size").getAttribute("aria-pressed") !== "true");
addEventListener("keydown", e => { if (e.key === "Escape" && document.querySelector(".editor-full") && !document.querySelector("dialog[open]")) bigEditor(false); });

function noPaste() {
  $("save-state").textContent = "No pasting here. Type it out.";
}

// Light formatting for Chip's replies: `code`, **bold**, line breaks. Everything else is escaped.
function formatReply(text) {
  // ``` blocks become code blocks; they're set aside first so the line-break rule below can't touch them.
  const blocks = [];
  text = text.replace(/```[\w-]*\n?([\s\S]*?)(```|$)/g, (_, code) => `\u0000${blocks.push(code.trimEnd()) - 1}\u0000`);
  return escapeHtml(text)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/^\s*[-*] /gm, "• ")
    .replace(/\n+/g, "<br>")
    .replace(/\u0000(\d+)\u0000/g, (_, i) => `<pre class="clean-code">${escapeHtml(blocks[i])}</pre>`);
}

// ---- Chip, docked beside the editor -------------------------------------------------
const chip = $("w-chip");

// Chip's latest words: plain text arrives word by word, a formatted reply all at once. A question asked shows above it.
// replyShowing: Chip's panel holds a hint or an answer, so the small talk while you type waits.
let replyShowing = false;
function buddy(content, { html = false, asked = "" } = {}) {
  replyShowing = html;
  $("w-asked").hidden = !asked;
  $("w-asked").textContent = asked ? "You asked: " + asked : "";
  const el = $("w-say");
  if (html) {
    el.innerHTML = content;
    el.classList.remove("fade-in");
    void el.offsetWidth;
    el.classList.add("fade-in");
    Chip.mood(chip, "talk", 1200);
  } else {
    el.classList.remove("fade-in");
    Chip.say(el, content, chip);
  }
  say(el);
  return el;
}

// ---- Voice: talk to Chip, and have its replies read out loud ------------------------
let speakOn = false;
try { speakOn = localStorage.getItem("tutorSpeaks") === "1"; } catch {}

function say(el) {
  if (speakOn && el) Voice.speak((el.querySelector(".clean-points") || el).innerText);
}

function setSpeak(on) {
  speakOn = on;
  try { localStorage.setItem("tutorSpeaks", on ? "1" : "0"); } catch {}
  $("speak-toggle").setAttribute("aria-pressed", on);
  $("speak-toggle").firstElementChild.className = "ph-bold " + (on ? "ph-speaker-high" : "ph-speaker-slash");
  if (!on) Voice.stopSpeaking();
}
$("speak-toggle").onclick = () => setSpeak(!speakOn);
setSpeak(speakOn);

// The mic fills the box as you talk and asks when you pause.
$("tutor-mic").hidden = !Voice.canListen;
$("tutor-mic").onclick = async () => {
  if (Voice.listening) return Voice.stopListening();
  Voice.stopSpeaking();
  $("tutor-mic").setAttribute("aria-pressed", "true");
  const said = await Voice.listen(text => ($("chat-input").value = text));
  $("tutor-mic").setAttribute("aria-pressed", "false");
  if (said) $("ask-form").requestSubmit();
};

// Chip thinks while the AI answers; the button that asked always comes back.
async function askChip(url, body, button) {
  if (button) button.disabled = true;
  chip.classList.add("think");
  const res = await api("POST", url, body).catch(() => ({ error: "The tutor couldn’t be reached. Try again in a moment." }));
  chip.classList.remove("think");
  if (button) button.disabled = false;
  return res;
}

async function getHint(afterSubmit) {
  const res = await askChip("api/hint", { code: editor.getValue(), after_submit: afterSubmit }, $("hint"));
  if (cleaning || passedNow) $("hint").disabled = true;
  buddy(formatReply(res.hint || res.error || ""), { html: true });
}
$("hint").onclick = () => getHint(false);

$("ask-form").onsubmit = async (e) => {
  e.preventDefault();
  const text = $("chat-input").value.trim();
  if (!text) return;
  $("chat-input").value = "";
  const res = await askChip("api/ask", { question: text, code: editor.getValue() }, $("ask"));
  buddy(formatReply(res.answer || res.error || ""), { html: true, asked: text });
};

// ---- The task card: what to write, and the closed sections to read when you want them ----------
let overview = null;

async function loadOverview() {
  if (overview) return;
  overview = await api("GET", "api/overview");
  const render = items => items.map(i => i.dir
    ? `<li class="dir"><details open><summary><i class="ph-bold ph-folder-simple" aria-hidden="true"></i>${escapeHtml(i.name)}/</summary><ul>${render(i.children)}</ul></details></li>`
    : `<li class="${i.path === overview.current ? "you" : ""}"><i class="ph-bold ph-file" aria-hidden="true"></i><code>${escapeHtml(i.name)}</code>` +
      (i.path === overview.current ? ` <span class="tag">you’re here</span>` : "") + `</li>`).join("");
  $("file-tree").innerHTML = `<li class="dir"><details open><summary><i class="ph-bold ph-folder-simple" aria-hidden="true"></i>${escapeHtml(overview.root)}/</summary><ul>${render(overview.tree)}</ul></details></li>`;
  $("map-view").insertAdjacentHTML("beforeend", `<optgroup label="Requests that reach your code">${
    overview.flows.map((f, i) => `<option value="${i}">${escapeHtml(f.name)}</option>`).join("")}</optgroup>`);
  drawDiagram();
}
for (const id of ["files-details", "map-details"]) $(id).addEventListener("toggle", () => { if ($(id).open) loadOverview(); });

const CAPTIONS = {
  system: "Each box is a file, listing the functions other files call: what goes in → what comes back. Your file is highlighted and ★ marks your function. Thick arrows show who calls your code and what it calls, so you can see what your code affects. Click the diagram to see it full size.",
  flow: "One request, read top to bottom: the numbers give the order, from the click to what goes back to the browser. Your file is the shaded column, and the shaded band is the moment your code runs. A framed \"alt\" block shows two paths (if / otherwise); a \"loop\" block repeats, and says when it stops.",
};
$("map-view").onchange = () => drawDiagram();
$("map-expand").onclick = () => { $("map-dialog").showModal(); drawDiagram($("diagram-big")); };
$("diagram").onclick = () => $("map-expand").click();
$("map-close").onclick = () => $("map-dialog").close();

// Mermaid draws in the page's own calm colors.
async function drawDiagram(target = $("diagram")) {
  if (!overview) return;
  const view = $("map-view").value;
  const text = view === "system" ? overview.system : overview.flows[view].diagram;
  $("map-caption").textContent = CAPTIONS[view === "system" ? "system" : "flow"];
  if (!window.mermaid) { target.innerHTML = `<pre>${escapeHtml(text)}</pre>`; return; }
  const css = getComputedStyle(document.documentElement), v = name => css.getPropertyValue(name).trim();
  mermaid.initialize({
    // Clean lines, roomy spacing, and natural size (the box scrolls instead of shrinking the text).
    startOnLoad: false, look: "classic", theme: "base",
    flowchart: { nodeSpacing: 56, rankSpacing: 78, padding: 18, wrappingWidth: 640, useMaxWidth: false },
    sequence: { useMaxWidth: false, messageMargin: 44, boxMargin: 12, noteMargin: 12, mirrorActors: false },
    themeVariables: {
      fontFamily: v("--text"), fontSize: "15px", background: v("--surface"),
      primaryColor: v("--bg"), primaryTextColor: v("--ink"), primaryBorderColor: v("--muted"),
      lineColor: v("--muted"), edgeLabelBackground: v("--surface"), tertiaryColor: v("--surface"),
    },
  });
  const { svg } = await mermaid.render("map-" + Date.now(), text);
  target.innerHTML = svg;
}

let criteriaText = {};

function showTask(s) {
  const t = s.task;
  $("w-crumb").innerHTML = `${escapeHtml(project)} / <b class="mono">${escapeHtml(t.name)}</b>`;
  $("w-step").textContent = `Function ${s.step} of ${s.total_steps}`;
  $("w-name").textContent = t.name;
  $("w-sig").textContent = t.signature;
  $("w-desc").textContent = t.description;
  $("w-file").textContent = t.file;
  $("w-checks").innerHTML = t.criteria
    .map(c => `<li data-test="${escapeHtml(c.test)}" data-state="idle"><span class="ck" aria-hidden="true"></span><span>${escapeHtml(c.text)}</span></li>`).join("");
  criteriaText = Object.fromEntries(t.criteria.map(c => [c.test, c.text]));
  $("w-used").innerHTML = t.call_sites.map(c => `<li>${escapeHtml(c)}</li>`).join("");
  $("w-breaks").textContent = t.breaks;
  $("w-refs").innerHTML = t.references
    .map(r => `<details><summary><code>${escapeHtml(r.name)}</code> in ${escapeHtml(r.file)}</summary><pre>${escapeHtml(r.code)}</pre></details>`).join("")
    || `<p class="muted">Nothing else to read for this one.</p>`;
  document.title = `${t.name} | Carve-Out Tutor`;
}

// Each check gets its result from the test run, by name, one after another.
function tickChecks(results) {
  const byName = Object.fromEntries((results || []).map(r => [r.name, r.passed]));
  const items = [...document.querySelectorAll("#w-checks li")];
  return new Promise(done => {
    if (!items.length) return done();
    items.forEach((li, i) => setTimeout(() => {
      const state = byName[li.dataset.test];
      li.dataset.state = state === undefined ? "idle" : state ? "pass" : "fail";
      if (i === items.length - 1) done();
    }, RM ? 0 : 300 * (i + 1)));
  });
}

function showResults(results, passed) {
  if (!results) { $("results").hidden = true; return; }
  // Focus on this function's checks; other tests only show if this function broke them.
  const all = results.filter(r => !r.passed), mine = all.filter(r => r.name in criteriaText);
  const failing = mine.length ? mine : all;
  $("results").hidden = false;
  $("results").innerHTML =
    `<p class="summary ${passed ? "good" : "bad"}">${passed
      ? `It works. Your function is part of ${escapeHtml(project)} now.`
      : "Not quite yet. Here’s what to look at:"}</p>` +
    (failing.length ? `<ul class="tests">${failing.map(r => `<li>
        <span>${escapeHtml(criteriaText[r.name] || r.name.replace(/^test_/, "").replaceAll("_", " "))}</span>
        ${r.message ? `<pre>${escapeHtml(r.message)}</pre>` : ""}</li>`).join("")}</ul>` : "");
}

// ---- Editor and steps ----------------------------------------------------------
let allDone = false, project = "your project", fnName = "", runs = false, check = null;  // the open project and function
let passedCount = 0, totalCount = 0, passedNow = false, plan = null;

function setOwn(n, total, bump) {
  const own = $("w-own");
  own.querySelector(".own-n").textContent = n;
  own.querySelector(".own-t").textContent = total;
  own.querySelector(".val").style.strokeDashoffset = String(44 - 44 * (total ? n / total : 0));
  if (bump) { own.classList.remove("bump"); void own.offsetWidth; own.classList.add("bump"); }
}

function afterPass() {
  passedNow = true;
  cleaning = false;
  $("submit").disabled = $("hint").disabled = true;
  $("clean").hidden = false;
  $("submit").lastChild.textContent = "Check my code";
  editor.setOption("readOnly", true);
  if (allDone) {
    $("results").hidden = false;
    $("results").insertAdjacentHTML("beforeend",
      `<p class="done-note">That’s every function in your plan. ${runs ? `Open your app to see ${escapeHtml(project)} running on your code, or add` : "Add"} more functions from home.</p>`);
  } else {
    $("next").hidden = false;
  }
}

// After a passing check (not a Clean retry). The guided extras hook in here.
function onPass(res) {
  $("w-editor").classList.add("ok");
  Chip.mood(chip, "happy");
  Chip.mood(chip, "jump", 750);
  buddy(`It works. ${fnName} now runs inside ${project}.`);
  $("save-state").textContent = "Saved. This version runs in your app now.";
  passedCount += 1;
  afterPass();
  // The finished function flies up into the "yours" counter, then one question about it.
  fly(fnName, () => {
    setOwn(passedCount, totalCount, true);
    setTimeout(() => openWin(res.shown_claim), RM ? 0 : 380);
  });
}

function fly(name, done) {
  const own = $("w-own");
  if (RM || !own.getBoundingClientRect().width) return done();
  const a = $("w-editor").getBoundingClientRect(), b = own.getBoundingClientRect();
  const el = document.createElement("div");
  el.className = "flyer";
  el.innerHTML = `<span class="fc"><i class="ph-bold ph-check" aria-hidden="true"></i></span><span class="mono">${escapeHtml(name)}</span>`;
  document.body.append(el);
  const w = el.offsetWidth, h = el.offsetHeight;
  const x0 = a.left + a.width / 2 - w / 2, y0 = a.top + Math.min(a.height / 2, 260) - h / 2;
  const x1 = b.left + b.width / 2 - w / 2, y1 = b.top + b.height / 2 - h / 2;
  el.animate([
    { transform: `translate(${x0}px, ${y0 + 24}px) scale(.8)`, opacity: 0 },
    { transform: `translate(${x0}px, ${y0}px) scale(1.06)`, opacity: 1, offset: 0.25 },
    { transform: `translate(${x0}px, ${y0 - 8}px) scale(1)`, opacity: 1, offset: 0.45 },
    { transform: `translate(${x1}px, ${y1}px) scale(.35)`, opacity: 0.3 },
  ], { duration: 1500, easing: "cubic-bezier(.45, 0, .25, 1)", fill: "forwards" }).onfinish = () => { el.remove(); done(); };
}

// ---- The win: the function is yours, then one question, graded by the AI as before ----------------
const win = $("win");

function nextName() {  // what api/next opens: the plan's first function to write that hasn't passed, in Chip's order
  const f = plan.functions.filter(f => f.mark === "write" && f.rank !== null && !f.blocked && f.status !== "passed" && f.name !== fnName)
    .sort((a, b) => a.rank - b.rank)[0];
  return f && f.name;
}

function openWin(claim) {
  $("win-title").textContent = `${fnName} is yours.`;
  $("win-sub").textContent = `${passedCount} of ${totalCount} functions in ${project} run your code now.` + (allDone ? " That’s every function in your plan." : "");
  $("win-note").hidden = !claim;
  $("win-note").textContent = claim ? `Spot check passed: you’ve shown “${claim}”. It’s marked in your profile.` : "";
  const next = !allDone && nextName();
  $("win-next").hidden = !next;
  $("win-next").innerHTML = `Next: ${escapeHtml(next || "")} <i class="ph-bold ph-arrow-right go" aria-hidden="true"></i>`;
  $("win-run").hidden = !(allDone && runs);
  $("win-reply").innerHTML = "";
  $("win-answer").value = "";
  $("win-label").textContent = "One question before you move on.";
  const asking = check?.question && !check.done;
  $("win-q").textContent = check?.question || "";
  $("win-qa").hidden = !asking;
  $("win-after").hidden = asking;
  $("answer-it").hidden = true;
  win.showModal();
  (asking ? $("win-answer") : $("win-next").hidden ? $("win-home") : $("win-next")).focus();
}

let skipped = false;
function afterQuestion() {
  skipped = true;
  $("win-qa").hidden = true;
  $("win-after").hidden = false;
  ($("win-next").hidden ? $("win-home") : $("win-next")).focus();
}

$("win-qa").onsubmit = async (e) => {
  e.preventDefault();
  const text = $("win-answer").value.trim();
  if (!text) return;
  $("win-send").disabled = true;
  $("win-reply").textContent = "Checking your answer…";
  const res = await api("POST", "api/explain", { explanation: text }).catch(() => ({ error: "The tutor couldn’t be reached. Try again in a moment." }));
  $("win-send").disabled = false;
  if (res.error) { $("win-reply").textContent = res.error; return; }
  let html = `<strong>${res.score}/10.</strong> `;
  if (res.hint) html += formatReply(res.hint);
  if (res.feedback) html += formatReply(res.feedback);
  if (res.final_explanation) html += `<br><br>Here’s the full answer: ${formatReply(res.final_explanation)}`;
  if (res.extra) html += `<br><br>Good to know: ${formatReply(res.extra)}`;
  $("win-reply").innerHTML = html;
  say($("win-reply"));
  if (res.done) {
    check.done = true;
    $("win-after").hidden = false;
    $("win-answer").disabled = $("win-send").disabled = $("win-skip").disabled = true;
    ($("win-next").hidden ? $("win-home") : $("win-next")).focus();
  } else {
    $("win-answer").value = "";
    $("win-label").textContent = "Try once more, in your own words.";
  }
};
$("win-skip").onclick = afterQuestion;
$("win-mic").hidden = !Voice.canListen;
$("win-mic").onclick = async () => {
  if (Voice.listening) return Voice.stopListening();
  $("win-mic").setAttribute("aria-pressed", "true");
  const said = await Voice.listen(text => ($("win-answer").value = text));
  $("win-mic").setAttribute("aria-pressed", "false");
  if (said) $("win-qa").requestSubmit();
};
$("win-next").onclick = () => { win.close(); $("next").click(); };
$("win-run").onclick = () => runProject($("run-status"));
$("win-home").onclick = () => (location.href = "project");
// Closing the sheet (Esc) leaves an unanswered question waiting in Chip's panel.
win.addEventListener("close", () => {
  if (check?.question && !check.done && !skipped) {
    buddy(`${fnName} is yours. One question about it is waiting.`);
    $("answer-it").hidden = false;
  }
});
$("answer-it").onclick = () => openWin();

// ---- A short tour of the workspace, the first time only ----------------------------------
const TOUR = [
  ["w-task", "Start here. This is what your function has to do, and the checks it has to pass."],
  ["w-editor", "Then write your code in here. Just this one function."],
  ["submit", "When you think it works, press Check my code. I’ll run the tests for you."],
  ["w-buddy", "Stuck? I’m right here. Ask me anything, or ask for a hint."],
];
let stop = -1, spotted = null;

function startTour() {
  try { if (localStorage.getItem("seenTour") === "1") return; localStorage.setItem("seenTour", "1"); } catch {}
  stop = -1;
  $("shield").hidden = $("coach").hidden = false;
  tourNext();
}
function placeCoach() {
  if (!spotted) return;
  const card = $("coach"), r = spotted.getBoundingClientRect(), cw = card.offsetWidth, ch = card.offsetHeight, m = 16;
  let x, y;
  if (r.right + 20 + cw < innerWidth - m) { x = r.right + 20; y = r.top + 12; }
  else if (r.left - 20 - cw > m) { x = r.left - 20 - cw; y = r.top + 12; }
  else if (r.bottom + 16 + ch < innerHeight - m) { x = r.left + (r.width - cw) / 2; y = r.bottom + 16; }
  else if (r.top - 16 - ch > m) { x = r.left + (r.width - cw) / 2; y = r.top - 16 - ch; }
  else { x = (innerWidth - cw) / 2; y = innerHeight - ch - 40; }
  x = Math.max(m, Math.min(x, innerWidth - cw - m));
  y = Math.max(m, Math.min(y, innerHeight - ch - m));
  card.style.transform = `translate(${Math.round(x)}px, ${Math.round(y)}px)`;
}
function tourNext() {
  if (spotted) spotted.classList.remove("spot");
  stop += 1;
  if (stop >= TOUR.length) return endTour();
  const [id, text] = TOUR[stop];
  spotted = $(id);
  spotted.scrollIntoView({ block: spotted.offsetHeight > innerHeight * 0.6 ? "start" : "nearest" });
  spotted.classList.add("spot");
  $("coach-count").textContent = `${stop + 1} of ${TOUR.length}`;
  $("coach-next").textContent = stop === TOUR.length - 1 ? "Got it" : "Next";
  Chip.say($("coach-say"), text, $("coach-chip"));
  placeCoach();
  Chip.lookAt($("coach-chip"), spotted);
  $("coach-next").focus({ preventScroll: true });
}
function endTour() {
  if (spotted) spotted.classList.remove("spot");
  spotted = null;
  $("shield").hidden = $("coach").hidden = true;
  buddy("Your turn. Take your time, I’m right here.");
  editor.focus?.();
}
$("coach-next").onclick = tourNext;
$("coach-skip").onclick = endTour;
addEventListener("keydown", e => { if (e.key === "Escape" && !$("coach").hidden) endTour(); });
addEventListener("resize", placeCoach);

// ---- Chip watches you type, and says a little once in a while --------------------------
const said = new Set();
let idle = 0, lookBack = 0;
function sayOnce(key, text) { if (!said.has(key) && !replyShowing) { said.add(key); buddy(text); } }
function armIdle() {
  clearTimeout(idle);
  idle = setTimeout(() => {
    if (!passedNow && /NotImplementedError/.test(editor.getValue())) sayOnce("stuck", "Stuck? Press Get a hint and I’ll nudge you.");
  }, 25000);
}
editor.on("change", () => {
  if (!loaded || passedNow || cleaning) return;
  Chip.lookAt(chip, $("w-editor"));
  clearTimeout(lookBack);
  lookBack = setTimeout(() => Chip.lookAt(chip, null), 1600);
  armIdle();
  const code = editor.getValue();
  if (!said.has("first")) return sayOnce("first", "Nice start. Take your time.");
  if (/\breturn\b/.test(code) && !/NotImplementedError/.test(code)) sayOnce("close", "Looks close. Press Check my code when you’re ready.");
});

$("next").onclick = async () => {
  $("next").disabled = true;
  $("next").firstChild.textContent = "Chip is preparing it… ";  // a function without a hand-made card gets its card and tests written
  const s = await api("POST", "api/next");
  if (s.error) {
    $("next").disabled = false;
    $("next").firstChild.textContent = "Next function ";
    buddy(s.error);
    return;
  }
  location.reload();
};

// ---- Clean: after passing, short hints toward a smaller, cleaner version -------
// The editor unlocks so they can try it; a cleaner version only replaces theirs if it passes too.
let cleaning = false;

$("clean").onclick = async () => {
  const res = await askChip("api/clean", {}, $("clean"));
  if (res.error) { buddy(res.error); return; }
  if (res.clean) { buddy("Already clean. Nothing to cut or fix here."); return; }
  const points = `<ul class="clean-points">${res.hints.map(h => `<li>${formatReply(h)}</li>`).join("")}</ul>`;
  const el = buddy(res.code
    ? `<strong>A cleaner version</strong><pre class="clean-code"></pre><strong>What changed, and why</strong>${points}`
    : `<strong>How to make it cleaner</strong>${points}`, { html: true });
  if (res.code) el.querySelector(".clean-code").textContent = res.code;
  cleaning = true;
  editor.setOption("readOnly", false);
  $("submit").disabled = false;
  $("submit").lastChild.textContent = "Check the cleaner version";
  $("save-state").textContent = "Try a cleaner version";
};

// Autosave a moment after typing stops.
let saveTimer, loaded = false;
editor.on("change", () => {
  if (!loaded) return;
  if (cleaning) { $("save-state").textContent = "Check to keep this version"; return; }
  if (passedNow) return;
  $("save-state").textContent = "Editing…";
  clearTimeout(saveTimer);
  saveTimer = setTimeout(async () => {
    await api("PUT", "api/code", { code: editor.getValue() });
    $("save-state").textContent = "Saved";
  }, 1500);
});

$("submit").onclick = async () => {
  bigEditor(false);  // so the checks are visible
  clearTimeout(saveTimer);
  $("submit").disabled = $("hint").disabled = true;
  $("w-editor").classList.remove("bad");
  document.querySelectorAll("#w-checks li").forEach(li => (li.dataset.state = "run"));
  Chip.mood(chip, "busy");
  buddy("Running the tests on your code…");
  const res = await api("POST", "api/submit", { code: editor.getValue() }).catch(() => ({ error: "The tests couldn’t run. Try again in a moment." }));
  chip.classList.remove("busy");
  if (res.error) {
    document.querySelectorAll("#w-checks li").forEach(li => (li.dataset.state = "idle"));
    $("results").hidden = false;
    $("results").innerHTML = `<p class="summary bad">${escapeHtml(res.error)}</p>`;
    $("submit").disabled = $("hint").disabled = false;
    return;
  }
  await tickChecks(res.results);
  showResults(res.results, res.passed);
  if (cleaning) {
    if (res.passed) { afterPass(); buddy("Cleaner, and still yours."); $("save-state").textContent = "Cleaner, and still yours."; }
    else {
      $("results").insertAdjacentHTML("beforeend", `<p class="muted small">Your earlier passing version is still the one that runs.</p>`);
      $("submit").disabled = false;
    }
    return;
  }
  if (res.passed) {
    allDone = res.all_done;
    onPass(res);
    return;
  }
  $("w-editor").classList.add("bad");
  setTimeout(() => $("w-editor").classList.remove("bad"), 800);
  buddy("Not yet. Here’s what to look at.");
  $("submit").disabled = $("hint").disabled = false;
  getHint(true);
};

$("run").onclick = () => runProject($("run-status"));

(async () => {
  const [s, p] = await Promise.all([api("GET", "api/state"), api("GET", "api/plan")]);
  if (!s.current) { location.href = "project"; return; }
  plan = p;
  project = s.project;
  fnName = s.task.name;
  runs = s.runs;
  $("run").hidden = !runs;  // a tests-only project has nothing to run
  check = s.check;
  allDone = s.all_done;
  passedCount = p.functions.filter(f => f.status === "passed").length;
  totalCount = p.functions.length;
  setOwn(passedCount, totalCount, false);
  $("w-own").title = `You wrote ${s.ownership}% of the code, by lines.`;
  showTask(s);
  editor.setValue(s.code);
  loaded = true;
  if (s.last_results) {
    const byName = Object.fromEntries(s.last_results.map(r => [r.name, r.passed]));
    document.querySelectorAll("#w-checks li").forEach(li => {
      const state = byName[li.dataset.test];
      if (state !== undefined) li.dataset.state = state ? "pass" : "fail";
    });
  }
  showResults(s.last_results, s.status === "passed");
  if (s.status === "passed") {
    afterPass();
    const waiting = check?.question && !check.done;
    buddy(`${fnName} is yours.` + (waiting ? " One question about it is waiting." : ""));
    $("answer-it").hidden = !waiting;
    $("save-state").textContent = "This function is yours now.";
  } else {
    setTimeout(() => buddy(`Your turn. Write ${fnName} in the editor. I’ll be right here.`), RM ? 0 : 450);
    armIdle();
    setTimeout(startTour, RM ? 50 : 950);
  }
})();
