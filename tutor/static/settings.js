// Settings: the learner's own AI provider, model and key. Adds a gear to the header of every page.
const PROVIDERS = {
  groq: { name: "Groq (free key)", url: "https://api.groq.com/openai/v1", model: "openai/gpt-oss-120b", keys: "https://console.groq.com/keys" },
  openrouter: { name: "OpenRouter (free models)", url: "https://openrouter.ai/api/v1", model: "openai/gpt-oss-120b:free", keys: "https://openrouter.ai/settings/keys" },
  gemini: { name: "Google Gemini (free tier)", url: "https://generativelanguage.googleapis.com/v1beta/openai", model: "gemini-2.5-flash", keys: "https://aistudio.google.com/apikey" },
  other: { name: "Other (OpenAI-compatible)", url: "", model: "", keys: "" },
};

document.addEventListener("DOMContentLoaded", () => {
  const gear = document.createElement("button");
  gear.className = "gear";
  gear.title = gear.ariaLabel = "Settings: your AI provider";
  gear.innerHTML = `<i class="ph-bold ph-gear-six" aria-hidden="true"></i>`;
  document.querySelector(".theme-switch")?.before(gear);

  const dialog = document.createElement("dialog");
  dialog.className = "settings-dialog";
  dialog.innerHTML = `
    <form method="dialog">
      <h2>Your AI tutor</h2>
      <p class="muted small">The tutor uses your own AI provider. Your key is saved only in this browser and sent only to that provider.</p>
      <label>Provider <select name="provider">${Object.entries(PROVIDERS).map(([k, p]) => `<option value="${k}">${p.name}</option>`).join("")}</select></label>
      <label>Address <input name="base_url" required spellcheck="false"></label>
      <label>Model <input name="model" required spellcheck="false"></label>
      <label>Key <input name="api_key" type="password" autocomplete="off" spellcheck="false"></label>
      <p class="small"><a class="get-key" target="_blank" rel="noopener">Get a free key</a> <span class="key-state muted"></span></p>
      <div class="chat-buttons"><button class="btn" value="save">Save</button><button class="btn secondary" value="cancel" formnovalidate>Cancel</button></div>
    </form>`;
  document.body.append(dialog);
  const form = dialog.querySelector("form"), field = name => form.elements[name];

  function pick(key, keepFields) {
    const p = PROVIDERS[key];
    field("provider").value = key;
    if (!keepFields) { field("base_url").value = p.url; field("model").value = p.model; }
    form.querySelector(".get-key").hidden = !p.keys;
    form.querySelector(".get-key").href = p.keys;
  }
  field("provider").onchange = () => pick(field("provider").value);

  gear.onclick = async () => {
    const s = await fetch("api/settings").then(r => r.json());
    const key = Object.keys(PROVIDERS).find(k => PROVIDERS[k].url && s.base_url.startsWith(PROVIDERS[k].url)) || "other";
    pick(key, true);
    field("base_url").value = s.base_url;
    field("model").value = s.model;
    field("api_key").value = "";
    field("api_key").placeholder = s.key_end ? "Saved key ending in " + s.key_end : "Paste your key";
    form.querySelector(".key-state").textContent = s.key_end ? "" : "No key yet.";
    dialog.showModal();
  };

  form.onsubmit = async e => {
    if (e.submitter?.value !== "save") return;
    await fetch("api/settings", {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ base_url: field("base_url").value, model: field("model").value, api_key: field("api_key").value }),
    });
  };
});
