const $ = (id) => document.getElementById(id);
const api = (method, url, body) =>
  fetch(url, { method, headers: { "Content-Type": "application/json" }, body: body && JSON.stringify(body) }).then(r => r.json());

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// CodeMirror from the CDN, or the plain textarea if it didn't load (offline).
let editor;
if (window.CodeMirror) {
  editor = CodeMirror.fromTextArea($("editor"), {
    mode: "python", lineNumbers: true, indentUnit: 4,
    extraKeys: { Tab: cm => cm.execCommand(cm.somethingSelected() ? "indentMore" : "insertSoftTab") },
  });
} else {
  const ta = $("editor");
  editor = { getValue: () => ta.value, setValue: v => (ta.value = v), on: (_, fn) => ta.addEventListener("input", fn), setOption() {} };
}

// Light formatting for tutor replies: `code`, **bold**, line breaks. Everything else is escaped.
function formatReply(text) {
  return escapeHtml(text)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br>");
}

// The tutor window shows one thing at a time: in "hint" mode only the latest hint,
// in "check" mode the explanation exchange (and Ask answers) for this piece.
let mode = null;

function setMode(newMode) {
  if (newMode === mode) return;
  mode = newMode;
  $("messages").innerHTML = "";
  $("tutor-mode").textContent = newMode === "hint" ? "Hints" : "Explain your code";
}

function addMessage(html, cls = "tutor-msg") {
  if (mode === "hint") $("messages").innerHTML = "";
  const el = document.createElement("p");
  el.className = "msg " + cls;
  el.innerHTML = html;
  $("messages").appendChild(el);
  el.scrollIntoView({ behavior: "smooth", block: "nearest" });
  return el;
}

// Shows "thinking…" while the tutor answers, then replaces it with the reply.
async function askTutor(url, body) {
  const pending = addMessage("Thinking…", "tutor-msg thinking");
  const res = await api("POST", url, body);
  pending.classList.remove("thinking");
  return { el: pending, res };
}

async function getHint(afterSubmit) {
  setMode("hint");
  openTutor();
  $("hint").disabled = true;
  const { el, res } = await askTutor("/api/hint", { code: editor.getValue(), after_submit: afterSubmit });
  el.innerHTML = formatReply(res.hint);
  $("hint").disabled = false;
}

// The understanding check: shown once the tests pass. Ask stays available after it's done.
let allDone = false;

function showNext() {
  if (allDone) {
    addMessage("That's every piece. The login and the cart are both your code now. Click <strong>Run project</strong> to see your store working end to end.");
  } else {
    $("next").hidden = false;
  }
}

$("next").onclick = async () => {
  $("next").disabled = true;
  await api("POST", "/api/round/start");
  location.reload();
};

function openCheck(check) {
  setMode("check");
  $("chat").hidden = false;
  if (check.done) {
    $("explain").hidden = true;
    $("chat-input").placeholder = "Ask the tutor anything about this piece…";
    addMessage(`Understanding check complete${check.best_score !== null ? ` (best score ${check.best_score}/10)` : ""}. You can still ask me questions.`);
  } else {
    addMessage("Nice work, all tests pass! Now tell me in your own words: what does your code do, and why does it work that way?");
  }
  showNext();
}

$("explain").onclick = async () => {
  const text = $("chat-input").value.trim();
  if (!text) return;
  addMessage(escapeHtml(text), "learner-msg");
  $("chat-input").value = "";
  $("explain").disabled = true;
  const { el, res } = await askTutor("/api/explain", { explanation: text });
  $("explain").disabled = false;
  if (res.error) { el.textContent = res.error; return; }
  let html = `<strong>Score: ${res.score}/10.</strong> `;
  if (res.feedback) html += formatReply(res.feedback) + " ";
  if (res.hint) html += `<br><br>${formatReply(res.hint)} Try explaining again.`;
  if (res.final_explanation) html += `<br><br>You got the implementation right. To be more precise: ${formatReply(res.final_explanation)}`;
  if (res.extra) html += `<br><br><em>Good to know:</em> ${formatReply(res.extra)}`;
  el.innerHTML = html;
  if (res.done) {
    $("explain").hidden = true;
    $("chat-input").placeholder = "Ask the tutor anything about this piece…";
  }
};

$("ask").onclick = async () => {
  const text = $("chat-input").value.trim();
  if (!text) return;
  addMessage(escapeHtml(text), "learner-msg");
  $("chat-input").value = "";
  $("ask").disabled = true;
  const { el, res } = await askTutor("/api/ask", { question: text });
  $("ask").disabled = false;
  el.innerHTML = formatReply(res.answer);
};

const fab = $("tutor-fab"), win = $("tutor-win");

function placeWindow() {
  // Open the window beside the button, on whichever side has room, kept inside the screen.
  const b = fab.getBoundingClientRect(), w = win.offsetWidth, h = win.offsetHeight, gap = 10;
  let left = b.left + b.width / 2 < innerWidth / 2 ? b.left : b.right - w;
  let top = b.top + b.height / 2 < innerHeight / 2 ? b.bottom + gap : b.top - h - gap;
  win.style.left = Math.max(8, Math.min(left, innerWidth - w - 8)) + "px";
  win.style.top = Math.max(8, Math.min(top, innerHeight - h - 8)) + "px";
}

