// Chip's live voice: Kokoro, an open AI voice model, running in the browser. No key, no limit.
// The model (~90 MB) downloads once and the browser keeps it. Runs in a worker so the page never freezes.
import { KokoroTTS } from "https://cdn.jsdelivr.net/npm/kokoro-js@1.2.1/dist/kokoro.web.js";

const VOICE = "af_heart";  // Kokoro's most natural voice
let tts = null;

const ready = KokoroTTS.from_pretrained("onnx-community/Kokoro-82M-v1.0-ONNX", {
  dtype: "q8", device: "wasm",  // the small model; WebGPU needs the 4x larger one to sound right
  progress_callback: p => p.status === "progress" && p.file?.endsWith(".onnx") && postMessage({ type: "progress", percent: Math.round(p.progress) }),
}).then(async model => {
  tts = model;
  await tts.generate("Hi.", { voice: VOICE });  // the very first sentence is slow; get it out of the way unheard
  postMessage({ type: "ready" });
})
  .catch(err => postMessage({ type: "failed", error: String(err.message || err) }));

onmessage = async ({ data: { id, text, speed } }) => {
  try {
    await ready;
    const audio = await tts.generate(text, { voice: VOICE, speed });
    const wav = await audio.toBlob().arrayBuffer();
    postMessage({ id, wav }, [wav]);
  } catch (err) {
    postMessage({ id, error: String(err.message || err) });
  }
};
