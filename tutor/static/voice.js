// Talking and listening. The tutor speaks with a natural AI voice from the learner's provider (Groq's Orpheus),
// and falls back to the most natural voice the browser has. Listening uses the browser's speech-to-text
// (Chrome, Edge and Safari; Chrome sends the audio to Google to turn it into text).
const Voice = (() => {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  let current = null, playing = null, natural = true, run = 0;

  // Said out loud, code reads as words: check_login -> "check login", → -> "gives back".
  const plain = text => text
    .replace(/```[\s\S]*?```/g, " (see the code example) ")
    .replace(/→/g, " gives back ").replace(/\(\)/g, "").replace(/_/g, " ")
    .replace(/[`*•#★\[\]]/g, " ").replace(/\s+/g, " ").trim();

  // Few pieces (the voice allows 10 requests a minute): the first sentence alone so it starts quickly,
  // then the rest in pieces of up to 450 characters.
  const RATE = 1.1;  // a little faster than the voice's own pace: livelier
  const pieces = text => (text.match(/[^.!?]+[.!?]*/g) || [text]).reduce((out, s, i) => {
    const last = out[out.length - 1];
    if (i > 1 && (last + s).length < 450) out[out.length - 1] = last + s; else out.push(s.trim());
    return out;
  }, []).filter(Boolean);

  // The browser's best voice: "Natural"/"Online" (Edge), "Google" (Chrome), "Premium"/"Enhanced" (Safari).
  function browserVoice() {
    const score = v => 4 * /natural|neural|online/i.test(v.name) + 3 * /google|premium|enhanced/i.test(v.name)
      + 2 * /aria|jenny|samantha|ava|guy/i.test(v.name) + (v.lang === "en-US");
    return speechSynthesis.getVoices().filter(v => v.lang.startsWith("en")).sort((a, b) => score(b) - score(a))[0];
  }
  window.speechSynthesis?.addEventListener?.("voiceschanged", browserVoice);

  function notice(message) {
    const el = document.createElement("div");
    el.className = "voice-notice";
    el.innerHTML = message.replace(/(https:\/\/\S+)/, '<a href="$1" target="_blank" rel="noopener">accept them here</a>');
    document.body.append(el);
    setTimeout(() => el.remove(), 15000);
  }

  function sayInBrowser(text) {
    return new Promise(done => {
      if (!window.speechSynthesis) return done();
      const say = new SpeechSynthesisUtterance(text);
      say.voice = browserVoice() || null;
      say.rate = RATE;
      say.onend = say.onerror = done;
      speechSynthesis.speak(say);
      setTimeout(done, 3000 + text.split(" ").length * 450);  // some browsers never say they've finished
    });
  }

  const fetchAudio = text => fetch("api/speak", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) })
    .then(async r => (r.ok ? URL.createObjectURL(await r.blob()) : Promise.reject(await r.json())));

  function play(url, id) {
    return new Promise(done => {
      if (id !== run) return done();
      playing = new Audio(url);
      playing.playbackRate = RATE;  // keeps the pitch natural
      playing.onended = playing.onerror = done;
      playing.play().catch(done);
    });
  }

  return {
    canListen: Boolean(Recognition),
    RATE,

    // A recorded clip (Chip's introduction): instant, no AI call. Resolves when it ends.
    playClip(url) {
      this.stopSpeaking();
      return play(url, ++run);
    },

    // Resolves when the tutor has finished speaking (or right away if there's nothing to say).
    async speak(text) {
      this.stopSpeaking();
      const id = ++run, words = plain(text || "");
      if (!words) return;
      if (natural) {
        try {
          const parts = pieces(words);
          let next = fetchAudio(parts[0]);
          for (let i = 0; i < parts.length && id === run; i++) {
            const url = await next;
            if (i + 1 < parts.length) next = fetchAudio(parts[i + 1]);  // fetched while this one plays
            await play(url, id);
          }
          return;
        } catch (err) {
          if (!err?.busy) {  // busy: just this once in the browser's voice. Otherwise, for the rest of the visit.
            natural = false;
            if (err?.error) notice(err.error);
          }
        }
      }
      if (id === run) await sayInBrowser(words);
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
