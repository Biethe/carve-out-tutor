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

function noPaste() {
  $("save-state").textContent = "No pasting here. Type it out!";
}

// Light formatting for tutor replies: `code`, **bold**, line breaks. Everything else is escaped.
function formatReply(text) {
  return escapeHtml(text)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/^\s*[-*] /gm, "• ")
    .replace(/\n+/g, "<br>");
}

// ---- Tutor window --------------------------------------------------------------
// "hint": while coding, each hint or question replaces the last one.
// "check": after passing, the one question about this function and the replies to it.
// "done": the question is answered; questions still welcome, one at a time.
// Closing the window clears it.
let mode = "hint", check = null;

function setMode(newMode) {
  mode = newMode;
  $("messages").innerHTML = "";
  $("tutor-mode").textContent = { hint: "Hints & questions", check: "One question", done: "Questions" }[newMode];
  $("explain").hidden = newMode !== "check";
  $("chat-input").placeholder = newMode === "check"
    ? "Answer in your own words…"
    : "Ask about a library, a method, or a concept…";
  if (newMode === "check") addMessage(`Nice, it works! One quick question: <strong>${escapeHtml(check.question)}</strong>`);
}

function addMessage(html, cls = "tutor-msg") {
  const el = document.createElement("p");
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
  if (res.done) {
    check.done = true;
    mode = "done";
    $("tutor-mode").textContent = "Questions";
    $("explain").hidden = true;
    $("chat-input").placeholder = "Ask about a library, a method, or a concept…";
  }
};

const fab = $("tutor-fab"), win = $("tutor-win");

function placeWindow() {
  // Open beside the button on whichever side has room. The window is anchored on the button's side,
  // so when replies make it taller it grows away from the button instead of over it.
  const b = fab.getBoundingClientRect(), gap = 10;
  const below = b.top + b.height / 2 < innerHeight / 2, leftSide = b.left + b.width / 2 < innerWidth / 2;
  win.style.top = below ? Math.min(b.bottom + gap, innerHeight - 200) + "px" : "auto";
  win.style.bottom = below ? "auto" : Math.min(innerHeight - b.top + gap, innerHeight - 200) + "px";
  win.style.left = leftSide ? Math.max(8, b.left) + "px" : "auto";
  win.style.right = leftSide ? "auto" : Math.max(8, innerWidth - b.right) + "px";
  win.style.maxHeight = Math.min(520, below ? innerHeight - b.bottom - gap - 8 : b.top - gap - 8) + "px";
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
  setMode(mode);  // clears the window; the question comes back if it's still open
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
  $("map-view").insertAdjacentHTML("beforeend", `<optgroup label="Follow one request">${
    overview.flows.map((f, i) => `<option value="${i}">${escapeHtml(f.name)}</option>`).join("")}</optgroup>`);
  drawDiagram();
}

const CAPTIONS = {
  system: "Each box is a file. Arrows show what travels between them: form fields, function calls with what goes in and what comes back, the session cookie, and the database tables. Your file has the dashed outline.",
  flow: "One request from start to finish, top to bottom: every function it reaches, what it hands over, and what it gets back.",
};
$("map-view").onchange = () => drawDiagram();
$("map-expand").onclick = () => { $("map-dialog").showModal(); drawDiagram($("diagram-big")); };
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
    startOnLoad: false, look: "handDrawn", theme: "base",
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
  $("round").textContent = `Round ${s.round} of ${s.total_rounds} · ${t.piece}`;
  $("step-label").textContent = `Function ${s.step} of ${s.total_steps} · ${t.file}`;
  $("fn-signature").textContent = t.signature;
  $("fn-description").textContent = t.description;
  $("criteria").innerHTML = t.criteria
    .map(c => `<li data-test="${c.test}"><span class="mark">•</span>${escapeHtml(c.text)}</li>`).join("");
  criteriaText = Object.fromEntries(t.criteria.map(c => [c.test, c.text]));
  $("task-calls").innerHTML = t.call_sites.map(c => `<li>${escapeHtml(c)}</li>`).join("");
  $("task-breaks").textContent = t.breaks;
  $("task-refs").innerHTML = t.references
    .map(r => `<details open><summary><code>${escapeHtml(r.name)}</code> in ${escapeHtml(r.file)}</summary><pre>${escapeHtml(r.code)}</pre></details>`).join("");
  $("next").textContent = s.step < s.total_steps ? "Next function →" : "Next piece →";
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
      `<p class="done-note">That's every function. The login and the cart are your code now. Click <strong>Run project</strong> to see your store working end to end.</p>`);
  } else {
    $("next").hidden = false;
  }
}

$("next").onclick = async () => {
  $("next").disabled = true;
  await api("POST", "api/next");
  location.reload();
};

// ---- Clean: after passing, short hints toward a smaller, cleaner version -------
// The editor unlocks so they can try it; a cleaner version only replaces theirs if it passes too.
let cleaning = false;

$("clean").onclick = async () => {
  openTutor();
  startExchange();
  $("clean").disabled = true;
  const { el, res } = await askTutor("api/clean", {});
  $("clean").disabled = false;
  if (res.error) { el.textContent = res.error; return; }
  if (res.clean) { el.innerHTML = "Already clean. Nothing to cut here."; return; }
  el.innerHTML = res.hints.map(h => "• " + formatReply(h)).join("<br>");
  if (res.code) {
    const show = document.createElement("button");
    show.className = "btn small secondary";
    show.textContent = "Show a cleaner version";
    show.onclick = () => show.replaceWith(Object.assign(document.createElement("pre"), { className: "clean-code", textContent: res.code }));
    el.after(show);
  }
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
