// Chip, the tutor's mascot: a little microchip whose eyes follow you. Shared by every page.
const Chip = (() => {
  const RM = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const esc = (t) => String(t).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  // The paint every Chip shares: a soft sage-teal-blue body, a shine, a dark screen, silver pins. Added once per page.
  const DEFS = `<svg width="0" height="0" style="position: absolute" aria-hidden="true" focusable="false"><defs>
    <linearGradient id="chipBody" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#A6C99A"></stop><stop offset=".5" stop-color="#74B2A7"></stop><stop offset="1" stop-color="#86A6CC"></stop></linearGradient>
    <radialGradient id="chipShine" cx=".3" cy=".2" r=".75"><stop offset="0" stop-color="#FFFFFF" stop-opacity=".45"></stop><stop offset=".45" stop-color="#FFFFFF" stop-opacity=".12"></stop><stop offset="1" stop-color="#FFFFFF" stop-opacity="0"></stop></radialGradient>
    <linearGradient id="chipScreen" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#22394A"></stop><stop offset="1" stop-color="#15252F"></stop></linearGradient>
    <linearGradient id="chipPin" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#EEF3F7"></stop><stop offset="1" stop-color="#9DB0C3"></stop></linearGradient>
  </defs></svg>`;
  const SVG = `<svg viewBox="0 0 120 120" aria-hidden="true" focusable="false">
    <g fill="url(#chipPin)">
      <rect class="pin l" x="2" y="40" width="16" height="9" rx="4.5"></rect><rect class="pin l" x="2" y="57" width="16" height="9" rx="4.5"></rect><rect class="pin l" x="2" y="74" width="16" height="9" rx="4.5"></rect>
      <rect class="pin r" x="102" y="40" width="16" height="9" rx="4.5"></rect><rect class="pin r" x="102" y="57" width="16" height="9" rx="4.5"></rect><rect class="pin r" x="102" y="74" width="16" height="9" rx="4.5"></rect>
      <rect class="pin b" x="40" y="100" width="9" height="16" rx="4.5"></rect><rect class="pin b" x="71" y="100" width="9" height="16" rx="4.5"></rect>
    </g>
    <rect x="13" y="12" width="94" height="94" rx="30" fill="url(#chipBody)"></rect>
    <rect x="13" y="12" width="94" height="94" rx="30" fill="url(#chipShine)"></rect>
    <path d="M24 23 h10 v5 M86 96 h-10 v-4" fill="none" stroke="#FFFFFF" stroke-opacity=".6" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"></path>
    <circle class="led" cx="95" cy="25" r="4.6"></circle>
    <rect x="26" y="30" width="68" height="56" rx="18" fill="url(#chipScreen)"></rect>
    <rect x="26" y="30" width="68" height="56" rx="18" fill="none" stroke="#FFFFFF" stroke-opacity=".18" stroke-width="1.5"></rect>
    <g class="look">
      <g class="eyes"><rect class="eye" x="41" y="46" width="12" height="17" rx="6"></rect><rect class="eye" x="67" y="46" width="12" height="17" rx="6"></rect></g>
      <path class="smile" d="M40 58 q6.5 -9 13 0 M67 58 q6.5 -9 13 0" fill="none" stroke-width="4" stroke-linecap="round"></path>
    </g>
    <rect class="mouth" x="54" y="71" width="12" height="4" rx="2"></rect>
    <ellipse class="cheek" cx="31" cy="93" rx="6" ry="3.2"></ellipse><ellipse class="cheek" cx="89" cy="93" rx="6" ry="3.2"></ellipse>
  </svg>`;

  function mount(root = document) {
    if (!document.getElementById("chipBody")) document.body.insertAdjacentHTML("afterbegin", DEFS);
    root.querySelectorAll("[data-chip]").forEach((el) => { if (!el.firstElementChild) el.innerHTML = SVG; });
    look();
  }

  function mood(chip, name, ms) {
    if (!chip) return;
    chip.classList.add(name);
    clearTimeout(chip[name + "Timer"]);
    if (ms) chip[name + "Timer"] = setTimeout(() => chip.classList.remove(name), ms);
  }

  // Chip's words arrive one at a time; Chip's mouth moves while they do.
  function say(el, text, chip) {
    if (!el) return;
    const words = String(text).split(" ");
    el.innerHTML = words.map((w, i) => `<span class="w" style="animation-delay:${RM ? 0 : i * 55}ms">${esc(w)}</span>`).join(" ");
    if (chip && !RM) mood(chip, "talk", words.length * 55 + 450);
  }

  // The eyes follow your pointer, or whatever you're about to press.
  let px = innerWidth / 2, py = innerHeight * 0.4, moved = 0, frame = 0;
  function lookAll() {
    frame = 0;
    for (const c of document.querySelectorAll(".chip")) {
      const r = c.getBoundingClientRect();
      if (!r.width) continue;
      const t = c.target || { x: px, y: py };
      const dx = t.x - (r.left + r.width / 2), dy = t.y - (r.top + r.height / 2);
      const d = Math.hypot(dx, dy) || 1, m = 4.5 * Math.min(1, d / 160);
      c.style.setProperty("--px", `${(dx / d * m).toFixed(2)}px`);
      c.style.setProperty("--py", `${(dy / d * m).toFixed(2)}px`);
    }
  }
  function look() { if (!frame) frame = requestAnimationFrame(lookAll); }
  function lookAt(chip, el) {
    if (!chip) return;
    if (el) { const r = el.getBoundingClientRect(); chip.target = { x: r.left + r.width / 2, y: r.top + r.height / 2 }; } else chip.target = null;
    look();
  }
  addEventListener("pointermove", (e) => { px = e.clientX; py = e.clientY; moved = Date.now(); look(); }, { passive: true });
  if (!RM) setInterval(() => {  // when nobody moves, Chip glances around on its own
    if (Date.now() - moved < 3500) return;
    px = innerWidth * (0.25 + Math.random() * 0.5);
    py = innerHeight * (0.2 + Math.random() * 0.5);
    look();
  }, 2600);

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => mount());
  else mount();
  return { mount, say, lookAt, mood };
})();