function openTutor() {
  win.hidden = false;
  fab.setAttribute("aria-expanded", "true");
  if (!$("messages").children.length && mode === "hint") {
    addMessage("Stuck? Click <strong>Hint</strong> and I'll nudge you, but I won't give you the answer.");
  }
  placeWindow();
}

function closeTutor() {
  win.hidden = true;
  fab.setAttribute("aria-expanded", "false");
}

function moveFab(x, y) {
  x = Math.max(8, Math.min(x, innerWidth - fab.offsetWidth - 8));
  y = Math.max(8, Math.min(y, innerHeight - fab.offsetHeight - 8));
  fab.style.left = x + "px";
  fab.style.top = y + "px";
  fab.style.right = fab.style.bottom = "auto";
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

function setOwnership(pct) {
  $("own-pct").textContent = pct + "%";
  $("own-fill").style.width = pct + "%";
}

function showTask(task, round, totalRounds) {
  $("round").textContent = `Round ${round} of ${totalRounds} · ${task.title}`;
  $("task-title").textContent = task.title;
  $("task-summary").textContent = task.summary;
  $("task-file").textContent = task.file;
  $("task-functions").innerHTML = task.functions
    .map(f => `<li><code>${escapeHtml(f.signature)}</code><p>${escapeHtml(f.description)}</p>
      <p class="criteria-title">To pass, it must:</p>
      <ul class="criteria">${f.criteria.map(c => `<li data-test="${c.test}"><span class="mark">•</span>${escapeHtml(c.text)}</li>`).join("")}</ul></li>`).join("");
  criteriaText = Object.fromEntries(task.functions.flatMap(f => f.criteria.map(c => [c.test, c.text])));
  $("task-calls").innerHTML = task.call_sites.map(c => `<li>${escapeHtml(c)}</li>`).join("");
  $("task-breaks").textContent = task.breaks;
  $("task-refs").innerHTML = task.references
    .map(r => `<details><summary><code>${escapeHtml(r.name)}</code> in ${escapeHtml(r.file)}</summary><pre>${escapeHtml(r.code)}</pre></details>`).join("");
}

let criteriaText = {};

// Marks each criterion in the task ✓ or ✗ from the latest test run.
function markCriteria(results) {
  const byName = Object.fromEntries((results || []).map(r => [r.name, r.passed]));
  document.querySelectorAll(".criteria li").forEach(li => {
    const state = byName[li.dataset.test];
    li.className = state === undefined ? "" : state ? "pass" : "fail";
    li.querySelector(".mark").textContent = state === undefined ? "•" : state ? "✓" : "✗";
  });
}

function showResults(results, passed) {
  markCriteria(results);
  if (!results) return;
  const done = results.filter(r => r.passed).length;
  $("results").innerHTML =
    `<p class="summary ${passed ? "pass" : "fail"}">${passed
      ? "All tests passed. Your code is running this part of the store now."
      : `${done} of ${results.length} tests passed. What failed:`}</p>` +
    `<ul class="tests">${results.filter(r => !r.passed).map(r => `<li class="fail">
        <span class="mark">✗</span><span>${escapeHtml(criteriaText[r.name] || r.name.replace(/^test_/, "").replaceAll("_", " "))}</span>
        ${r.message ? `<pre>${escapeHtml(r.message)}</pre>` : ""}</li>`).join("")}</ul>`;
}

function lockIfPassed(status) {
  const locked = status === "passed";
  $("submit").disabled = locked;
  $("hint").disabled = locked;
  editor.setOption("readOnly", locked);
  if (locked) $("save-state").textContent = "This piece is yours now.";
}

// Autosave a moment after typing stops.
let saveTimer, loaded = false;
editor.on("change", () => {
  if (!loaded) return;
  $("save-state").textContent = "Editing…";
  clearTimeout(saveTimer);
  saveTimer = setTimeout(async () => {
    await api("PUT", "/api/code", { code: editor.getValue() });
    $("save-state").textContent = "Saved";
  }, 1500);
});

$("submit").onclick = async () => {
  clearTimeout(saveTimer);
  $("submit").disabled = true;
  $("results").innerHTML = `<p class="muted">Running the tests…</p>`;
  const res = await api("POST", "/api/submit", { code: editor.getValue() });
  $("submit").disabled = false;
  if (res.error) { $("results").innerHTML = `<p class="summary fail">${escapeHtml(res.error)}</p>`; return; }
  showResults(res.results, res.passed);
  setOwnership(res.ownership);
  if (res.passed) {
    allDone = res.all_done;
    lockIfPassed("passed");
    openCheck({ done: false, best_score: null });
    openTutor();
  } else getHint(true);
};

$("hint").onclick = () => getHint(false);

$("run").onclick = () => runProject($("run-status"));

(async () => {
  const s = await api("GET", "/api/state");
  if (!s.current) { location.href = "/project"; return; }
  showTask(s.task, s.round, s.total_rounds);
  editor.setValue(s.code);
  loaded = true;
  setOwnership(s.ownership);
  showResults(s.last_results, s.status === "passed");
  lockIfPassed(s.status);
  allDone = s.all_done;
  if (s.status === "passed") openCheck(s.check);
  else setMode("hint");
})();
