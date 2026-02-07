(() => {
  const HAS_ANON = document.body.dataset.hasAnon === "1";

  // ===== Pixelated video background (Canvas) =====
  (() => {
    const video = document.getElementById("bgVideo");
    const canvas = document.getElementById("bgCanvas");
    const ctx = canvas.getContext("2d", { alpha: false });

    const PIXEL = 2;
    const PLAYBACK = 0.7;
    const SAT = 1;
    const CON = 1;

    const off = document.createElement("canvas");
    const offCtx = off.getContext("2d", { alpha: false });

    function resize() {
      const dpr = Math.max(1, window.devicePixelRatio || 1);
      const cssW = window.innerWidth;
      const cssH = window.innerHeight;

      canvas.width = Math.floor(cssW * dpr);
      canvas.height = Math.floor(cssH * dpr);
      canvas.style.width = cssW + "px";
      canvas.style.height = cssH + "px";
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      off.width = Math.max(1, Math.floor(cssW / PIXEL));
      off.height = Math.max(1, Math.floor(cssH / PIXEL));
      offCtx.imageSmoothingEnabled = false;
      ctx.imageSmoothingEnabled = false;
    }

    function draw() {
      if (video.readyState >= 2 && video.videoWidth && video.videoHeight) {
        const vw = video.videoWidth;
        const vh = video.videoHeight;

        const targetW = off.width;
        const targetH = off.height;

        const videoAspect = vw / vh;
        const targetAspect = targetW / targetH;

        let sx = 0, sy = 0, sw = vw, sh = vh;

        if (videoAspect > targetAspect) {
          sh = vh;
          sw = Math.round(vh * targetAspect);
          sx = Math.round((vw - sw) / 2);
          sy = 0;
        } else {
          sw = vw;
          sh = Math.round(vw / targetAspect);
          sx = 0;
          sy = Math.round((vh - sh) / 2);
        }

        offCtx.drawImage(video, sx, sy, sw, sh, 0, 0, targetW, targetH);

        ctx.filter = `saturate(${SAT}) contrast(${CON})`;
        ctx.drawImage(off, 0, 0, targetW, targetH, 0, 0, window.innerWidth, window.innerHeight);
        ctx.filter = "none";
      }
      requestAnimationFrame(draw);
    }

    resize();
    window.addEventListener("resize", resize, { passive: true });

    video.playbackRate = PLAYBACK;
    video.addEventListener("canplay", () => {
      video.playbackRate = PLAYBACK;
      video.play().catch(() => {});
    });

    const p = video.play();
    if (p && typeof p.catch === "function") p.catch(() => {});
    requestAnimationFrame(draw);
  })();

  const SCENE_FADE_MS = 1200;

  function show(id){
    const next = document.getElementById(id);
    if (!next) return;

    const current = document.querySelector(".scene.is-active");

    // 先に次を出す（クロスフェード）
    next.classList.add("is-active");

    // 旧シーンは leaving にしてフェードアウト
    if (current && current !== next) {
      current.classList.add("is-leaving");
      current.classList.remove("is-active");

      window.setTimeout(() => {
        current.classList.remove("is-leaving");
      }, SCENE_FADE_MS);
    }

    // 保険：どのシーンでもトップへ
    window.scrollTo(0, 0);
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;
  }

  // ===== Boot animation =====
  (() => {
    document.body.classList.add("is-booting");

    const SHOW_MS = 1800;
    const FADE_MS = 6000;

    const start = () => {
      setTimeout(() => {
        document.body.classList.remove("is-booting");
        document.body.classList.add("is-ready");
        const audio = document.getElementById("bgAudio");
        if (audio) {
          audio.volume = 0.25;
          audio.play().catch(() => {});
        }
        show(HAS_ANON ? "scene-choice" : "scene-nick");
      }, SHOW_MS);

      setTimeout(() => {
        const s = document.getElementById("splash");
        if (s) s.remove();
      }, SHOW_MS + FADE_MS + 150);
    };

    const v = document.getElementById("bgVideo");
    if (v && v.readyState >= 2) start();
    else if (v) {
      v.addEventListener("canplay", start, { once: true });
      setTimeout(start, 1800);
    } else {
      setTimeout(start, 800);
    }
  })();

  // ===== Nickname submit (no page reload) =====
  (() => {
    const form = document.getElementById("nickForm");
    const input = document.getElementById("nickInput");
    if (!form || !input) return;

    form.addEventListener("submit", async (e) => {
      e.preventDefault();

      const fd = new FormData(form);
      const nickname = (fd.get("nickname") || "").toString().trim();
      if (!nickname) return;

      try {
        const res = await fetch(form.action, {
          method: "POST",
          body: fd,
          credentials: "same-origin",
          headers: { "Accept": "application/json" },
        });

        if (!res.ok) return;

        // cookieはサーバで set-cookie される想定
        document.body.dataset.hasAnon = "1";

        // 演出：砂浜 → choice
        show("scene-walk");
        window.setTimeout(() => show("scene-choice"), 900);
      } catch (_) {}
    });
  })();

  // ===== Choice animation control =====
  (() => {
    const sceneChoice = document.getElementById("scene-choice");
    const chooseBottle = document.getElementById("chooseBottle");
    const choosePen = document.getElementById("choosePen");
    const choiceBack = document.getElementById("choiceBack");

    const DURATION_MS = 1200;
    let locked = false;

    function resetChoice() {
      if (!sceneChoice) return;
      sceneChoice.classList.remove("is-selected");
      chooseBottle?.classList.remove("is-picked","is-faded");
      choosePen?.classList.remove("is-picked","is-faded");
      locked = false;
    }

    function pick(which) {
      if (locked) return;
      locked = true;

      sceneChoice?.classList.add("is-selected");

      if (which === "bottle") {
        chooseBottle?.classList.add("is-picked");
        choosePen?.classList.add("is-faded");
      } else {
        choosePen?.classList.add("is-picked");
        chooseBottle?.classList.add("is-faded");
      }

      window.setTimeout(() => {
        show(which === "bottle" ? "scene-read" : "scene-write");
        locked = false;
      }, DURATION_MS);
    }

    function backToChoice() {
      document.body.classList.remove("is-letter-open");
      document.getElementById("letterOverlay")?.classList.remove("is-show");
      document.getElementById("letterOverlay")?.setAttribute("aria-hidden","true");

      show("scene-choice");
      requestAnimationFrame(() => resetChoice());
    }

    chooseBottle?.addEventListener("click", () => pick("bottle"));
    choosePen?.addEventListener("click", () => pick("pen"));

    choiceBack?.addEventListener("click", () => resetChoice());
    choiceBack?.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        resetChoice();
      }
    });

    document.getElementById("backFromRead")?.addEventListener("click", backToChoice);
    document.getElementById("backFromWrite")?.addEventListener("click", backToChoice);

    if (HAS_ANON) resetChoice();
  })();

  // ===== Read scene wiring =====
  (() => {
    const takeLetter = document.getElementById("takeLetter");
    const letterOverlay = document.getElementById("letterOverlay");

    async function openLetter(){
      document.body.classList.add("is-letter-open");
      letterOverlay?.classList.add("is-show");
      letterOverlay?.setAttribute("aria-hidden", "false");

      const textEl = document.getElementById("letterText");
      const metaEl = document.getElementById("letterMeta");
      if (!textEl) return;

      textEl.textContent = "……";
      if (metaEl) metaEl.textContent = "";

      try{
        const res = await fetch("/today", {
          method: "GET",
          headers: { "Accept": "application/json" },
          credentials: "same-origin",
        });
        if (!res.ok) throw new Error("failed");
        const data = await res.json();

        const content = (data?.bottle?.content ?? data?.message ?? "").toString();

        // 1文字ずつ span 化
        textEl.innerHTML = "";
        const inner = document.createElement("div");
        inner.className = "inner";
        textEl.appendChild(inner);

        const chars = [...content];
        const baseDelay = 1;   // 秒
        const maxDelay  = 2.2;    // 秒

        let k = 0; // ← 表示文字カウント（改行は増やさない）
        chars.forEach((ch) => {
          if (ch === "\n") {
            inner.appendChild(document.createElement("br"));
            return;
          }

          // スペースも「間」として出したいならカウント増やす
          const span = document.createElement("span");
          span.className = "ch";
          span.textContent = ch;

          const d = Math.min(k * baseDelay, maxDelay);
          span.style.animationDelay = `${d}s`;
          inner.appendChild(span);

          // 空白もタイピング感として遅らせたいなら：if (ch === " ") k += 0.5; みたいにしても良い
          k += 1;
        });

        if (metaEl) metaEl.textContent = data?.date ? `— ${data.date}` : "";
      }catch(e){
        textEl.textContent = "波の音に、ことばが消えた。";
      }
    }
    function closeLetter(){
      document.body.classList.remove("is-letter-open");
      letterOverlay?.classList.remove("is-show");
      letterOverlay?.setAttribute("aria-hidden", "true");
    }

    takeLetter?.addEventListener("click", openLetter);
    letterOverlay?.addEventListener("click", closeLetter);
    window.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeLetter();
    });
  })();
})();