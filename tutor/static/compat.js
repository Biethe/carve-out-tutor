// Plain words for the compatibility check (tutor/compat.py): can this uploaded project run in the browser?
const Compat = {
  STATUS: { "built in": ["good", "built in"], installable: ["good", "installs here"], "can't run in a browser": ["bad", "can’t run in a browser"], unknown: ["warn", "couldn’t check"] },
  verdict(c) {
    if (!c) return "";
    const bad = c.libraries.filter(l => l.status === "can't run in a browser").map(l => l.name);
    const files = Object.keys(c.blocked).length;
    const machine = c.machine.length ? ` It also uses ${c.machine.join(", ")}, which needs a real computer.` : "";
    if (c.verdict === "full") return "Runs fully in your browser.";
    if (c.verdict === "none") return `Can’t run in a browser: it needs ${bad.join(", ")}. You can still look through its files and how its data flows, and rebuild it in the local tutor.` + machine;
    return (files ? `Partly runs here: ${files} file${files > 1 ? "s" : ""} need${files > 1 ? "" : "s"} ${bad.join(", ")}, which can’t run in a browser. Here those functions are left out of your plan; everything else works.` : "Runs here.") + machine;
  },
  libraries(c) {
    return c && c.libraries.length
      ? `<ul class="libs">${c.libraries.map(l => `<li><code>${l.name.replace(/</g, "&lt;")}</code> <span class="tag ${this.STATUS[l.status][0]}">${this.STATUS[l.status][1]}</span></li>`).join("")}</ul>` : "";
  },
};
