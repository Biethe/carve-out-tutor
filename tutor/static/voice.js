// Talking and listening. Chip speaks with Kokoro, an open AI voice model running in the browser (no key, no limit;
// ~90 MB downloaded once). Until it has loaded, or if it can't run, the browser's most natural voice speaks instead.
// Listening uses the browser's speech-to-text (Chrome, Edge and Safari; Chrome sends the audio to Google).
const Voice = (() => {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const RATE = 1.1;  // a little faster than a calm reading pace: livelier
  const HERE = document.currentScript.src;  // only readable while this file loads
  let current = null, playing = null, run = 0;

  // Said out loud, code reads as words: check_login -> "check login", → -> "gives back".
  const plain = text => text
    .replace(/```[\s\S]*?```/g, " (see the code example) ")
    .replace(/→/g, " gives back ").replace(/\(\)/g, "").replace(/_/g, " ")
    .replace(/[`*•#★\[\]]/g, " ").replace(/\s+/g, " ").trim();
  // Sentences, with the opening words up to the first comma on their own: a tiny first piece starts sooner.
  const sentences = text => {
    const parts = (text.match(/[^.!?]+[.!?]*/g) || [text]).map(s => s.trim()).filter(Boolean);
    const comma = parts[0].indexOf(",");
    if (comma > 0 && comma < 30) parts.splice(0, 1, parts[0].slice(0, comma + 1), parts[0].slice(comma + 1).trim());
    return parts.filter(Boolean);
  };

  // ---- Kokoro, in a worker -----------------------------------------------------
  let kokoro = null, kokoroReady = false, nextId = 0;
  const waiting = new Map();
  const badge = Object.assign(document.createElement("div"), { className: "voice-notice", hidden: true });

  function startKokoro() {
    if (kokoro) return;
    try {
      kokoro = new Worker(new URL("kokoro-worker.js", HERE), { type: "module" });
    } catch { return; }
    kokoro.onmessage = ({ data }) => {
      if (data.type === "progress") {
        if (!badge.isConnected) document.body.append(badge);
        badge.hidden = false;
        badge.textContent = `Loading Chip's voice… ${data.percent}% (only the first time)`;
      } else if (data.type === "ready") {
        kokoroReady = true;
        badge.remove();
      } else if (data.type === "failed") {
        badge.remove();
        kokoro = null;  // the browser's voice it is
      } else {
        waiting.get(data.id)?.(data);
        waiting.delete(data.id);
      }
    };
  }

  // A sentence in Kokoro's voice, as an audio URL.
  const kokoroSay = text => new Promise((resolve, reject) => {
    const id = ++nextId;
    waiting.set(id, m => (m.wav ? resolve(URL.createObjectURL(new Blob([m.wav], { type: "audio/wav" }))) : reject(m.error)));
    kokoro.postMessage({ id, text, speed: RATE });
  });

  function play(url, id) {
    return new Promise(done => {
      if (id !== run) return done(true);
      playing = new Audio(url);
      playing.onended = () => done(true);
      playing.onerror = () => done(false);
      playing.play().catch(() => done(false));
    });
  }

  // ---- The browser's own voice ----------------------------------------------------
  // The most natural one it has: "Natural"/"Online" (Edge), "Google" (Chrome), "Premium"/"Enhanced" (Safari).
  async function browserVoice() {
    if (!speechSynthesis.getVoices().length) {  // voices load a moment after the page
      await new Promise(r => { speechSynthesis.addEventListener("voiceschanged", r, { once: true }); setTimeout(r, 1500); });
    }
    const score = v => 4 * /natural|neural|online/i.test(v.name) + 3 * /google|premium|enhanced/i.test(v.name)
      + 2 * /aria|jenny|samantha|ava|guy/i.test(v.name) + (v.lang === "en-US");
    return speechSynthesis.getVoices().filter(v => v.lang.startsWith("en")).sort((a, b) => score(b) - score(a))[0];
  }

  async function sayInBrowser(text, id) {
    if (!window.speechSynthesis) return;
    const voice = await browserVoice();
    await new Promise(r => setTimeout(r, 60));  // Chrome ignores speak() right after cancel()
    if (id !== run) return;
    return new Promise(done => {
      const say = new SpeechSynthesisUtterance(text);
      say.voice = voice || null;
      say.rate = RATE;
      say.onend = say.onerror = done;
      speechSynthesis.resume();  // Chrome sometimes leaves speech paused
      speechSynthesis.speak(say);
      setTimeout(done, 3000 + text.split(" ").length * 450);  // some browsers never say they've finished
    });
  }

  return {
    canListen: Boolean(Recognition),
    RATE,
    warmUp: startKokoro,  // start downloading Chip's voice before it's needed

    // Resolves when Chip has finished speaking (or right away if there's nothing to say).
    // onStart() runs when the sound actually starts (making Kokoro's first sentence takes a moment).
    async speak(text, onStart = () => {}) {
      this.stopSpeaking();
      const id = ++run, words = plain(text || "");
      if (!words) return;
      startKokoro();
      if (kokoroReady) {
        try {
          const parts = sentences(words);
          let next = kokoroSay(parts[0]);
          for (let i = 0; i < parts.length && id === run; i++) {
            const url = await next;
            if (i + 1 < parts.length) next = kokoroSay(parts[i + 1]);  // made while this one plays
            if (i === 0) onStart();
            if (!(await play(url, id))) throw new Error("couldn't play");
          }
          return;
        } catch {}  // fall through to the browser's voice
      }
      if (id === run) { onStart(); await sayInBrowser(words, id); }
    },

    stopSpeaking() {
      run++;
      playing?.pause();
      window.speechSynthesis?.cancel();
    },

    // Listens until the learner pauses. onText(text, final) gets the words as they come.
    // Resolves with everything that was said ("" if nothing).
    listen(onText) {
      if (!Recognition) return Promise.resolve("");
      this.stopListening();
      return new Promise(done => {
        const r = current = new Recognition();
        r.lang = document.documentElement.lang || "en";
        r.interimResults = true;
        let said = "";
        r.onresult = e => {
          said = [...e.results].map(x => x[0].transcript).join(" ").trim();
          onText?.(said, e.results[e.results.length - 1].isFinal);
        };
        r.onend = () => { current = null; done(said); };
        r.onerror = () => {};  // onend still follows
        r.start();
      });
    },

    stopListening() { current?.stop(); },
    get listening() { return Boolean(current); },
  };
})();
