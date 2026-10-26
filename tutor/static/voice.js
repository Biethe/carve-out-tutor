// Talking and listening. Chip has the demo video's voice. Onboarding is pre-recorded (tutor/static/voice/);
// live replies come from /api/speak. When that isn't available, Chip stays quiet and the words stay on screen.
// Listening uses the browser's speech-to-text (Chrome, Edge and Safari; Chrome sends the audio to Google).
const Voice = (() => {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  let current = null, playing = null, run = 0, resting = false;

  // Said out loud, code reads as words: check_login -> "check login", → -> "gives back".
  const plain = text => text
    .replace(/```[\s\S]*?```/g, " (see the code example) ")
    .replace(/→/g, " gives back ").replace(/\(\)/g, "").replace(/_/g, " ")
    .replace(/[`*•#★\[\]]/g, " ").replace(/\s+/g, " ").trim();

  // Orpheus allows 10 requests a minute: the first sentence alone so it starts quickly, the rest in big pieces.
  const pieces = text => (text.match(/[^.!?]+[.!?]*/g) || [text]).reduce((out, s, i) => {
    const last = out[out.length - 1];
    if (i > 1 && (last + s).length < 450) out[out.length - 1] = last + s; else out.push(s.trim());
    return out;
  }, []).filter(Boolean);

  function notice(message) {
    const el = document.createElement("div");
    el.className = "voice-notice";
    el.innerHTML = message.replace(/(https:\/\/\S+)/, '<a href="$1" target="_blank" rel="noopener">accept them here</a>');
    document.body.append(el);
    setTimeout(() => el.remove(), 12000);
  }

  const say = text => fetch("api/speak", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) })
    .then(async r => (r.ok ? URL.createObjectURL(await r.blob()) : Promise.reject(await r.json())));

  function play(url, id) {
    return new Promise(done => {
      if (id !== run) return done();
      playing = new Audio(url);
      playing.onended = playing.onerror = done;
      playing.play().catch(done);
    });
  }

  return {
    canListen: Boolean(Recognition),

    // Resolves when Chip has finished speaking, or right away if Chip's voice is resting.
    // onStart() runs when the sound actually starts.
    async speak(text, onStart = () => {}) {
      this.stopSpeaking();
      const id = ++run, words = plain(text || "");
      if (!words || resting) return;
      try {
        const parts = pieces(words);
        let next = say(parts[0]);
        for (let i = 0; i < parts.length && id === run; i++) {
          const url = await next;
          if (i + 1 < parts.length) next = say(parts[i + 1]);  // made while this one plays
          if (i === 0) onStart();
          await play(url, id);
        }
      } catch (err) {
        if (err?.busy && !err.today) return;  // the per-minute limit: just this reply stays silent
        resting = true;  // for the rest of the visit: Chip's words stay on screen, in the same voice or none
        notice(err?.today ? "Chip's voice is resting for today (the free voice allowance is used up). Replies stay on screen."
                          : err?.error || "Chip's voice isn't available right now. Replies stay on screen.");
      }
    },

    stopSpeaking() {
      run++;
      playing?.pause();
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
