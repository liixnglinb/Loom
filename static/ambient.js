/* ModelFlow · 环境微光粒子层（E1：浅底淡蓝/淡紫微光，克制版）
   设计意图：在白底 + 点阵网格之上叠加极淡的蓝紫「微光粒子」，呼应
   「清亮通透」的偏好，但保持低饱和、低密度、慢速漂移，不做密集科技感。
   降级：prefers-reduced-motion 时只画一帧静态、不运行动画；
   canvas 不支持 / 出错时静默退出。纯装饰，aria-hidden。 */
(function () {
  "use strict";
  var c = document.getElementById("ambientParticles");
  if (!c || !c.getContext) return;
  var ctx = c.getContext("2d");
  var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var DPR = window.devicePixelRatio || 1;

  // 低饱和「微光」色板（蓝 / 淡紫 / 青，alpha 靠粒子自身呼吸）
  var HUES = [218, 228, 248, 195];          // 蓝 / 蓝紫 / 浅蓝紫 / 青
  var SAT = 38, LIGHT = 66;
  var MAX_PARTICLES = 54;

  var parts = [], W = 0, H = 0, RAF = null;

  function resize() {
    W = window.innerWidth; H = window.innerHeight;
    c.width = Math.floor(W * DPR); c.height = Math.floor(H * DPR);
    c.style.width = W + "px"; c.style.height = H + "px";
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
  }

  function seed() {
    parts = [];
    for (var i = 0; i < MAX_PARTICLES; i++) {
      parts.push({
        x: Math.random() * W,
        y: Math.random() * H,
        r: 1.2 + Math.random() * 2.1,          // 半径 1.2-3.3px，细小微光
        vx: (Math.random() - 0.5) * 0.16,       // 慢速漂移
        vy: (Math.random() - 0.5) * 0.16,
        ph: Math.random() * Math.PI * 2,         // 呼吸相位
        sp: 0.004 + Math.random() * 0.014,       // 呼吸速率
        a: 0.10 + Math.random() * 0.18,          // 基础透明度 0.10-0.28
        h: HUES[(Math.random() * HUES.length) | 0]
      });
    }
  }

  function drawFrame(t) {
    ctx.clearRect(0, 0, W, H);
    for (var i = 0; i < parts.length; i++) {
      var p = parts[i];
      p.x += p.vx; p.y += p.vy;
      if (p.x < -8) p.x = W + 8; else if (p.x > W + 8) p.x = -8;
      if (p.y < -8) p.y = H + 8; else if (p.y > H + 8) p.y = -8;
      var breath = 0.5 + 0.5 * Math.sin(t * p.sp + p.ph);
      var alpha = p.a * (0.45 + 0.55 * breath);
      ctx.globalAlpha = alpha;
      // 径向微光：中心亮核 + 外周淡晕（fillStyle 用 HSL，低饱和）
      var color = "hsla(" + p.h + "," + SAT + "%," + LIGHT + "%,1)";
      var grad = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * 4);
      grad.addColorStop(0, color);
      grad.addColorStop(1, "hsla(" + p.h + "," + SAT + "%," + LIGHT + "%,0)");
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r * 4, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  function loop(t) { drawFrame(t || 0); RAF = requestAnimationFrame(loop); }

  // DOM 就绪后初始化（defer 脚本入口）
  function warmup() {
    resize(); seed();
    if (reduced) { drawFrame(0); return; }      // 静态一帧，尊重减弱动效
    loop();
  }

  window.addEventListener("resize", function () { resize(); if (reduced) drawFrame(0); });
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", warmup);
  else warmup();
})();