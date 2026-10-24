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

function addMessage(html, cls = "tutor-msg") {
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
  $("hint").disabled = true;
  const { el, res } = await askTutor("/api/hint", { code: editor.getValue(), after_submit: afterSubmit });
  el.innerHTML = formatReply(res.hint);
  $("hint").disabled = false;
}

function setOwnership(pct) {
  $("own-pct").textContent = pct + "%";
  $("own-fill").style.width = pct + "%";
}

function showTask(task, round) {
  $("round").textContent = `Round ${round} · ${task.title}`;
  $("task-title").textContent = task.title;
  $("task-summary").textContent = task.summary;
  $("task-file").textContent = task.file;
  $("task-functions").innerHTML = task.functions
    .map(f => `<li><code>${escapeHtml(f.signature)}</code><p>${escapeHtml(f.description)}</p></li>`).join("");
  $("task-calls").innerHTML = task.call_sites.map(c => `<li>${escapeHtml(c)}</li>`).join("");
  $("task-breaks").textContent = task.breaks;
  $("task-refs").innerHTML = task.references
    .map(r => `<details><summary><code>${escapeHtml(r.name)}</code> in ${escapeHtml(r.file)}</summary><pre>${escapeHtml(r.code)}</pre></details>`).join("");
}

function showResults(results, passed) {
  if (!results) return;
  const done = results.filter(r => r.passed).length;
  $("results").innerHTML =
    `<p class="summary ${passed ? "pass" : "fail"}">${passed
      ? "All tests passed. Your code is running this part of the store now."
      : `${done} of ${results.length} tests passed.`}</p>` +
    `<ul class="tests">${results.map(r => `<li class="${r.passed ? "pass" : "fail"}">
        <span class="mark">${r.passed ? "✓" : "✗"}</span><span>${escapeHtml(r.name.replace(/^test_/, "").replaceAll("_", " "))}</span>
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
  if (res.passed) lockIfPassed("passed");
  else getHint(true);
};

$("hint").onclick = () => getHint(false);

$("run").onclick = () => runProject($("run-status"));

(async () => {
  const s = await api("GET", "/api/state");
  if (!s.current) { location.href = "/project"; return; }
  showTask(s.task, s.round);
  editor.setValue(s.code);
  loaded = true;
  setOwnership(s.ownership);
  showResults(s.last_results, s.status === "passed");
  lockIfPassed(s.status);
})();
