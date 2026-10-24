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
  if (res.passed) {
    allDone = res.all_done;
    lockIfPassed("passed");
    openCheck({ done: false, best_score: null });
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
})();
