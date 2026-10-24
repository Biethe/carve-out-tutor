// Opens the tab right away (inside the click, so popup blockers allow it), then
// points it at the store once the tutor has (re)started it.
async function runProject(statusEl) {
  const tab = window.open("", "carve-store");
  if (tab) tab.document.body.innerHTML = "<p style='font:16px system-ui;padding:2rem'>Starting the store…</p>";
  statusEl.textContent = "Starting the store…";
  statusEl.className = "status";
  const res = await fetch("/api/run", { method: "POST" }).then(r => r.json());
  if (res.url) {
    statusEl.textContent = "The store is running in the other tab.";
    if (tab) tab.location = res.url; else window.open(res.url, "carve-store");
  } else {
    statusEl.textContent = res.error + (res.output ? "\n" + res.output : "");
    statusEl.className = "status error";
    if (tab) tab.close();
  }
}
