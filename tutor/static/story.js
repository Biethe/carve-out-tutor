// The first-visit story: what Carve-Out is, one sentence at a time, in seven beats. Used by the published site's boot
// page (while Python loads) and by the start page on a first local visit.
const Story = (() => {
  const RM = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const MARKUP = `  <header class="top gut">
    <span class="brand"><span class="chip xs" data-chip></span>Carve-Out</span>
    <div class="top-right">
      <span class="py-status" id="py"><span class="spin" aria-hidden="true"></span>Getting Python ready</span>
      <button class="icon-btn" id="story-sound" aria-pressed="true" aria-label="Chip’s voice" title="Chip’s voice"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 9.5h3.5L12 5.5v13L7.5 14.5H4z"></path><path class="waves" d="M15.5 9a4 4 0 0 1 0 6M18 6.5a7.5 7.5 0 0 1 0 11"></path></svg></button>
      <button class="navb" id="skip-intro">Skip intro</button>
    </div>
  </header>
  <div class="story gut s-hello" id="story">
    <div class="stage-wrap" id="stage-wrap">
      <div class="stage" id="stage" aria-hidden="true">
        <div class="hello"><span class="hello-glow"></span><span class="chip xl hop" id="big-chip" data-chip></span></div>

        <div class="idea-box">
          <span class="ib-label">Your idea</span>
          <div class="ib-field panel raised"><span class="ib-text"><span id="ib-typed"></span><span class="caret"></span></span><span class="ib-go" id="ib-go">Build it</span></div>
        </div>

        <div class="app-win panel raised">
          <div class="aw-head"><span class="aw-logo">Family Recipes</span><span class="aw-add" id="aw-add">+ Add recipe</span></div>
          <div class="aw-search">Search recipes</div>
          <div class="aw-list">
            <div class="aw-row"><span class="aw-thumb" style="background: #D9A48F"></span><span class="aw-title">Grandma’s jollof rice</span><span class="aw-time">45 min</span></div>
            <div class="aw-row"><span class="aw-thumb" style="background: #CACF96"></span><span class="aw-title">Lemon drizzle cake</span><span class="aw-time">1 h 5 min</span></div>
            <div class="aw-row"><span class="aw-thumb" style="background: #B48C6B"></span><span class="aw-title">Sunday beef stew</span><span class="aw-time">2 h 10 min</span></div>
            <div class="aw-row new" id="aw-new"><span class="aw-thumb" style="background: #E2BE98"></span><span class="aw-title">Mum’s pancakes</span><span class="aw-time">20 min</span></div>
          </div>
          <div class="aw-toast"><span class="tk"><svg viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"></path></svg></span>Search runs your code now</div>
        </div>

        <div class="code-win panel"><div class="cw-head"><span>Your app’s code</span><span class="muted">23 functions</span></div></div>
        <div class="slot-ghost"></div>
        <div class="blk b0" style="--i: 0; --y: 98px"><span class="bd"></span><span class="bn">find_recipes</span><span class="bf">recipes.py</span><span class="bc"><svg viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"></path></svg></span></div>
        <div class="blk" style="--i: 1; --y: 145px"><span class="bd"></span><span class="bn">scale_servings</span><span class="bf">recipes.py</span><span class="bc"><svg viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"></path></svg></span></div>
        <div class="blk" style="--i: 2; --y: 192px"><span class="bd"></span><span class="bn">total_time</span><span class="bf">recipes.py</span><span class="bc"><svg viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"></path></svg></span></div>
        <div class="blk" style="--i: 3; --y: 239px"><span class="bd"></span><span class="bn">save_recipe</span><span class="bf">storage.py</span><span class="bc"><svg viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"></path></svg></span></div>
        <div class="blk" style="--i: 4; --y: 286px"><span class="bd"></span><span class="bn">load_recipes</span><span class="bf">storage.py</span><span class="bc"><svg viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"></path></svg></span></div>
        <div class="blk" style="--i: 5; --y: 333px"><span class="bd"></span><span class="bn">delete_recipe</span><span class="bf">storage.py</span><span class="bc"><svg viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"></path></svg></span></div>

        <div class="desk panel raised">
          <div class="dk-head"><span class="dk-name">find_recipes</span><span class="dk-tag">Your turn</span></div>
          <pre class="dk-code"><span class="kw">def</span> <span class="fn">find_recipes</span>(recipes, text):
    <span class="str">"""Recipes whose name contains the text, any case."""</span>
    <span id="dk-typed"></span><span class="caret"></span></pre>
          <div class="dk-tests"><span class="t"><i></i>Finds a recipe by its name</span><span class="t"><i></i>Ignores upper and lower case</span></div>
          <div class="dk-hint" id="dk-hint"><span class="chip xs" data-chip></span>Lower-case both sides, then compare.</div>
        </div>

        <div class="meter"><span><b id="m-n">0</b> of 23 functions are yours</span><span class="m-track"><span class="m-fill" id="m-fill"></span></span></div>

        <svg class="cursor" id="cursor" viewBox="0 0 24 24"><path d="M5 3l14 8.2-6.1 1.4L16.4 20l-2.9 1.3-3.5-7.4L5 18.4z" fill="#22303A" stroke="#FFFFFF" stroke-width="1.6" stroke-linejoin="round"></path></svg>
      </div>
    </div>
    <div class="caption">
      <span class="chip md" id="story-chip" data-chip></span>
      <p class="say" id="story-say" aria-live="polite"></p>
    </div>
    <div class="story-nav">
      <button class="btn ghost" id="story-back" disabled>Back</button>
      <div class="dots" id="story-dots" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div>
      <button class="btn primary lg" id="story-next"><span id="story-next-label">Show me</span><svg class="go" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14"></path><path d="M13 6l6 6-6 6"></path></svg></button>
    </div>
  </div>`;
  const STORY = [
    ["Hi, I’m Chip. Let’s build something you actually care about.", "Show me"],
    ["It starts with your idea. Any idea.", "Next"],
    ["I build the whole app for you, and it already works.", "Next"],
    ["Inside, it’s made of small pieces of code called functions.", "Next"],
    ["We take one piece out, and you write it back. I give hints, never answers.", "Next"],
    ["Your piece goes back in, and the app keeps working on your code.", "Next"],
    ["Piece by piece, the app you dreamed up becomes yours.", "What will you build?"],
  ];
  const FULL = 'words = text.lower()\n    return [r for r in recipes if words in r["name"].lower()]';
  const FULL_HTML = 'words = text.<span class="fn">lower</span>()\n    <span class="kw">return</span> [r <span class="kw">for</span> r <span class="kw">in</span> recipes <span class="kw">if</span> words <span class="kw">in</span> r[<span class="str">"name"</span>].<span class="fn">lower</span>()]';
  const IDEAS = ["a game where you dodge falling stars", "a tracker for my morning runs", "a recipe box for my family"];
  let root = null, beat = 1, timers = [], finish = null;

  const seen = () => { try { return localStorage.getItem("seenStory") === "1"; } catch { return false; } };

  function python(state) {
    const py = root && !root.hidden && root.querySelector("#py");
    if (!py) return;
    py.classList.toggle("failed", state === "failed");
    py.innerHTML = state === "ready" ? '<span class="ready" aria-hidden="true"></span>Python is ready' : "Python couldn’t start";
  }

  function play(el, { python: withPython = false, voice = "static/voice/", onDone }) {
    root = el;
    root.innerHTML = MARKUP;
    root.hidden = false;
    if (!withPython) root.querySelector("#py").remove();
    Chip.mount(root);
    const $ = (s) => root.querySelector(s), $$ = (s) => [...root.querySelectorAll(s)];
    const story = $("#story"), stage = $("#stage"), nextBtn = $("#story-next"), backBtn = $("#story-back");
    const blocks = $$(".blk"), tests = $$(".dk-tests .t"), cursor = $("#cursor"), awAdd = $("#aw-add"), awNew = $("#aw-new");
    const typed = $("#dk-typed"), ibTyped = $("#ib-typed"), ibGo = $("#ib-go");
    const later = (ms, fn) => { timers.push(setTimeout(fn, RM ? 0 : ms)); };

    // Chip says each beat out loud (recorded once, see tutor/record_intro.py). Some browsers block sound until the
    // first click: then the speaker button pulses, and a tap on it plays the line.
    const soundBtn = $("#story-sound");
    let sound = true, clip = null;
    function speakBeat() {
      clip?.pause();
      if (!sound) return;
      clip = new Audio(`${voice}story${beat}.wav`);
      clip.play().then(() => soundBtn.classList.remove("nudge"))
        .catch((err) => { if (err.name === "NotAllowedError") soundBtn.classList.add("nudge"); });
    }
    soundBtn.addEventListener("click", () => {
      if (soundBtn.classList.contains("nudge")) { soundBtn.classList.remove("nudge"); return speakBeat(); }
      sound = !sound;
      soundBtn.setAttribute("aria-pressed", String(sound));
      soundBtn.classList.toggle("off", !sound);
      sound ? speakBeat() : clip?.pause();
    });
    const clear = () => { timers.forEach(clearTimeout); timers = []; };
    const setMeter = (n) => { $("#m-n").textContent = n; $("#m-fill").style.width = `${n / 23 * 100}%`; };
    const nudge = (ms) => later(ms, () => nextBtn.classList.add("nudge"));

    function fitStage() {  // the stage is drawn at 1040 by 470 and scaled down to fit the window, so nothing scrolls
      const wrap = $("#stage-wrap");
      if (!wrap) return;
      wrap.style.width = "";
      const rest = document.documentElement.scrollHeight - wrap.offsetHeight;  // the top bar, Chip's words, the buttons
      const k = Math.min(1, wrap.clientWidth / 1040, Math.max(0.4, (innerHeight - rest) / 470));
      stage.style.setProperty("--k", k);
      wrap.style.height = `${470 * k}px`;
      wrap.style.width = `${1040 * k}px`;  // narrower when scaled for height, so it stays centred
    }
    function clickAt(el, then) {  // the pointer walks to el and clicks it
      if (RM) return then();  // with reduced motion, the click just happens
      const s = stage.getBoundingClientRect(), k = s.width / 1040 || 1, b = el.getBoundingClientRect();
      const to = `translate(${(b.left - s.left) / k + b.width / k * 0.55}px, ${(b.top - s.top) / k + b.height / k * 0.45}px)`;
      cursor.animate([{ transform: "translate(960px, 450px)", opacity: 0 }, { transform: "translate(960px, 450px)", opacity: 1, offset: 0.15 }, { transform: to, opacity: 1 }],
        { duration: 1100, easing: "cubic-bezier(.45, 0, .2, 1)", fill: "forwards" });
      later(1150, () => {
        cursor.animate([{ transform: `${to} scale(1)`, opacity: 1 }, { transform: `${to} scale(.8)`, opacity: 1 }, { transform: `${to} scale(1)`, opacity: 1 }], { duration: 260, fill: "forwards" });
        then();
      });
      later(2100, () => cursor.animate([{ transform: to, opacity: 1 }, { transform: `${to} translate(12px, 16px)`, opacity: 0 }], { duration: 500, fill: "forwards" }));
    }

    const PLAY = {
      2() {  // ideas get typed, changed, and one gets built
        let t = 350;
        IDEAS.forEach((idea, n) => {
          for (let i = 1; i <= idea.length; i++) later(t + i * 38, () => { ibTyped.textContent = idea.slice(0, i); });
          t += idea.length * 38;
          if (n < IDEAS.length - 1) {
            t += 650;
            for (let i = idea.length - 1; i >= 0; i--) later(t + (idea.length - i) * 14, () => { ibTyped.textContent = idea.slice(0, i); });
            t += idea.length * 14 + 250;
          }
        });
        later(t + 300, () => ibGo.classList.add("pressed"));
        later(t + 550, () => ibGo.classList.remove("pressed"));
        nudge(t + 900);
      },
      3() {  // the app works: a recipe gets added
        later(1150, () => clickAt(awAdd, () => { awAdd.classList.add("pressed"); later(250, () => { awAdd.classList.remove("pressed"); awNew.classList.add("show"); }); }));
        nudge(3600);
      },
      5() {  // Chip hints, the code types itself, the tests turn green
        later(250, () => $("#dk-hint").classList.add("show"));
        const start = 1400;
        for (let i = 1; i <= FULL.length; i++) later(start + i * 30, () => { typed.textContent = FULL.slice(0, i); });
        const end = start + FULL.length * 30;
        later(end + 120, () => { typed.innerHTML = FULL_HTML; });
        tests.forEach((t, i) => {
          later(end + 350 + i * 420, () => t.classList.add("show"));
          later(end + 800 + i * 420, () => t.classList.add("ok"));
        });
        nudge(end + 1800);
      },
      6() {
        later(800, () => blocks[0].classList.add("mine", "pop"));
        later(1150, () => setMeter(1));
        nudge(2500);
      },
      7() {
        blocks.slice(1).forEach((b, i) => later(500 + i * 330, () => { b.classList.add("mine", "pop"); setMeter(2 + i); }));
        nudge(500 + 5 * 330 + 700);
      },
    };

    function goBeat(n) {
      clear();
      beat = n;
      story.classList.toggle("s-hello", n === 1);
      story.classList.toggle("s-idea", n === 2);
      story.classList.toggle("s-app", n >= 3);
      story.classList.toggle("s-code", n >= 4);
      story.classList.toggle("b4", n === 4);
      story.classList.toggle("s-lift", n === 5);
      story.classList.toggle("s-back", n >= 6);
      story.classList.toggle("s-all", n === 7);
      // Where this beat starts from; its own animation plays on top.
      ibTyped.textContent = n > 2 ? IDEAS[2] : "";
      awNew.classList.toggle("show", n >= 4);
      awAdd.classList.remove("pressed");
      blocks.forEach((b, i) => { b.classList.remove("pop"); b.classList.toggle("mine", n === 7 && i === 0); });
      cursor.getAnimations().forEach((a) => a.cancel());
      typed.innerHTML = n >= 6 ? FULL_HTML : "";
      tests.forEach((t) => { t.classList.toggle("show", n >= 6); t.classList.toggle("ok", n >= 6); });
      $("#dk-hint").classList.remove("show");
      setMeter(n === 7 ? 1 : 0);
      Chip.say($("#story-say"), STORY[n - 1][0], n > 1 ? $("#story-chip") : null);
      speakBeat();
      $("#story-next-label").textContent = STORY[n - 1][1];
      backBtn.disabled = n === 1;
      $$("#story-dots i").forEach((d, i) => { d.classList.toggle("on", i === n - 1); d.classList.toggle("done", i < n - 1); });
      nextBtn.classList.remove("nudge");
      if (PLAY[n]) PLAY[n]();
      else nudge(n === 1 ? 2400 : 1800);
    }

    function keys(e) {
      if (root.hidden || /INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) return;
      if (e.key === "ArrowRight") nextBtn.click();
      if (e.key === "ArrowLeft" && beat > 1) backBtn.click();
    }
    finish = () => {
      clear();
      clip?.pause();
      removeEventListener("resize", fitStage);
      document.removeEventListener("keydown", keys);
      try { localStorage.setItem("seenStory", "1"); } catch {}
      onDone();
    };
    nextBtn.addEventListener("click", () => (beat < 7 ? goBeat(beat + 1) : finish()));
    backBtn.addEventListener("click", () => { if (beat > 1) goBeat(beat - 1); });
    $("#skip-intro").addEventListener("click", () => finish());
    document.addEventListener("keydown", keys);
    addEventListener("resize", fitStage);
    fitStage();
    goBeat(1);
  }

  return { play, seen, python };
})();
