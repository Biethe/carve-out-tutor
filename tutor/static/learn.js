const $ = (id) => document.getElementById(id);
const api = (method, url, body) =>
  fetch(url, { method, headers: { "Content-Type": "application/json" }, body: body && JSON.stringify(body) }).then(r => r.json());

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

// The editor can take the whole workspace width, for longer code. Esc puts the task panel back.
function bigEditor(on) {
  document.querySelector(".workspace").classList.toggle("editor-full", on);
  $("editor-size").setAttribute("aria-pressed", on);
  $("editor-size").title = on ? "Back to normal size (Esc)" : "Make the editor taller";
  $("editor-size").firstElementChild.className = "ph-bold " + (on ? "ph-arrows-in" : "ph-arrows-out");
  editor.refresh?.();  // CodeMirror re-measures after its box changes size
}
$("editor-size").onclick = () => bigEditor($("editor-size").getAttribute("aria-pressed") !== "true");
addEventListener("keydown", e => { if (e.key === "Escape" && document.querySelector(".editor-full") && !document.querySelector("dialog[open]")) bigEditor(false); });

function noPaste() {
  $("save-state").textContent = "No pasting here. Type it out!";
}

// Light formatting for tutor replies: `code`, **bold**, line breaks. Everything else is escaped.
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

// ---- Tutor window --------------------------------------------------------------
// "hint": while coding, each hint or question replaces the last one.
// "check": after passing, the one question about this function and the replies to it.
// "done": the question is answered; questions still welcome, one at a time.
// "clean": the Clean result, in its own wider view. Closing it goes back to the view before.
// Closing the window clears it.
let mode = "hint", check = null, modeBeforeClean = null;
const fab = $("tutor-fab"), win = $("tutor-win");

function setMode(newMode) {
  mode = newMode;
  $("messages").innerHTML = "";
  win.classList.toggle("wide", newMode === "clean");
  $("tutor-mode").textContent = { hint: "Hints & questions", check: "One question", done: "Questions", clean: "Clean code" }[newMode];
  $("explain").hidden = newMode !== "check";
  $("chat-input").placeholder = newMode === "check"
    ? "Answer in your own words…"
    : "Ask about a library, a method, or a concept…";
  if (newMode === "check") say(addMessage(`Nice, it works! One quick question: <strong>${escapeHtml(check.question)}</strong>`));
}

// ---- Voice: talk to the tutor, and have its replies read out loud --------------------
let speakOn = false;
try { speakOn = localStorage.getItem("tutorSpeaks") === "1"; } catch {}

function say(el) {
  if (speakOn && el) Voice.speak((el.querySelector(".clean-points") || el).innerText);
  return el;
}

function setSpeak(on) {
  speakOn = on;
  try { localStorage.setItem("tutorSpeaks", on ? "1" : "0"); } catch {}
  $("speak-toggle").setAttribute("aria-pressed", on);
  $("speak-toggle").firstElementChild.className = "ph-bold " + (on ? "ph-speaker-high" : "ph-speaker-slash");
  if (on) Voice.warmUp(); else Voice.stopSpeaking();
}
$("speak-toggle").onclick = () => setSpeak(!speakOn);
setSpeak(speakOn);

// The mic fills the box as you talk and sends when you pause: an answer to the question, or a question to the tutor.
$("tutor-mic").hidden = !Voice.canListen;
$("tutor-mic").onclick = async () => {
  if (Voice.listening) return Voice.stopListening();
  Voice.stopSpeaking();
  $("tutor-mic").setAttribute("aria-pressed", "true");
  const said = await Voice.listen(text => ($("chat-input").value = text));
  $("tutor-mic").setAttribute("aria-pressed", "false");
  if (said) (mode === "check" ? $("explain") : $("ask")).click();
};

function addMessage(html, cls = "tutor-msg") {
  const el = document.createElement("div");  // a div, so a code block can sit inside it
  el.className = "msg " + cls;
  el.innerHTML = html;
  $("messages").appendChild(el);
  el.scrollIntoView({ behavior: "smooth", block: "nearest" });
  return el;
}

