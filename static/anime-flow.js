/* ============================================================
   ModelFlow · Anime.js 动画融入层（v3.2.2 本地 vendor）
   应用场景（三处，克制原则）：
   ① 实时输出面板新日志行滑入（stagger 级联）
   ② 步骤完成时 ✓ 图标弹性强调
   ③ 进度百分比数字滚动
   其余交由 CSS（motion.css 已覆盖），不滥用。
   降级：anime 未加载时全部静默跳过，页面功能零影响。
   ============================================================ */
(function(){
  "use strict";
  function hasAnime(){ return typeof window.anime === "function"; }
  function reduced(){ return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches; }

  /* ① 实时输出面板：新日志行滑入（替换 CSS 动画，Anime 驱动更有弹性） */
  window.mfAnimLogLine = function(el){
    if(!hasAnime() || reduced()) return;
    anime({ targets: el, opacity: [0, 1], translateX: [-14, 0],
            duration: 320, easing: "easeOutCubic" });
  };

  /* ② 步骤完成 ✓ 弹跳强调 */
  window.mfAnimStepDone = function(el){
    if(!hasAnime() || reduced()) return;
    anime({ targets: el, scale: [ { value: 0.5, duration: 0 },
                                   { value: 1.25, duration: 220 },
                                   { value: 1, duration: 180 } ],
            easing: "easeOutElastic(1, .6)" });
  };

  /* ③ 进度数字滚动（0→目标值） */
  window.mfAnimProgress = function(el, target){
    if(!hasAnime() || reduced()){ el.textContent = target + "%"; return; }
    const obj = { v: parseInt(el.textContent) || 0 };
    anime({ targets: obj, v: target, round: 1, duration: 600, easing: "easeOutCubic",
            update: function(){ el.textContent = obj.v + "%"; } });
  };

  /* 面板新行自动触发（监听 runLogBody 子节点增加） */
  function armLogObserver(){
    const body = document.getElementById("runLogBody");
    if(!body || body.dataset.mfAnime) return;
    body.dataset.mfAnime = "1";
    new MutationObserver(function(muts){
      muts.forEach(function(m){
        m.addedNodes.forEach(function(n){
          if(n.nodeType === 1 && n.classList.contains("run-log-line")) window.mfAnimLogLine(n);
        });
      });
    }).observe(body, { childList: true });
  }

  /* 步骤完成检测：观察 .run-step 内 dot-done 出现时触发弹跳 */
  function armStepObserver(){
    const v = document.getElementById("view");
    if(!v || v.dataset.mfStepAnime) return;
    v.dataset.mfStepAnime = "1";
    new MutationObserver(function(){
      document.querySelectorAll(".run-step .dot-done:not([data-anim])").forEach(function(d){
        d.dataset.anim = "1";
        window.mfAnimStepDone(d);
      });
      const pct = document.querySelector(".rp-pct");
      if(pct && pct.dataset.lastPct !== pct.textContent){
        const target = parseInt(pct.textContent) || 0;
        if(pct.dataset.lastPct !== undefined && target !== (parseInt(pct.dataset.lastPct)||0)){
          window.mfAnimProgress(pct, target);
        }
        pct.dataset.lastPct = pct.textContent;
      }
    }).observe(v, { childList: true, subtree: true });
    // 日志面板观察器挂载（面板可能后建）
    setTimeout(armLogObserver, 300);
    setTimeout(armLogObserver, 1200);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", armStepObserver);
  } else {
    armStepObserver();
  }
})();
