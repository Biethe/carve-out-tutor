// Talking and listening, with the browser's own speech tools (no extra service).
// Speech-to-text works in Chrome, Edge and Safari; Chrome sends the audio to Google to turn it into text.
const Voice = (() => {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  let current = null;

  // Spoken text: no code blocks, no markdown marks, no bullets.
  const plain = text => text.replace(/```[\s\S]*?```/g, " (see the code example) ").replace(/[`*•#]/g, "").replace(/\s+/g, " ").trim();

  return {
    canListen: Boolean(Recognition),

    // Resolves when the tutor has finished speaking (or right away if speech isn't available).
    speak(text) {
      return new Promise(done => {
        if (!window.speechSynthesis || !text) return done();
        speechSynthesis.cancel();
        const say = new SpeechSynthesisUtterance(plain(text));
        say.rate = 1.03;
        say.onend = say.onerror = done;
        speechSynthesis.speak(say);
      });
    },

    stopSpeaking() { window.speechSynthesis?.cancel(); },

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