// Outside the question, every exchange starts from a clean window.
function startExchange() {
  if (mode !== "check") $("messages").innerHTML = "";
}

// Shows "thinking…" while the tutor answers, then replaces it with the reply.
async function askTutor(url, body) {
  const pending = addMessage("Thinking…", "tutor-msg thinking");
  const res = await api("POST", url, body);
  pending.classList.remove("thinking");
  return { el: pending, res };
}

async function getHint(afterSubmit) {
  openTutor();
  startExchange();
  $("hint").disabled = true;
  const { el, res } = await askTutor("api/hint", { code: editor.getValue(), after_submit: afterSubmit });
  el.innerHTML = formatReply(res.hint);
  say(el);
  $("hint").disabled = false;
}

$("ask").onclick = async () => {
  const text = $("chat-input").value.trim();
  if (!text) return;
  startExchange();
  addMessage(escapeHtml(text), "learner-msg");
  $("chat-input").value = "";
  $("ask").disabled = true;
  const { el, res } = await askTutor("api/ask", { question: text, code: editor.getValue() });
  $("ask").disabled = false;
  el.innerHTML = formatReply(res.answer);
  say(el);
};

$("explain").onclick = async () => {
  const text = $("chat-input").value.trim();
  if (!text) return;
  addMessage(escapeHtml(text), "learner-msg");
  $("chat-input").value = "";
  $("explain").disabled = true;
  const { el, res } = await askTutor("api/explain", { explanation: text });
  $("explain").disabled = false;
  if (res.error) { el.textContent = res.error; return; }
  let html = `<strong>${res.score}/10.</strong> `;
  if (res.hint) html += formatReply(res.hint);
  if (res.feedback) html += formatReply(res.feedback);
  if (res.final_explanation) html += `<br><br>Here's the full answer: ${formatReply(res.final_explanation)}`;
  if (res.extra) html += `<br><br><em>Good to know:</em> ${formatReply(res.extra)}`;
  el.innerHTML = html;
  say(el);
  if (res.done) {
    check.done = true;
    mode = "done";
    $("tutor-mode").textContent = "Questions";
    $("explain").hidden = true;
    $("chat-input").placeholder = "Ask about a library, a method, or a concept…";
  }
};

function placeWindow() {
  // Open beside the button on whichever side has room. The window is anchored on the button's side,
  // so when replies make it taller it grows away from the button instead of over it.
  const b = fab.getBoundingClientRect(), gap = 10;
  const below = b.top + b.height / 2 < innerHeight / 2, leftSide = b.left + b.width / 2 < innerWidth / 2;
  win.style.top = below ? Math.min(b.bottom + gap, innerHeight - 200) + "px" : "auto";
  win.style.bottom = below ? "auto" : Math.min(innerHeight - b.top + gap, innerHeight - 200) + "px";
  win.style.left = leftSide ? Math.max(8, b.left) + "px" : "auto";
  win.style.right = leftSide ? "auto" : Math.max(8, innerWidth - b.right) + "px";
  const room = below ? innerHeight - b.bottom - gap - 8 : b.top - gap - 8;
  win.style.maxHeight = Math.max(320, Math.min(win.classList.contains("wide") ? innerHeight * .85 : 520, room)) + "px";
}

function openTutor() {
  if (!win.hidden) return;
  win.hidden = false;
  fab.setAttribute("aria-expanded", "true");
  if (!$("messages").children.length && mode === "hint") {
    addMessage("Stuck? Click <strong>Hint</strong> for a nudge. You can also ask me about a library, a method, or a concept.");
  }
  placeWindow();
  $("chat-input").focus();
}

function closeTutor() {
  win.hidden = true;
  fab.setAttribute("aria-expanded", "false");
  setMode(mode === "clean" ? modeBeforeClean : mode);  // clears the window; the question comes back if it's still open
}

