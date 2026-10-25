// The demo proxy: the published tutor calls this when a visitor hasn't added an AI key of their own, so judges and
// first-time visitors can try everything. The Groq key lives here as an encrypted secret (GROQ_KEY), never in the site.
// It only answers the tutor's own pages, and only forwards the two calls the tutor makes, with the two models it uses.
const GROQ = "https://api.groq.com/openai/v1";
const ORIGINS = ["https://biethe.github.io", "http://127.0.0.1:8020", "http://localhost:8020"];
const ALLOWED = { "/chat/completions": "openai/gpt-oss-120b", "/audio/speech": "canopylabs/orpheus-v1-english" };
const MAX_BODY = 60_000;  // the tutor's biggest request (a card, with a whole file) is well under this

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    if (!ORIGINS.includes(origin)) return new Response("This proxy only serves the Carve-Out Tutor.", { status: 403 });
    const cors = { "Access-Control-Allow-Origin": origin, "Access-Control-Allow-Methods": "POST, OPTIONS",
                   "Access-Control-Allow-Headers": "authorization, content-type", "Vary": "Origin" };
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });

    const path = new URL(request.url).pathname;
    if (request.method !== "POST" || !ALLOWED[path]) return new Response("Not found.", { status: 404, headers: cors });
    const body = await request.text();
    if (body.length > MAX_BODY) return new Response("Too large.", { status: 413, headers: cors });
    let model;
    try { model = JSON.parse(body).model; } catch { return new Response("Bad request.", { status: 400, headers: cors }); }
    if (model !== ALLOWED[path]) return new Response("That model isn't available here.", { status: 400, headers: cors });

    const reply = await fetch(GROQ + path, {
      method: "POST", body,
      headers: { "Authorization": `Bearer ${env.GROQ_KEY}`, "Content-Type": "application/json" },
    });
    return new Response(reply.body, { status: reply.status,
      headers: { ...cors, "Content-Type": reply.headers.get("Content-Type") || "application/json" } });
  },
};