function moveFab(x, y) {
  x = Math.max(8, Math.min(x, innerWidth - fab.offsetWidth - 8));
  y = Math.max(8, Math.min(y, innerHeight - fab.offsetHeight - 8));
  fab.style.left = x + "px";
  fab.style.top = y + "px";
  fab.style.bottom = "auto";
  if (!win.hidden) placeWindow();
}

// A press that moves more than a few pixels is a drag; otherwise it's a click that toggles the window.
let drag = null;
fab.addEventListener("pointerdown", e => {
  const r = fab.getBoundingClientRect();
  drag = { dx: e.clientX - r.left, dy: e.clientY - r.top, x: e.clientX, y: e.clientY, moved: false };
  fab.setPointerCapture(e.pointerId);
});
fab.addEventListener("pointermove", e => {
  if (!drag) return;
  if (Math.abs(e.clientX - drag.x) + Math.abs(e.clientY - drag.y) > 4) drag.moved = true;
  if (drag.moved) moveFab(e.clientX - drag.dx, e.clientY - drag.dy);
});
fab.addEventListener("pointerup", () => {
  if (drag && !drag.moved) (win.hidden ? openTutor : closeTutor)();
  if (drag && drag.moved) {
    try { localStorage.setItem("tutorFab", JSON.stringify([fab.offsetLeft, fab.offsetTop])); } catch {}
  }
  drag = null;
});
fab.addEventListener("keydown", e => {
  if (e.key === "Enter" || e.key === " ") { e.preventDefault(); (win.hidden ? openTutor : closeTutor)(); }
});
$("tutor-close").onclick = closeTutor;
addEventListener("resize", () => { moveFab(fab.offsetLeft, fab.offsetTop); });
try {
  const saved = JSON.parse(localStorage.getItem("tutorFab"));
  if (saved) moveFab(saved[0], saved[1]);
} catch {}

// ---- Task panel ----------------------------------------------------------------
const TABS = ["task", "read", "files", "map"];

function showTab(name) {
  for (const tab of TABS) {
    $("tab-" + tab).hidden = tab !== name;
    $("tab-btn-" + tab).classList.toggle("active", tab === name);
    $("tab-btn-" + tab).setAttribute("aria-selected", tab === name);
  }
  if (name === "files" || name === "map") loadOverview();
}
for (const tab of TABS) $("tab-btn-" + tab).onclick = () => showTab(tab);

// ---- Files and Map tabs: fetched once, the first time either opens -------------
let overview = null;

async function loadOverview() {
  if (overview) return;
  overview = await api("GET", "api/overview");
  const render = items => items.map(i => i.dir
    ? `<li class="dir"><details open><summary><i class="ph-bold ph-folder-simple" aria-hidden="true"></i>${escapeHtml(i.name)}/</summary><ul>${render(i.children)}</ul></details></li>`
    : `<li class="${i.path === overview.current ? "you" : ""}"><i class="ph-bold ph-file" aria-hidden="true"></i><code>${escapeHtml(i.name)}</code>` +
      (i.path === overview.current ? ` <span class="chip">you're here</span>` : "") + `</li>`).join("");
  $("file-tree").innerHTML = `<li class="dir"><details open><summary><i class="ph-bold ph-folder-simple" aria-hidden="true"></i>store/</summary><ul>${render(overview.tree)}</ul></details></li>`;
  $("map-view").insertAdjacentHTML("beforeend", `<optgroup label="Requests that reach your code">${
    overview.flows.map((f, i) => `<option value="${i}">${escapeHtml(f.name)}</option>`).join("")}</optgroup>`);
  drawDiagram();
}

const CAPTIONS = {
  system: "Each box is a file, listing the functions other files call: what goes in → what comes back. Your file is highlighted and ★ marks your function. Thick arrows show who calls your code and what it calls, so you can see what your code affects. Click the diagram to see it full size.",
  flow: "One request, read top to bottom: the numbers give the order, from the click to what goes back to the browser. Your file is the yellow column, and the yellow band is the moment your code runs. A framed \"alt\" block shows two paths (if / otherwise); a \"loop\" block repeats, and says when it stops.",
};
$("map-view").onchange = () => drawDiagram();
$("map-expand").onclick = () => { $("map-dialog").showModal(); drawDiagram($("diagram-big")); };
$("diagram").onclick = () => $("map-expand").click();
$("map-close").onclick = () => $("map-dialog").close();

// Mermaid draws in a hand-drawn style, in the current theme's colors. Redrawn when the theme changes.
async function drawDiagram(target = $("diagram")) {
  if (!overview) return;
  const view = $("map-view").value;
  const text = view === "system" ? overview.system : overview.flows[view].diagram;
  $("map-caption").textContent = CAPTIONS[view === "system" ? "system" : "flow"];
  if (!window.mermaid) { target.innerHTML = `<pre>${escapeHtml(text)}</pre>`; return; }
  const css = getComputedStyle(document.documentElement), v = name => css.getPropertyValue(name).trim();
  mermaid.initialize({
    // Clean lines, roomy spacing, and natural size (the panel scrolls instead of shrinking the text).
    startOnLoad: false, look: "classic", theme: "base",
    flowchart: { nodeSpacing: 56, rankSpacing: 78, padding: 18, wrappingWidth: 640, useMaxWidth: false },
    sequence: { useMaxWidth: false, messageMargin: 44, boxMargin: 12, noteMargin: 12, mirrorActors: false },
    themeVariables: {
      fontFamily: v("--code-hand"), fontSize: "15px", background: v("--surface"),
      primaryColor: v("--surface-2"), primaryTextColor: v("--ink"), primaryBorderColor: v("--ink"),
      lineColor: v("--ink-soft"), edgeLabelBackground: v("--surface"), tertiaryColor: v("--surface"),
    },
  });
  const { svg } = await mermaid.render("map-" + Date.now(), text);
  target.innerHTML = svg;
}
addEventListener("themechange", () => { drawDiagram(); if ($("map-dialog").open) drawDiagram($("diagram-big")); });

let criteriaText = {};

function showTask(s) {
  const t = s.task;
  $("round").textContent = t.piece;
  $("step-label").innerHTML = `Function ${s.step} of ${s.total_steps} in your plan · ${escapeHtml(t.file)} · <a href="project">pick another</a>`;
  $("fn-signature").textContent = t.signature;
  $("fn-description").textContent = t.description;
  $("criteria").innerHTML = t.criteria
    .map(c => `<li data-test="${c.test}"><span class="mark">•</span>${escapeHtml(c.text)}</li>`).join("");
  criteriaText = Object.fromEntries(t.criteria.map(c => [c.test, c.text]));
  $("task-calls").innerHTML = t.call_sites.map(c => `<li>${escapeHtml(c)}</li>`).join("");
  $("task-breaks").textContent = t.breaks;
  $("task-refs").innerHTML = t.references
    .map(r => `<details open><summary><code>${escapeHtml(r.name)}</code> in ${escapeHtml(r.file)}</summary><pre>${escapeHtml(r.code)}</pre></details>`).join("");
  $("next").textContent = "Next function →";
}

// Marks each criterion ✓ or ✗ from the latest test run.
function markCriteria(results) {
  const byName = Object.fromEntries((results || []).map(r => [r.name, r.passed]));
  document.querySelectorAll("#criteria li").forEach(li => {
    const state = byName[li.dataset.test];
    li.className = state === undefined ? "" : state ? "pass" : "fail";
    li.querySelector(".mark").textContent = state === undefined ? "•" : state ? "✓" : "✗";
  });
}

function showResults(results, passed) {
  markCriteria(results);
  if (!results) return;
  // Focus on this function's criteria; other tests only show if this function broke them.
  const all = results.filter(r => !r.passed), mine = all.filter(r => r.name in criteriaText);
  const failing = mine.length ? mine : all;
  $("results").innerHTML =
    `<p class="summary ${passed ? "pass" : "fail"}">${passed
      ? `<i class="ph-bold ph-confetti" aria-hidden="true"></i> It works! Your function is running inside the store now.`
      : `<i class="ph-bold ph-wrench" aria-hidden="true"></i> Not quite yet. Here's what to look at:`}</p>` +
    `<ul class="tests">${failing.map(r => `<li class="fail">
        <span class="mark">✗</span><span>${escapeHtml(criteriaText[r.name] || r.name.replace(/^test_/, "").replaceAll("_", " "))}</span>
        ${r.message ? `<pre>${escapeHtml(r.message)}</pre>` : ""}</li>`).join("")}</ul>`;
}

// ---- Choose any function, any time -------------------------------------------------
// The roadmap is Chip's suggestion; the learner can jump to any function. A half-written one keeps its draft.
async function fillPicker(current) {
  const plan = await api("GET", "api/plan");
  const option = f => `<option value="${f.key}" ${f.key === current ? "selected" : ""}>${
    f.status === "passed" ? "✓" : f.status === "in_progress" ? "✎" : "·"} ${escapeHtml(f.name)}  (${escapeHtml(f.file)})</option>`;
  const roadmap = plan.functions.filter(f => f.mark === "write").sort((a, b) => a.rank - b.rank);
  const others = plan.functions.filter(f => f.mark !== "write");
  $("pick").innerHTML = `<optgroup label="Your roadmap">${roadmap.map(option).join("")}</optgroup>`
    + (others.length ? `<optgroup label="Keep the original (pick one to write it)">${others.map(option).join("")}</optgroup>` : "");
}
$("pick").onchange = async () => {
  $("pick").disabled = true;
  $("save-state").textContent = "Chip is getting it ready…";
  clearTimeout(saveTimer);
  if (!$("submit").disabled) await api("PUT", "api/code", { code: editor.getValue() });  // keep the draft you're leaving
  const s = await api("POST", "api/open", { key: $("pick").value });
  if (s.error) {
    $("pick").disabled = false;
    $("save-state").textContent = "";
    $("results").insertAdjacentHTML("beforeend", `<p class="summary fail">${escapeHtml(s.error)}</p>`);
    return;
  }
  location.reload();
};

// ---- Editor and steps ----------------------------------------------------------
let allDone = false;

function afterPass() {
  cleaning = false;
  $("submit").disabled = $("hint").disabled = true;
  $("clean").hidden = false;
  $("submit").lastChild.textContent = " Submit";
  editor.setOption("readOnly", true);
  $("save-state").textContent = "This function is yours now.";
  if (allDone) {
    $("results").insertAdjacentHTML("beforeend",
      `<p class="done-note">That's every function in your plan. Click <strong>Run project</strong> to see the store running on your code, or add more functions to your plan on the project page.</p>`);
  } else {
    $("next").hidden = false;
  }
}

$("next").onclick = async () => {
  $("next").disabled = true;
  $("next").textContent = "Chip is preparing it…";  // a function without a hand-made card gets its card and tests written
  const s = await api("POST", "api/next");
  if (s.error) {
    $("next").disabled = false;
    $("next").textContent = "Next function →";
    $("results").insertAdjacentHTML("beforeend", `<p class="summary fail">${escapeHtml(s.error)}</p>`);
    return;
  }
  location.reload();
};

// ---- Clean: after passing, short hints toward a smaller, cleaner version -------
// The editor unlocks so they can try it; a cleaner version only replaces theirs if it passes too.
let cleaning = false;

$("clean").onclick = async () => {
  if (mode !== "clean") modeBeforeClean = mode;
  setMode("clean");  // its own view: the question waits until this one is closed
  win.hidden ? openTutor() : placeWindow();
  $("clean").disabled = true;
  const { el, res } = await askTutor("api/clean", {});
  $("clean").disabled = false;
  if (res.error) { el.textContent = res.error; return; }
  if (res.clean) { el.innerHTML = "<strong>Already clean.</strong> Nothing to cut or fix here."; return; }
  const points = `<ul class="clean-points">${res.hints.map(h => `<li>${formatReply(h)}</li>`).join("")}</ul>`;
  el.innerHTML = res.code
    ? `<strong>A cleaner version</strong><pre class="clean-code"></pre><strong>What changed, and why</strong>${points}`
    : `<strong>How to make it cleaner</strong>${points}`;
  if (res.code) el.querySelector(".clean-code").textContent = res.code;
  say(el);
  if (modeBeforeClean === "check") {
    const back = Object.assign(document.createElement("button"), { className: "btn small secondary", textContent: "Back to the question" });
    back.onclick = () => setMode("check");
    el.after(back);
  }
  placeWindow();
  cleaning = true;
  editor.setOption("readOnly", false);
  $("submit").disabled = false;
  $("submit").lastChild.textContent = " Submit cleaner version";
  $("save-state").textContent = "Try a cleaner version";
};

// Autosave a moment after typing stops.
let saveTimer, loaded = false;
editor.on("change", () => {
  if (!loaded) return;
  if (cleaning) { $("save-state").textContent = "Submit to keep this version"; return; }
  $("save-state").textContent = "Editing…";
  clearTimeout(saveTimer);
  saveTimer = setTimeout(async () => {
    await api("PUT", "api/code", { code: editor.getValue() });
    $("save-state").textContent = "Saved";
  }, 1500);
});

$("submit").onclick = async () => {
  bigEditor(false);  // so the results are visible
  clearTimeout(saveTimer);
  $("submit").disabled = true;
  $("results").innerHTML = `<p class="muted">Running the tests…</p>`;
  const res = await api("POST", "api/submit", { code: editor.getValue() });
  $("submit").disabled = false;
  if (res.error) { $("results").innerHTML = `<p class="summary fail">${escapeHtml(res.error)}</p>`; return; }
  showResults(res.results, res.passed);
  setOwnership(res.ownership);
  if (cleaning) {
    if (res.passed) { celebrate(); afterPass(); $("save-state").textContent = "Cleaner, and still yours."; }
    else $("results").insertAdjacentHTML("beforeend", `<p class="muted small">Your earlier passing version is still the one that runs.</p>`);
    return;
  }
  if (res.passed) {
    allDone = res.all_done;
    celebrate();
    afterPass();
    if (res.shown_claim) {
      $("results").insertAdjacentHTML("beforeend",
        `<p class="done-note">★ Spot check passed: you've <strong>shown</strong> "${escapeHtml(res.shown_claim)}". It's marked in your profile.</p>`);
    }
    setMode("check");
    openTutor();
  } else getHint(true);
};

$("hint").onclick = () => getHint(false);

$("run").onclick = () => runProject($("run-status"));

let shownPct = null;

function setOwnership(pct) {
  const el = $("own-pct");
  el.textContent = pct + "%";
  $("own-fill").style.width = pct + "%";
  if (shownPct !== null && pct > shownPct) {  // a little bump when more of the project becomes theirs
    el.classList.remove("bump");
    void el.offsetWidth;
    el.classList.add("bump");
  }
  shownPct = pct;
}

// Confetti from the Submit button when a function passes, in the current theme's colors.
function celebrate() {
  if (!window.confetti) return;
  const css = getComputedStyle(document.documentElement);
  const colors = ["--accent", "--marker", "--pass"].map(v => css.getPropertyValue(v).trim());
  const r = $("submit").getBoundingClientRect();
  confetti({
    particleCount: 90, spread: 75, startVelocity: 38, ticks: 160, scalar: .9, colors,
    origin: { x: (r.left + r.width / 2) / innerWidth, y: r.top / innerHeight },
    disableForReducedMotion: true,
  });
}

(async () => {
  const s = await api("GET", "api/state");
  if (!s.current) { location.href = "project"; return; }
  check = s.check;
  allDone = s.all_done;
  showTask(s);
  fillPicker(`${s.current}.${s.task.name}`);
  editor.setValue(s.code);
  loaded = true;
  setOwnership(s.ownership);
  showResults(s.last_results, s.status === "passed");
  if (s.status === "passed") {
    afterPass();
    setMode(check.done ? "done" : "check");
  } else {
    setMode("hint");
  }
})();
