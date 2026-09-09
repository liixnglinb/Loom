/* ==========================================================================
 * ModelFlow 智模流水线 · 单页应用
 * 路由：#/relative. 视图：list / new / run / settings
 * ========================================================================== */
(() => {
'use strict';

/* ---------------- 工具 ---------------- */
const $ = s => document.querySelector(s);
const $$ = s => Array.from(document.querySelectorAll(s));

function esc(s){ return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function escd(s){ return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

async function api(path, opts){
  const r = await fetch(path, opts);
  const ct = r.headers.get('content-type')||'';
  if(ct.includes('application/json')) return r.json();
  if(!r.ok) throw new Error('HTTP '+r.status);
  return r.text();
}
function post(path, data){
  return api(path, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data||{})});
}
function put(path, data){
  return api(path, {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data||{})});
}

let toastTimer=null;
function toast(msg, ok=false){
  const el = $('#toast');
  if(!el) return;
  el.textContent = msg||'';
  el.className = 'toast show '+(ok?'ok':'err');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(()=>{ el.className='toast'; }, 2000);
}

function fmtSize(b){ if(!b&&b!==0) return ''; if(b>=1048576) return (b/1048576).toFixed(1)+' MB'; if(b>=1024) return (b/1024).toFixed(0)+' KB'; return b+' B'; }
function fmtDur(sec){
  if(sec==null) return '';
  sec=Math.round(sec); if(sec<0) sec=0;
  if(sec<60) return sec+' 秒';
  if(sec<3600) return Math.floor(sec/60)+' 分 '+(sec%60)+' 秒';
  return Math.floor(sec/3600)+' 时 '+Math.floor((sec%3600)/60)+' 分';
}
function fileIcon(name){
  const ext = (name.split('.').pop()||'').toLowerCase();
  if(ext==='json') return '<span class="fif fif-json">J</span>';
  if(ext==='md')   return '<span class="fif fif-md">M↓</span>';
  if(ext==='py')   return '<span class="fif fif-py">py</span>';
  if(ext==='pdf')  return '<span class="fif fif-pdf">PDF</span>';
  if(['png','jpg','jpeg','gif','svg'].includes(ext)) return '<span class="fif fif-img">▦</span>';
  return '<span class="fif fif-def">📄</span>';
}

/* 常用 SVG 图标（Voyra 线性细描边风格，stroke-width 1.5） */
const ICON = {
  list: "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><path d=\"M11 19.5h10M11 12.5h10M11 5.5h10M3 5.5l1 1 3-3M3 12.5l1 1 3-3M3 19.5l1 1 3-3\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/></svg>",
  plus: "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><path d=\"M6 12h12M12 18V6\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/></svg>",
  run:  "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><path d=\"M4 12V8.44c0-4.42 3.13-6.23 6.96-4.02l3.09 1.78 3.09 1.78c3.83 2.21 3.83 5.83 0 8.04l-3.09 1.78-3.09 1.78C7.13 21.79 4 19.98 4 15.56V12Z\" stroke-width=\"1.5\" stroke-miterlimit=\"10\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/></svg>",
  gear: "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><path d=\"M3 9.11v5.77C3 17 3 17 5 18.35l5.5 3.18c.83.48 2.18.48 3 0l5.5-3.18c2-1.35 2-1.35 2-3.46V9.11C21 7 21 7 19 5.65l-5.5-3.18c-.82-.48-2.17-.48-3 0L5 5.65C3 7 3 7 3 9.11Z\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><path d=\"M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/></svg>",
  home: "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><path d=\"m9.02 2.84-5.39 4.2C2.73 7.74 2 9.23 2 10.36v7.41c0 2.32 1.89 4.22 4.21 4.22h11.58c2.32 0 4.21-1.9 4.21-4.21V10.5c0-1.21-.81-2.76-1.8-3.45l-6.18-4.33c-1.4-.98-3.65-.93-5 .12ZM12 17.99v-3\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/></svg>",
};
/* 工具页卡片图标 */
const TOOL_ICON = {
  search: "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><path d=\"M11.5 21a9.5 9.5 0 1 0 0-19 9.5 9.5 0 0 0 0 19ZM22 22l-2-2\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/></svg>",
  image: "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><path d=\"M9 22h6c5 0 7-2 7-7V9c0-5-2-7-7-7H9C4 2 2 4 2 9v6c0 5 2 7 7 7Z\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><path d=\"M9 10a2 2 0 1 0 0-4 2 2 0 0 0 0 4ZM2.67 18.95l4.93-3.31c.79-.53 1.93-.47 2.64.14l.33.29c.78.67 2.04.67 2.82 0l4.16-3.57c.78-.67 2.04-.67 2.82 0L22 13.9\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/></svg>",
  review: "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><path d=\"M16 2H8C4 2 2 4 2 8v13c0 .55.45 1 1 1h13c4 0 6-2 6-6V8c0-4-2-6-6-6Z\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><path d=\"M7 9.5h10M7 14.5h7\" stroke-width=\"1.5\" stroke-miterlimit=\"10\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/></svg>",
  check: "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><path d=\"M12 22c5.5 0 10-4.5 10-10S17.5 2 12 2 2 6.5 2 12s4.5 10 10 10Z\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><path d=\"m7.75 12 2.83 2.83 5.67-5.66\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/></svg>",
  derive: "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><path d=\"M22 10v5c0 5-2 7-7 7H9c-5 0-7-2-7-7V9c0-5 2-7 7-7h5\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><path d=\"M22 10h-4c-3 0-4-1-4-4V2l8 8ZM7 13h6M7 17h4\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/></svg>",
};

/* ============================================================
 * Iconsax 线性图标（Linear · 24px · 社区开自版，本地内联无需 CDN）
 * ============================================================ */
const IX = {
  flash:'<path d="M6.09 13.28h3.09v7.2c0 1.68.91 2.02 2.02.76l7.57-8.6c.93-1.05.54-1.92-.87-1.92h-3.09v-7.2c0-1.68-.91-2.02-2.02-.76l-7.57 8.6c-.92 1.06-.53 1.92.87 1.92Z" stroke-width="1.5" stroke-miterlimit="10" stroke-linecap="round" stroke-linejoin="round"/>',
  cup:'<path d="M12.15 16.5v2.1" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M7.15 22h10v-1c0-1.1-.9-2-2-2h-6c-1.1 0-2 .9-2 2v1Z" stroke-width="1.5" stroke-miterlimit="10"/><path d="M6.15 22h12M12 16c-3.87 0-7-3.13-7-7V6c0-2.21 1.79-4 4-4h6c2.21 0 4 1.79 4 4v3c0 3.87-3.13 7-7 7Z" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M5.47 11.65c-.75-.24-1.41-.68-1.93-1.2-.9-1-1.5-2.2-1.5-3.6s1.1-2.5 2.5-2.5h.65c-.2.46-.3.97-.3 1.5v3c0 1 .21 1.94.58 2.8ZM18.53 11.65c.75-.24 1.41-.68 1.93-1.2.9-1 1.5-2.2 1.5-3.6s-1.1-2.5-2.5-2.5h-.65c.2.46.3.97.3 1.5v3c0 1-.21 1.94-.58 2.8Z" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>',
  medal:'<path d="M12 15c3.728 0 6.75-2.91 6.75-6.5S15.728 2 12 2 5.25 4.91 5.25 8.5 8.272 15 12 15Z" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="m7.52 13.52-.01 7.38c0 .9.63 1.34 1.41.97l2.68-1.27c.22-.11.59-.11.81 0l2.69 1.27c.77.36 1.41-.07 1.41-.97v-7.56" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>',
  search:'<path d="M11.5 21a9.5 9.5 0 1 0 0-19 9.5 9.5 0 0 0 0 19ZM22 22l-2-2" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>',
  pencil:'<path d="m13.26 3.6-8.21 8.69c-.31.33-.61.98-.67 1.43l-.37 3.24c-.13 1.17.71 1.97 1.87 1.77l3.22-.55c.45-.08 1.08-.41 1.39-.75l8.21-8.69c1.42-1.5 2.06-3.21-.15-5.3-2.2-2.07-3.87-1.34-5.29.16Z" stroke-width="1.5" stroke-miterlimit="10" stroke-linecap="round" stroke-linejoin="round"/><path d="M11.89 5.05a6.126 6.126 0 0 0 5.45 5.15M3 22h18" stroke-width="1.5" stroke-miterlimit="10" stroke-linecap="round" stroke-linejoin="round"/>',
  doc:'<path d="M21 7v10c0 3-1.5 5-5 5H8c-3.5 0-5-2-5-5V7c0-3 1.5-5 5-5h8c3.5 0 5 2 5 5Z" stroke-width="1.5" stroke-miterlimit="10" stroke-linecap="round" stroke-linejoin="round"/><path d="M14.5 4.5v2c0 1.1.9 2 2 2h2M8 13h4M8 17h8" stroke-width="1.5" stroke-miterlimit="10" stroke-linecap="round" stroke-linejoin="round"/>',
  bulb:'<path d="M10.5 16h3c2.5 0 4-1.8 4-4V6.91c0-1.05-.86-1.91-1.91-1.91H8.42c-1.05 0-1.91.86-1.91 1.91V12C6.5 14.2 8 16 10.5 16ZM9.5 2v3M14.5 2v3M12 22v-6" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>',
  globe:'<path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10Z" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M8 3h1a28.424 28.424 0 0 0 0 18H8M15 3a28.424 28.424 0 0 1 0 18" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M3 16v-1a28.424 28.424 0 0 0 18 0v1M3 9a28.424 28.424 0 0 1 18 0" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>',
  dl:'<path stroke-linecap="round" stroke-linejoin="round" stroke-miterlimit="10" stroke-width="1.5" d="M9.32 11.68l2.56 2.56 2.56-2.56M11.88 4v10.17"/> <path stroke-linecap="round" stroke-linejoin="round" stroke-miterlimit="10" stroke-width="1.5" d="M20 12.18c0 4.42-3 8-8 8s-8-3.58-8-8"/>',
  bookOpen:'<path d="M22 16.74V4.67c0-1.2-.98-2.09-2.17-1.99h-.06c-2.1.18-5.29 1.25-7.07 2.37l-.17.11c-.29.18-.77.18-1.06 0l-.25-.15C9.44 3.9 6.26 2.84 4.16 2.67 2.97 2.57 2 3.47 2 4.66v12.08c0 .96.78 1.86 1.74 1.98l.29.04c2.17.29 5.52 1.39 7.44 2.44l.04.02c.27.15.7.15.96 0 1.92-1.06 5.28-2.17 7.46-2.46l.33-.04c.96-.12 1.74-1.02 1.74-1.98ZM12 5.49v15M7.75 8.49H5.5M8.5 11.49h-3" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>',
  book:'<path d="M3.5 18V7c0-4 1-5 5-5h7c4 0 5 1 5 5v10c0 .14 0 .28-.01.42" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M6.35 15H20.5v3.5c0 1.93-1.57 3.5-3.5 3.5H7c-1.93 0-3.5-1.57-3.5-3.5v-.65C3.5 16.28 4.78 15 6.35 15ZM8 7h8M8 10.5h5" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>',
  flask:'<path d="M10 17.5h4M2 17.5v-10c0-4 1-5 5-5M22 17.5v-10c0-4-1-5-5-5" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M10 15.91v3.29c0 2-.8 2.8-2.8 2.8H4.8c-2 0-2.8-.8-2.8-2.8v-3.29c0-2 .8-2.8 2.8-2.8h2.4c2 0 2.8.8 2.8 2.8ZM22 15.91v3.29c0 2-.8 2.8-2.8 2.8h-2.4c-2 0-2.8-.8-2.8-2.8v-3.29c0-2 .8-2.8 2.8-2.8h2.4c2 0 2.8.8 2.8 2.8Z" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>',
  micro:'<path d="m15.03 10.77 5.66-3.79c.57-.38.72-1.16.34-1.72l-1.82-2.71c-.38-.57-1.16-.72-1.72-.34L11.83 6l3.2 4.77Z" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="m12.174 6.48-4.778 3.2 2.56 3.821 4.778-3.2-2.56-3.822ZM5.83 15.9l3.95-2.64-2.24-3.34-3.95 2.64c-.46.31-.58.93-.27 1.39l1.13 1.68c.3.45.92.57 1.38.27ZM12.05 12.2 7.56 22M12 12.2l4.44 9.8" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>',
  chart:'<path d="M3 22h18M5.6 8.38H4c-.55 0-1 .45-1 1V18c0 .55.45 1 1 1h1.6c.55 0 1-.45 1-1V9.38c0-.55-.45-1-1-1ZM12.8 5.19h-1.6c-.55 0-1 .45-1 1V18c0 .55.45 1 1 1h1.6c.55 0 1-.45 1-1V6.19c0-.55-.45-1-1-1ZM20 2h-1.6c-.55 0-1 .45-1 1v15c0 .55.45 1 1 1H20c.55 0 1-.45 1-1V3c0-.55-.45-1-1-1Z" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>',
  rocket:'<path d="m7.4 6.32 8.49-2.83c3.81-1.27 5.88.81 4.62 4.62l-2.83 8.49c-1.9 5.71-5.02 5.71-6.92 0l-.84-2.52-2.52-.84c-5.71-1.9-5.71-5.01 0-6.92ZM10.11 13.65l3.58-3.59" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>',
  clipboard:'<path d="M8 12.2h7M8 16.2h4.38M10 6h4c2 0 2-1 2-2 0-2-1-2-2-2h-4C9 2 8 2 8 4s1 2 2 2Z" stroke-width="1.5" stroke-miterlimit="10" stroke-linecap="round" stroke-linejoin="round"/><path d="M16 4.02c3.33.18 5 1.41 5 5.98v6c0 4-1 6-6 6H9c-5 0-6-2-6-6v-6c0-4.56 1.67-5.8 5-5.98" stroke-width="1.5" stroke-miterlimit="10" stroke-linecap="round" stroke-linejoin="round"/>',
  user:'<path d="M12.16 10.87c-.1-.01-.22-.01-.33 0a4.42 4.42 0 0 1-4.27-4.43C7.56 3.99 9.54 2 12 2a4.435 4.435 0 0 1 .16 8.87ZM7.16 14.56c-2.42 1.62-2.42 4.26 0 5.87 2.75 1.84 7.26 1.84 10.01 0 2.42-1.62 2.42-4.26 0-5.87-2.74-1.83-7.25-1.83-10.01 0Z" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>',
  rotate:'<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M22 12c0 5.52-4.48 10-10 10s-8.89-5.56-8.89-5.56m0 0h4.52m-4.52 0v5M2 12C2 6.48 6.44 2 12 2c6.67 0 10 5.56 10 5.56m0 0v-5m0 5h-4.44"/>',
  shuffle:'<path stroke-linecap="round" stroke-linejoin="round" stroke-miterlimit="10" stroke-width="1.5" d="M20.5 14.99l-5.01 5.02M3.5 14.99h17M3.5 9.01l5.01-5.02M20.5 9.01h-17"/>',
  palette:'<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M10 4.5V18c0 1.08-.44 2.07-1.14 2.79l-.04.04c-.09.09-.19.18-.28.25-.3.26-.64.46-.99.6-.11.05-.22.09-.33.13-.39.13-.81.19-1.22.19-.27 0-.54-.03-.8-.08-.13-.03-.26-.06-.39-.1-.16-.05-.31-.1-.46-.17 0-.01 0-.01-.01 0-.28-.14-.55-.3-.8-.49l-.01-.01c-.13-.1-.25-.2-.36-.32-.11-.12-.22-.24-.33-.37-.19-.25-.35-.52-.49-.8.01-.01.01-.01 0-.01 0 0 0-.01-.01-.02-.06-.14-.11-.29-.16-.44a5.58 5.58 0 01-.1-.39c-.05-.26-.08-.53-.08-.8V4.5C2 3 3 2 4.5 2h3C9 2 10 3 10 4.5z"/> <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M22 16.5v3c0 1.5-1 2.5-2.5 2.5H6c.41 0 .83-.06 1.22-.19.11-.04.22-.08.33-.13.35-.14.69-.34.99-.6.09-.07.19-.16.28-.25l.04-.04 6.8-6.79h3.84c1.5 0 2.5 1 2.5 2.5zM4.81 21.82c-.6-.18-1.17-.51-1.64-.99-.48-.47-.81-1.04-.99-1.64a4.02 4.02 0 002.63 2.63z"/> <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M18.37 11.29L15.66 14l-6.8 6.79C9.56 20.07 10 19.08 10 18V8.34l2.71-2.71c1.06-1.06 2.48-1.06 3.54 0l2.12 2.12c1.06 1.06 1.06 2.48 0 3.54zM6 19a1 1 0 100-2 1 1 0 000 2z"/>',
  ruler:'<path stroke-linecap="round" stroke-width="1.5" d="M5 17h14c2 0 3-1 3-3v-4c0-2-1-3-3-3H5c-2 0-3 1-3 3v4c0 2 1 3 3 3zM18 7v5M6 7v4M10.05 7L10 12M14 7v3"/>',
  target:'<path d="M6.45 2v20M6.95 4l8.1 3.5c3.3 1.4 3.3 3.8.2 5.4L6.95 17" stroke-width="1.5" stroke-miterlimit="10" stroke-linecap="round" stroke-linejoin="round"/>',
  image:'<path d="M9 22h6c5 0 7-2 7-7V9c0-5-2-7-7-7H9C4 2 2 4 2 9v6c0 5 2 7 7 7Z" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M9 10a2 2 0 1 0 0-4 2 2 0 0 0 0 4ZM2.67 18.95l4.93-3.31c.79-.53 1.93-.47 2.64.14l.33.29c.78.67 2.04.67 2.82 0l4.16-3.57c.78-.67 2.04-.67 2.82 0L22 13.9" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>',
  wrench:'<path d="M3.17 7.44 12 12.55l8.77-5.08M12 21.61v-9.07" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M9.93 2.48 4.59 5.45c-1.21.67-2.2 2.35-2.2 3.73v5.65c0 1.38.99 3.06 2.2 3.73l5.34 2.97c1.14.63 3.01.63 4.15 0l5.34-2.97c1.21-.67 2.2-2.35 2.2-3.73V9.18c0-1.38-.99-3.06-2.2-3.73l-5.34-2.97c-1.15-.64-3.01-.64-4.15 0Z" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M17 13.24V9.58L7.51 4.1" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>',
  ban:'<path d="M14.9 2H9.1c-.68 0-1.64.4-2.12.88l-4.1 4.1C2.4 7.46 2 8.42 2 9.1v5.8c0 .68.4 1.64.88 2.12l4.1 4.1c.48.48 1.44.88 2.12.88h5.8c.68 0 1.64-.4 2.12-.88l4.1-4.1c.48-.48.88-1.44.88-2.12V9.1c0-.68-.4-1.64-.88-2.12l-4.1-4.1C16.54 2.4 15.58 2 14.9 2ZM8.5 15.5l7-7M15.5 15.5l-7-7" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>',
  folder:'<path d="M22 11v6c0 4-1 5-5 5H7c-4 0-5-1-5-5V7c0-4 1-5 5-5h1.5c1.5 0 1.83.44 2.4 1.2l1.5 2c.38.5.6.8 1.6.8h3c4 0 5 1 5 5Z" stroke-width="1.5" stroke-miterlimit="10"/><path d="M8 2h9c2 0 3 1 3 3v1.38" stroke-width="1.5" stroke-miterlimit="10" stroke-linecap="round" stroke-linejoin="round"/>',
};

const EMOJI2IX = {
  '⚡':'flash','🏆':'cup','🏅':'medal',
  '🔍':'search','🔎':'search',
  '✎':'pencil','✏':'pencil','✏️':'pencil','📝':'pencil','📄':'doc','📑':'doc','🖋':'pencil',
  '💡':'bulb','🌍':'globe','🌏':'globe','🌎':'globe','🌐':'globe',
  '⬇':'dl','📚':'bookOpen','📖':'book','🧪':'flask','🔬':'micro',
  '📊':'chart','📈':'chart','🚀':'rocket','📋':'clipboard','👤':'user',
  '🔁':'rotate','🔄':'rotate','🔀':'shuffle','🎨':'palette','📐':'ruler',
  '🖼':'image','🎯':'target','🧰':'wrench','⛔':'ban','🗂':'folder','🗂️':'folder',
};
const LUC_SVG = n => `<svg class="luc" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${IX[n]||''}</svg>`;
/* 遍历文本节点，把图标用途的 emoji 替换为 Iconsax SVG（幂等：替换后无映射残余即收敛） */
function applyIcons(root){
  const scope = (root && root.nodeType===1) ? root : document.body;
  const walker = document.createTreeWalker(scope, NodeFilter.SHOW_TEXT, {
    acceptNode(n){
      const p = n.parentElement;
      if(!p || p.closest('input,textarea,select,option,script,style,symbol,.luc,code,pre,#runLogBody,.run-live-body,#toast')) return NodeFilter.FILTER_REJECT;
      return NodeFilter.FILTER_ACCEPT;
    }
  });
  const texts=[]; let t; while((t=walker.nextNode())) texts.push(t);
  if(!texts.length) return;
  const keys=Object.keys(EMOJI2IX).sort((a,b)=>b.length-a.length);
  for(const tn of texts){
    let s=tn.nodeValue; if(!s) continue;
    let out=s, hit=false;
    for(const k of keys){ if(out.includes(k)){ hit=true; out=out.split(k).join(LUC_SVG(EMOJI2IX[k])); } }
    if(hit){ out=out.replace(/\uFE0F/g,''); const span=document.createElement('span'); span.className='tx'; span.innerHTML=out; tn.parentNode.replaceChild(span,tn); }
  }
}
/* 首次 + 后续动态渲染自动图标化 */
if(document.body) applyIcons(document.body);
else document.addEventListener('DOMContentLoaded', ()=>applyIcons(document.body));

/* ============================================================
 * Dropdown 通用下拉组件（Voyra 明亮极简）
 *   DD.menu(triggerEl, items, opts)   按钮式下拉（opts: align/left|right, minWidth, head）
 *   DD.auto(root)                     自动把原生 <select> 增强为同款下拉（保留 value/change）
 *   DD.closeAll()                     关闭当前打开的下拉（点外部 / Esc / 滚动 / 缩放已内置）
 * item = { icon:'iconsax键', label, sel, danger, disabled, onClick } | { head:'分组名' } | '-'
 */
const DD = (()=>{
  const CARET = '<svg class="dd-caret" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>';
  let cur = null;

  function itemHtml(it, i){
    if(it === '-') return '<div class="dd-sep"></div>';
    if(it && it.head) return `<div class="dd-head">${esc(it.head)}</div>`;
    it = it || {};
    const svg = it.svg || (it.icon ? LUC_SVG(it.icon) : '');
    const mark = it.sel ? '<svg class="dd-tick" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m7.4 12.6 3.1 3.1 6.2-6.4"/></svg>' : '';
    return `<button type="button" class="dd-item${it.sel?' sel':''}${it.danger?' danger':''}" data-i="${i}"${it.disabled?' disabled':''}>${svg}<span class="dd-lb">${esc(it.label || '')}</span>${mark}</button>`;
  }

  function panelBody(items){
    return items.map((it, i) => itemHtml(it, i)).join('');
  }

  function open(trig, items, opts){
    close(true);
    const o = Object.assign({align:'left', minWidth:192}, opts || {});
    const panel = document.createElement('div');
    panel.className = 'dd-panel';
    panel.style.minWidth = o.minWidth + 'px';
    panel.innerHTML = panelBody(items);
    document.body.appendChild(panel);
    trig.classList.add('open');
    const place = ()=>{
      const r = trig.getBoundingClientRect();
      const pr = panel.getBoundingClientRect();
      let left = o.align==='right' ? r.right - pr.width : r.left;
      if(left < 8) left = 8;
      if(left + pr.width > innerWidth - 8) left = innerWidth - pr.width - 8;
      let top = r.bottom + 6;
      if(top + pr.height > innerHeight - 8){ top = r.top - pr.height - 6; if(top < 8) top = 8; }
      panel.style.left = left + 'px';
      panel.style.top = top + 'px';
    };
    place();
    // 菜单项点击
    const els = [...panel.querySelectorAll('.dd-item')];
    els.forEach((el, i) => {
      const it = items[i];
      if(!it || it.disabled || it.head || it === '-') return;
      el.addEventListener('click', ()=>{
        if(it.sticky !== true){
          close();
          trig.focus && trig.focus();
        }
        try{ it.onClick && it.onClick(); }catch(e){ console.warn('dd:', e); }
      });
    });
    // 键盘导航
    panel.addEventListener('keydown', (e)=>{
      const list = [...panel.querySelectorAll('.dd-item:not(:disabled)')];
      if(e.key === 'Escape'){ e.preventDefault(); close(); trig.focus && trig.focus(); return; }
      if(!list.length) return;
      let idx = list.indexOf(document.activeElement);
      if(e.key === 'ArrowDown'){ e.preventDefault(); list[(idx+1)%list.length].focus(); }
      else if(e.key === 'ArrowUp'){ e.preventDefault(); list[(idx-1+list.length)%list.length].focus(); }
      else if(e.key === 'Enter' && idx >= 0){ e.preventDefault(); list[idx].click(); }
    });
    const first = els.find(el => !el.disabled);
    if(first) first.focus();
    // 面板适配后再补一次定位（滚动条出现后高度变化）
    requestAnimationFrame(place);
    cur = {trig, panel};
  }

  function close(instant){
    if(!cur) return;
    const {trig, panel} = cur;
    cur = null;
    trig.classList.remove('open');
    if(instant){ panel.remove(); return; }
    panel.classList.add('closing');
    setTimeout(()=>panel.remove(), 120);
  }

  /* 原生 select → 同款下拉（不动 value/change 语义，所有读 .value/onchange 的逻辑照常工作） */
  function enhanceSelect(sel){
    if(sel.dataset.ddSel) return;
    sel.dataset.ddSel = '1';
    const w = sel.getBoundingClientRect().width || 180;
    const wrap = document.createElement('span');
    wrap.className = 'dd';
    const inline = sel.getAttribute('style') || '';
    const isFlex = /flex\s*:/i.test(inline);
    if(inline) wrap.setAttribute('style', inline.replace(/width\s*:[^;]+;/i, ''));
    const trig = document.createElement('button');
    trig.type = 'button';
    trig.className = 'dd-trig';
    if(sel.disabled) trig.classList.add('is-disabled');
    const val = document.createElement('span');
    val.className = 'dd-val';
    trig.appendChild(val);
    trig.insertAdjacentHTML('beforeend', CARET);
    const sync = ()=>{
      const idx = sel.selectedIndex;
      const t = (idx >= 0 && sel.options[idx]) ? sel.options[idx].text : '';
      val.textContent = t === undefined ? '' : t;
    };
    sync();
    sel.tabIndex = -1;
    sel.classList.add('dd-sel-hidden');
    /* ⚠️ 顺序必须：先用 wrap 原位替换 sel（此时 sel 仍是原父节点的子节点，
     * replaceChild 合法），再把 trig/sel 移进 wrap。原先先 append 再 replaceChild，
     * 会让 wrap 变成 sel 的父节点后触发 HierarchyRequestError，select 被移出文档。 */
    sel.parentNode.replaceChild(wrap, sel);
    wrap.appendChild(trig);
    wrap.appendChild(sel);
    /* flex 布局（如逐步骤下拉）保留弹性填充；否则按原宽固定 */
    if(isFlex) wrap.style.minWidth = '120px';
    else wrap.style.width = Math.max(w, 120) + 'px';
    trig.addEventListener('click', (ev)=>{
      ev.stopPropagation();
      if(sel.disabled) return;
      if(cur && cur.trig === trig){ close(); return; }
      const items = [...sel.options].map((opt, i)=>({
        label: opt.text || opt.value,
        sel: opt.selected,
        onClick: ()=>{ sel.selectedIndex = i; sel.dispatchEvent(new Event('change', {bubbles:true})); }
      }));
      open(trig, items, {minWidth: 200});
    });
    /* 外部程序改 select.value 时同步触发器文本 */
    sel.addEventListener('change', sync);
  }

  function auto(root){
    const scope = (root && root.nodeType === 1) ? root : document.body;
    scope.querySelectorAll('select:not([data-dd-sel])').forEach(enhanceSelect);
  }

  /* 点外部关闭（捕获阶段，先于触发器自身事件判定） */
  document.addEventListener('pointerdown', (e)=>{
    if(!cur) return;
    if(cur.panel.contains(e.target) || cur.trig.contains(e.target)) return;
    close();
  }, true);
  document.addEventListener('keydown', (e)=>{ if(e.key === 'Escape' && cur) close(); });
  window.addEventListener('resize', ()=>{ if(cur) close(true); }, true);
  document.addEventListener('scroll', (e)=>{
    if(cur && !cur.panel.contains(e.target)) close(true);
  }, true);

  auto();
  return {menu:open, closeAll:close, auto, enhance:enhanceSelect};
})();
const __icMO = new MutationObserver(()=>{ requestAnimationFrame(()=>{ applyIcons(document.body); DD.auto(); }); });
if(document.body) __icMO.observe(document.body,{childList:true,subtree:true});

/* ---------------- 状态 ---------------- */
const ST = {
  workflows: [], presets: [], defaultPreset: null, pipelines: [],
  filter: 'all', wfTimer: null,
  running: new Set(),
};

/* 模板 -> 展示名 & 分组 */
const TEMPLATE_META = {
  competition:['竞赛极速流','competition','🏆'],
  competition_bzd:['BZD 双审精制流','competition','🏅'],
  competition_mathmodel:['个人自制流','competition','🧭'],
  competition_modex:['Modex 原版流','competition','🎯'],
};
const STATUS_TXT = {completed:['已完成','st-completed'], running:['运行中','st-running'],
  failed:['失败','st-failed'], pending:['待运行','st-pending'], paused:['已暂停','st-pending']};

function tplName(t){ const m=TEMPLATE_META[t]; return m?m[0]:t; }

/* 统计卡图标（线性 SVG，随主题色） */
const STAT_ICO = {
  total: "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><path d=\"M22 8.52V3.98C22 2.57 21.36 2 19.77 2h-4.04c-1.59 0-2.23.57-2.23 1.98v4.53c0 1.42.64 1.98 2.23 1.98h4.04c1.59.01 2.23-.56 2.23-1.97ZM22 19.77v-4.04c0-1.59-.64-2.23-2.23-2.23h-4.04c-1.59 0-2.23.64-2.23 2.23v4.04c0 1.59.64 2.23 2.23 2.23h4.04c1.59 0 2.23-.64 2.23-2.23ZM10.5 8.52V3.98C10.5 2.57 9.86 2 8.27 2H4.23C2.64 2 2 2.57 2 3.98v4.53c0 1.42.64 1.98 2.23 1.98h4.04c1.59.01 2.23-.56 2.23-1.97ZM10.5 19.77v-4.04c0-1.59-.64-2.23-2.23-2.23H4.23c-1.59 0-2.23.64-2.23 2.23v4.04C2 21.36 2.64 22 4.23 22h4.04c1.59 0 2.23-.64 2.23-2.23Z\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/></svg>",
  run: "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><path d=\"M6.09 13.28h3.09v7.2c0 1.68.91 2.02 2.02.76l7.57-8.6c.93-1.05.54-1.92-.87-1.92h-3.09v-7.2c0-1.68-.91-2.02-2.02-.76l-7.57 8.6c-.92 1.06-.53 1.92.87 1.92Z\" stroke-width=\"1.5\" stroke-miterlimit=\"10\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/></svg>",
  done: "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><path d=\"M12 22c5.5 0 10-4.5 10-10S17.5 2 12 2 2 6.5 2 12s4.5 10 10 10Z\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><path d=\"m7.75 12 2.83 2.83 5.67-5.66\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/></svg>",
  fail: "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><path d=\"M12 22c5.5 0 10-4.5 10-10S17.5 2 12 2 2 6.5 2 12s4.5 10 10 10ZM9.17 14.83l5.66-5.66M14.83 14.83 9.17 9.17\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/></svg>",
};

function statCard(cls,ico,num,lbl){
  const arr=['sv-total','sv-run','sv-done','sv-fail'];
  const n=String(arr.indexOf(cls)+1).padStart(2,'0');
  return `<div class="stat ${cls}" data-num="${n}"><span class="stat-ico">${STAT_ICO[ico]}</span>
    <span><b class="num">${num}</b><span class="lbl">${lbl}</span></span>
    <span class="stat-ghost-num">${n}</span></div>`;
}

/* ---------------- 布局（顶部导航 & 面包屑） ---------------- */
const NAV = [
  {id:'list', label:'工作流', ico:ICON.list},
  {id:'new',  label:'新建', ico:ICON.plus},
  {id:'pipelines', label:'编排', ico:ICON.list},
  {id:'skills', label:'技能', ico:ICON.list},
  {id:'run-placeholder', label:'运行', ico:ICON.run, hidden:true},
];
function renderNav(active){
  $('#mainNav').innerHTML = NAV.filter(n=>!n.hidden).map(n=>
    `<a class="tn-link ${n.id===active?'active':''}" data-v="${n.id}" onclick="nav.go('${n.id}')">${n.label}</a>`).join('');
  updateTnModel();
}
async function updateTnModel(){
  try{
    const r = await api('/api/providers');
    ST.presets = r.presets||[]; ST.defaultPreset = r.default||null;
  }catch(e){}
}

/* ---------------- 路由 ---------------- */
/* 页面切换过渡：离场用 transition 淡出（mf-leave），入场用一次性 animation 淡入上浮（mf-enter）。
   两者都只挂在固定容器 #view 上，不随 innerHTML全局部重建触发，杜绝闪烁与渲染冲突。 */
function viewTransitionOut(){
  const v = document.getElementById('view');
  if(!v) return Promise.resolve();
  v.classList.remove('mf-enter');
  v.classList.add('mf-leave');
  return new Promise(r=>setTimeout(r, 180));
}
function viewTransitionIn(){
  const v = document.getElementById('view');
  if(!v) return;
  v.classList.remove('mf-leave');
  // 先摘掉旧动画 class 并强制回流，再加回，确保每次切换都重新播放一次入场动画
  v.classList.remove('mf-enter');
  void v.offsetWidth;
  v.classList.add('mf-enter');
}

let NAV_SEQ=0;
const nav = {
  go(id, extra){
    let hash = '#/'+id;
    if(extra) hash += '/'+extra;
    if(location.hash === hash && id==='run-placeholder') return;
    if(location.hash === hash){ nav.resolve(); return; }
    location.hash = hash;
  },
  resolve(){
    const seq=++NAV_SEQ;
    // 优先 pathname（直接访问 /new /settings /run/5），其次 hash
    let raw = (location.hash||'').replace(/^#\/?/,'');
    const path = location.pathname;
    if(!raw){
      if(path==='/new') raw='new';
      else if(path==='/tools') raw='tools';
      else if(path==='/settings') raw='settings';
      else { const m=path.match(/^\/run\/(\d+)/); if(m) raw='run/'+m[1]; else raw='list'; }
    }
    const [view, ...rest] = raw.split('/');
    const extra = rest.join('/');
    viewTransitionOut().then(async ()=>{
      if(seq!==NAV_SEQ) return;
      if(view==='run'){ await renderRun(extra); renderNav('run-placeholder'); }
      else if(view==='new'){ await renderNew(); renderNav('new'); }
      else if(view==='tools'){ renderTools(); renderNav('tools'); }
      else if(view==='settings'){ await renderSettings(); renderNav('settings'); }
      else if(view==='pipelines'){ await window.renderPipelines(); renderNav('pipelines'); }
      else if(view==='pipeline-edit'){ await window.renderPipelineEdit(extra); renderNav('pipelines'); }
      else if(view==='skills'){ await window.renderSkills(); renderNav('skills'); }
      else if(view==='skill-edit'){ await window.renderSkillEdit(extra); renderNav('skills'); }
      else { await renderList(); renderNav('list'); }
      if(seq===NAV_SEQ) viewTransitionIn();
    });
  },
};
window.nav = nav;

/* ================= 视图：工作流列表 ================= */
async function renderList(){
  $('#view').innerHTML=`<div class="loading-bar"></div>    </div>
`;
  try{ ST.workflows = await api('/api/workflows'); }catch(e){ ST.workflows=[]; }

  // 统计
  const all=ST.workflows.length, run=ST.workflows.filter(w=>w.status==='running').length,
        done=ST.workflows.filter(w=>w.status==='completed').length,
        fail=ST.workflows.filter(w=>w.status==='failed').length;
  const cnt = k=>ST.workflows.filter(w=>w.template===k).length;
  const acadCount = Object.keys(TEMPLATE_META).filter(k=>TEMPLATE_META[k][1]==='acad').reduce((a,k)=>a+cnt(k),0);

  $('#view').innerHTML = `
    <div class="page-head">
      <div><h1>工作流</h1><div class="sub">管理你的科研与竞赛流水线</div></div>
      <div style="display:flex;gap:10px">
        ${run>0?'<button class="btn btn-ghost btn-sm" onclick="location.href=\'/\'">刷新</button>':''}
      </div>
    </div>
    <div class="stats">
      ${statCard('sv-total','total',all,'总计')}
      ${statCard('sv-run','run',run,'运行中')}
      ${statCard('sv-done','done',done,'已完成')}
      ${statCard('sv-fail','fail',fail,'失败')}
    </div>
    <div class="card">
      <div class="filter-bar">
        <span class="chip" data-f="all" onclick="listSetFilter(this)">全部 <span>(${all})</span></span>
        <span class="chip" data-f="competition" onclick="listSetFilter(this)">竞赛 <span>(${cnt('competition')})</span></span>
        <span class="chip" data-f="acad" onclick="listSetFilter(this)">学术写作 <span>(${acadCount})</span></span>
        <div style="flex:1"></div>
        <button class="btn btn-primary btn-sm" onclick="nav.go('new')">+ 新建工作流</button>
      </div>
      <table class="table">
        <thead><tr><th style="width:30px"></th><th>标题</th><th>模板</th><th>状态</th><th>创建时间</th><th style="width:130px"></th></tr></thead>
        <tbody id="listBody"></tbody>
      </table>
    </div>`;
  listRenderBody();
  clearInterval(ST.wfTimer);
  if(run>0){
    ST.wfTimer = setInterval(async ()=>{
      try{ ST.workflows = await api('/api/workflows'); }catch(e){}
      listRenderBody();
      updateNavState();
      if(!ST.workflows.some(w=>w.status==='running')){ clearInterval(ST.wfTimer); renderList(); }
    }, 3000);
  }
}

function listCurrentFilter(){
  const c = $('.filter-bar .chip.active');
  return c ? c.dataset.f : ST.filter;
}
function listSetFilter(el){
  $$('.filter-bar .chip').forEach(c=>c.classList.remove('active'));
  el.classList.add('active'); ST.filter=el.dataset.f; listRenderBody();
}

function listRenderBody(){
  const f = listCurrentFilter();
  const list = f==='all' ? ST.workflows
     : f==='acad' ? ST.workflows.filter(w=>TEMPLATE_META[w.template]&&TEMPLATE_META[w.template][1]==='acad')
     : ST.workflows.filter(w=>w.template===f);
  const tb = $('#listBody');
  if(!tb) return;
  if(!list.length){ tb.innerHTML='<tr class="no-tr"><td colspan="6">暂无工作流，点击右上角「新建工作流」开始 →</td></tr>'; return; }
  tb.innerHTML = list.map(w=>{
    const st = STATUS_TXT[w.status]||STATUS_TXT.pending;
    const meta = TEMPLATE_META[w.template];
    const rowState = w.status==='completed'?'bar-done':w.status==='running'?'bar-run'
      :w.status==='failed'?'bar-fail':w.status==='paused'?'bar-pause':'bar-wait';
    const pct = w.progress||0;
    return `<tr>
      <td><span style="font-size:16px;opacity:.7">${meta?meta[2]:(w.template==='competition'?'🏆':'📄')}</span></td>
      <td><a href="#/run/${w.id}" style="font-weight:600">${esc(w.title)}</a>
        <div class="step-tag" title="步骤 Key: ${esc(w.step||'')}">步骤: ${esc(listStepName(w.step))} · ${pct}%</div>
        ${pct>0?`<div class="mini-bar ${rowState}" style="width:${Math.min(100,pct)}%"></div>`:''}</td>
      <td><span class="tpl-badge">${esc(tplName(w.template))}</span></td>
      <td><span class="badge ${st[1]}"><i></i>${st[0]}</span></td>
      <td class="muted ts-cell" title="${esc(w.created_at||'')}">${relDate(w.created_at)}</td>
      <td><div class="row-actions">
        <button class="btn btn-ghost btn-sm" onclick="location.hash='#/run/${w.id}'">查看</button>
        <button class="btn btn-ghost btn-sm ra-del" onclick="delFlow(${w.id})">删除</button>
      </div></td>
    </tr>`;
  }).join('');
}
/* 列表步骤 Key → 中文名（未知 Key 回退原文，不抛错） */
function listStepName(key){
  if(!key) return '—';
  try{
    const s = (typeof COMP_STEPS!=='undefined' && Array.isArray(COMP_STEPS)) ? COMP_STEPS.find(x=>x.key===key) : null;
    return s ? s.label : key;
  }catch(e){ return key; }
}
/* "YYYY-MM-DD HH:MM:SS" → 本地相对时间（原始串放 title） */
function relDate(str){
  if(!str) return '';
  const m = String(str).match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?/);
  if(!m) return str;
  const ts = new Date(+m[1], +m[2]-1, +m[3], +m[4], +m[5], +(m[6]||0)).getTime();
  return _relTime(ts);
}
function appConfirm(msg, opt){
  opt = opt || {};
  return new Promise(resolve=>{
    const prevFocus = document.activeElement;
    const old=document.getElementById('appConfirmRoot'); if(old) old.remove();
    const root=document.createElement('div');
    root.id='appConfirmRoot'; root.className='modal open';
    const okCls = opt.danger ? 'btn btn-danger' : 'btn btn-primary';
    const okTxt = opt.okText || '确定';
    // 结构：短标题 + （可选）正文描述 —— 不再把整句长文案放大成 h3
    const title = opt.title ? opt.title : String(msg).replace(/\n[\s\S]*$/, '');
    let body = '';
    if(opt.title){ body = String(msg); }
    else if(String(msg).indexOf('\n') > 0){
      body = String(msg).split('\n').slice(1).join('\n');
    }
    root.innerHTML=`<div class="modal-box" style="width:420px" role="dialog" aria-modal="true" aria-label="${esc(opt.title||'确认操作')}">
      <div class="modal-top"><div><h3 style="font-size:15px;line-height:1.4">${esc(title)}</h3></div>
        <button class="modal-x" aria-label="关闭" data-act="0">×</button></div>
      ${body?`<div style="padding:2px 20px 14px;color:var(--muted);font-size:13px;line-height:1.6">${esc(body)}</div>`:''}
      <div style="padding:14px 18px;display:flex;gap:10px;justify-content:flex-end;border-top:1px solid var(--line,#e5e7eb)">
        <button class="btn btn-ghost" data-act="0">取消</button>
        <button class="${okCls}" data-act="1" autofocus>${esc(okTxt)}</button>
      </div></div>`;
    document.body.appendChild(root);
    const _box=root.querySelector('.modal-box'); if(_box){ _box.classList.add('mf-pop'); }
    const okBtn=root.querySelector('[data-act="1"]'); if(okBtn && okBtn.focus){ try{ okBtn.focus(); }catch(e){} }
    const finish = v=>{
      if(_box) _box.classList.add('mf-pop-out');
      setTimeout(()=>{ root.remove(); if(prevFocus && prevFocus.focus){ try{ prevFocus.focus(); }catch(e){} } resolve(v); }, 120);
    };
    root.addEventListener('click', e=>{
      const b = e.target.closest('[data-act]');
      if(b) finish(b.dataset.act === '1');
    });
    root.addEventListener('keydown', e=>{
      if(e.key==='Escape'){ e.stopPropagation(); finish(false); }
    });
  });
}
/* 全局 Esc：关闭最上层 .modal.open（各弹窗的 × 按钮承担关闭逻辑，Esc 触发它） */
document.addEventListener('keydown', function(e){
  if(e.key!=='Escape') return;
  const modals=document.querySelectorAll('.modal.open');
  if(!modals.length) return;
  const top=modals[modals.length-1];
  if(top.id==='appConfirmRoot') return;          // appConfirm 自带 Esc 处理
  const x=top.querySelector('.modal-x');
  if(x && typeof x.click==='function') x.click();
});
window.appConfirm = appConfirm;

window.delFlow = async function(id){
  if(!(await appConfirm('确认删除该工作流？删除后不可恢复。', {danger:true, okText:'删除'}))) return;
  try{ await api('/api/workflows/'+id,{method:'DELETE'}); toast('已删除',true); renderList(); }catch(e){ toast('删除失败'); }
};
window.listSetFilter = listSetFilter;

function updateNavState(){ /* no-op, keep hook */ }

/* ================= 视图：新建 ================= */
let ACADEMIC = [];
const CN_CONTESTS = [
  {id:'天府杯',emoji:'🐼',stars:4,month:'3月'},{id:'认证杯',emoji:'📝',stars:3,month:'4-5月'},
  {id:'MathorCup',emoji:'☕',stars:4,month:'4月'},{id:'泰迪杯',emoji:'🧸',stars:3,month:'4月'},
  {id:'华东杯',emoji:'🌊',stars:2,month:'4-5月'},{id:'华中杯',emoji:'🏛️',stars:2,month:'4-5月'},
  {id:'五一杯',emoji:'🎯',stars:3,month:'5月'},{id:'中青杯',emoji:'🌱',stars:3,month:'5月'},
  {id:'长三角',emoji:'🌉',stars:2,month:'5月'},{id:'统计建模大赛',emoji:'📈',stars:3,month:'5月'},
  {id:'数维杯',emoji:'🔢',stars:3,month:'5月'},{id:'电工杯',emoji:'⚡',stars:4,month:'5-6月'},
  {id:'辽宁省/东三省',emoji:'🏔️',stars:2,month:'6月'},{id:'亚太赛中文(APMCM)',emoji:'🌏',stars:3,month:'6月'},
  {id:'深圳杯',emoji:'🏙️',stars:4,month:'7-9月'},{id:'华数杯',emoji:'🔮',stars:3,month:'8月'},
  {id:'国赛(CUMCM)',emoji:'🏆',stars:5,month:'9月'},{id:'华为杯',emoji:'📱',stars:5,month:'9月'},
];
const EN_CONTESTS = [
  {id:'美赛(MCM/ICM)',emoji:'🌍',stars:5,month:'2月'},{id:'数维杯国际赛',emoji:'🔢',stars:3,month:'11月'},
  {id:'亚太(APMCM)',emoji:'🌏',stars:3,month:'11月'},{id:'小美赛(认证杯国际)',emoji:'📝',stars:3,month:'12月'},
];
const PALETTES = ['随机（推荐）',
  /* ▍最热门（GitHub 公认 · 论文常用） */
  '现代明亮（Urban）','科研经典（SCI）','Kelly 对比','材质亮色',
  'Nature 顶刊','优雅 Elegant','Okabe-Ito 经典','色盲友好（Wong）'];
const LAYOUTS = ['随机（推荐）','清爽开放','柔和网格','框线期刊','极简无框','粗描边','清晰深轴',
  'SCI 期刊框线','通透留白','点状网格'];

async function loadAcademic(){
  try{ const r = await api('/api/pipelines'); ACADEMIC=(r.pipelines||[]).filter(p=>p.g!=='comp'); }catch(e){ ACADEMIC=[]; }
}

async function renderNew(){
  if(!ACADEMIC.length) await loadAcademic();
  $('#view').innerHTML = `
    <div class="page-head"><div><h1>新建工作流</h1></div></div>
    <div id="nwFormRoot"></div>
    <div class="card" id="nwTplCard">
      <!-- 国赛 CUMCM：独立大卡，通栏突出展示，点击直接进入 -->
      <div class="tpl-national-hero" data-go="comp" data-tpl="competition" data-contest="国赛(CUMCM)" onclick="nwPick(this)">
        <span class="tpl-national-hero-ribbon">🏆 推荐</span>
        <div class="tpl-national-hero-ico">🏆</div>
        <div class="tpl-national-hero-copy">
          <div class="tpl-national-hero-name">国赛（CUMCM）</div>
          <div class="tpl-national-hero-desc">从赛题 → 建模 → 代码 → 论文 → 编译 PDF → 审查改进，全自动完成全国大学生数学建模竞赛</div>
          <div class="tpl-national-hero-tags">
            <span>★★★★★</span><span>9月</span><span>完整流水线</span>
          </div>
        </div>
        <span class="tpl-national-hero-open">直接进入 ›</span>
      </div>

      <!-- ① 竞赛工作流（除国赛外，其余数模赛项正在开发中） -->
      <div class="nw-cat">
        <div class="nw-cat-head"><span class="nw-cat-ico">🏆</span><span class="nw-cat-name">竞赛工作流</span><span class="nw-dev-tag">开发中</span></div>
        <p class="nw-cat-desc">除国赛外的其他数学建模竞赛赛项正在开发中，敬请期待</p>
        <div class="contest-grid-wrap">
          <div class="contest-group-h">🇨🇳 中文赛项 <em>${CN_CONTESTS.length-1} 项</em></div>
          <div class="contest-card-grid" id="cnContestGrid"></div>
          <div class="contest-group-h" style="margin-top:18px">🌍 英文赛项 <em>${EN_CONTESTS.length} 项</em></div>
          <div class="contest-card-grid" id="enContestGrid"></div>
        </div>
      </div>
    </div>`;
  renderContestGrid();
}
/* 竞赛赛项卡片墙（点击直达表单并预选该赛项；国赛由顶部大卡单独承载） */
function renderContestGrid(){
  const cn=document.getElementById('cnContestGrid'); if(cn) cn.innerHTML=CN_CONTESTS.filter(c=>c.id!=='国赛(CUMCM)').map(c=>contestCard(c)).join('');
  const en=document.getElementById('enContestGrid'); if(en) en.innerHTML=EN_CONTESTS.map(c=>contestCard(c)).join('');
}
function contestCard(c){
  const stars='★'.repeat(c.stars)+'☆'.repeat(5-c.stars);
  const hot=c.id.includes('国赛')||c.id.includes('美赛')||c.id.includes('华为杯')||c.stars>=5;
  return `<div class="contest-card ${hot?'hot':''}" data-contest="${esc(c.id)}" onclick="nwDevToast('${esc(c.id)}')">
    ${hot?'<span class="contest-card-hot">★ 热门</span>':''}
    ${'<span class="nw-dev-mini contest-dev">开发中</span>'}
    <span class="contest-card-emoji">${c.emoji}</span>
    <div class="contest-card-main"><b>${esc(c.id)}</b><span>${stars}</span><em>${c.month}</em></div>
  </div>`;
}
window.nwPickContest=function(id){
  // 所有已列出的赛项共用成熟的竞赛流水线；区别仅由 contest 参数决定模板与默认页数。
  renderCompForm(id, id==='国赛(CUMCM)');
};

window.nwDevToast=function(name){ toast('「'+name+'」正在开发中，敬请期待'); };
const WIP_ITEMS=[
  {name:'竞赛 · 中文赛项', emoji:'🐼', desc:'天府杯 / 认证杯 / MathorCup / 华为杯 等'},
  {name:'竞赛 · 英文赛项', emoji:'🌍', desc:'美赛 MCM/ICM、亚太赛 APMCM、小美赛'},
  {name:'美赛（MCM/ICM）', emoji:'🌎', desc:'0.8pt 英文论文，翻译 + 英文写作'},
  {name:'华中杯', emoji:'🏛️', desc:'以湖北高校为主的区域赛'},
  {name:'MathorCup 挑战赛', emoji:'☕', desc:'面向学科竞赛的建模挑战'},
  {name:'认证杯', emoji:'📝', desc:'数学中国主办，两轮阶段赛'},
];
let WIP_OPEN=false;
window.nwWip=function(){
  const body=document.getElementById('nwWipBody'); if(!body) return;
  const arrow=document.getElementById('nwWipArrow');
  WIP_OPEN=!WIP_OPEN;
  if(WIP_OPEN){
    body.innerHTML=WIP_ITEMS.map(o=>`<div class="wip-item" onclick="event.stopPropagation();nwWipToast('${esc(o.name)}')">
      <span>${o.emoji}</span><b>${esc(o.name)}</b><em>${esc(o.desc)}</em></div>`).join('');
    if(arrow) arrow.textContent='▴';
    body.classList.add('open');
  }else{
    body.innerHTML='<div class="tpl-wip-desc">中文 / 英文赛项及其他区域赛正在开发中</div>';
    if(arrow) arrow.textContent='▾';
    body.classList.remove('open');
  }
};
window.nwWipToast=function(name){ toast('「'+name+'」正在开发中，敬请期待'); };
window.nwPick = function(el){
  const go=el.dataset.go, tpl=el.dataset.tpl;
  const contest=el.dataset.contest;
  if(go==='comp'){
    const nm=contest||el.querySelector('.name')||el.querySelector('.tpl-national-hero-name');
    const label=contest?contest:(nm?nm.textContent:'竞赛工作流');
    // 国赛：默认就是国赛，直接进入工作流，不再显示赛项选择
    renderCompForm(label, label==='国赛(CUMCM)');
  }else{
    const name=el.querySelector('.name').textContent;
    renderAcadForm(ACADEMIC.find(p=>p.template===tpl), name);
  }
};
function nwBack(){
  $('#nwFormRoot').innerHTML='';
  const tplCard=document.getElementById('nwTplCard');
  if(tplCard) tplCard.style.display='';
  window.scrollTo({top:0,behavior:'smooth'});
}
window.nwBack = nwBack;

/* ---- 模型下拉（预设） ---- */
function modelOptions(sel, current){
  const presets = ST.presets;
  let opts = '<option value="">跟随全局默认</option>';
  presets.forEach(p=>{ opts += `<option value="${esc(p.name)}" ${p.name===current?'selected':''}>${esc(p.name)}（${esc(p.model||'-')}）</option>`; });
  if(sel) $(sel).innerHTML = opts;
  return opts;
}
/* 每次进入新建表单都拉一次模型预设，保证与「设置 → 模型预设」完 一致（不依赖启动时的缓存） */
function refreshModelDropdowns(){
  return api('/api/providers').then(r=>{
    if(!r) return;
    ST.presets=r.presets||[]; ST.defaultPreset=r.default||null;
    const opts=modelOptions();
    const fill=(el)=>{ if(!el) return; const v=el.value; el.innerHTML=opts;
      if(v){ try{ el.value=v; }catch(e){} }
      el.dispatchEvent(new Event('change',{bubbles:true}));  // 同步 Dropdown 触发器文案
    };
    fill(document.getElementById('cfModel'));
    fill(document.getElementById('afModel'));
    document.querySelectorAll('#cfStepModels select').forEach(fill);
  }).catch(()=>{});
}

/* ---- 竞赛表单 ---- */
function renderCompForm(name, skipContest){
  const tplCard=document.getElementById('nwTplCard'); if(tplCard) tplCard.style.display='none';
  const hideContest=!!skipContest;
  const starsS = n=>'★'.repeat(n)+'☆'.repeat(5-n);
  const compC = CN_CONTESTS.map(c=>`<div class="contest-opt" data-id="${c.id}" onclick="nwSelContest(this)">
      <input type="radio" name="contest"><div class="co-main"><div class="co-name">${c.emoji} ${c.id}</div>
      <div class="co-extra">${starsS(c.stars)} · ${c.month}</div></div><span class="co-state">✓</span></div>`).join('');
  const enC = EN_CONTESTS.map(c=>`<div class="contest-opt" data-id="${c.id}" onclick="nwSelContest(this)">
      <input type="radio" name="contest"><div class="co-main"><div class="co-name">${c.emoji} ${c.id}</div>
      <div class="co-extra">${starsS(c.stars)} · ${c.month}</div></div><span class="co-state">✓</span></div>`).join('');
  $('#nwFormRoot').innerHTML = `
    <div class="nw-form-wrap">
    <div class="card">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:22px;flex-wrap:wrap">
        <span style="font-size:26px">🏆</span><h2 style="font-size:20px">${name||'竞赛工作流'}</h2>
        <div style="flex:1"></div><button class="btn btn-ghost btn-sm" onclick="nwBack()">返回模板</button>
      </div>
      <div class="field"><label for="cfTitle" class="f">工作流标题</label>
        <input type="text" id="cfTitle" value="${esc(name)} - 新建"></div>

      <div class="sect-row">
        <div class="sect">流程方案</div>
        <button type="button" class="btn btn-ghost btn-sm" onclick="showFlowCompare()">🗺 查看流程对比 ›</button>
      </div>
      <div class="field"><div class="radio-pills flow-fill" data-field="compFlow">
        <div class="pill active" data-val="native" onclick="nwPill(this);nwFlowChanged()">⚡ 极速 自动流</div>
        <div class="pill" data-val="bzd" onclick="nwPill(this);nwFlowChanged()">🏅 BZD 双审精制流</div>
        <div class="pill" data-val="mms" onclick="nwPill(this);nwFlowChanged()">🧭 个人自制流</div>
        <div class="pill" data-val="modex" onclick="nwPill(this);nwFlowChanged()">🎯 Modex 原版流</div>
      </div></div>

      <div class="sect" id="cfContestSect" style="${hideContest?'display:none':''}">赛项选择</div>
      <div class="contest-wrap" id="cfContestWrap" style="${hideContest?'display:none':''}">
        <div class="contest-col"><div class="col-h"><span class="col-state"></span>🇨🇳 中文赛项</div>${compC}</div>
        <div class="contest-col"><div class="col-h"><span class="col-state"></span>🌍 英文赛项</div>${enC}</div>
      </div>

      <div class="sect">竞赛参数</div>
      <div class="field"><label class="f">输出格式</label>
        <div class="radio-pills alloc-fill" data-field="outFormat">
          <div class="pill active" data-val="pdf" onclick="nwPill(this)">PDF（格式完整）</div>
          <div class="pill" data-val="word" onclick="nwPill(this)">Word（可二次编辑）</div>
        </div></div>
      <div class="field"><label class="f" for="cfQiHao">题号</label><input type="text" id="cfQiHao" placeholder="例如：A、B、C、D"></div>
      <div class="grid2">
        <div class="field"><label class="f">审查模式</label>
          <div class="radio-pills" data-field="reviewMode">
            <div class="pill active" data-val="strict" onclick="nwPill(this)">严格（完整审查）</div>
            <div class="pill" data-val="fast" onclick="nwPill(this)">快速（省额度）</div>
          </div></div>
        <div class="field"><label class="f" for="cfPage">页数限制</label>
          <div style="display:flex;align-items:center;gap:10px">
            <input type="number" id="cfPage" value="30" min="5" max="60" style="max-width:120px">
            <span class="muted" style="font-size:13px">页</span></div></div>
      </div>
      <div class="switch-row"><label class="switch"><input type="checkbox" id="cfRich"><span class="slider"></span></label>
        <div class="st"><div class="st-t">📚 丰满模式（华为杯标准）</div><div class="st-d">正文 40-60 页 · 30+ 张图表 · 候选方法对比 · 过程式叙述 · 自动 12 类章节扩展</div></div></div>
      <div class="switch-row"><label class="switch"><input type="checkbox" id="cfLogicReview" checked disabled><span class="slider"></span></label>
        <div class="st"><div class="st-t">🔍 逻辑对抗复核（费额度）</div><div class="st-d">编程后、写论文前，换独立视角挑"方向反 / 重复计量 / 外推过硬 / 漏变量 / 跨问矛盾 / 任务读歪"，发现致命逻辑错则回炉。默认开启，不可关闭。</div></div></div>

      <div class="sect">图形 / 配色设置</div>
      <div style="display:flex;justify-content:flex-end;margin:-14px 0 8px">
        <button type="button" class="btn btn-ghost btn-sm" onclick="showStylePreview()">👁 查看全部图表 ›</button>
      </div>
      <div class="field"><label class="f">图表生成方案</label>
        <div class="radio-pills fill" data-field="figMode">
          <div class="pill active" data-val="builtin" onclick="nwPill(this)">📚 内置图表库（100+ 模板）</div>
          <div class="pill" data-val="nature_ai" onclick="nwPill(this)">🌍 Nature 顶刊 AI 生成（联网）</div>
        </div></div>
      <div class="field"><label class="f">流程图配色</label>
        <div style="display:flex;gap:10px;align-items:stretch">
          <div class="radio-pills fill" data-field="colorScheme" style="flex:1">
            <div class="pill active" data-val="bw" onclick="nwPill(this)">纯黑白</div>
            <div class="pill" data-val="plain" onclick="nwPill(this)">朴素竞赛</div>
            <div class="pill" data-val="modern" onclick="nwPill(this)">现代精致</div>
          </div>
          <button type="button" class="btn btn-ghost btn-sm" style="white-space:nowrap;height:auto" onclick="showFlowPalette()">👁 查看流程图配色 ›</button>
        </div></div>
      <div class="field"><label class="f">数据图配色</label>
        <div class="pick-row"><span>🎨 低饱和 · 按题目气质手选</span>
          <button type="button" class="btn btn-ghost btn-sm" id="cfPaletteBtn" onclick="nwModal('palette')">随机 ›</button></div></div>
      <div class="field"><label class="f">图表版式</label>
        <div class="pick-row"><span>📐 边框 / 网格 / 轴线风格</span>
          <button type="button" class="btn btn-ghost btn-sm" id="cfLayoutBtn" onclick="nwModal('layout')">随机 ›</button></div></div>

      <details class="adv-fold">
        <summary>高级选项 <span class="muted">图片 / 表格 / 模型数量（默认自动）</span></summary>
        <div class="grid3">
          <div class="field"><label class="f">图片数量</label>
            <div class="ctl-row">
              <label class="ctl-switch"><input type="checkbox" id="cfImgAuto" class="ctl-chk" checked onchange="nwCtlAuto('cfImgCount',this)"><span class="sw"></span><span class="sw-t">自动</span></label>
              <input type="number" id="cfImgCount" class="ctl-num" value="0" min="1" max="50" placeholder="自定义" disabled>
            </div></div>
          <div class="field"><label class="f">表格数量</label>
            <div class="ctl-row">
              <label class="ctl-switch"><input type="checkbox" id="cfTblAuto" class="ctl-chk" checked onchange="nwCtlAuto('cfTblCount',this)"><span class="sw"></span><span class="sw-t">自动</span></label>
              <input type="number" id="cfTblCount" class="ctl-num" value="0" min="1" max="50" placeholder="自定义" disabled>
            </div></div>
          <div class="field"><label class="f">模型数量</label>
            <div class="ctl-row">
              <label class="ctl-switch"><input type="checkbox" id="cfModelAuto" class="ctl-chk" checked onchange="nwCtlAuto('cfModelCount',this)"><span class="sw"></span><span class="sw-t">自动</span></label>
              <input type="number" id="cfModelCount" class="ctl-num" value="0" min="1" max="50" placeholder="自定义" disabled>
            </div></div>
        </div>
      </details>

      <div class="sect">选填 / 上传</div>
      <div class="field"><label for="cfOutline" class="f">解题思路 / 大纲文档 <small>(可选)</small></label>
        <textarea id="cfOutline" placeholder="上传你的解题大纲、思路文档或额外要求"></textarea></div>
      <div class="field"><label for="cfCustom" class="f">自定义要求 <small>(可选)</small></label>
        <textarea id="cfCustom" placeholder="例如：侧重灵敏度分析与鲁棒性检验、使用遗传算法求解..."></textarea></div>
      <div class="field"><label class="f">上传赛题</label>
        <div class="upload-zone" onclick="fileClick('cfProblem')"><div class="muted">点击上传赛题文件（推荐 .docx 或 PDF）</div></div>
        <input type="file" id="cfProblem" multiple class="hidden"></div>
      <div class="field"><label class="f">赛题图片 <small>(可选)</small></label>
        <div class="upload-zone" onclick="fileClick('cfProbImg')"><div class="muted">点击上传赛题中的图片（PNG / JPG）</div></div>
        <input type="file" id="cfProbImg" multiple class="hidden"></div>
      <div class="field"><label for="cfSupplement" class="f">赛题补充说明 <small>(可选)</small></label>
        <textarea id="cfSupplement" placeholder="赛题无法解析时可粘贴文字；或补充说明选择哪道题"></textarea></div>
      <div class="field"><label class="f">上传附件数据</label>
        <div class="upload-zone" onclick="fileClick('cfData')"><div class="muted">点击选择文件或拖拽到此处</div></div>
        <input type="file" id="cfData" multiple class="hidden"></div>

      <div class="sect">参数设置</div>
      <div class="switch-row"><label class="switch"><input type="checkbox" id="cfDataFig"><span class="slider"></span></label>
        <div class="st"><div class="st-t">🔍 数据图视觉质检</div><div class="st-d">生成数据图后额外调 AI 视觉模型看图，查坐标轴标签截断等硬伤，最多自动修 3 轮</div></div></div>
      <div class="switch-row"><label class="switch"><input type="checkbox" id="cfPerFlow" checked><span class="slider"></span></label>
        <div class="st"><div class="st-t">🔀 每个问题都画求解流程图</div><div class="st-d">默认只画一张总的技术路线图。开启后每个子问题各配一张求解流程图。</div></div></div>
      <div class="switch-row"><label class="switch"><input type="checkbox" id="cfFlowFig"><span class="slider"></span></label>
        <div class="st"><div class="st-t">🖼️ 流程图 / 架构图视觉质检</div><div class="st-d">编译前对流程图、架构图、TikZ 矢量图额外调 AI 视觉模型检查版式硬伤（费额度）。默认关闭。</div></div></div>
      <div class="switch-row"><label class="switch"><input type="checkbox" id="cfAI"><span class="slider"></span></label>
        <div class="st"><div class="st-t">📝 AI 工具使用声明</div><div class="st-d">按竞赛规范在参考文献前加「AI 工具使用声明」章节。</div></div></div>
      <div class="switch-row"><label class="switch"><input type="checkbox" id="cfCheckpoint"><span class="slider"></span></label>
        <div class="st"><div class="st-t">👤 人工检查点</div><div class="st-d">关键步骤完成后暂停，可预览产出并提交修改意见</div></div></div>
      <div class="switch-row"><label class="switch"><input type="checkbox" id="cfLoop" checked disabled><span class="slider"></span></label>
        <div class="st"><div class="st-t">🔁 论文改进循环</div><div class="st-d">编译后自动审稿→修改→重编译（2轮，约30分钟）。默认开启，不可关闭。</div></div></div>

      <div class="sect">模型分配</div>
      <div class="field"><label class="f">选择模型跑。不选=跟随设置页默认预设。</label>
        <div class="radio-pills alloc-fill" data-field="modelAlloc">
          <div class="pill active" data-val="global" onclick="nwPill(this);nwModelAlloc()">整个工作流统一 / 跟随默认</div>
          <div class="pill" data-val="perstep" onclick="nwPill(this);nwModelAlloc()">为每个步骤单独指定</div>
        </div></div>
      <div id="cfGlobalModel" class="field"><label for="cfModel" class="f">运行模型 <small>(整个工作流统一用)</small></label>
        <select id="cfModel">${modelOptions()}</select></div>
      <div id="cfStepModels" class="field" style="display:none"><label class="f">按步骤指定模型</label>
        <div style="display:flex;flex-direction:column;gap:8px;margin-top:6px">${COMP_STEPS.map((s,i)=>`
          <div class="step-model-row"><span class="sm-name">${i+1}. ${esc(s.label)}</span>
            <select id="cfsm_${s.key}" style="flex:1">${modelOptions()}</select></div>`).join('')}
        </div></div>
      <div style="padding:24px 0 10px">
        <button class="btn btn-lg btn-primary" style="width:100%" onclick="createComp()">开始生成 · 启动工作流</button>
      </div>
    </div>
    </div>`;
  setupUploads();
  refreshModelDropdowns();
  // 若由赛项卡片进入（name 是赛项名），自动预选对应赛项
  if(name){
    setTimeout(()=>{
      const safe=(name||'').replace(/[\\"()[\]{}]/g,'\\$&');
      const opt=document.querySelector(`.contest-opt[data-id="${safe}"]`);
      if(opt) nwSelContest(opt);
    }, 60);
  }
  window.scrollTo({top:0,behavior:'smooth'});
}

/* ---- 学术表单 ---- */
function renderAcadForm(card, name){
  const tplCard=document.getElementById('nwTplCard'); if(tplCard) tplCard.style.display='none';
  const steps=(card&&card.steps)||[];
  $('#nwFormRoot').innerHTML = `
    <div class="card">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:22px;flex-wrap:wrap">
        <span style="font-size:26px">${card?card.emoji||'📄':'📄'}</span><h2 style="font-size:20px">${esc(card?card.name:'学术工作流')}</h2>
        <div style="flex:1"></div><button class="btn btn-ghost btn-sm" onclick="nwBack()">返回模板</button>
      </div>
      <div class="sect">流水线步骤</div>
      <div id="afSteps" style="display:flex;flex-direction:column;gap:8px;margin-bottom:20px">
        ${steps.map((s,i)=>`<div class="step-mini"><span class="si">${i+1}</span><span class="sl">${esc(s.label)}</span><span class="sm">skill: <code>${esc(s.skill)}</code></span></div>`).join('')}
      </div>
      <div class="sect">基本信息</div>
      <div class="field"><label class="f">工作流标题</label><input type="text" id="afTitle" value="${esc(name)} - 新建"></div>
      <div class="field"><label class="f">研究主题 / 待办内容 <small>(必填)</small></label>
        <textarea id="afQuestion" placeholder="填写你要研究的方向、论文主题、综述范围、待审稿件内容等"></textarea></div>
      <div class="grid2">
        <div class="field"><label class="f">目标字数 <small>(可选)</small></label>
          <input type="number" id="afWords" value="8000" min="500" max="200000"></div>
        <div class="field"><label class="f">运行模型 <small>(可选)</small></label>
          <select id="afModel">${modelOptions()}</select></div>
      </div>
      <div class="sect">选填 / 上传</div>
      <div class="field"><label class="f">自定义要求 <small>(最高优先级)</small></label>
        <textarea id="afCustom" placeholder="例如：侧重某个方法 / 指定参考方向 / 格式要求等"></textarea></div>
      <div class="field"><label class="f">大纲 / 思路文档 <small>(可选)</small></label>
        <textarea id="afOutline" placeholder="粘贴已有大纲、思路或额外说明"></textarea></div>
      <div class="field"><label class="f">上传资料 / 数据 <small>(可选)</small></label>
        <div class="upload-zone" onclick="fileClick('afData')"><div class="muted">点击选择文件或拖拽（pdf / docx / md / bib / csv / json / 代码等）</div></div>
        <input type="file" id="afData" multiple class="hidden"></div>
      <div style="padding:24px 0 10px">
        <button class="btn btn-lg btn-primary" style="width:100%" onclick="createAdv('${card.template}')">开始生成 · 启动工作流</button>
      </div>
    </div>`;
  setupUploads();
  refreshModelDropdowns();
  window.scrollTo({top:0,behavior:'smooth'});
}

/* 上传：集中处理，绑定一次 change */
let UPLOAD_INIT = false;
function setupUploads(){
  if(UPLOAD_INIT) return;
  UPLOAD_INIT = true;
  document.body.addEventListener('change', async e=>{
    const input = e.target;
    if(!input || input.tagName!=='INPUT' || input.type!=='file') return;
    const cat = input.id;
    if(!window.CFILES) window.CFILES={};
    for(const f of input.files){
      const fd=new FormData(); fd.append('file',f);
      try{ const r=await fetch('/api/upload',{method:'POST',body:fd}).then(x=>x.json());
        (window.CFILES[cat]=window.CFILES[cat]||[]).push({name:f.name,path:r.path,cat}); }
      catch(err){ (window.CFILES[cat]=window.CFILES[cat]||[]).push({name:f.name,path:'',cat}); }
    }
    toast('已上传文件',true);
    input.value='';
  });
}
function fileClick(id){ const el=document.getElementById(id); if(el) el.click(); }
window.fileClick = fileClick;

function nwPill(el){
  const parent=el.parentElement;
  parent.querySelectorAll('.pill').forEach(p=>p.classList.remove('active'));
  el.classList.add('active');
}
window.nwPill = nwPill;
window.nwModelAlloc = function(){
  const group=$('[data-field="modelAlloc"]'); if(!group) return;
  const perstep=group.querySelector('.pill.active').dataset.val==='perstep';
  const gm=$('#cfGlobalModel'), sm=$('#cfStepModels');
  if(gm) gm.style.display=perstep?'none':''; if(sm) sm.style.display=perstep?'':'none';
};
function nwPillVal(scope){
  const all = (scope||document).querySelectorAll('.radio-pills');
  const o={};
  all.forEach(g=>{ const a=g.querySelector('.pill.active'); if(a) o[g.dataset.field||''] = a.dataset.val; });
  return o;
}
function pillValOf(el){
  const group=el.parentElement; return group.querySelector('.pill.active').dataset.val;
}
window.nwSelContest = function(el){
  const wrap = el.closest('.contest-wrap');
  wrap.querySelectorAll('.contest-opt').forEach(c=>c.classList.remove('sel'));
  el.classList.add('sel'); el.querySelector('input').checked=true;
  const id=el.dataset.id;
  const cur=document.getElementById('cfTitle'); const v=cur.value;
  if(!v || /新建竞赛工作流/.test(v) || / - 新建$/.test(v)) cur.value=id+' - 新建';
  const pageMap={'国赛(CUMCM)':30,'美赛(MCM/ICM)':25,'华为杯':40,'深圳杯':20};
  if(pageMap[id]){$('#cfPage').value=pageMap[id];}
};

/* ---- 配色/版式弹窗 ---- */
let NW_PICK = {palette:'随机（推荐）', layout:'随机（推荐）'};
let NW_SNAP = {palette: null, layout: null};

/* 配色方案色板（与 _utils_py/plot_utils.py 的 PALETTES 对齐，改动需三处同步：
   app.js PALETTES/PALETTE_HEX ↔ jobs.py _DATA_PALETTE ↔ plot_utils.py PALETTES） */
const PALETTE_HEX = {
  '经典柔和（原默认）': ['#5B9BD5','#ED7D7D','#7BC8A4','#B0B0B0','#9B8EC4','#F4A261'],
  'Okabe-Ito 经典':     ['#0072B2','#E69F00','#009E73','#CC79A7','#56B4E9','#D55E00'],
  'Tol 柔和':           ['#4477AA','#CC6677','#228833','#CCBB44','#66CCEE','#AA3377'],
  'Tol 明快':           ['#0077BB','#EE7733','#009988','#CC3311','#33BBEE','#EE3377'],
  '北欧 Nord':          ['#5E81AC','#BF616A','#A3BE8C','#EBCB8B','#B48EAD','#88C0D0'],
  '日暮渐变':           ['#003F5C','#58508D','#BC5090','#FF6361','#FFA600','#7A5195'],
  '海洋青蓝':           ['#05668D','#028090','#00A896','#02C39A','#0A9396','#3D8DAE'],
  '珊瑚':               ['#FF6B6B','#4ECDC4','#45B7D1','#F7A072','#A06CD5','#F79256'],
  '明快春日':           ['#219EBC','#FB8500','#6A994E','#8ECAE6','#BC4749','#FFB703'],
  '随机（推荐）':       ['#7AAEC8','#E8945A','#7BC8A4','#9B8EC4','#E0A0A0','#F0C05A'],
  /* —— 期刊 / 顶刊风 —— */
  '期刊顶刊（SCI）':    ['#4A90B8','#E8927C','#7BC8A4','#B8B8B8','#F7D097','#9B8EC4','#8DBFA3','#D4A0A0'],
  'Nature 顶刊':        ['#0F4D92','#3775BA','#8BCF8B','#B64342','#767676','#42949E','#9A4D8E','#FFD700'],
  'NEJM 医学':          ['#BC3C29','#0072B5','#E18727','#20854E','#7876B1','#6F99AD','#FFDC91','#EE4C97'],
  'Science 学术':       ['#0C5DA5','#00B945','#FF9500','#FF2C00','#845B97','#474747','#9e9e9e'],
  'Tableau 专业':       ['#4E79A7','#F28E2B','#E15759','#76B7B2','#59A14F','#EDC948','#B07AA1','#FF9DA7','#9C755F','#BAB0AC'],
  'NPG 自然':           ['#E64B35','#4DBBD5','#00A087','#3C5488','#F39B7F','#8491B4','#91D1C2','#DC0000','#7E6148','#B09C85'],
  '色盲友好（Wong）':   ['#0072B2','#D55E00','#009E73','#CC79A7','#F0E442','#56B4E9','#E69F00','#000000'],
  /* —— 气质风格 —— */
  '优雅 Elegant':       ['#7AAEC8','#E8945A','#7BC8A4','#9B8EC4','#E0A0A0','#F0C05A','#8FAEC0','#A8C4D8'],
  '柔和粉彩':           ['#8AB6D6','#F6A6B2','#8FCB9B','#C3A0D6','#F9C979','#7EC4C4','#E0A0B8'],
  '薄荷薰衣草':         ['#4CB5AE','#B39CD0','#FF8FA3','#A8DADC','#457B9D','#FCBF49','#8E7DBE'],
  '鼠尾草玫瑰':         ['#84A98C','#A4243B','#6B9080','#C9ADA7','#52796F','#D8A48F','#354F52'],
  '大地森林':           ['#386641','#BC4749','#6A994E','#A7C957','#C9A227','#D4A373','#7F5539'],
  '孔雀青':             ['#006D77','#E29578','#83C5BE','#EE9B00','#CA6702','#0A9396','#9B2226'],
  '沙漠暖沙':           ['#E07A5F','#3D405B','#81B29A','#F2CC8F','#6D597A','#B56576','#E56B6F'],
  '钴蓝珊瑚':           ['#274690','#FF7F51','#1B98E0','#E8505B','#47B39C','#FFD166','#6A4C93'],
  '星空紫金':           ['#4B3F72','#FFC857','#E9724C','#255F85','#C5283D','#9B5094','#F2A65A'],
  /* —— 复古 / 个性 —— */
  '火烈鸟':             ['#3A86FF','#F72585','#4CC9F0','#7209B7','#4361EE','#B5179E','#4895EF'],
  '复古霓虹':           ['#EA5545','#EF9B20','#87BC45','#27AEEF','#B33DC6','#F46A9B','#BDCF32'],
  '荷兰田野':           ['#E60049','#0BB4FF','#50E991','#E6A800','#9B19F5','#F58518','#00BFA0'],
  '红酒':               ['#5F0F40','#9A031E','#CB793A','#0F4C5C','#457B9D','#7B2D26','#BC6C25'],
  '苔藓陶土':           ['#606C38','#DDA15E','#BC6C25','#4A5A2B','#A68A64','#7F4F24','#936639'],
  '青橙':               ['#1F6F78','#FF8C42','#2A9D8F','#E76F51','#457B9D','#F4A261','#264653'],
  /* ▍首选热门（GitHub 公认） */
  '现代明亮（Urban）':  ['#1696D2','#FDBF11','#55B748','#DB2B27','#EC008B','#00A3A1','#8C6DB1','#7F8C8D'],
  '科研经典（SCI）':    ['#0C5DA5','#00B945','#FF9500','#FF2C00','#845B97','#474747','#9E9E9E'],
  'Kelly 对比':         ['#F3C300','#875692','#F38400','#A1CAF1','#BE0032','#C2B280','#848482','#008856','#E68FAC','#0067A5'],
  '材质亮色':           ['#2196F3','#FFC107','#4CAF50','#F44336','#9C27B0','#00BCD4','#FF9800','#E91E63'],
};

/* 版式渲染参数：边框 / 网格 / 轴色轴粗 / 线宽 / 不透明度（差异显著，便于一眼区分） */
const LAYOUT_STYLE = {
  '随机（推荐）':{frame:'1px solid #e5e7eb', grid:true,  axis:'#555', aw:1.0, lw:1.6, op:.92, dots:3.1,
                 desc:'每篇运行随机应用一种版式并自动统一'},
  '清爽开放':   {frame:'1px solid #ececec', grid:false, axis:'#9aa0aa', aw:.9,  lw:1.3, op:.92, dots:2.6,
                 desc:'浅灰细边 · 无网格 · 细轴'},
  '柔和网格':   {frame:'1px solid #e5e7eb', grid:true,  axis:'#6a6f78', aw:1.0, lw:1.6, op:.92, dots:3.1,
                 desc:'柔和灰网格 · 中度线条'},
  '框线期刊':   {frame:'1.5px solid #3f3f46', grid:false, axis:'#333', aw:1.1, lw:1.8, op:1,    dots:3.3,
                 inner:'inset 0 0 0 3px #fff, inset 0 0 0 4px #d8d8de',
                 desc:'期刊框线 + 内衬 · 深轴'},
  '极简无框':   {frame:'none', grid:false, axis:'#c7cbd1', aw:.7,  lw:1.1, op:.85, dots:2.6,
                 desc:'无边框 · 极细轴 · 低饱和'},
  '粗描边':     {frame:'3px solid #18181b', grid:false, axis:'#000', aw:1.7, lw:2.5, op:1,    dots:4.2,
                 desc:'粗黑描边 · 重轴 · 醒目'},
  '清晰深轴':   {frame:'1px solid #e2e2e6', grid:true,  axis:'#000', aw:2.0, lw:1.8, op:.95, dots:3.2,
                 desc:'浅边 + 深色粗轴 · 网格'},
  'SCI 期刊框线':{frame:'1.5px solid #27272a', grid:false, axis:'#111', aw:1.3, lw:1.9, op:1,    dots:3.4,
                 inner:'inset 0 0 0 2px #f4f4f5, inset 0 0 0 3px #18181b',
                 desc:'SCI 双线框 · 深色精细'},
  '通透留白':   {frame:'1px solid #f1f2f4', grid:false, axis:'#b4bac1', aw:.6,  lw:1.0, op:.82, dots:2.2,
                 pad:'12px',
                 desc:'轻淡无边 · 少装饰 · 大量留白'},
  '点状网格':   {frame:'1px solid #e7e9ee', grid:'dots', axis:'#63666b', aw:.9, lw:1.5, op:.95, dots:3.0,
                 desc:'点状网格 · 中等轴'},
};

/* 论文真实出图素材（matplotlib 论文级渲染，非 AI 生成）。
   图墙统一用 vivid 主题：static/img/paper-{key}__vivid.png；
   配色弹窗另备 8 张代表图 × 5 配色主题（paper-{key}__{theme}.png，key 见 _realPrev）。 */

/* 图表类型清单（覆盖配方库全部 70 种，按类目分组；key 对应 paper-{key}__vivid.png） */
const PAPER_GROUPS = [
  {g:'比较类', items:[
    {k:'bar', t:'分组柱状图'}, {k:'stacked', t:'堆叠柱状图'}, {k:'divbar', t:'发散条形图'},
    {k:'hbar', t:'水平条形图'}, {k:'lollipop', t:'棒棒糖图'}, {k:'dumbbell', t:'哑铃图'},
    {k:'back2back', t:'背靠背图'}, {k:'dotci', t:'点误差图'}, {k:'paired', t:'配对点图'},
    {k:'sigbar', t:'显著性柱状图'}, {k:'forest', t:'森林图'},
    {k:'bubble', t:'气泡图'}]},
  {g:'趋势类', items:[
    {k:'line', t:'折线图 · 置信带'}, {k:'area', t:'面积图'}, {k:'dual', t:'双轴图'},
    {k:'slope', t:'斜率图'}, {k:'waterfall', t:'瀑布图'}, {k:'pareto', t:'帕累托图'},
    {k:'fan', t:'扇形预测图'}, {k:'bump', t:'排名轨迹图'},
    {k:'cusum', t:'CUSUM 累积和'}, {k:'qband', t:'分位数趋势带'},
    {k:'convergence', t:'收敛曲线'}, {k:'step', t:'阶梯图'}, {k:'timeline', t:'事件时间线'},
    {k:'learning', t:'学习曲线'}, {k:'grey', t:'灰色预测 GM(1,1)'}, {k:'montecarlo', t:'蒙特卡洛模拟带'}]},
  {g:'分布类', items:[
    {k:'box', t:'箱线图'}, {k:'violin', t:'小提琴图'}, {k:'gviolin', t:'分组小提琴图'},
    {k:'hist', t:'直方图'}, {k:'kde', t:'密度曲线'}, {k:'ridge', t:'山脊图'},
    {k:'rain', t:'雨云图'},
    {k:'qq', t:'Q-Q 图'}, {k:'ecdf', t:'ECDF 累积分布'}, {k:'joint', t:'联合分布图'},
    {k:'hexbin', t:'六角密度图'}, {k:'strip', t:'条带散点图'},
    {k:'dendrogram', t:'聚类谱系图'}, {k:'violin_split', t:'分裂小提琴图'}]},
  {g:'相关 / 回归', items:[
    {k:'scatter', t:'散点图 · 回归'}, {k:'pair', t:'散点矩阵'}, {k:'bivar', t:'二维密度图'},
    {k:'ba', t:'Bland-Altman'}, {k:'heatmap', t:'热力图 · 相关矩阵'},
    {k:'cheat', t:'聚类热力图'}, {k:'network', t:'网络图'},
    {k:'resid', t:'残差诊断四联'}, {k:'sigheat', t:'相关显著性热力图'}, {k:'predobs', t:'预测-观测 1:1'}]},
  {g:'组成 / 多维', items:[
    {k:'donut', t:'环形饼图'}, {k:'radar', t:'雷达图'}, {k:'parallel', t:'平行坐标'},
    {k:'contour', t:'等高线图'}, {k:'3d', t:'三维曲面图'}, {k:'sankey', t:'桑基图'},
    {k:'pca', t:'PCA 双标图'}, {k:'treemap', t:'矩形树状图'}, {k:'scatter3d', t:'三维散点'},
    {k:'bar3d', t:'三维柱状图'}, {k:'3d_contour', t:'三维等高线'}]},
  {g:'专业 / 高级', items:[
    {k:'subplots', t:'组合子图'}, {k:'tornado', t:'Tornado 灵敏度'}, {k:'gantt', t:'甘特图'},
    {k:'phase', t:'相平面图'}, {k:'paramgrid', t:'参数扫描热力图'},
    {k:'gradbar', t:'渐变柱状图'}, {k:'roc', t:'ROC 曲线 + AUC'}, {k:'confusion', t:'混淆矩阵'},
    {k:'importance', t:'特征重要性'},
    {k:'neural_net', t:'神经网络结构'}, {k:'decision_tree', t:'决策树'}, {k:'fuzzy', t:'模糊隶属函数'},
    {k:'ahp', t:'AHP 判断矩阵'}]},
  {g:'流程 / 架构图', items:[
    {k:'chartflow', t:'图表总览流程'},
    {k:'flow-html', t:'流程图（HTML）', engine:'html'},
    {k:'seq', t:'时序图', engine:'html'}, {k:'state', t:'状态机图', engine:'html'},
    {k:'swimlane', t:'泳道图', engine:'html'}, {k:'indextree', t:'指标体系树', engine:'html'}]},
];
const _figSrc = (key, theme)=>`/static/img/paper-${key}__${theme||'vivid'}.png`;

/* 分类图墙：按当前主题渲染一组图表（engine 项用于流程图引擎筛选） */
function _groupWall(items, theme){
  return `<div class="prev-real">${items.map(p=>
    `<figure class="pg-paper"${p.engine?` data-engine="${p.engine}"`:''}><img loading="lazy" data-key="${p.k}" src="${_figSrc(p.k, theme)}" alt="${p.t}"><figcaption>${p.t}</figcaption></figure>`
  ).join('')}</div>`;
}

/* 全量预览：所有图表直接铺开（无文字标题，纯图墙 · 供"点击查看所有图表"弹窗） */
function _allPrev(theme){
  return PAPER_GROUPS.map(g=>
    `<div class="prev-group">${_groupWall(g.items, theme)}</div>`
  ).join('');
}

/* 精简预览：核心 8 类代表图墙（配色/版式弹窗用 · 一行 2 张） */
function _realPrev(label, note, theme){
  const items = [
    {k:'bar', t:'柱状图 · 误差棒'}, {k:'line', t:'折线图 · 置信带'},
    {k:'scatter', t:'散点图 · 回归'}, {k:'radar', t:'雷达图'},
    {k:'box', t:'箱线图'}, {k:'heatmap', t:'热力图'}, {k:'dual', t:'双轴图'}, {k:'3d', t:'三维曲面'}];
  return `<div class="prev-real prev-2col">${items.map(p=>
      `<figure class="pg-paper"><img loading="lazy" data-key="${p.k}" src="${_figSrc(p.k, theme)}" alt="${p.t}"><figcaption>${p.t}</figcaption></figure>`
    ).join('')}</div>`;
}

/* 中文配色方案 → 预渲染主题键（未覆盖的用默认现代明亮 vivid） */
const _paletteTheme = (name)=>{
  const map = {'现代明亮（Urban）':'vivid','科研经典（SCI）':'journal','Kelly 对比':'kelly',
    '材质亮色':'vivid','期刊顶刊（SCI）':'journal','Nature 顶刊':'nature','优雅 Elegant':'elegant',
    '经典柔和（原默认）':'soft'};
  return map[name] || 'vivid';
};

function _paletteBars(hex, label){
  return _realPrev(label, '低饱和 · 按题目气质应用', _paletteTheme(label));
}
/* 版式弹窗预览：4 张小图实时按当前版式参数重绘（边框/网格/轴色/线宽/透明度差异可见） */
function _layoutRealDiff(label){
  const st = LAYOUT_STYLE[label] || {};
  const frame = st.frame === 'none' ? 'none' : (st.frame || '1px solid #e5e7eb');
  const axisC = st.axis || '#555', aw = st.aw || 1, op = st.op || 0.9, lw = st.lw || 1.5;
  const gridMode = st.grid || false;
  const h1 = 66;

  const axes = (w, h) => `<line x1="8" y1="${h-10}" x2="${w-6}" y2="${h-10}" stroke="${axisC}" stroke-width="${aw}"/>` +
    `<line x1="8" y1="8" x2="8" y2="${h-10}" stroke="${axisC}" stroke-width="${aw}"/>`;

  const gridHtml = (w, h) => {
    if (gridMode === 'dots') return Array.from({length: 18}, (_,i)=>
      `<circle cx="${12+(i%6)*((w-26)/5)}" cy="${12+((i/6)|0)*((h-30)/3)}" r="1.1" fill="${axisC}" opacity=".35"/>`).join('');
    if (gridMode) return Array.from({length: 3}, (_,i)=>
      `<line x1="8" y1="${14+i*((h-34)/3)}" x2="${w-6}" y2="${14+i*((h-34)/3)}" stroke="${axisC}" stroke-width=".6" opacity=".3"/>`).join('');
    return '';
  };

  const mini = (inner, h) => {
    const w = 118;
    return `<div style="border:${frame};border-radius:8px;background:#fff;padding:6px">
      <svg viewBox="0 0 ${w} ${h}" width="100%" style="display:block">${gridHtml(w,h)}${inner}${axes(w,h)}</svg></div>`;
  };

  /* 柱状图 */
  const bars = [30,46,38,54,42].map((v,i)=>{
    const bh = Math.round(v/58*(h1-26));
    const x = 12 + i*20;
    return `<rect x="${x}" y="${h1-10-bh}" width="11" height="${bh}" rx="1.5" fill="rgba(21,101,192,${op})" stroke="#123a6b" stroke-width="${Math.max(lw*.3,.7).toFixed(2)}"/>` +
      `<line x1="${x+5.5}" y1="${h1-10-bh-2}" x2="${x+5.5}" y2="${h1-10-bh-6}" stroke="${axisC}" stroke-width="1"/>`;
  }).join('');
  const barChart = `<svg viewBox="0 0 118 ${h1}" width="100%" style="display:block">${gridHtml(118,h1)}${bars}${axes(118,h1)}</svg>`;

  /* 折线图（置信带） */
  const pts = [[10,40],[42,30],[74,38],[106,22]];
  const band = [35,36,33,30,28,25,24,19,17,16].map((y,i)=>`${10+i*10.6},${y}`).join(' ');
  const line = pts.map((p,i)=>`${p[0]},${p[1]}`).join(' ');
  const lineChart = `<svg viewBox="0 0 118 ${h1}" width="100%" style="display:block">${gridHtml(118,h1)}
    <polygon points="10,42 ${line.replace(/ /g,',')} 106,44 10,44" fill="rgba(21,101,192,${op*.35})"/>
    <polyline points="${line}" fill="none" stroke="#1565C0" stroke-width="${lw}" stroke-linejoin="round" stroke-linecap="round"/>
    <line x1="10" y1="42" x2="106" y2="42" stroke="${axisC}" stroke-width=".7" stroke-dasharray="3 3" opacity=".5"/>${axes(118,h1)}</svg>`;

  /* 散点图（回归线） */
  const sc = [[18,52],[30,46],[42,48],[54,38],[66,34],[78,28],[90,24],[100,20]];
  const dots = sc.map(p=>`<circle cx="${p[0]}" cy="${p[1]}" r="3" fill="rgba(21,101,192,${op})" stroke="#123a6b" stroke-width="${Math.max(lw*.25,.6).toFixed(2)}"/>`).join('');
  const scChart = `<svg viewBox="0 0 118 ${h1}" width="100%" style="display:block">${gridHtml(118,h1)}${dots}
    <line x1="14" y1="56" x2="104" y2="16" stroke="#1565C0" stroke-width="${Math.max(lw*.8,1).toFixed(1)}" stroke-dasharray="4 3"/>${axes(118,h1)}</svg>`;

  /* 热力矩阵 3×3 */
  const hm = [0.15,0.5,0.85,0.4,0.7,0.35,0.8,0.25,0.6].map((a,i)=>
    `<rect x="${12+(i%3)*30}" y="${10+((i/3)|0)*17}" width="26" height="13" rx="2" fill="rgba(21,101,192,${(op*a).toFixed(2)})" stroke="#123a6b" stroke-width="${Math.max(lw*.3,.6).toFixed(2)}"/>`).join('');
  const hmChart = `<svg viewBox="0 0 118 ${h1}" width="100%" style="display:block">${gridHtml(118,h1)}${hm}${axes(118,h1)}</svg>`;

  const cell = (t, body) => `<div style="min-width:0">
    ${body}
    <div style="font-size:11px;font-weight:600;color:#555;margin-top:4px;text-align:center">${t}</div></div>`;

  return `<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
      ${cell('柱状图 · 误差棒', mini(bars, h1))}
      ${cell('折线图 · 置信带', lineChart)}
      ${cell('散点图 · 回归', scChart)}
      ${cell('热力矩阵', hmChart)}
    </div>
    <div style="margin-top:8px;font-size:12px;font-weight:600;color:#444">${esc(label)}</div>
    <div style="font-size:11px;color:#999;margin-top:2px">${esc(st.desc||'')}</div>`;
}
function nwRenderPrev(type){
  const el=document.getElementById('nwPrev'); if(!el) return;
  const cur=NW_PICK[type];
  if(type==='palette'){
    el.innerHTML=_paletteBars(PALETTE_HEX[cur]||PALETTE_HEX['随机（推荐）'], cur);
  }else{
    el.innerHTML=_layoutRealDiff(cur||'随机（推荐）');
  }
}
function nwModal(type){
  NW_SNAP[type] = NW_PICK[type];
  const items = type==='palette'?PALETTES:LAYOUTS;
  const overlay=document.createElement('div');
  overlay.className='modal open'; overlay.id='nwModal';
  overlay.innerHTML=`<div class="modal-box modal-wide">
    <div class="modal-top"><h3>${type==='palette'?'数据图配色':'图表版式'}</h3>
      <button class="modal-x" aria-label="关闭" onclick="nwModalClose(true,'${type}')">✕</button></div>
    <div class="picker-cols">
      <div class="pick-list">
        ${items.map((it,i)=>`<div class="pick-item ${it===NW_PICK[type]?'sel':''}" data-idx="${i}" data-item="${esc(it)}" onclick="nwPickItem(this,'${type}')">${esc(it)} ${it===NW_PICK[type]?'✓':''}</div>`).join('')}
      </div>
      <div class="pick-prev" id="nwPrev"></div>
    </div>
    <div class="modal-foot"><button class="btn btn-ghost" onclick="nwModalClose(true,'${type}')">取消</button>
      <button class="btn btn-primary" onclick="nwModalClose(false,'${type}')">确定</button></div>
  </div>`;
  document.body.appendChild(overlay);
  nwRenderPrev(type);
}
window.nwModalClose = function(cancel, type){
  if (cancel) NW_PICK[type] = NW_SNAP[type];
  const m = document.getElementById('nwModal'); if (m) m.remove();
  nwPickBtn(type);
};
/* 流程图配色预览：3 种配色（纯黑白/朴素竞赛/现代精致）各渲染一张精致流程图，点击即选定 */
const FP_META = [
  {v:'bw',     t:'纯黑白',   node:'#ffffff', border:'#111111', text:'#111111', arr:'#3a3a3a', sub:'#777777', bg:'#ffffff'},
  {v:'plain',  t:'朴素竞赛', node:'#f2f6fc', border:'#3b5b92', text:'#23466f', arr:'#4a7ab5', sub:'#7a90ad', bg:'#ffffff'},
  {v:'modern', t:'现代精致', node:'#2563eb', border:'#1d4ed8', text:'#ffffff', arr:'#2563eb', sub:'#93c5fd', bg:'#eef4ff'},
];
/* 六步流程链（两列三行） */
function _flowPreviewSvg(m){
  const node = (x, y, t, sub) => `<rect x="${x}" y="${y}" width="96" height="32" rx="9" fill="${m.node}" stroke="${m.border}" stroke-width="1.3"/>
    <text x="${x+48}" y="${y+14}" text-anchor="middle" font-size="11" font-weight="600" fill="${m.text}">${t}</text>
    <text x="${x+48}" y="${y+25}" text-anchor="middle" font-size="7" fill="${m.sub}">${sub}</text>`;
  const arrow = (x1,y1,x2,y2) => `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${m.arr}" stroke-width="1.6" stroke-linecap="round"/>
    <path d="M${x2-5} ${y2-3} L${x2} ${y2} L${x2-5} ${y2+3}" fill="none" stroke="${m.arr}" stroke-width="1.4"/>`;
  const h = 164;
  return `<svg viewBox="0 0 264 ${h}" width="100%" style="display:block;background:${m.bg}">
    ${node(14, 18, '赛题输入', 'PROBLEM')}${node(154, 18, '数据预处理', 'DATA CLEAN')}
    ${node(14, 74, '建模求解', 'MODELING')}${node(154, 74, '编程实现', 'SOLVING')}
    ${node(14, 130, '结果验证', 'VALIDATION')}${node(154, 130, '论文输出', 'REPORT')}
    ${arrow(110, 34, 150, 34)}${arrow(110, 90, 150, 90)}${arrow(110, 146, 150, 146)}
    ${arrow(202, 50, 202, 70)}${arrow(62, 50, 62, 70)}${arrow(202, 106, 202, 126)}${arrow(62, 106, 62, 126)}
  </svg>`;
}
window.showFlowPalette = function(){
  const cur = (document.querySelector('[data-field="colorScheme"] .pill.active')||{}).dataset?.val || 'bw';
  let overlay = document.getElementById('fpModal'); if(overlay) overlay.remove();
  _mfLockScroll();
  overlay = document.createElement('div');
  overlay.className='modal open'; overlay.id='fpModal';
  overlay.innerHTML=`<div class="modal-box modal-wide">
    <div class="modal-top"><h3>流程图配色预览</h3>
      <button class="modal-x" aria-label="关闭" onclick="fpClose()">✕</button></div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:14px;padding:2px 2px 12px">
      ${FP_META.map(m=>`
      <div class="fp-card ${m.v===cur?'sel':''}" data-v="${m.v}" onclick="fpPick('${m.v}')">
        ${_flowPreviewSvg(m)}
        <div class="fp-name">${m.t} ${m.v===cur?'✓':''}</div>
      </div>`).join('')}
    </div>
    <div class="modal-foot"><button class="btn btn-primary" onclick="fpClose()">完成</button></div>
  </div>`;
  document.body.appendChild(overlay);
};
window.fpPick = function(v){
  const pill = document.querySelector(`[data-field="colorScheme"] .pill[data-val="${v}"]`);
  if(pill) nwPill(pill);
  document.querySelectorAll('#fpModal .fp-card').forEach(c=>{
    const on = c.dataset.v === v;
    c.classList.toggle('sel', on);
    const nm = c.querySelector('.fp-name');
    if(nm) nm.innerHTML = c.dataset.v===v ? (nm.textContent.replace(' ✓','') + ' ✓') : nm.textContent.replace(' ✓','');
  });
  fpClose();
};
window.fpClose = function(){
  const m = document.getElementById('fpModal'); if(m) m.remove();
  _mfUnlockScroll();
};
window.nwPickBtn = function(type){
  const id = type==='palette' ? 'cfPaletteBtn' : 'cfLayoutBtn';
  const el = document.getElementById(id); if (!el) return;
  const v = NW_PICK[type] || '';
  el.textContent = (v === '随机（推荐）' || !v) ? '随机 ›' : v + ' ✓';
};
window.nwPickItem = function(el, type){
  document.querySelectorAll('#nwModal .pick-item').forEach(p=>{p.classList.remove('sel');p.textContent=p.textContent.replace(' ✓','');});
  el.classList.add('sel'); el.textContent=el.textContent+' ✓';
  NW_PICK[type]=el.dataset.item;
  nwRenderPrev(type);
  nwPickBtn(type);
};
window.nwRenderPrev = nwRenderPrev;
window.nwModal = nwModal;

/* ---- 所有图表类型预览：全部图表实例图墙 ----
   只保留一套鲜艳明亮的默认配色（vivid），不做主题/风格切换，直接铺开全部图表。 */
window.showStylePreview = function(){
  const total = PAPER_GROUPS.reduce((n,g)=>n+g.items.length,0);
  const overlay=document.createElement('div');
  overlay.className='modal open'; overlay.id='spModal';
  overlay.innerHTML=`<div class="modal-box modal-full">
    <div class="modal-top">
      <span class="sp-title">全部图表 · 示例（共 ${total} 种 · 鲜艳明亮默认配色）</span>
      <button class="modal-x" aria-label="关闭" onclick="document.getElementById('spModal').remove()">✕</button>
    </div>
    <div class="sp-scroll" id="spWall">${_allPrev('vivid')}</div>
  </div>`;
  document.body.appendChild(overlay);
};

/* ---- 流程对比：极速快跑流 vs 双审冲奖流 vs 个人自制流（树状图：主环节 → 子步骤，点击看详情） ---- */
const FLOW_DATA = [
  {key:'native', ico:'⚡', name:'极速快跑流', accent:'#2E5EA8', steps:[
    {t:'赛题分析', d:'解析题意 · 提取数据与参数', more:'第一步先把题目"吃透"：通读题面抓目标与约束，把附件里的数据表提取成干净清单，再锁定该用什么方法方向。方向定了后面才不容易白跑。\n\n【内置 skill】comp-prob-analysis（赛题分析）\n【配套软件资产】\n- 附件/数据读取：pandas + data_profile.py 自动做字段画像与缺失分析\n- LLM 通读题面 → 复述目标/约束/评价指标\n- numpy/pandas 把表格整理成干净 csv 供后面建模直接引用\n【产出】题意复述 + 数据清单 + 拟用方法方向（写入工作区 RESULTS.md）', ch:[
      {t:'解析题意', d:'厘清赛题目标、约束条件与评价指标', more:'动手前先把题"吃透"到底：第一遍通读抓大结构（共几问、每问要什么结论），第二遍圈出关键词——目标、约束、评价指标、数据口径；再对照评分标准看每问的采分点，把"题目要我回答什么"复述成一句话写进 PROBLEM_ANALYSIS.md 开头。做完这步，后面所有环节都照着这条"题意基线"走，防止跑偏。'},
      {t:'提取数据', d:'读取上传赛题/附件中的数据与参数', more:'把赛题附件当"原材料"处理：先用脚本扫描所有表格（xlsx/csv/dat）看字段与行数，再清洗缺失值、重复行、量纲换算，生成干净的 data_clean.csv；同时把题目正文里的常量参数（人数、容量、成本等）登记成参数表。数据缺项或口径模糊处一律标注"待确认"，不要在建模型时才发现。产出：数据清单 + 清洗后数据文件，落到工作区供后面建模直接引用。'},
      {t:'定位方向', d:'锁定关键问题与拟采用的方法方向', more:'动手建模型前先给题目"对号入座"：评价/排序类→层次分析、熵权、TOPSIS；预测类→回归、时间序列、机器学习；优化类→线性规划、启发式算法；分类/识别类→统计判别、聚类。判断依据是"题目要输出什么结论"，而不是第一直觉。写下一句话方向说明 + 备选方向，后续步骤从中定主力方法深入。'}]},
    {t:'建模求解', d:'建立模型 · 选择算法 · 公式推导', more:'把实际问题翻译成数学问题：设变量、构造目标函数与约束，选一个能算得动的算法，并把公式和假设推导写清楚。\n\n【内置 skill】comp-modeling（建模求解）\n【配套软件资产】\n- stats_utils.py（scipy）：显著性检验 / 分布拟合 / 相关性分析\n- LaTeX 公式渲染（KaTeX/tex 流程），公式可直接进论文\n- CLAUDE.md 注入题目与数据上下文，建模方向一致\n【产出】数学模型 + 公式 + 算法与假设说明', ch:[
      {t:'建立模型', d:'构造数学模型与目标函数', more:'把现实问题抽象成符号语言：哪些是变量、目标是什么函数、约束怎么写，模型的好坏决定论文的下限。'},
      {t:'算法选型', d:'对比常用解法，选择合适算法', more:'把候选求解算法摆出来比：适用范围（连续/离散/大规模）、求解质量、实现难度、耗时，再结合数据量和工作流剩余时间，选一个"够用且能跑完"的算法。比选记录连同选择理由写进报告，论文的"方法选择"小节直接取材于此，体现严谨性；若主算法跑不动，留下的备选就是退路。'},
      {t:'推导假设', d:'完成公式推导并写明模型假设', more:'把模型的数学推导完整走一遍保证自洽：关键公式手推/验算、边界情况是否成立；同时把模型的假设写清楚——忽略了什么、近似的粒度、参数取值依据。假设不是借口而是严谨性的体现，评委主要看这部分。推导结论与假设一并记入 MODELING_REPORT.md，供复核环节挑刺。'}]},
    {t:'编程实现', d:'求解计算 · 输出结果数据', more:'把模型写成 Python 脚本真正跑出数字：写代码、运行求解、自动审计结果完整性，缺项自动回补重算。\n\n【内置 skill】comp-code（编程实现）\n【配套软件资产】\n- python3 求解脚本（numpy/pandas），结果以 JSON 落盘\n- 多进程并行（提前预热 matplotlib 字体缓存防竞态）\n- 自审计：缺项/越界/格式检查，自动回补重算，缺数据自动补跑\n【产出】各问数值结果 + 可复现代码（figures/*_results.json）', ch:[
      {t:'代码实现', d:'编写 Python 求解脚本', more:'按模型把算法写成 Python 脚本：数据结构（numpy 数组/DataFrame）与结果输出格式（JSON 字段名）先约定死，再写求解主体，最后固定随机种子、打印关键中间量便于排查。代码放到工作区并保证可复现——同一输入跑两次结果一致。产出可运行脚本，后续数值求解与复核都直接调用它。'},
      {t:'数值求解', d:'运行计算并产出结果数据', more:'运行脚本算出每一问的数值结果：检查精度设置、迭代收敛条件、结果量级是否合理。结果统一保存为 JSON，论文里的数据表与图全部从这里取数，保证"论文数字 = 代码输出"，不做二次手工改动。若求解失败或明显不合理，回代码定位修复后重跑。'},
      {t:'自审计', d:'自动审计结果完整性，缺项回补', more:'用自动检查脚本过一遍结果质量：字段是否齐全、有无 NaN/Inf、数值是否越界（如概率 >1、比例非负）、各问结果是否自洽。发现问题自动回补重算最多三轮，仍不过则标记出来人工介入。这一步把"结果不合理/明显错误"挡在进论文之前。'}]},
    {t:'图表生成', d:'论文级数据图 · 自动质检', more:'把结果画成论文级数据图（柱/线/散/热力等），再用 AI 检查坐标轴、标签这类硬伤，不合格自动修图。\n\n【内置 skill】paper-figure（图表生成）\n【配套软件资产】\n- plot_utils.py 风格基线（setup_style：自动配色/字体/网格，论文出版级）\n- 图表模板库 chart_library（70 类：三阶段选型→查 recipe 抄码→填数据）\n- figure_recipes_*.md 画法配方 + get_recipe.py 取码\n- figure_check.sh 尺寸档位闸 + 视觉质检（坐标轴截断/标签重叠自动修）\n【产出】可直接插入论文的 SVG/PDF 矢量图', ch:[
      {t:'绘制图表', d:'柱/线/散/热力等论文级出图', more:'按 70 类图表模板库流程出图：先三阶段选型定类别与具体图（比较/趋势/分布/相关/组成/专业），再打开对应 recipe 抄代码、填入真实结果数据，统一用 plot_utils 论文风格基线（配色/字体/清晰度）。每张图导出 SVG/PDF 矢量格式、命名规范，供论文直接 include。'},
      {t:'视觉质检', d:'AI 检查坐标轴/标签等硬伤', more:'让 AI 把每张图"看"一遍，检查坐标轴截断、刻度标签重叠、图例缺失、单位缺失、中文变方框等肉眼易漏的硬伤；发现问题的自动修图后复查，最多修 3 轮。质检通过才允许进论文，杜绝投稿级低级错误。'}]},
    {t:'流程与架构图', d:'技术路线图 · 流程图 · TikZ', more:'画整体技术路线图、按子问题拆的求解流程图，以及 LaTeX 矢量架构图，把"方法全貌"讲清楚。\n\n【内置 skill】paper-figure-html（流程与架构图）\n【配套软件资产】\n- HTML+CSS 自动布局引擎：AI 只描述结构不乱写坐标，天然免疫节点重叠/连线穿越\n- 截图转图 screenshot_capture.py → PNG/PDF + html_pdf_check 质检\n- Mermaid（轻量备选）；TikZ + xelatex（精密几何矢量示意）\n【产出】技术路线图 + 求解流程图 + TikZ 矢量架构图', ch:[
      {t:'技术路线', d:'绘制整体技术路线图', more:'画一张"数据 → 建模 → 求解 → 检验 → 结论"的整体技术路线图，把每个子问题的方法与数据流标注在图上，评委扫一眼就能看懂你的整体设计。用 HTML 自动布局引擎绘制：只需描述结构关系，节点连线自动排布、不重叠。导出高清 PNG 供论文使用。'},
      {t:'流程图', d:'按问题拆分求解流程图', more:'除了总路线图，再为每个子问题单独画一张求解流程图：输入 → 处理步骤 → 输出，标注关键参数与方法名，展示你的解题过程与逻辑。同样用 HTML 布局引擎产出，风格与总图统一，放进对应问题分析章节。'},
      {t:'TikZ 矢量', d:'输出可编译矢量架构图', more:'对需要精密几何的架构图（如系统结构、训练流程、机制示意）用 LaTeX TikZ 绘制：矢量输出放大不糊、字号字体与论文一致，编译 PDF 时保持清晰。TikZ 代码写在 tex 里可直接复用，配合 xelatex 编译检查无误后随论文交付。'}]},
    {t:'逻辑对抗复核', d:'独立视角挑逻辑漏洞 · 发现则回炉', more:'换个"挑刺"视角通查全流程：方向有没有反、是不是重复计量、外推太猛、漏变量、跨问矛盾，发现致命错误就回炉重修。\n\n【内置 skill】comp-review（逻辑对抗复核）\n【配套软件资产】\n- 独立 AI 视角反向审查：方向反/重复计量/外推过硬/漏变量\n- fatal/major/minor 分级披露：致命项回炉触发重跑\n- 复核意见落盘，写论文前优先修复\n【产出】复核意见（发现问题则触发建模/编程步骤重跑）', ch:[
      {t:'对抗审查', d:'换视角排查方向反/漏变量/外推过硬', more:'让一个独立视角反向审查整套方案，专门找漏洞：方向有没有写反、同一指标是否重复计量、外推是否过于自信、是否漏掉关键变量、跨问结论是否矛盾。审查结果按 fatal / major / minor 分级记录，思路与证据落入 LOGIC_REVIEW.md，写论文前优先处理。'},
      {t:'回炉修复', d:'发现致命逻辑错则触发上一步重跑', more:'若审查发现 fatal 级问题：自动把对应的建模/编程环节标记为待重跑，被标记的环节重跑一遍后，再触发一次复核确认修复生效，然后才继续进论文阶段，形成"发现→修复→复查"闭环，防止带病进入写作。'}]},
    {t:'竞赛论文撰写', d:'生成 LaTeX 论文 main.tex', more:'按竞赛规范把正文写出来：结构完整、图表引用到位、LaTeX 排版正确，生成 main.tex 自文件。\n\n【内置 skill】comp-paper-zh（竞赛论文撰写）\n【配套软件资产】\n- LaTeX 模板库（_templates/cumcm 竞赛规范版式）\n- 图表/结果表自动引用校验（figure_style_guide 与表引用规则）\n- AI 工具使用声明自动注入（ai_disclosure 规范化）\n【产出】main.tex 论文正文自文件', ch:[
      {t:'正文撰写', d:'按竞赛规范撰写完整正文', more:'按竞赛论文规范写正文：摘要→问题分析→模型假设→模型建立→模型求解→结果分析→模型评价，每章结构完整、逻辑连贯、图表引用到位；语言按学术写作风格避免口语化，重点章节（建模与求解）写细，评价章节给出改进方向。产出 main.tex 自文件。'},
      {t:'嵌入图表', d:'引用数据图/结果表与架构图', more:'把前面生成的数据图、结果表、架构图插到对应章节，并逐一在正文中引用（"如图 X 所示"），检查图号、表号、交叉引用是否错位，杜绝"图在文不在"。图注写清横纵轴含义与主要结论，帮评委快速抓重点。'}]},
    {t:'编译与合规检查', d:'编译 PDF · 合规清单校验', more:'用 XeLaTeX 把 main.tex 编译成 PDF 成品，再用清单检查页数、格式、声明等合规项，不过关就修。\n\n【内置 skill】comp-compile-zh（编译与合规检查）\n【配套软件资产】\n- XeLaTeX（MiKTeX）编译，中文/图表位置/交叉引用自动处理\n- compile_check.sh + 合规清单（页数/格式/声明逐项核对）\n- 图尺寸校验（fig_include_size/fig_size_consistency_check）防字体糊\n【产出】成品论文 PDF', ch:[
      {t:'编译 PDF', d:'XeLaTeX 编译输出成品论文', more:'用 XeLaTeX 编译 main.tex 输出成品 PDF：自动处理中文字体、图表位置、交叉引用与目录页码。若编译报错，按错误信息逐条修复（缺宏包、表超宽、语法错误）后重新编译，直到零警告通过，产出可提交的 PDF 文件。'},
      {t:'合规校验', d:'页数/格式/声明等清单检查', more:'按竞赛合规清单逐项核对成品：页数是否超限、字体字号样式是否符合规则、摘要页与承诺书是否齐全、AI 工具使用是否声明、图表是否都有引用。任何一项不达标就回修并重新编译，确保提交前全部通过。'}]},
    {t:'论文改进循环', d:'自动审稿 → 修改 → 重编译', more:'让 AI 扮演评委通读论文挑薄弱点，按意见改稿并重新编译，最多两轮收敛，把论文从"能交"推到"能打"。\n\n【内置 skill】auto-paper-improvement-loop（论文改进循环）\n【配套软件资产】\n- AI 评委视角审稿（论证最弱/逻辑最松/表达含糊排序）\n- 改稿→重编译闭环，最多两轮，改完校验不引新问题\n【产出】改进后的论文终稿', ch:[
      {t:'自动审稿', d:'以评委视角挑论文薄弱点', more:'让 AI 扮演评委通读论文终稿，按"论证最弱 → 逻辑最松 → 表达含糊"排序挑出需要改进的点，并结合竞赛采分点检查是否有得分点没写到。审稿意见写入文档，作为下一轮修改的输入。'},
      {t:'修改重编', d:'改稿后重新编译，最多两轮', more:'针对审稿意见逐条修改正文（补充论证、收紧逻辑、润色表达），修改后重新编译 PDF 并校验没有引入新问题；最多迭代两轮，两轮后若仍可优化则记录待改进点但不阻塞交付，把论文从"能交"推到"能打"。'}]}]},
  {key:'bzd', ico:'🏅', name:'双审冲奖流', accent:'#C9A227', steps:[
    {t:'启动与题面解析', d:'翻译题面 · 提取约束与目标', more:'冲奖流的起步动作：把题面翻译复述清楚，列出约束、数据集和交付物，并对着评分标准圈出得分重点。\n\n【内置 skill】bzd-2026-stage-01（启动与题面解析）\n【配套软件资产】\n- BZD 2026 专用资自包（_bzd：状态模板/题库对标数据）\n- 题目翻译复述 → 约束/数据/交付物清单\n- 对照评分标准圈定得分重点\n【产出】题面理解 + 评分对标计划', ch:[
      {t:'理解题面', d:'翻译并复述赛题，明确任务边界', more:'冲奖流的起步：把题目用一句话翻译成自己的话，明确"要解决什么、交付什么、评分看什么"。对题面里每个术语和参数做一次释义校验，避免对题意的默认理解跑偏。理解结论写入状态模板，作为整条流水线的基线。'},
      {t:'提取约束', d:'列出约束条件、数据集与交付物', more:'逐条列出题目给出的约束条件（资自限制、边界条件、数据范围）、可用的数据集清单与必须交付的材料（论文、代码、承诺书等），形成清单。逐项打勾跟踪，防止写作阶段漏项，交付前可一键核对。'},
      {t:'评分对标', d:'对照评分标准确定答题重点', more:'把竞赛评分标准原文逐条提取（摘要质量、模型合理、创新性、稳健性、格式规范等），和题目任务建立映射，圈出得分权重最高的重点。后面每个环节都对着这张对标表自查"这步对哪个采分点有贡献"。'}]},
    {t:'建模策略与模型选型', d:'技术路线 · 候选模型对比选型', more:'动手前先想清楚整体技术路线和分工，再把候选模型摆在一起对比优劣，最终定下主模型并记录决策依据。\n\n【内置 skill】bzd-2026-stage-02（建模策略与模型选型）\n【配套软件资产】\n- 整体技术路线与分工设计\n- 候选模型对比（精度/复杂度/可解释性/适用场景）\n- 选型定案并记录决策依据\n【产出】技术路线 + 选型说明', ch:[
      {t:'路线设计', d:'制定整体技术路线与分工', more:'写论文前先把全局画清楚：问题怎么分问、每问数据怎么处理、用什么方法、结果如何汇总成一篇文章。确定各环节的责任边界与交付物，避免边做边乱；路线用一张技术路线图固定下来，后续执行严格对照。'},
      {t:'候选对比', d:'对比候选模型优劣与适用性', more:'把候选模型的精度、复杂度、可解释性、适用范围放在一起对比，配合数据量评估训练/求解可行性。对比维度与结论写入选型记录，比"拍脑袋选中"更有说服力，论文的方法对比小节直接取材。'},
      {t:'选型定案', d:'确定主模型并记录决策依据', more:'在主模型与备选之间按下"确定"：记录一句"为什么选它"及备选方案的适用场景与切换条件（如主模型跑不动或效果差时启用）。选型依据落盘，后续稳健性检验与论文方法选择都有据可查。'}]},
    {t:'建模执行', d:'按路线求解 · 结果落盘', more:'按技术路线把模型真正跑起来：编程求解每一问、结果和图表统一落盘，并交叉验证结果合理性。\n\n【内置 skill】bzd-2026-stage-03（建模执行）\n【配套软件资产】\n- 按路线编程求解各问（python/numpy/pandas，可复现）\n- 结果与图表统一落盘（JSON/figures）\n- query_model_dict 模型字典辅助选参，交叉验证自洽\n【产出】各问数值结果 + 图表', ch:[
      {t:'求解实现', d:'按技术路线编程求解各问', more:'照着技术路线把每问写成可复现的 Python 脚本并真实跑出结果：统一随机种子、固定数据预处理顺序，保证同一输入多次运行结果一致。脚本按问题分文件组织，关键中间量留日志，方便复核时回溯。'},
      {t:'结果落盘', d:'数值结果/图表保存到工作区', more:'把数值结果统一保存到工作区：JSON 存结果数据、figures 目录存生成的图表、代码保持可追溯。文件命名统一规范（问题号_方法_日期），论文阶段引用时按命名直接取数，避免"结果散落找不到来自"。'},
      {t:'验证输出', d:'交叉验证结果与模型合理性', more:'交叉验证结果与模型的合理性：数值量级对不对、边界情况是否符合物理/经济直觉、相邻问题的结果是否自洽。发现异常先查代码和数据，再查模型假设，把"算出来了但明显不对"的隐患挡在论文外，检验记录供稳健性小节引用。'}]},
    {t:'稳健性总检验', d:'灵敏度 · 鲁棒性 · 稳健性检验', more:'冲奖的说服力来自：参数小幅扰动看灵敏度、加噪声和极端数据看鲁棒性，把检验证据整理进论文。\n\n【内置 skill】bzd-2026-stage-04（稳健性总检验）\n【配套软件资产】\n- 灵敏度/鲁棒性检验脚本（扰动、加噪、极端数据）\n- figure_recipes_competition 画法（灵敏度图/稳健对比图）\n- 检验证据整理成论文小节\n【产出】稳健性检验小节', ch:[
      {t:'灵敏度', d:'参数扰动对结果的影响分析', more:'对关键参数做系统扰动（如 ±5%、±10%、±20%），看结果变化曲线，识别对结果影响最大的敏感参数。灵敏度结果用灵敏度图/单变量变化图呈现，论文中说明"哪些参数必须精确、哪些可以放宽"。'},
      {t:'鲁棒性', d:'噪声/极端数据下模型表现', more:'给数据加噪声、删改极端样本、换数据口径等压力测试，观察模型输出是否仍然稳定合理；对随机性算法多次运行看方差。鲁棒性检验证明你的方法不是"针对该数据过拟合出来的"，这是冲奖的关键加分证据。'},
      {t:'稳健结论', d:'整理稳健性检验证据入论文', more:'把灵敏度与鲁棒性检验的结果整理成论文里的"稳健性分析"小节：给出图表、关键结论、以及如何指导实际应用（参数取值建议）。用证据支撑结论可信度，形成完整的检验闭环。'}]},
    {t:'章节写作', d:'按 BZD 模板分章撰写', more:'套用 BZD 2026 模板逐章写正文，边写边嵌入图表，每章结构、字数、图表配比都对齐模板要求。\n\n【内置 skill】bzd-2026-stage-05（章节写作）\n【配套软件资产】\n- BZD 分章模板（结构/字数/图表配比约束）\n- LaTeX 排版体系（结论可编译）\n- 逐章嵌入结果表/图并引用\n【产出】分章正文草稿', ch:[
      {t:'分章撰写', d:'按 BZD 模板逐章产出正文', more:'按 BZD 2026 模板的章节骨架逐章写作：问题分析、模型建立、模型求解、结果分析、检验与结论，一章完整再进下一章。每章对照模板的结构、字数、图表配比要求，边写边落盘，确保与最终装配格式兼容。'},
      {t:'图表嵌入', d:'嵌入结果图/表并逐章引用', more:'把求解阶段的各问结果表与图表嵌进对应章节，并在正文逐一出现"如下表/如图"的引用。检查图表编号连续、前后一致、图注表题规范，保证每章的论证都有数据与图表支撑，杜绝有文无图。'}]},
    {t:'摘要与首页', d:'摘要 · 承诺书 · 首页排版', more:'摘要是评委第一眼，逼着自己提炼核心方法与结果亮点；首页的承诺书、编号、排版按规则填好。\n\n【内置 skill】bzd-2026-stage-06（摘要与首页）\n【配套软件资产】\n- 摘要提炼：做了什么/用了什么方法/得到什么结果\n- 承诺书/编号/队员信息按规则填写\n- 首页排版对齐官方模板\n【产出】摘要 + 合规首页', ch:[
      {t:'摘要', d:'提炼核心方法与结果亮点', more:'精心提炼一段摘要：你做了什么、用了什么方法、得到什么关键结果（带数字）、有什么亮点。摘要是评委第一印象，通常最后写、反复改——把全文最硬的结果和最高级的看点上提。长度与措辞对齐官方要求。'},
      {t:'首页', d:'承诺书/编号/排版按要求填写', more:'按竞赛规则填写首页要素：承诺书、参赛编号、队员信息、赛题编号等，逐项与官方模板对照填写，格式与排版保持原样。首页合规是最低门槛，任何一项格式不符都有直接扣分风险。'}]},
    {t:'全面审查 I：章节自查', d:'逐章自查 · 评分质量门', more:'第一轮质量门：按清单逐章核对完整性、格式、图表引用，不达标的章节打标记安排回修。\n\n【内置 skill】bzd-2026-stage-07（全面审查 I）\n【配套软件资产】\n- 质量门清单逐章核对（完整性/格式/图表引用）\n- 不达标章节标记 → 回修 → 复查闭环\n【产出】章节自查意见 + 回修清单', ch:[
      {t:'逐章自查', d:'按质量门逐章核对完整性', more:'用质量门清单把每章逐条核对：章节完整性、图表是否全部引用、编号与格式是否统一、公式与结论是否自洽。把发现的问题按严重程度记入自查台账，为回修提供明确清单。'},
      {t:'问题标记', d:'不达标章节标记并回修', more:'把自查发现的不达标章节明确标记（问题定位到章/节/表/图），安排进入回修流程：修改后重新自查一遍直到过关，形成"检查→标记→修复→复查"的章节质量闭环。'}]},
    {t:'全面审查 II：综合评审', d:'评审组综合把关 · 不达标回炉', more:'第二轮质量门：评审组通读全篇查逻辑连贯和表达，并对照竞赛采分点逐条核对，缺了就回炉。\n\n【内置 skill】bzd-2026-stage-08（全面审查 II）\n【配套软件资产】\n- 评审组通读全篇查逻辑连贯与表达\n- 对照竞赛采分点逐条核对，缺项回炉补充\n- doctor.py/score_artifact.py 评分脚本钻取\n【产出】综合评审意见 + 回炉清单', ch:[
      {t:'综合评审', d:'评审组通读全篇查逻辑与表达', more:'评审组（相当于多位评委）从头到尾通读终稿，专门查前后矛盾、逻辑断层、表达含糊、重复论述，输出整体修改建议。与章节自查不同，这里看重的是"全篇看下来是否经得起推敲"。'},
      {t:'冲奖把关', d:'核对竞赛采分点，缺则回炉', more:'逐条对照竞赛采分点最终核对：稳健性检验有没有写、对比实验是否充分、创新点是否突出、结论是否呼应目标。缺项的立即回炉补充，确保把采分点吃满，这是从"合格"到"冲奖"的临门一脚。'}]},
    {t:'终稿装配与合规出库', d:'装配终稿 · 26 项 AI 合规清单', more:'把各章节拼成终稿，过 26 项 AI 使用合规清单，最后导出 PDF、自码、数据包形成可提交的参赛包。\n\n【内置 skill】bzd-2026-stage-09（终稿装配与合规出库）\n【配套软件资产】\n- 终稿装配：合并章节/编号/交叉引用/目录页码\n- 26 项 AI 使用合规清单逐项核验（含工具声明）\n- 导出 PDF + 自码 + 数据包（参赛提交件 zip）\n【产出】可提交的参赛包', ch:[
      {t:'终稿装配', d:'合并各章节为装配终稿', more:'把通过审查的各章节合并成终稿：统一章节编号、公式编号、交叉引用、目录与页码，检查边距与页眉页脚等排版细节。装配完成后通读一遍全文，保证卷面整体一致、无拼接痕迹。'},
      {t:'AI 合规', d:'过 26 项 AI 使用合规清单', more:'逐项核对 26 项 AI 使用合规清单：AI 用到了哪一步、生成内容如何标注、有没有按规则声明 AI 工具参与；把 AI 使用说明补进承诺书/说明页。确保合规不出问题，避免被取消成绩。'},
      {t:'出库提交', d:'导出 PDF/自码/数据包', more:'导出最终提交物：论文 PDF、全部自码、数据文件包，检查文件齐全性与命名规范，按竞赛要求打包成参赛提交件（zip 或指定格式）。提交前最后核对一遍赛题号与材料清单，确认无误即可出库。'}]}]},
  {key:'mms', ico:'🧭', name:'个人自制流', accent:'#1F7A5C', steps:[
    {t:'选题决策', d:'多题对比 · 证据驱动定一题', more:'个人自制流的第一步：对 A-E 各题做可行性与得分潜力对比，把选题从"拍脑袋"变成有依据的决策。\n\n【内置 skill】mathmodel-skill（Stage 1）\n【配套软件资产】\n- _mms/competitions/mathmodel/ 获奖规律库（winning_patterns / topic_specs）\n- 决策与理由写入 state/decision_log.json，出现新证据可审计地重开决策\n【产出】TOPIC_DECISION.md（定题结论 + 逐题对比依据）', ch:[
      {t:'多题对比', d:'数据可得性/建模难度/发挥空间逐题评估', more:'把每个候选题放到同一张桌上比：数据好不好拿、建模难度是否匹配自己水平、有没有发挥空间拿亮点分。逐题列出证据与直觉冲突的地方，避免"第一眼看顺眼就定题"。'},
      {t:'定题决策', d:'题号与任务类型写入决策日志', more:'定下题目后把题号、task_type 和选题理由写进 state/decision_log.json。这不是仪式感——后面每一步都从决策日志取上下文，中途换题也有据可查，评委问起选题依据时论文里也写得出。'}]},
    {t:'问题深度解析与分解', d:'题意拆解 · 分离子问题 Q1..Qn', more:'把选定的题"吃透"：解析目标/约束/数据，把大问题递归拆成可独立求解的子问题清单。\n\n【内置 skill】mathmodel-skill（Stage 2）\n【配套软件资产】\n- 子问题数与权重写入 decision_log，供 Stage 5 逐问循环直接引用\n- 上传的赛题附件已落盘工作区，数据画像与清洗可直接做\n【产出】PROBLEM_DECOMPOSITION.md（题意解析 + 子问题清单）', ch:[
      {t:'题意解析', d:'目标/约束/评价指标/数据口径逐项明确', more:'通读题面圈出目标、约束、评价指标和数据口径，把"题目要我回答什么"复述成一句话写进文档开头；对每个术语做释义校验，防止默认理解跑偏。'},
      {t:'子问题分解', d:'递归拆成 Q1..Qn 并标注依赖关系', more:'把大问题拆成可独立求解的子问题：每个 Qi 的输入、输出、与其他子问题的依赖标注清楚。拆得好坏直接决定 Stage 5 循环的质量——这一步值得多花半小时。'}]},
    {t:'模型选型（候选对比）', d:'证据驱动比较 · 反事实校验 · 定案', more:'把候选模型摆在一起做证据驱动对比（精度/复杂度/可解释性/数据适配），再用反事实校验压一遍，最后定案记录。\n\n【内置 skill】mathmodel-skill（Stage 3）\n【配套软件资产】\n- _mms/config/dim_weights.json 多维评分权重\n- 选型结论与"为什么选它"写入 decision_log\n【产出】MODEL_SELECTION.md（对比表 + 定案依据）', ch:[
      {t:'候选对比', d:'多维度证据驱动比较候选模型', more:'精度、复杂度、可解释性、与数据形态的适配度放在一起比，评分维度权重按 _mms/config/dim_weights.json。对比记录直接成为论文"方法选择"小节的素材。'},
      {t:'反事实校验', d:'换个问法验证选型结论是否稳健', more:'对选型结论做反事实提问：如果数据量减半/评价指标变了，这个模型还是最优吗？经不起反事实的选型趁早换，比解出来再推倒重来省得多。'}]},
    {t:'基础框架', d:'假设 · 符号 · 术语三统一', more:'动笔建模前把全篇的"语言"统一定义好：模型假设、符号表、术语表，后面的公式和论文全部沿用。\n\n【内置 skill】mathmodel-skill（Stage 4）\n【产出】FOUNDATION.md（假设清单 + 符号表 + 术语表）', ch:[
      {t:'模型假设', d:'列出假设并写明依据与影响范围', more:'每条假设写清"为什么可以这么假设、影响哪些结论"——假设是严谨性的体现不是借口，评委主要看这部分。'},
      {t:'符号表', d:'全篇统一变量符号与量纲', more:'变量、参数、下标统一登记成符号表，量纲标注齐全。后面所有公式、代码、图表沿用同一套符号，避免"同一变量两张脸"。'}]},
    {t:'递归子问题求解循环', d:'Q1..Qn 逐问建模求解 · rubric 质量闸门', more:'流水线的主体环节：按子问题清单逐问建模求解，每问出结果图，五维 rubric 自评达标才放行进入下一问。\n\n【内置 skill】mathmodel-skill（Stage 5）+ paper-figure（论文级数据图）\n【配套软件资产】\n- chart_library 图表模板库 + plot_utils 论文风格基线出图\n- 数据图视觉质检（坐标轴/标签硬伤自动修）\n- 结果落盘 results/ + figures/，摘要写入 decision_log\n【产出】SOLVING_SUMMARY.md + 各问数值结果与图表', ch:[
      {t:'逐问求解', d:'每个 Qi 独立建模求解并交叉验证', more:'按分解清单逐问求解：建模、写代码、跑出数值结果，与相邻子问题交叉验证自洽。每问产出经过 rubric 自评（原始分≥7 且加权均分≥8 才放行），不达标自动精修。'},
      {t:'结果出图', d:'论文级数据图 + 视觉质检', more:'每问结果按图表模板库出论文级数据图，AI 视觉质检坐标轴截断/标签重叠等硬伤，不合格自动修图；"什么论证动作配什么图"参照 _mms/competitions/mathmodel/plotting_placement.md 获奖论文基线。'}]},
    {t:'全局灵敏度与稳健性', d:'参数扰动 · 噪声压测 · 检验证据入文', more:'参数系统扰动看灵敏度，加噪/极端数据看鲁棒性，检验证据整理成论文小节——这是冲奖说服力的关键。\n\n【内置 skill】mathmodel-skill（Stage 6）+ paper-figure（灵敏度图）\n【配套软件资产】\n- 灵敏度/稳健性图表模板（扰动曲线/区间对比）\n- L2 跨阶段回检：与子问题循环结论对表\n【产出】ROBUSTNESS_REPORT.md（检验结论 + 图表）', ch:[
      {t:'灵敏度分析', d:'关键参数 ±5%/10%/20% 扰动曲线', more:'对关键参数做系统扰动看结果变化曲线，识别"必须精确"与"可以放宽"的参数，论文里据此给出参数取值建议。'},
      {t:'稳健性检验', d:'噪声/极端数据下验证模型不过拟合', more:'加噪、删改极端样本、换数据口径做压力测试，随机性算法多次运行看方差。证明方法不是"针对该数据过拟合出来的"。'}]},
    {t:'模型评价与推广', d:'优缺点 · 推广性 · 改进方向', more:'客观评价模型优缺点，讨论推广到同类问题的路径与改进方向——论文"模型评价"章节的素材全在这里。\n\n【内置 skill】mathmodel-skill（Stage 7）\n【产出】MODEL_EVALUATION.md（评价 + 推广 + 改进）', ch:[
      {t:'客观评价', d:'优点不吹嘘、缺点不回避', more:'优点结合稳健性证据说，缺点给出改进方向——敢自曝有边界的模型反而显得可信，评委对"完美模型"天然警惕。'},
      {t:'模型推广', d:'同类问题的迁移路径', more:'讨论这套模型还能用在什么场景、换数据/换目标函数要改哪里。推广性体现建模功力，是加分项。'}]},
    {t:'论文写作与合规装配', d:'官方规则优先 · AI 披露 · LaTeX 装配', more:'把 Stage 0-7 的产出装配成论文：先读当届官方规则再动笔，AI 使用如实披露，按 LaTeX 模板装配编译。\n\n【内置 skill】mathmodel-skill（Stage 8）+ diagram-design（技术路线图）\n【配套软件资产】\n- _mms/templates/latex/mathmodel/main.tex 国赛规范版式\n- 摘要类型与措辞参照 abstract_template / phrase_bank\n- 技术路线图按图表路由用 diagram-design 补绘\n【产出】paper_workspace/main.tex（+ 编译 PDF）', ch:[
      {t:'分章写作', d:'按论文骨架装配既有产出，不造新结果', more:'写作阶段的原则是"装配不发明"：只把已验证的 Stage 0-7 产出组织成文，发现矛盾记录并触发定向回滚，不在写作时顺手改结论。'},
      {t:'AI 披露', d:'AI 参与环节如实声明', more:'按当届官方规则如实声明 AI 工具参与情况，披露链路贯穿全文；合规是底线，披露不清直接危及成绩。'},
      {t:'LaTeX 装配', d:'国赛模板装配并编译 PDF', more:'用 _mms 内置国赛 LaTeX 模板装配：摘要、目录、正文、附录、承诺书逐一入位，XeLaTeX 编译通过零报错。'}]},
    {t:'提交合规与多视角终审', d:'合规闸门 · L3 Panel · 回退闭环', more:'最后一道闸：先对照当届官方规则查合规（页数/匿名/披露），再由多视角 Panel 终审内容质量，不合规触发定向回退重改。\n\n【内置 skill】mathmodel-skill（Stage 9）\n【配套软件资产】\n- 26 项 AI 自查清单 + anti-patterns 反模式清单终审\n- _mms/scripts/score_artifact.py 评分脚本、doctor.py 环境自检\n【产出】SUBMISSION_REVIEW.md + 可提交参赛包', ch:[
      {t:'合规闸门', d:'页数/匿名/披露对照当届官方规则', more:'重新打开当届官方规则逐条对照：页数上限、匿名要求、AI 披露格式。合规优先于内容——再好的论文违反规则也不是"可提交"状态。'},
      {t:'多视角终审', d:'L3 Panel 多角色独立评审', more:'多个独立视角（评委/审稿人/技术审查）分别通读终稿，按反模式清单挑问题，问题按归属定向回退到对应阶段修复，改完只重跑受影响的检查。'},
      {t:'出库确认', d:'submission_ready 后打包参赛件', more:'所有合规检查与终审通过、submission_ready=true 后，导出论文 PDF、代码与数据包，按官方要求打包成参赛提交件。'}]}]},
];

function _flowTree(d){
  const steps=d.steps.map((s,i)=>{
    const ch=(s.ch||[]).map((c,j)=>`
      <div class="ft-chip" data-pop="${d.key}-${i}-${j}" tabindex="0" role="button" aria-label="查看详情">
        <div class="ft-chip-m">
          <span class="ft-chip-t">${c.t}</span>
          ${c.d?`<span class="ft-chip-d">${c.d}</span>`:''}
        </div>
        <span class="ft-more-hint">查看详情</span>
      </div>`).join('');
    return `<div class="ft-node">
      <div class="ft-dot" style="border-color:${d.accent};color:${d.accent}">${i+1}</div>
      <div class="ft-card" data-pop="${d.key}-${i}" tabindex="0" role="button" aria-label="查看详情">
        <div class="ft-head">
          <span class="ft-title">${s.t}</span>
          ${s.d?`<span class="ft-desc">${s.d}</span>`:''}
          <span class="ft-more-hint">查看详情</span>
        </div>
        ${ch?`<div class="ft-chips">${ch}</div>`:''}
      </div>
    </div>`; }).join('');
  return `<div class="ft-tree">${steps}</div>`;
}

let FC_CUR = 'native';

window.spFlowTab = function(key){
  FC_CUR = key;
  document.querySelectorAll('#fcModal .ft-flow').forEach(b=>{
    b.classList.toggle('on', b.dataset.key===key);
  });
  const d = FLOW_DATA.find(x=>x.key===key);
  document.getElementById('ftView').innerHTML = _flowTree(d);
};

window.showFlowCompare = function(){
  FC_CUR = FLOW_DATA.some(x=>x.key===FC_CUR) ? FC_CUR : 'native';
  const overlay=document.createElement('div');
  overlay.className='modal open'; overlay.id='fcModal';
  overlay.innerHTML=`<div class="modal-box modal-flow">
    <div class="modal-top">
      <h3>竞赛内部流程全景</h3>
      <button class="modal-x" aria-label="关闭" onclick="document.getElementById('fcModal').remove()">✕</button>
    </div>
    <div class="ft-flowbar">
      ${FLOW_DATA.map(d=>`<button type="button" class="ft-flow ${d.key===FC_CUR?'on':''}" data-key="${d.key}"
          onclick="spFlowTab('${d.key}')">
        <span class="ft-f-ico">${d.ico}</span>
        <span class="ft-f-name">${d.name}</span>
        <span class="ft-check">✓</span>
      </button>`).join('')}
    </div>
    <div class="ft-view" id="ftView">${_flowTree(FLOW_DATA.find(x=>x.key===FC_CUR))}</div>
  </div>`;
  document.body.appendChild(overlay);
};

/* 流程全景：点击环节/子环节弹出详情（复用 dd-panel 磨砂卡片视觉）。
   定位策略：优先锚点下方 → 空间不足翻上方 → 仍不足视口内垂直居中；
   锚点所在滚动容器滚动 / 窗口缩放时动态跟随；锚点滚出可视区自动关闭。 */
window.ftPop = function(anchor, title, text){
  ftPopClose(true);
  const panel = document.createElement('div');
  panel.className = 'dd-panel ft-pop';
  panel.setAttribute('role','dialog');
  panel.innerHTML = `<div class="ft-pop-t">${esc(title)}</div>
    <button class="ft-pop-x" aria-label="关闭" onclick="ftPopClose()">✕</button>
    <div class="ft-pop-b">${String(text||'').split('\n').map(l=>esc(l)).join('<br>')}</div>`;
  document.body.appendChild(panel);
  panel._anchor = anchor;
  const MARGIN = 8;
  // 向上查找锚点所在的滚动容器（fcModal 的 .modal-box overflow-y:auto）
  let scrollEl = null;
  let el = anchor.parentElement;
  while(el && el !== document.body){
    const cs = getComputedStyle(el);
    if(/auto|scroll|overlay/.test(cs.overflowY) && el.scrollHeight > el.clientHeight){
      const rEl = el.getBoundingClientRect();
      if(rEl.width > 0 && rEl.height > 0){ scrollEl = el; break; }
    }
    el = el.parentElement;
  }
  let detached = false;
  const detach = ()=>{
    if(detached) return;
    detached = true;
    if(scrollEl) scrollEl.removeEventListener('scroll', onScroll, true);
    window.removeEventListener('resize', onResize);
  };
  // 返回 true 表示锚点已滚出可视区（调用方应关闭并解绑）
  const place = ()=>{
    if(detached || !panel.isConnected || !document.body.contains(anchor)) return true;
    const r = anchor.getBoundingClientRect();
    const vw = document.documentElement.clientWidth;
    const vh = document.documentElement.clientHeight;
    if(r.bottom < 0 || r.top > vh || r.right < 0 || r.left > vw){ detach(); ftPopClose(true); return true; }
    const pr = panel.getBoundingClientRect();
    // 水平：锚点左缘对齐；右侧溢出则右对齐；仍溢出则贴边
    let left = r.left;
    if(left + pr.width > vw - MARGIN) left = Math.max(MARGIN, r.right - pr.width);
    if(left + pr.width > vw - MARGIN) left = vw - pr.width - MARGIN;
    if(left < MARGIN) left = MARGIN;
    // 垂直：优先下方 → 上方 → 视口内居中
    const below = r.bottom + MARGIN;
    const above = r.top - pr.height - MARGIN;
    const fits = t => t >= MARGIN && t + pr.height <= vh - MARGIN;
    let top;
    if(fits(below)) top = below;
    else if(fits(above)) top = above;
    else top = Math.max(MARGIN, Math.round((vh - pr.height) / 2));
    panel.style.left = left + 'px';
    panel.style.top = top + 'px';
    return false;
  };
  const onScroll = ()=>{ place(); };
  const onResize = ()=>place();
  if(scrollEl) scrollEl.addEventListener('scroll', onScroll, {passive:true});
  window.addEventListener('resize', onResize);
  panel._detach = detach;
  place();
  requestAnimationFrame(place);
  panel.tabIndex = -1;
  panel.focus();
};
window.ftPopClose = function(instant){
  const p = document.querySelector('.ft-pop');
  if(!p) return;
  if(p._detach){ try{ p._detach(); }catch(e){} }   // 解绑滚动/缩放监听，避免泄漏
  if(instant){ p.remove(); return; }
  p.classList.add('closing');
  setTimeout(()=>{ if(p.isConnected) p.remove(); }, 120);
};
/* 点击流程全景内的任意环节/子环节 → 弹详情；点外部/Esc 关闭（两条流都生效） */
document.addEventListener('click', (e)=>{
  const t = e.target.closest('[data-pop]');
  if(!t || !t.closest('#fcModal')) return;
  const [fk, si, ci] = t.dataset.pop.split('-');
  const d = FLOW_DATA.find(x=>x.key===fk);
  if(!d) return;
  if(ci !== undefined){
    const s = d.steps[+si], c = s && s.ch && s.ch[+ci];
    if(c) ftPop(t, c.t, c.more || c.d);
  }else{
    const s = d.steps[+si];
    if(s) ftPop(t, s.t, s.more || s.d);
  }
});
document.addEventListener('pointerdown', (e)=>{
  const p = document.querySelector('.ft-pop');
  if(!p) return;
  if(p.contains(e.target) || (p._anchor && p._anchor.contains(e.target))) return;
  ftPopClose();
}, true);
document.addEventListener('keydown', (e)=>{ if(e.key === 'Escape') ftPopClose(); });

/* ---- 弹窗滚动锁（统一实现） ----
   用 body{position:fixed} 把背景钉在当前滚动位置，弹窗期间页面不移动；
   解锁后移除 fixed 并滚动回原位。坑：不能对 documentElement 设 overflow:hidden，
   那会禁用视口滚动并把 window.scrollY 归零，导致开/关弹窗页面"跳回顶部"。 */
let _MF_LOCK_Y = 0;
function _mfLockScroll(){
  _MF_LOCK_Y = window.scrollY;
  const sbw = window.innerWidth - document.documentElement.clientWidth;
  document.body.style.position='fixed';
  document.body.style.top = (-_MF_LOCK_Y)+'px';
  document.body.style.left='0';
  document.body.style.right='0';
  document.body.style.overflowY='scroll';       // 保留纵向滚动条，防止视口宽度抖动
  if(sbw>0) document.body.style.paddingRight = sbw+'px';
}
function _mfUnlockScroll(){
  const y = _MF_LOCK_Y;
  document.body.style.position='';
  document.body.style.top='';
  document.body.style.left='';
  document.body.style.right='';
  document.body.style.overflowY='';
  if(document.body.style.paddingRight) document.body.style.paddingRight='';
  // 等 fixed 移除后（双 rAF）再恢复滚动位置
  requestAnimationFrame(()=>{ requestAnimationFrame(()=>{ window.scrollTo(0, y); }); });
}

/* 弹窗打开时锁定背景滚动：只要存在显示中的 .modal（含流程全景 fcModal/图表示例 spModal/
   配色版式 nwModal 等）就锁住 body，全部关闭后恢复。修复"弹框内部滚动时背后页面跟着滚"。 */
(()=>{
  let _locked = false;
  const _syncModalScrollLock = ()=>{
    const anyOpen = document.querySelector('.modal.open') !== null;
    if(anyOpen === _locked) return;
    _locked = anyOpen;
    if(anyOpen) _mfLockScroll(); else _mfUnlockScroll();
  };
  const _obs = new MutationObserver(_syncModalScrollLock);
  _obs.observe(document.body, {childList:true, subtree:true});
  // 初始化一次（若页面初始就带打开状态的弹窗）
  _syncModalScrollLock();
})();

/* 高级选项数量：自动开关（开=自动，输入禁灰；关=手填，输入可编辑） */
window.nwCtlAuto = function(inputId, chk){
  const inp = document.getElementById(inputId);
  if(!inp) return;
  if(chk.checked){
    inp.value = '0';
    inp.disabled = true;
    inp.placeholder = '自动';
  }else{
    inp.disabled = false;
    inp.placeholder = '自定义';
    inp.focus && inp.focus();
  }
};

/* ---- 创建竞赛 ---- */
window.createComp = async function(){
  const title=$('#cfTitle').value.trim()||'新建竞赛工作流';
  const contestSel=document.querySelector('.contest-opt.sel');
  const contest=contestSel?contestSel.dataset.id:'';
  // 收集所有 radio-pills 的选中值（按 data-field 分类）
  const pv = {};
  document.querySelectorAll('.radio-pills').forEach(g=>{ const a=g.querySelector('.pill.active'); if(a) pv[g.dataset.field||'']=a.dataset.val; });
  const chk=id=>document.getElementById(id).checked;
  // 图片数量：0/空 = auto（skill 自动决定），>0 = 硬目标（skill source .env_skill 读 MIN_FIGURES）
  const _numOrAuto=(id)=>{ const el=document.getElementById(id);
    if(!el) return 'auto'; const n=parseInt(el.value,10);
    return (Number.isFinite(n)&&n>0)?String(n):'auto'; };
  const _imgCount=_numOrAuto('cfImgCount');
  const _tblCount=_numOrAuto('cfTblCount');
  const _modelCount=_numOrAuto('cfModelCount');
  const supplement=$('#cfSupplement')?$('#cfSupplement').value.trim():'';
  const files=Object.values(window.CFILES||{}).flat();
  const modelAlloc=pv.modelAlloc||'global';
  const step_models={};
  if(modelAlloc==='perstep'){
    (COMP_FLOW_STEPS[pv.compFlow]||COMP_STEPS).forEach(s=>{ const el=document.getElementById('cfsm_'+s.key); if(el&&el.value) step_models[s.key]=el.value; });
  }
  const config = {
    contest, qiHao:($('#cfQiHao').value||'').trim(), question:supplement, supplement,
    out_format: pv.outFormat||'pdf', review_mode: pv.reviewMode||'strict',
    page_limit:$('#cfPage').value, img_count:_imgCount, tbl_count:_tblCount, model_count:_modelCount,
    rich_mode:chk('cfRich'), logic_review:chk('cfLogicReview'),
    flow_engine: pv.flowEngine||'html', color_scheme: pv.colorScheme||'bw',
    data_palette:NW_PICK.palette, data_layout:NW_PICK.layout,
    fig_mode: pv.figMode||'builtin',
    data_fig_check:chk('cfDataFig'), per_flow:chk('cfPerFlow'), flow_fig_check:chk('cfFlowFig'),
    ai_declare:chk('cfAI'), improve_loop:chk('cfLoop'), manual_checkpoint:chk('cfCheckpoint'),
    executor:'cli',
    model:$('#cfModel').value, model_alloc:modelAlloc, step_models,
    custom_require:($('#cfCustom').value||'').trim(), outline:($('#cfOutline').value||'').trim(),
    files,
  };
  if(!config.question && !files.some(f=>f.cat==='cfProblem')){ toast('请上传赛题文件或填写赛题内容'); return; }
  // 流程方案：极速 自动流(native) / BZD 双审精制流(bzd) / 个人自制流(mms)
  const flowKind = pv.compFlow==='bzd' ? 'competition_bzd'
                 : pv.compFlow==='mms' ? 'competition_mathmodel'
                 : pv.compFlow==='modex' ? 'competition_modex' : 'competition';
  const firstStep = flowKind==='competition_bzd' ? 'stage01_kickoff'
                  : flowKind==='competition_mathmodel' ? 'mms01_topic' : 'analysis';
  const r=await post('/api/workflows',{title, template:flowKind, step:firstStep, config});
  location.hash='#/run/'+r.id;
};

/* ---- 创建学术 ---- */
window.createAdv = async function(tpl){
  const title=$('#afTitle').value.trim()||'新建学术工作流';
  const question=$('#afQuestion').value.trim();
  const config={ question, custom_require:($('#afCustom').value||'').trim(),
    outline:($('#afOutline').value||'').trim(), word_count_target:$('#afWords').value,
    model:$('#afModel').value, files:Object.values(window.CFILES||{}).flat() };
  if(!config.question && !config.files.length){ toast('请填写研究主题或上传资料'); return; }
  const card=ACADEMIC.find(p=>p.template===tpl)||{};
  const first=(card.steps&&card.steps[0]&&card.steps[0].key)||'plan';
  const r=await post('/api/workflows',{title, template:tpl, step:first, config});
  location.hash='#/run/'+r.id;
};

/* ================= 视图：运行 ================= */
const COMP_STEPS = [
  {key:'analysis',label:'赛题分析',skill:'comp-prob-analysis'},
  {key:'modeling',label:'建模求解',skill:'comp-modeling'},
  {key:'code',label:'编程实现',skill:'comp-code'},
  {key:'figure',label:'图表生成',skill:'paper-figure'},
  {key:'arch',label:'流程与架构图绘制',skill:'paper-figure-html'},
  {key:'review',label:'逻辑对抗复核',skill:'comp-review'},
  {key:'paper',label:'竞赛论文撰写',skill:'comp-paper-zh'},
  {key:'compile',label:'编译与合规检查',skill:'comp-compile-zh'},
  {key:'improve',label:'论文改进循环',skill:'auto-paper-improvement-loop'},
];
/* 三套国赛流程的步骤清单（新建表单「按步骤指定模型」随所选流程方案渲染） */
const COMP_FLOW_STEPS = {
  native: COMP_STEPS,
  bzd: [
    {key:'stage01_kickoff',label:'启动与题面解析'},
    {key:'stage02_strategy',label:'建模策略与模型选型'},
    {key:'stage03_solving',label:'建模执行'},
    {key:'stage04_robust',label:'稳健性总检验'},
    {key:'stage05_writing',label:'章节写作'},
    {key:'stage06_abstract',label:'摘要与首页'},
    {key:'stage07_review1',label:'全面审查 I：章节自查'},
    {key:'stage08_review2',label:'全面审查 II：综合评审'},
    {key:'stage09_release',label:'终稿装配与合规出库'},
  ],
  mms: [
    {key:'mms01_topic',label:'选题决策'},
    {key:'mms02_analysis',label:'问题深度解析与分解'},
    {key:'mms03_model',label:'模型选型（候选对比）'},
    {key:'mms04_foundation',label:'基础框架（假设·符号·术语）'},
    {key:'mms05_solving',label:'递归子问题求解循环'},
    {key:'mms06_robust',label:'全局灵敏度与稳健性'},
    {key:'mms07_eval',label:'模型评价与推广'},
    {key:'mms08_writing',label:'论文写作与合规装配'},
    {key:'mms09_review',label:'提交合规与多视角终审'},
  ],
};
function nwCurFlow(){
  const g=document.querySelector('.radio-pills[data-field="compFlow"] .pill.active');
  return g ? g.dataset.val : 'native';
}
/* 切换流程方案后重渲染「按步骤指定模型」行（保留已选值） */
window.nwFlowChanged = function(){
  const box=document.getElementById('cfStepModels'); if(!box) return;
  const inner=box.querySelector('div'); if(!inner) return;
  const old={}; inner.querySelectorAll('select').forEach(s=>{ old[s.id]=s.value; });
  const steps=COMP_FLOW_STEPS[nwCurFlow()]||COMP_STEPS;
  inner.innerHTML=steps.map((s,i)=>`
    <div class="step-model-row"><span class="sm-name">${i+1}. ${esc(s.label)}</span>
      <select id="cfsm_${s.key}" style="flex:1">${modelOptions()}</select></div>`).join('');
  inner.querySelectorAll('select').forEach(s=>{ if(old[s.id]) s.value=old[s.id]; });
};
let RUN_STEPS=[], RUN_WF=null, RUN_GROUPS={}, RUN_TIMER=null, RUN_WS=null;


/* 运行页标题：优先用上传赛题文件名（去扩展名），否则退回工作流标题 */
function runDisplayName(W){
  try{
    const ups = (W && W.config && W.config.files) || [];
    for(const f of ups){
      const n = f.name || f.path || '';
      if(/\.(docx?|pdf|md|txt)$/i.test(n)) return n.replace(/\.[^.]+$/, '');
    }
  }catch(e){}
  return W ? (W.title || '工作流 #' + W.id) : '';
}

async function renderRun(extra){
  const wid=parseInt(extra||0);
  clearInterval(RUN_TIMER);
  closeRunWs();
  RUN_LOG_LINES=[];
  // 即时骨架屏：不等任何网络请求先画框架，消除"点了没反应"
  $('#view').innerHTML = `
    <div class="run-head"><div style="flex:1;min-width:0"><h1 class="run-title">加载中…</h1></div></div>
    <div class="run-progress"><span class="rp-label">—</span><div class="rp-track"></div><span class="rp-pct"></span></div>
    <div class="run-cols"><div class="run-left"><div class="run-left-card"><div class="loading-bar"></div></div></div>
    <div class="run-right"><div class="card run-panel"><div class="panel-title-row"><span class="panel-title">产物文件</span></div>
      <div class="file-groups-vert"><div class="muted" style="padding:12px">加载中…</div></div></div></div></div>`;
  RUN_WF = await api('/api/workflows/'+wid);
  if(!RUN_WF || RUN_WF.detail){ $('#view').innerHTML='<div class="empty"><div class="em">⚠</div><div>工作流不存在或已被删除</div><button class="btn btn-primary" onclick="location.hash=\'#/list\'">返回列表</button></div>'; return; }
  // 加载步骤：优先实例创建时的步骤快照（配置驱动核心语义），
  // 快照为空（旧数据）才回退：模板当前定义 → 内置 COMP_STEPS
  let snap = Array.isArray(RUN_WF.steps_snapshot) ? RUN_WF.steps_snapshot : [];
  if(snap.length){
    RUN_STEPS = snap.map(s=>({key:s.key,label:s.label,skill:s.skill}));
  }else{
    RUN_STEPS=[...COMP_STEPS];
    if(RUN_WF.template && RUN_WF.template!=='competition'){
      const p=(ST.pipelines.length?ST.pipelines:await api('/api/pipelines').then(r=>r.pipelines||[]).catch(()=>[]));
      ST.pipelines=p;
      const tmpl=p.find(x=>x.template===RUN_WF.template);
      if(tmpl&&tmpl.steps&&tmpl.steps.length) RUN_STEPS=tmpl.steps.map(s=>({key:s.key,label:s.label,skill:s.skill}));
    }
  }
  runDraw();
  RUN_LAST_STATUS=RUN_WF.status;                            // 增量刷新基线
  RUN_LAST_DONECNT=Object.values(RUN_WF.steps||{}).filter(s=>s&&s.status==='done').length;
  connectRunWs(wid);
  if(RUN_WF.status==='running') runTick();
}
/* WebSocket 实时推送（优先）；断线/不支持时回落 3s 轮询。
   性能关键：log 类消息走「轻量追加」不再触发整页刷新；
   step/status 变化合并节流 1.2s 后统一拉一次数据，避免 CLI 高频工具调用把页面打爆 */
let RUN_REFRESH_T=null, RUN_LAST_SIG='';
function scheduleRunRefresh(){
  if(RUN_REFRESH_T) return;
  RUN_REFRESH_T=setTimeout(async ()=>{
    RUN_REFRESH_T=null;
    await refreshRunFromServer();
  }, 1200);
}
function connectRunWs(wid){
  closeRunWs();
  try{
    const proto=location.protocol==='https:'?'wss:':'ws:';
    const sock=new WebSocket(`${proto}//${location.host}/ws/${wid}`);
    sock.onopen=()=>{ RUN_WS_RETRY=0; };
    sock.onmessage=(ev)=>{
      let d; try{ d=JSON.parse(ev.data); }catch(e){ return; }
      if(d.type==='log'){
        appendRunLog(d);                      // 轻量：只追加日志行
      }else if(d.type==='step'||d.type==='status'){
        const sig=(d.step||'')+'|'+(d.status||'')+'|'+(d.progress??'');
        if(sig!==RUN_LAST_SIG){ RUN_LAST_SIG=sig; scheduleRunRefresh(); }
      }
    };
    sock.onclose=()=>{ RUN_WS=null; if(RUN_WF && RUN_WF.status==='running'){ scheduleWsRetry(wid); } };
    sock.onerror=()=>{ try{sock.close();}catch(e){} };
    RUN_WS=sock;
  }catch(e){ RUN_WS=null; }
}
/* 运行页活动日志区（轻量追加，上限 200 条防内存膨胀） */
let RUN_LOG_LINES=[];
function ensureLogBox(){
  // 日志体固定在「实时输出」卡片内（进度条正下方），runDraw 重绘会重建该卡片
  const body = document.getElementById('runLogBody');
  if(!body) return null;
  // 重绘后恢复历史日志行
  if(body.children.length === 0 && RUN_LOG_LINES.length){
    const frag = document.createDocumentFragment();
    for(const lineTxt of RUN_LOG_LINES){
      const div = document.createElement('div');
      div.className = 'run-log-line';
      div.textContent = lineTxt;
      frag.appendChild(div);
    }
    body.appendChild(frag);
    body.scrollTop = body.scrollHeight;
  }
  return body;
}
function appendRunLog(d){
  const stateEl = document.getElementById('runLiveState');
  if(stateEl) stateEl.textContent = '● 实时';
  const body=document.getElementById('runLogBody');
  RUN_LOG_LINES.push(`[${(d.step||'')}]] ${d.msg||''}`);
  if(RUN_LOG_LINES.length>200) RUN_LOG_LINES.splice(0,RUN_LOG_LINES.length-200);
  if(body){
    const div=document.createElement('div');
    div.className='run-log-line';
    div.textContent=`[${d.step||''}] ${d.msg||''}`;
    body.appendChild(div);
    while(body.children.length>200) body.removeChild(body.firstChild);
    body.scrollTop=body.scrollHeight;
  }
}
let RUN_WS_RETRY=0;
function scheduleWsRetry(wid){
  if(RUN_WS_RETRY>=3) return;               // 重试 3 次后放弃，靠轮询兜底
  RUN_WS_RETRY++;
  setTimeout(()=>{ if(RUN_WF && RUN_WF.status==='running') connectRunWs(wid); }, 2000*RUN_WS_RETRY);
}
function closeRunWs(){
  if(RUN_WS){ try{ RUN_WS.onclose=null; RUN_WS.close(); }catch(e){} RUN_WS=null; }
}
async function refreshRunFromServer(){
  try{
    const w=await api('/api/workflows/'+RUN_WF.id);
    RUN_WF=w; applyRunLight(w);
    if(w.status!=='running'){ clearInterval(RUN_TIMER); closeRunWs(); }
    else if(!RUN_WS){ runTick(); }           // WS 断了则确保轮询在跑
  }catch(e){}
}
async function runTick(){
  clearInterval(RUN_TIMER);
  if(RUN_WF && RUN_WF.status==='running'){
    RUN_TIMER=setInterval(async ()=>{
      try{ const w=await api('/api/workflows/'+RUN_WF.id); RUN_WF=w; applyRunLight(w); if(w.status!=='running') clearInterval(RUN_TIMER); }
      catch(e){ clearInterval(RUN_TIMER); }
    },3000);
  }
}
/* 轻量增量刷新：避免每次状态变更都整页 innerHTML 重建（C1）。
   更新：状态徽标 / 进度条 / 头部操作按钮（仅状态变化）/ 步骤卡状态文本 / 实时指示点；
   文件列表仅当「已完成步骤数」变化时重载。 */
const RUN_ST_MAP={completed:['已完成','st-completed'],running:['运行中','st-running'],failed:['失败','st-failed'],pending:['待运行','st-pending'],paused:['已暂停','st-pending']};
let RUN_LAST_STATUS='', RUN_LAST_DONECNT=0;
function runOpsHtml(w){
  return `
        ${w.status==='running'?`<button class="btn btn-ghost btn-sm" onclick="runPause()">⏸ 暂停</button>`:''}
        ${w.status==='paused'?`<button class="btn btn-primary btn-sm" onclick="runResume()">▶ 继续</button>`:''}
        <button class="btn ${w.status==='pending'?'btn-primary':'btn-ghost'} btn-sm" onclick="runStart()">${w.status==='pending'?'▶ 启动作业':'⟳ 重新运行'}</button>
        <button class="btn btn-ghost btn-sm btn-sub" onclick="openAllPrompt()">🗂 全部提示词</button>
        <button class="btn btn-ghost btn-sm btn-sub" title="下载 / 导出产物" onclick="runExportMenu(this)">⬇ 导出 <span style="opacity:.7">▾</span></button>`.trim();
}
function applyRunLight(w){
  if(!w) return;
  const st = RUN_ST_MAP[w.status]||RUN_ST_MAP.pending;
  const pct = w.progress||0;
  const steps = (w.steps||{});
  const doneCnt = w.status==='completed'
    ? RUN_STEPS.length
    : Object.values(steps).filter(s=>s&&(s.status==='done'||s.status==='warn')).length;
  // 1) 状态徽标
  const badge=document.querySelector('.run-head .badge');
  if(badge){ badge.className='badge '+st[1]; badge.innerHTML='<i></i>'+st[0]; }
  // 2) 进度条
  const lbl=document.querySelector('.rp-label'); if(lbl) lbl.textContent=doneCnt+' / '+RUN_STEPS.length+' 步骤';
  const fill=document.querySelector('.rp-fill'); if(fill) fill.style.width=pct+'%';
  const pctEl=document.querySelector('.rp-pct'); if(pctEl) pctEl.textContent=pct+'%';
  // 3) 头部操作按钮（仅状态变化时重建，避免抢焦点/闪烁）；
  //    终态/暂停态需要「重跑」与文件产物同步，直接全量渲染一次确保按钮齐全
  if(w.status!==RUN_LAST_STATUS){
    RUN_LAST_STATUS=w.status;
    if(w.status==='completed'||w.status==='failed'||w.status==='paused'){
      runDraw();
      RUN_LAST_DONECNT=doneCnt;
      return;
    }
    const opsBox=document.querySelector('.run-head > div:last-child');
    if(opsBox) opsBox.innerHTML=runOpsHtml(w);
  }
  // 4) 步骤卡状态文本/圆点/时长
  document.querySelectorAll('.run-step').forEach(card=>{
    const key=card.dataset.key; const s=steps[key]; if(!s) return;
    const status=s.status||'wait';
    const statusTxt={done:'已完成',running:'运行中',failed:'失败',warn:'有告警',wait:'等待中'}[status];
    const stColor={done:'var(--good)',running:'var(--on)',failed:'var(--bad)',warn:'var(--warn)',wait:'var(--muted)'}[status];
    const dot={done:'✓',running:'…',failed:'✕',warn:'!',wait:'·'}[status];
    const dotCls={done:'dot-done',running:'dot-run',failed:'dot-fail',warn:'dot-warn',wait:'dot-wait'}[status];
    const stEl=card.querySelector('.rs-status'); if(stEl){ stEl.textContent=statusTxt; stEl.style.color=stColor; }
    const dotEl=card.querySelector('.step-dot'); if(dotEl){ dotEl.textContent=dot; dotEl.className='step-dot '+dotCls; }
    const durEl=card.querySelector('.rs-dur'); if(durEl){ durEl.textContent = s.duration?fmtDur(s.duration):''; }
    card.classList.toggle('is-running', status==='running');
  });
  // 5) 实时指示点
  const rs=document.getElementById('runLiveState'); if(rs) rs.textContent = w.status==='running'?'● 实时':'○ 待机';
  // 6) 新完成步骤 → 重载文件列表
  if(doneCnt!==RUN_LAST_DONECNT){ RUN_LAST_DONECNT=doneCnt; loadRunFiles(); }
}
function runDraw(){
  const W=RUN_WF;
  const stMap={completed:['已完成','st-completed'],running:['运行中','st-running'],failed:['失败','st-failed'],pending:['待运行','st-pending'],paused:['已暂停','st-pending']};
  const st=stMap[W.status]||stMap.pending;
  const pct=W.progress||0;
  const steps=(W.steps||{});
  // 完成计数：已执行（done）算完成；warn 也算走完；整体 completed 直接显示全部步数，避免“ 完成却显示 6/9”
  const doneCnt = W.status==='completed'
    ? RUN_STEPS.length
    : Object.values(steps).filter(s=>s&&(s.status==='done'||s.status==='warn')).length;
  const stepCards=RUN_STEPS.map((sp,si)=>{
    const sts=steps[sp.key];
    const status=sts?sts.status:'wait';
    const statusTxt={done:'已完成',running:'运行中',failed:'失败',warn:'有告警',wait:'等待中'}[status];
    const statusCls={done:'',running:'',failed:'',warn:'',wait:''}[status];
    const model=sts&&sts.model?sts.model:'跟随全局默认';
    const dot={done:'✓',running:'…',failed:'✕',warn:'!',wait:'·'}[status];
    const dotCls={done:'dot-done',running:'dot-run',failed:'dot-fail',warn:'dot-warn',wait:'dot-wait'}[status];
    const dur=sts&&sts.duration?fmtDur(sts.duration):'';
    const stColor={done:'var(--good)',running:'var(--on)',failed:'var(--bad)',warn:'var(--warn)',wait:'var(--muted)'}[status];
    // 「重新生成本环节」：仅工作流未在运行/未暂停、且本步骤已执行过（完成/告警/失败）时可点
    const rerunnable = !['running','paused'].includes(W.status) && ['done','warn','failed'].includes(status);
    return `<div class="run-step ${status==='running'?'is-running':''}${status==='warn'?' is-warn':''}" data-key="${sp.key}">
      <div class="step-dot ${dotCls}">${dot}</div>
      <div class="rs-main">
        <div class="rs-t"><span class="rs-name"><span class="faint" style="font-family:var(--font-mono);font-weight:700;margin-right:6px">${String(si+1).padStart(2,'0')}</span>${esc(sp.label)}</span></div>
        <div class="rs-ops">
          ${rerunnable?`<button class="prompt-btn rr-btn" title="重新生成本环节（本步骤及其后步骤将从头重跑）" onclick="rerunStep('${esc(sp.key)}')">↻ 重跑</button>`:''}
        </div>
      </div>
      <div class="rs-side">
        <div class="rs-status" style="color:${stColor}">${statusTxt}</div>
        <div class="rs-dur">${dur}</div>
      </div>
    </div>`;
  }).join('');
  $('#view').innerHTML = `
    <div class="run-head">
      <div style="flex:1;min-width:0">
        <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
          <h1 class="run-title">${esc(runDisplayName(W))}</h1>
          <span class="badge ${st[1]}"><i></i>${st[0]}</span>
        </div>
        <div class="run-wid">ID: ${W.id} · ${esc(tplName(W.template))}</div>
      </div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        ${W.status==='running'?`<button class="btn btn-ghost btn-sm" onclick="runPause()">⏸ 暂停</button>`:''}
        ${W.status==='paused'?`<button class="btn btn-primary btn-sm" onclick="runResume()">▶ 继续</button>`:''}
        <button class="btn ${W.status==='pending'?'btn-primary':'btn-ghost'} btn-sm" onclick="runStart()">${W.status==='pending'?'▶ 启动作业':'⟳ 重新运行'}</button>
        <button class="btn btn-ghost btn-sm btn-sub" onclick="openAllPrompt()">🗂 全部提示词</button>
        <button class="btn btn-ghost btn-sm btn-sub" title="下载 / 导出产物" onclick="runExportMenu(this)">⬇ 导出 <span style="opacity:.7">▾</span></button>
      </div>
    </div>
    <div class="run-progress">
      <span class="rp-label">${doneCnt} / ${RUN_STEPS.length} 步骤</span>
      <div class="rp-track"><div class="rp-fill" style="width:${pct}%"></div></div>
      <span class="rp-pct">${pct}%</span>
    </div>
    <div class="run-cols">
      <div class="run-left">
        <div class="run-left-card">${stepCards}</div>
      </div>
      <div class="run-right">
        <!-- 实时输出：步骤下方、产物文件上方（右列上下排列，实时在上） -->
        <div class="card run-live" id="runLive">
          <div class="run-live-h">
            <span class="panel-title">实时输出</span>
            <span class="run-live-state" id="runLiveState">${W.status==='running'?'● 实时':'○ 待机'}</span>
          </div>
          <div class="run-live-body" id="runLogBody"></div>
        </div>
        <div class="card run-panel">
          <div class="panel-title-row"><span class="panel-title">产物文件</span>
            <span class="file-total" id="runFileCount">0</span><div style="flex:1"></div>
            <button class="btn btn-ghost btn-sm" onclick="runUpload()">上传文件</button>
            <input type="file" id="runFile" multiple style="display:none"></div>
          <div class="file-groups-vert" id="runFiles"></div>
        </div>
      </div>
    </div>`;
  ensureLogBox();
  loadRunFiles();
  // 上传逻辑
  const up=document.getElementById('runFile');
  up.onchange=async function(){
    for(const f of up.files){ const fd=new FormData(); fd.append('file',f);
      try{ await fetch('/api/upload',{method:'POST',body:fd}); }catch(e){} }
    toast('已上传',true); loadRunFiles();
  };
}
function runUpload(){ document.getElementById('runFile').click(); }
window.runUpload = runUpload;

async function loadRunFiles(){
  let groups={};
  try{ const r=await api('/api/workflows/'+RUN_WF.id+'/files'); groups=r.groups||{}; }catch(e){}
  // 过滤冗余：环境/模板/脚手架/临时/日志等内部文件不展示，只留用户关心的产物
  const _isNoise = f=>{
    const p=(f.path||'').replace(/\\/g,'/'); const n=f.name||'';
    if(/(^|\/)(_bzd|_utils_py|_templates|_checkpoints|_proof|__pycache__)(\/|$)/.test(p)) return true;
    if(/(^|\/)(\.git|\.mimosa|node_modules)(\/|$)/.test(p)) return true;
    if(/\.(log|lock)$/i.test(n)) return true;
    if(/\.(png|jpg|jpeg|svg)$/i.test(n) && /(figure|fig_|tmp|temp|preview|draft|_预览)/i.test(n)) return false; // 成品图保留
    if(/^(_|\.)/.test(n)) return /^(_bzd|\.)/.test(n);
    return false;
  };
  for(const k in groups) groups[k]=(groups[k]||[]).filter(f=>!_isNoise(f));
  // 分组内按「排版优先级」排序：论文 → 报告/正文 → 图 → 表 → 数据/结果 → 代码 → 其他；同级按名称
  const _rank = n=>{
    const l=n.toLowerCase();
    if(/\.(pdf)$/.test(l)) return 0;
    if(/\.(tex|cls|sty|bib)$/.test(l)) return 1;
    if(/\.(md)$/.test(l)) return 2;
    if(/\.(png|jpg|jpeg|svg|gif)$/.test(l)) return 3;
    if(/\.(csv|xlsx?|tsv)$/.test(l)) return 4;
    if(/\.(json)$/.test(l)) return 5;
    if(/\.(py|r|m|sh)$/.test(l)) return 6;
    return 7;
  };
  for(const k in groups){
    groups[k].sort((a,b)=>_rank(a.name)-_rank(b.name) || a.name.localeCompare(b.name,'zh'));
  }
  // 组装按步骤
  const total=RUN_STEPS.reduce((a,sp)=>{ const g=groups[sp.key]||[]; return a+g.length; },0);
  const fc=document.getElementById('runFileCount'); if(fc) fc.textContent=total;
  const box=document.getElementById('runFiles'); if(!box) return;
  box.innerHTML = RUN_STEPS.map(sp=>{
    // 全部默认折叠：文件传输/加载后不自动展开，用户想看时再点开
    const fs= groups[sp.key]||[]; const collapsed = true;
    return `<div class="fgv collapsed" data-key="${sp.key}">
      <div class="fgv-h" onclick="this.parentElement.classList.toggle('collapsed');this.querySelector('.fgv-arrow').textContent=this.parentElement.classList.contains('collapsed')?'▶':'▼';this.nextElementSibling.style.display=this.parentElement.classList.contains('collapsed')?'none':'block'">
        <span class="fgv-arrow">▶</span><span class="fgv-name">${esc(sp.label)}</span>
        <span class="fgv-count">${fs.length}</span></div>
      <div class="fgv-body" style="display:none">
        ${fs.length?fs.map(f=>`<div class="file-row">
          ${fileIcon(f.name)}
          <span class="fr-name">${esc(f.name)}</span>
          <span class="fr-cat">${esc(f.cat||'')}</span>
          <span class="fr-size">${fmtSize(f.size)}</span>
          <span class="fr-ops">
            <button class="fr-btn" onclick="window.open('/api/workflows/${RUN_WF.id}/file?path='+encodeURIComponent('${esc(f.path)}'))">预览</button>
            <button class="fr-btn" onclick="window.open('/api/workflows/${RUN_WF.id}/file?path='+encodeURIComponent('${esc(f.path)}')+'&dl=1')">下载</button>
          </span></div>`).join(''):'<div class="fgv-body" style="padding:6px 14px;color:var(--faint);font-size:12px">暂无产物</div>'}
      </div></div>`;
  }).join('')||'<div class="muted" style="padding:12px">暂无文件</div>';
}
window.runStart = async function(){
  try{ await api('/api/workflows/'+RUN_WF.id+'/start',{method:'POST'}); toast('已启动',true); renderRun(RUN_WF.id); }catch(e){ toast('启动失败'); }
};
window.runPause = async function(){
  try{ await api('/api/workflows/'+RUN_WF.id+'/pause',{method:'POST'}); toast('已暂停，下一步执行前会停下',true); renderRun(RUN_WF.id); }catch(e){ toast('暂停失败'); }
};
window.runResume = async function(){
  try{ await api('/api/workflows/'+RUN_WF.id+'/resume',{method:'POST'}); toast('已继续',true); renderRun(RUN_WF.id); }catch(e){ toast('继续失败'); }
};
/* 重新生成本环节：该步骤及其后所有步骤重置待重跑，并立即从该步骤续跑 */
window.rerunStep = async function(key){
  const label=(RUN_STEPS.find(s=>s.key===key)||{}).label||key;
  if(!(await appConfirm(`重新生成环节「${label}」？\n该步骤及其后的完成状态会被重置，并从这一步开始重新生成。`, {danger:true, okText:'重跑'}))) return;
  try{
    const r=await post('/api/workflows/'+RUN_WF.id+'/rerun',{step:key});
    if(r.detail){ toast(r.detail); return; }
    toast(r.msg==='该环节尚未执行过，无需重跑' ? r.msg : ('已从「'+label+'」重新生成'), true);
    renderRun(RUN_WF.id);
  }catch(e){ toast('重跑失败：'+String(e).slice(0,80)); }
};
window.runExport = function(){ if(RUN_WF) window.location='/api/workflows/'+RUN_WF.id+'/export'; };
window.runExportComp = function(){ if(RUN_WF) window.location='/api/workflows/'+RUN_WF.id+'/export-comp'; };
window.runExportDocx = function(){
  if(!RUN_WF) return;
  toast('正在生成 Word…');
  window.location='/api/workflows/'+RUN_WF.id+'/export-docx';
};
window.runExportMenu = function(btn){
  DD.menu(btn, [
    {head:'导出产物'},
    {icon:'rocket',  label:'导出参赛版',   onClick:()=>runExportComp()},
    {icon:'box',     label:'导出全部产物', onClick:()=>runExport()},
    '-',
    {icon:'doc',     label:'导出 Word',    onClick:()=>runExportDocx()},
  ], {align:'right', minWidth:210});
};
window.runNewFromEdit = function(){ if(RUN_WF) location.hash='#/new?edit='+RUN_WF.id; };

/* ================= 视图：设置 ================= */
let PRESETS=[], DEFAULT_P=null, EDIT_IDS=new Set();
/* 预设目录已迁移至 static/providers-catalog.js（window.PROVIDER_CATALOG，自自 cc-switch   agent 预设，中转站已排除） */
const PROVIDERS=[['openai','OpenAI 兼容'],['anthropic','Anthropic']];

/* ================= 视图：科研工具 ================= */
const TOOLS_DEF=[
  {id:'scholar',   name:'文献搜索',   tag:'搜论文 · 拿 BibTeX',            ico:'search',
   need:[], hint:'多自检索（AMiner / Semantic Scholar / CrossRef / DBLP / OpenAlex），中文优先，一键获取 BibTeX。'},
  {id:'image',     name:'AI 生图',    tag:'GPT-Image 示意图/路线图',       ico:'image',
   need:['图像生成 API Key'], hint:'生成科研示意图与技术路线图，自动转 PDF。密钥在「设置 → 图片生成」配置。'},
  {id:'docx',      name:'Word 导出',  tag:'Markdown → 规范 Word',          ico:'derive',
   need:[], hint:'把论文/报告的 Markdown 转成中文规范 Word（三线表、引用上标、黑体标题、首行缩进）。'},
  {id:'review',    name:'论文评审',   tag:'外部 LLM 审稿',                 ico:'review',
   need:['默认 API 预设'], hint:'调用全局默认预设对论文做外部评审，可临时指定其他模型。'},
  {id:'datacheck', name:'数据检查',   tag:'防 AI 编造数据',                ico:'check',
   need:[], hint:'确定性硬规则检查（LaTeX/Markdown 残留）+ 生成数据核对清单，交给 AI 自检修复。'},
  {id:'derive',    name:'排版派生',   tag:'从参考论文逆向规范',            ico:'derive',
   need:[], hint:'从一份优质 .docx 论文提取字号/字体/边距/题注等格式规范，输出 JSON + 自检表。'},
];
let TOOL_CUR='scholar';

function toolCardHead(icon,title,desc){
  return `<div class="tc-head"><span class="tc-ico">${TOOL_ICON[icon]||''}</span><div><div class="ct">${title}</div>
    <div class="cs">${desc}</div></div></div>`;
}

function renderTools(){
  $('#view').innerHTML = `
    <div class="page-head"><div><h1>科研工具</h1>
      <div class="sub">文献搜索 · AI 生图 · 论文评审 · 数据检查 · 排版派生 —— 科研工作台</div></div></div>
    <div class="tools-layout">
      <nav class="tools-nav" id="toolsNav"></nav>
      <div class="tools-panel" id="toolsPanel"></div>
    </div>`;
  renderToolsNav();
  renderToolPanel();
}
window.renderTools = renderTools;

function renderToolsNav(){
  const nav=$('#toolsNav'); if(!nav) return;
  nav.innerHTML=TOOLS_DEF.map(t=>`
    <button class="tools-nav-item ${t.id===TOOL_CUR?'active':''}" data-tid="${t.id}" onclick="toolSwitch('${t.id}')">
      <span class="tools-nav-ico">${TOOL_ICON[t.ico]||''}</span>
      <span class="tools-nav-meta"><b>${t.name}</b><em>${t.tag}</em></span>
      ${t.need.length?`<span class="tools-nav-need" title="需要配置：${t.need.join('、')}">●</span>`:''}
    </button>`).join('');
}
window.toolSwitch=function(id){
  TOOL_CUR=id;
  renderToolsNav();
  renderToolPanel();
};

function renderToolPanel(){
  const panel=$('#toolsPanel'); if(!panel) return;
  const t=TOOLS_DEF.find(x=>x.id===TOOL_CUR)||TOOLS_DEF[0];
  if(t.id==='scholar') panel.innerHTML=panelScholar(t);
  else if(t.id==='image') panel.innerHTML=panelImage(t);
  else if(t.id==='docx') panel.innerHTML=panelDocx(t);
  else if(t.id==='review') panel.innerHTML=panelReview(t);
  else if(t.id==='datacheck') panel.innerHTML=panelDataCheck(t);
  else panel.innerHTML=panelDerive(t);
}

/* ---- 工具面板模板 ---- */
function panelScholar(t){
  return `<div class="tools-card">${toolCardHead(t.ico,t.name,t.hint)}
    <div class="nrow">
      <input class="fi" id="schQ" placeholder="输入论文标题 / 关键词（支持中文）" onkeydown="if(event.key==='Enter')schSearch(true)">
      <button class="btn btn-primary" onclick="schSearch(true)"><span class="btn-plus">🔍</span>搜索 + BibTeX</button>
      <button class="btn btn-ghost" onclick="schSearch(false)">仅元数据</button>
    </div>
    <div class="tool-help">💡 输入标题或关键词，返回论文列表；「搜索 + BibTeX」额外附带引文条目，可直接复制进参考文献。</div>
    <div id="schOut" class="tool-out"></div>
  </div>`;
}
function panelDocx(t){
  return `<div class="tools-card">${toolCardHead(t.ico,t.name,t.hint)}
    <div class="field"><label class="f">Markdown 自文件 <small>论文/报告 .md 绝对路径</small></label>
      <input class="pf-input mono" id="dxSource" placeholder="C:\\...\\main.md"></div>
    <div class="field"><label class="f">文档标题 <small>(可选，用于封面标题)</small></label>
      <input class="pf-input" id="dxTitle" placeholder="如：全国大学生数学建模竞赛论文"></div>
    <button class="btn btn-primary" onclick="toolDocxConvert()">生成 Word</button>
    <div class="tool-help">💡 转换规则：标题→黑体大纲标题、正文→宋体 12pt 首行缩进 2 字符、表格→三线表、引用 [n]→上标、公式保留等宽。</div>
    <div id="dxOut" class="tool-out"></div>
  </div>`;
}
async function toolDocxConvert(){
  const src=($('#dxSource').value||'').trim();
  if(!src){ toast('请输入 Markdown 文件路径'); return; }
  const box=$('#dxOut'); box.innerHTML='<div class="loading-bar"></div>';
  const r=await post('/api/tools/docx-export',{source:src, title:$('#dxTitle').value.trim()})
    .catch(e=>({ok:false,error:String(e)}));
  box.innerHTML='';
  if(!r.ok){ box.innerHTML=`<div class="warn-text">${esc(r.error||'转换失败')}</div>`; return; }
  box.innerHTML=`
    <div class="muted" style="font-size:12px;margin:6px 0">${esc((r.stdout||'').split('\n').filter(l=>l.trim()).join('<br>'))}</div>
    ${r.output_exists?`<a class="btn btn-primary btn-sm" href="/api/tools-file?p=${encodeURIComponent(r.output)}&dl=1">⬇ 下载 Word 文档</a>`:'<div class="warn-text">未生成文件</div>'}`;
}
window.toolDocxConvert = toolDocxConvert;
function panelImage(t){
  const opts=IMG_PRESETS.length
    ? IMG_PRESETS.map(p=>`<option value="${p.id}">${esc(p.name)}${p.is_default?'（默认）':''}</option>`).join('')
    : '<option value="">未配置图像预设</option>';
  return `<div class="tools-card">${toolCardHead(t.ico,t.name,t.hint)}
    <div class="tools-need-tip">前置：在<b>「设置 → 图片生成」</b>新增并设为默认的图像预设</div>
    <div class="nrow">
      <input class="fi" id="imgPrompt" placeholder="描述你想生成的图（如：面向数学建模的技术路线图，含数据预处理/建模/求解/验证四阶段）">
      <select class="fi" id="imgRatio" style="max-width:130px">
        <option value="16:9">16:9 横图</option><option value="1:1">1:1 方图</option>
        <option value="9:16">9:16 竖图</option>
      </select>
    </div>
    <div class="field" style="margin-top:10px"><label class="f">图像预设 <small>(选择用哪个预设生图)</small></label>
      <select class="fi" id="imgPreset" style="max-width:360px">${opts}</select></div>
    <button class="btn btn-primary" onclick="toolGenImage()">生成图片</button>
    <div id="imgOut" class="tool-out"><div class="muted" style="font-size:12px">点击「生成图片」后结果在此展示。</div></div>
  </div>`;
}
function panelReview(t){
  return `<div class="tools-card">${toolCardHead(t.ico,t.name,t.hint)}
    <div class="tools-need-tip">前置：<b>${t.need.join('、')}</b>（在「设置」中添加并设为默认；也可在下方临时指定）</div>
    <div class="field"><label class="f">模型 <small>(可选，留空=全局默认)</small></label>
      <select class="fi" id="rvModel" style="max-width:360px">${modelOptions()}</select></div>
    <div class="field"><label class="f">评审内容 / 要求</label>
      <textarea id="rvPrompt" placeholder="粘贴论文段落或评审要求，例如：请以资深审稿人身份评审以下摘要的贡献与缺陷..."></textarea></div>
    <div class="field"><label class="f">System Prompt <small>(可选)</small></label>
      <input class="fi" id="rvSystem" placeholder="如：你是一个资深机器学习审稿人"></div>
    <button class="btn btn-primary" onclick="toolReview()">开始评审</button>
    <div id="rvOut" class="tool-out"></div>
  </div>`;
}
function panelDataCheck(t){
  return `<div class="tools-card">${toolCardHead(t.ico,t.name,t.hint)}
    <div class="nrow">
      <input class="fi" id="dcWs" placeholder="工作流 / 工作区目录（绝对路径）">
      <select class="fi" id="dcMode" style="max-width:150px">
        <option value="docx">docx(Word)</option><option value="pdf">pdf(LaTeX)</option>
        <option value="table">table(表格文件)</option>
      </select>
      <button class="btn btn-primary" onclick="toolDataCheck()">执行检查</button>
    </div>
    <div class="tool-help">💡 对论文或数据表格运行硬规则检查，输出报告 + 供 AI 自检的数据核对清单。</div>
    <div id="dcOut" class="tool-out"></div>
  </div>`;
}
function panelDerive(t){
  return `<div class="tools-card">${toolCardHead(t.ico,t.name,t.hint)}
    <div class="nrow">
      <input class="fi" id="ddDocx" placeholder="参考论文 .docx 绝对路径">
      <button class="btn btn-primary" onclick="toolDeriveDocx()">派生排版规范</button>
    </div>
    <div class="tool-help">💡 输出到 <code>docx_style_profiles/</code>，含结构化 JSON 与 Markdown 自检对照表。</div>
    <div id="ddOut" class="tool-out"></div>
  </div>`;
}

async function schSearch(withBib){
  const q=($('#schQ').value||'').trim();
  if(!q){ toast('请输入搜索关键词'); return; }
  const box=$('#schOut'); box.innerHTML='<div class="loading-bar"></div>';
  const r=await post('/api/tools/scholar'+(withBib?'/bibtex':''),{query:q,max:6})
    .catch(e=>({ok:false,error:String(e)}));
  box.innerHTML='';
  if(!r.ok){ box.innerHTML=`<div class="warn-text">${esc(r.error||'搜索失败')}</div>`; return; }
  const list=r.results||[];
  if(!list.length){ box.innerHTML='<div class="muted" style="padding:10px">无结果，可换关键词或改用英文检索。</div>'; return; }
  box.innerHTML=list.map((p,i)=>{
    const bib=p.bibtex?`<details style="margin-top:6px"><summary class="faint" style="cursor:pointer;font-size:12px">BibTeX（${p.bibtex_source||'-'}）</summary>
      <pre class="code-box" style="white-space:pre-wrap;margin-top:6px">${esc(p.bibtex)}</pre></details>`:'';
    const score=p.match_label==='low'?'<span class="muted" style="font-size:11px">匹配度低，谨慎引用</span>':
      p.match_score?`<span class="ck">${p.match_label||''}</span>`:'';
    return `<div class="rl" style="padding:12px 2px;border-bottom:1px solid var(--border)">
      <div style="font-weight:600">${i+1}. ${esc(p.title||'-')} ${score}</div>
      <div class="muted" style="font-size:12px;margin-top:3px">${esc((p.authors||[]).join(', '))} ${p.year?'· '+p.year:''} ${p.venue?'· '+esc(p.venue):''} ${p.doi?'· DOI: '+esc(p.doi):''}</div>
      ${bib}</div>`;
  }).join('');
}
window.schSearch = schSearch;

async function toolGenImage(){
  const p=($('#imgPrompt').value||'').trim();
  if(!p){ toast('请输入图片描述'); return; }
  const ratio=$('#imgRatio').value;
  const presetId=parseInt($('#imgPreset')&&$('#imgPreset').value||0)||0;
  if(!presetId){ toast('请先在「设置 → 图片生成」新增一个图像预设'); return; }
  const box=$('#imgOut');
  box.innerHTML='<div class="loading-bar"></div><div class="muted" style="text-align:center;font-size:12px;margin-top:8px">生成中（可能需 1-3 分钟）…</div>';
  const r=await post('/api/tools/gpt-image',{prompt:p,lang:'zh',aspect_ratio:ratio,preset_id:presetId}).catch(e=>({ok:false,error:String(e)}));
  if(!r.ok){ box.innerHTML=`<div class="warn-text">${esc(r.error||'生成失败')}</div>`; return; }
  box.innerHTML=`
    <div class="muted" style="font-size:12px;margin:8px 0">${esc((r.stdout||'').split('\n').filter(l=>l&&!l.startsWith('[')).join('<br>'))}</div>
    ${r.output_exists?`<a href="/api/tools-file?p=${encodeURIComponent(r.output)}" target="_blank"><img src="/api/tools-file?p=${encodeURIComponent(r.output)}" style="max-width:100%;border-radius:12px;border:1px solid var(--border)"></a>
    <div style="margin-top:8px"><a class="btn btn-ghost btn-sm" href="/api/tools-file?p=${encodeURIComponent(r.output)}&dl=1">下载 PNG</a></div>`:''}`;
}
window.toolGenImage = toolGenImage;

async function toolReview(){
  const prompt=($('#rvPrompt').value||'').trim();
  if(!prompt){ toast('请输入评审内容'); return; }
  const sel=$('#rvModel'); const model=sel?sel.value:'';
  const box=$('#rvOut');
  box.innerHTML='<div class="loading-bar"></div>';
  const r=await post('/api/tools/review',{prompt, system:$('#rvSystem').value.trim(), model}).catch(e=>({ok:false,error:String(e)}));
  if(!r.ok){ box.innerHTML=`<div class="warn-text">${esc(r.error||'评审失败')}</div>`; return; }
  box.innerHTML=`<div class="code-box" style="white-space:pre-wrap">${esc(r.review||r.stdout||'（无输出）')}</div>`;
}
window.toolReview = toolReview;

async function toolDataCheck(){
  const ws=($('#dcWs').value||'').trim();
  if(!ws){ toast('请输入工作区路径'); return; }
  const box=$('#dcOut');
  box.innerHTML='<div class="loading-bar"></div>';
  const r=await post('/api/tools/data-check',{workspace:ws, mode:$('#dcMode').value}).catch(e=>({ok:false,error:String(e)}));
  box.innerHTML='';
  if(!r.ok){ box.innerHTML=`<div class="warn-text">${esc(r.error||'检查失败')}</div>`; return; }
  box.innerHTML=`<div class="code-box" style="white-space:pre-wrap">${esc(r.report||r.stdout||'（无输出）')}</div>
    ${r.need_self_check?'<div class="hint" style="margin-top:8px">已生成 PAPER_DATA_CHECKLIST.md，等待 AI 自检修复。</div>':''}`;
}
window.toolDataCheck = toolDataCheck;

async function toolDeriveDocx(){
  const d=($('#ddDocx').value||'').trim();
  if(!d){ toast('请输入 .docx 路径'); return; }
  const box=$('#ddOut');
  box.innerHTML='<div class="loading-bar"></div>';
  const r=await post('/api/tools/derive-docx',{docx:d}).catch(e=>({ok:false,error:String(e)}));
  box.innerHTML='';
  if(!r.ok){ box.innerHTML=`<div class="warn-text">${esc(r.error||'派生失败')}</div>`; return; }
  const lines=(r.stdout||'').split('\n').filter(l=>l.trim());
  box.innerHTML=`<pre class="code-box" style="white-space:pre-wrap;margin-top:10px">${esc(lines.join('\n'))}</pre>`;
}
window.toolDeriveDocx = toolDeriveDocx;

async function renderSettings(){
  await loadProviders();
  await loadImgPresets();
  const s=await api('/api/settings').catch(()=>{});
  $('#view').innerHTML=`
    <div style="max-width:1240px;margin:0 auto">
    <div class="page-head"><div><h1>系统设置</h1></div></div>

    <div class="card">
      <div class="card-h">
        <div><div class="ct">模型预设</div></div>
        <button class="btn btn-accent" onclick="setNewForm()"><span class="btn-plus">＋</span> 新增预设</button>
      </div>
      <div id="setNewBox"></div>
      <div class="set-row" id="presetList"></div>
    </div>

    <div class="card">
      <div class="card-h">
        <div><div class="ct">图片生成</div></div>
        <button class="btn btn-accent" onclick="imgOpenModal()"><span class="btn-plus">＋</span> 新增预设</button>
      </div>
      <div class="set-row" id="imgPresetList"></div>
    </div>

    <div class="card">
      <div class="card-h"><div><div class="ct">软件更新</div>
        <div class="cs">当前版本 <b id="updVer">…</b></div></div></div>
      <div class="nrow">
        <input class="fi mono" id="updUrl" placeholder="https://你的域名/modelflow" style="flex:1">
        <button class="btn btn-ghost btn-sm" onclick="updSaveUrl()">保存更新自</button>
        <button class="btn btn-primary btn-sm" onclick="updCheck()">检查更新</button>
      </div>
      <div id="updBar" style="display:none;margin:10px 0">
        <div class="rp-track" style="max-width:420px"><div class="rp-fill" id="updFill" style="width:0%"></div></div>
        <span class="muted" id="updPct" style="font-size:12px;margin-left:8px"></span>
      </div>
      <div class="hint" id="updMsg" style="margin-top:6px">未检查。</div>
      <button class="btn btn-primary btn-sm" id="updApplyBtn" style="display:none;margin-top:8px" onclick="updApply()">⬇ 安装并重启</button>
    </div>

    <div class="card">
      <div class="card-h"><div><div class="ct">本地运行时</div><div class="cs">流水线执行依赖的本地组件，缺哪个点「安装」补齐</div></div></div>
      <div id="runtimeList" style="display:flex;flex-direction:column;gap:8px;margin-top:6px">检测中…</div>
    </div>

    <div class="card">
      <div class="card-h"><div><div class="ct">LaTeX 编译环境</div><div class="cs">用于将论文编译为 PDF</div></div></div>
      <div class="setting-row"><div class="k">当前状态</div><div class="v" id="latexCheck">检测中…</div></div>
    </div>
    <div class="muted" style="text-align:center;font-size:12px;color:var(--faint)">ModelFlow 智模流水线</div>`;
  // latex
  api('/api/health').then(r=>{
    const el=$('#latexCheck'); if(el) el.innerHTML=r.latex
      ?'<span class="latex-ok">√ LaTeX (MiKTeX) 已就绪</span>'
      :'<span class="muted">→ 未检测到 LaTeX，编译步骤将自动调用 xelatex</span>';
  }).catch(()=>{ const el=$('#latexCheck'); if(el) el.textContent='服务已就绪'; });
  renderPresets(); renderTplChips(); renderImgPresets();
  loadUpdateInfo();
  renderRuntimes();
}

/* 本地运行时清单：逐项展示 + 缺项一键安装 */
const RT_LABEL = {
  claude_cli:'Claude Code CLI', node:'Node.js', git:'Git', python:'Python',
  python_libs:'Python 核心库（matplotlib/numpy/pandas…）',
  xelatex:'LaTeX (MiKTeX)', ffmpeg:'FFmpeg'
};
async function renderRuntimes(){
  const box=document.getElementById('runtimeList'); if(!box) return;
  try{
    const r=await api('/api/runtimes'); const rt=r.runtimes||{};
    box.innerHTML=Object.keys(rt).map(k=>{
      const it=rt[k];
      return `<div class="rt-row">
        <span class="rt-name">${esc(RT_LABEL[k]||k)}</span>
        <span class="rt-st ${it.ok?'rt-ok':'rt-miss'}">${it.ok?'✓ 已就绪':'✗ 未安装'}</span>
        ${it.ok?'':`<button class="btn btn-accent btn-sm" onclick="rtInstall('${k}')">安装</button>`}
      </div>`;
    }).join('');
  }catch(e){ box.textContent='运行时检测失败'; }
}
window.rtInstall=async function(name){
  toast('开始安装 '+(RT_LABEL[name]||name)+' …（可能需要几分钟）');
  const r=await api('/api/runtimes/install',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});
  if(r && r.ok){ toast('已就绪',true); renderRuntimes(); }
  else toast('安装失败：'+(r&&r.msg?r.msg:'未知错误'));
};

async function loadProviders(){
  try{ const r=await api('/api/providers'); PRESETS=r.presets||[]; DEFAULT_P=r.default||null; }catch(e){ PRESETS=[]; DEFAULT_P=null; }
}
function setProviderBadge(p){
  return (p.provider||'openai')==='anthropic'?'<span class="badge9 pr-b-anthropic">Anthropic</span>':
         '<span class="badge9 pr-b-openai">OpenAI</span>';
}
function renderTplChips(){ /* 模板已移入新增弹窗（CC Switch 式），设置页不再常驻展示 */ }
/* 打开「新增预设」模态框：t=null 为空表单，t=模板对象 则预填（Voyra 风格分组表单）
   ⛔ 弹窗挂载到 document.body 顶层，避免嵌套在 .container 的 stacking context 内
      （否则遮罩无法覆盖顶部导航 → 顶部一小条不虚化）。 */
function openPresetModal(t, editId){
  closePresetModal();
  window.PV_EDIT_ID=editId||null;
  // 锁定页面滚动（统一实现：自动做滚动条宽度补偿；关闭后恢复原滚动位置）
  _mfLockScroll();
  const root=document.createElement('div');
  root.id='presetModalRoot';
  root._pf = document.activeElement;   // 记录打开前焦点，供关闭后归还
  root.innerHTML=`<div class="modal open">
    <div class="modal-box pv-modal mf-pop">
      <div class="modal-top">
        <div class="pv-head"><h3>${editId?'编辑供应商':'添加供应商'}</h3></div>
        <button class="modal-x" aria-label="关闭" onclick="setCancel()">×</button>
      </div>
      <div class="pv-scroll">
        <div id="pvPresetSection" style="display:${editId?'none':'block'}">
        <div class="pv-head" style="margin-bottom:6px">预设供应商
          <div style="flex:1"></div>
          <button class="pv-search-btn" id="pvSearchBtn" onclick="pvToggleSearch()" title="搜索供应商"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M11.5 21a9.5 9.5 0 1 0 0-19 9.5 9.5 0 0 0 0 19ZM22 22l-2-2" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
        </div>
        <div class="pv-search-wrap" id="pvSearchWrap" style="display:none">
          <input id="pvQ" placeholder="搜索供应商" oninput="pvSetQ(this.value)">
        </div>
        <div class="pv-grid" id="pvGrid"></div>
        </div>
        <div class="pv-form">
          <div class="pv-row2">
            <div class="pv-f"><label for="nf_disp" class="pv-label">供应商名称</label>
              <input class="pv-input" id="nf_disp" placeholder="例如：DeepSeek"></div>
            <div class="pv-f"><label for="nf_note" class="pv-label">备注</label>
              <input class="pv-input" id="nf_note" placeholder="例如：公司账号"></div>
          </div>
          <div class="pv-f"><label class="pv-label">官网链接</label>
            <input class="pv-input" id="nf_site" placeholder="https://example.com"></div>
          <div class="pv-f"><label class="pv-label">API Key</label>
            <input class="pv-input mono" id="nf_key" type="password" placeholder="sk-..." autocomplete="off"><a id="nf_keylink" href="#" target="_blank" rel="noreferrer" style="display:none;font-size:12px;color:#2563eb;text-decoration:none;margin-top:4px">↗ 获取 API Key</a></div>
          <div class="pv-f"><label for="nf_base" class="pv-label">请求地址</label>
            <input class="pv-input mono" id="nf_base" placeholder="https://api.example.com/v1">
            <div class="pv-fhint">兼容 Cloud API 的服务端点地址，不要以斜杠结尾。</div></div>
          <div class="pv-f"><div class="pv-label-row"><label class="pv-label">模型配置</label>
            <div style="display:flex;gap:8px">
              <button class="btn btn-ghost btn-sm" onclick="pvFetchModels()">获取模型列表</button>
              <button class="btn btn-ghost btn-sm" onclick="pvAddModel()">+ 添加模型</button>
            </div></div>
            <div id="pvModels" class="pv-models"><div class="pv-fhint">暂无模型</div></div></div>
          <div class="pv-f">
            <div class="pv-adv" id="pvAdv">
              <div class="pv-adv-title" onclick="this.parentElement.classList.toggle('open')"><span class="pv-adv-caret">›</span> 高级选项</div>
              <div class="pv-adv-body-wrap">
                <div class="pv-f"><label class="pv-label">上游格式</label>
                  <select class="pv-input pv-select" id="nf_provider" onchange="pvProtocolChanged()">
                    <option value="anthropic">Anthropic Messages（原生直连）</option>
                    <option value="openai">OpenAI Chat Completions（需路由转换）</option>
                    <option value="openai-resp">OpenAI Responses（需路由转换）</option>
                    <option value="gemini">Google Generative AI（需路由转换）</option>
                    <option value="bedrock">AWS Bedrock（原生接入）</option>
                  </select>
                  <div class="pv-fhint" id="nf_proto_hint">Anthropic Messages 为 Claude 原生协议，无需路由转换。</div></div>
                <div class="pv-f" id="nf_route_wrap" style="display:none"><label class="pv-label">路由设置</label>
                  <div class="pv-route">
                    <label class="pv-check" id="nf_route_openai_label"><input type="checkbox" id="nf_route_openai"> OpenAI 路由</label>
                    <label class="pv-check" id="nf_route_gemini_label"><input type="checkbox" id="nf_route_gemini"> Gemini 路由</label>
                  </div>
                  <div class="pv-fhint">仅非 Anthropic 上游需要路由接管，把请求/响应转换为 Anthropic Messages。</div></div>
                <div class="pv-f"><label for="nf_authfield" class="pv-label">认证字段</label>
                  <select class="pv-input pv-select" id="nf_authfield">
                    <option>ANTHROPIC_AUTH_TOKEN（默认）</option>
                    <option>x-api-key（官方直连）</option>
                    <option>OPENAI_API_KEY（兼容端点）</option>
                  </select></div>
                <div class="pv-divider"></div>
                <div class="pv-map-head"><b>模型映射</b></div>
                <div class="pv-map">
                  <div class="pv-map-h"><span>模型角色</span><span>实际请求模型</span></div>
                  ${['sonnet','opus','haiku','subagent'].map(r=>`
                  <div class="pv-map-r"><span class="pv-map-role">${r}</span>
                    <input class="pv-input mono" placeholder=""></div>`).join('')}
                </div>
                <div class="pv-f"><label class="pv-label">默认兜底模型</label>
                  <input class="pv-input mono" id="nf_fb" placeholder="未映射角色时使用"></div>
                <div class="pv-divider"></div>
                <div class="pv-f"><label class="pv-label">自定义 User-Agent</label>
                  <input class="pv-input mono" id="nf_ua_text" placeholder="默认代理浏览器标识，可留空"></div>
                <div class="pv-f"><label class="pv-label">本地代理请求覆盖</label>
                  <input class="pv-input mono" id="nf_proxy_override" placeholder="Headers / Body 覆盖，可留空"></div>
              </div>
            </div></div>
          <div class="pv-f"><label class="pv-label">配置 JSON</label>
            <div class="pv-json-wrap"><pre class="pv-json" id="pvJson"></pre></div>
            <button class="btn btn-ghost btn-sm" onclick="pvFormatJson()">格式化</button></div>
        </div>
      </div>
      <div class="pv-foot">
        <div style="flex:1"></div>
        <button class="btn btn-ghost btn-sm" onclick="setCancel()">取消</button>
        <button class="btn btn-accent btn-sm" onclick="saveNew()">${editId?'保存修改':'＋ 添加'}</button></div>
    </div></div>`;
  document.body.appendChild(root);
  if(editId && t){
    fillProviderFormForEdit(t);
  }else{
    renderPvGrid('__custom__');
    pvProtocolChanged();
    pvUpdateJson();
  }
}
function fillProviderFormForEdit(p){
  const extra=p.extra||{};
  const set=(id,val)=>{const el=document.getElementById(id);if(el)el.value=val==null?'':val;};
  window.PV_ENTRY=null; window.PV_KEYURL='';
  set('nf_disp',extra.display_name||p.name||''); set('nf_note',extra.note||'');
  set('nf_site',extra.site||''); set('nf_base',p.api_base||''); set('nf_key','');
  set('nf_provider',p.provider||'anthropic'); set('nf_authfield',extra.authfield||'ANTHROPIC_AUTH_TOKEN（默认）');
  set('nf_fb',extra.fallback_model||''); set('nf_ua_text',extra.user_agent||'');
  set('nf_proxy_override',extra.local_proxy_override||'');
  const models=[];
  if(p.model) models.push(p.model);
  const mmap=extra.model_map||{};
  Object.values(mmap).forEach(m=>{if(m&&!models.includes(m))models.push(m);});
  const mbox=document.getElementById('pvModels'); if(mbox) mbox.innerHTML='';
  models.forEach(m=>pvAddModel(m));
  if(!models.length && mbox) mbox.innerHTML='<div class="pv-fhint">暂无模型，可手动添加或获取列表</div>';
  document.querySelectorAll('#pvAdv .pv-map-r').forEach(row=>{
    const role=(row.querySelector('.pv-map-role')||{}).textContent||'';
    const input=row.querySelector('input'); if(input) input.value=mmap[role]||'';
  });
  const adv=document.getElementById('pvAdv');
  if(adv && (extra.authfield||Object.keys(mmap).length||extra.fallback_model||extra.user_agent||extra.local_proxy_override)) adv.classList.add('open');
  pvProtocolChanged(); pvUpdateJson();
}
/* 搜索折叠：点击按钮展开/收起输入框 */
window.pvToggleSearch=function(){
  const w=document.getElementById('pvSearchWrap'); if(!w) return;
  const show=w.style.display==='none';
  w.style.display=show?'block':'none';
  if(show) setTimeout(()=>{const q=document.getElementById('pvQ'); if(q) q.focus();},30);
};
/* 网格渲染：目录驱动（图标 + 中文名列表） */
const PV_CATALOG = window.PROVIDER_CATALOG || [];
let PV_FILTER = { q: '' };
function pvLogoImg(logo, fallbackTxt, fallbackColor){
  if(logo) return `<img class="pv-ico-img" src="/static/${esc(logo)}" onerror="this.style.display='none'" alt="">`;
  return `<span class="pv-ico" style="background:${fallbackColor}">${esc(fallbackTxt)}</span>`;
}
function renderPvGrid(selName){
  const grid=document.getElementById('pvGrid'); if(!grid) return;
  const q=PV_FILTER.q.trim().toLowerCase();
  const items=PV_CATALOG.filter(t =>
    (!q || t.name.toLowerCase().includes(q) || (t.site||'').toLowerCase().includes(q)));
  const customMatch=!q || '自定义预设 custom'.includes(q);
  if(!items.length && !customMatch){ grid.innerHTML='<div class="pv-fhint" style="padding:14px">无匹配的预设供应商</div>'; return; }
  grid.innerHTML=items.map(t=>{
    const letter=(t.name||'?').slice(0,1).toUpperCase();
    const ico=pvLogoImg(t.logo, letter, '#e8eaee');
    return `<div class="pv-item ${selName===t.name?'pv-sel':''}" data-name="${esc(t.name)}" onclick="pvPick('${esc(t.name)}')">${ico}<span class="pv-name">${esc(t.name)}</span></div>`;
  }).join('') + (customMatch ? `<div class="pv-item pv-item-custom ${selName==='__custom__'?'pv-sel':''}" data-name="__custom__" onclick="pvPickCustom()"><span class="pv-ico pv-ico-custom">＋</span><span class="pv-name">自定义预设</span></div>` : '');
}
window.pvPickCustom=function(){
  window.PV_ENTRY=null; window.PV_KEYURL='';
  const grid=document.getElementById('pvGrid');
  if(grid) grid.querySelectorAll('.pv-item').forEach(el=>el.classList.toggle('pv-sel',el.dataset.name==='__custom__'));
  const ids=['nf_disp','nf_note','nf_site','nf_key','nf_base','nf_fb','nf_ua_text','nf_proxy_override'];
  ids.forEach(id=>{const el=document.getElementById(id);if(el)el.value='';});
  const proto=document.getElementById('nf_provider'); if(proto) proto.value='anthropic';
  const mbox=document.getElementById('pvModels'); if(mbox) mbox.innerHTML='<div class="pv-fhint">暂无模型，可手动添加或填写端点后获取</div>';
  const kl=document.getElementById('nf_keylink'); if(kl) kl.style.display='none';
  pvProtocolChanged(); pvUpdateJson();
};
window.pvSetQ=function(v){ PV_FILTER.q=v||''; renderPvGrid(null); };

/* 原地切换：填表单+Logo+JSON，不重开弹窗 */
function pvPick(name){
  const t = (window.PROVIDER_CATALOG||[]).find(x=>x.name===name)
        || (window.PROVIDER_CATALOG||[])[0];
  if(!t) return;
  window.PV_SLUG='';
  window.PV_KEYURL=t.key_url||'';
  window.PV_ENTRY=t;
  // 选中态原地切换：不重渲染网格，保持滚动位置
  const grid=document.getElementById('pvGrid');
  if(grid) grid.querySelectorAll('.pv-item').forEach(el=>
    el.classList.toggle('pv-sel', el.dataset.name===t.name));
  const dispEl=document.getElementById('nf_disp'); if(dispEl) dispEl.value=t.name;
  document.getElementById('nf_provider').value=t.provider==='anthropic'?'anthropic':'openai';
  document.getElementById('nf_base').value=t.api_base||'';
  const mbox=document.getElementById('pvModels');
  if(mbox){ mbox.querySelectorAll('.pv-model-row').forEach(r=>r.remove()); }
  document.getElementById('nf_key').value='';
  const siteEl=document.getElementById('nf_site'); if(siteEl) siteEl.value=t.site||'';
  const kl=document.getElementById('nf_keylink');
  if(kl){ if(t.key_url){ kl.href=t.key_url; kl.style.display='inline-block'; } else { kl.style.display='none'; } }
  pvUpdateJson();
}
window.pvPick=pvPick;
function pvProtocolChanged(){
  const proto=(document.getElementById('nf_provider')||{}).value||'anthropic';
  const wrap=document.getElementById('nf_route_wrap');
  const openai=document.getElementById('nf_route_openai');
  const gemini=document.getElementById('nf_route_gemini');
  const ol=document.getElementById('nf_route_openai_label');
  const gl=document.getElementById('nf_route_gemini_label');
  const hint=document.getElementById('nf_proto_hint');
  const needsOpenAI=proto==='openai'||proto==='openai-resp';
  const needsGemini=proto==='gemini';
  if(wrap) wrap.style.display=(needsOpenAI||needsGemini)?'':'none';
  if(ol) ol.style.display=needsOpenAI?'inline-flex':'none';
  if(gl) gl.style.display=needsGemini?'inline-flex':'none';
  if(openai) openai.checked=needsOpenAI;
  if(gemini) gemini.checked=needsGemini;
  if(hint) hint.textContent=proto==='anthropic'?'Anthropic Messages 为 Claude 原生协议，无需路由转换。':
    (proto==='openai'||proto==='openai-resp'||proto==='gemini'||proto==='bedrock')
      ?'⚠ 当前版本流水线执行引擎（Claude Code CLI）只支持 Anthropic 兼容端点。非 Anthropic 协议在本机没有路由转换，保存后跑流水线会直接报错；除非你对接的网关本身提供 Anthropic 兼容地址，否则请保持 Anthropic Messages。'
      :'Anthropic Messages 为 Claude 原生协议，无需路由转换。';
  pvUpdateJson();
}
function pvProtoNote(){ pvProtocolChanged(); }
window.pvPick=pvPick; window.pvProtoNote=pvProtoNote; window.pvProtocolChanged=pvProtocolChanged;
window.pvFetchModels=async function(){
  const base=document.getElementById('nf_base').value.trim();
  const key=document.getElementById('nf_key').value.trim();
  if(!base||!key){ toast('先填 API 端点与 Key 再获取模型列表'); return; }
  toast('正在获取模型列表…');
  try{
    const provider=(document.getElementById('nf_provider')||{}).value||'anthropic';
    const r=await api('/api/models/list',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({api_base:base,api_key:key,provider})});
    if(!r.ok){ toast('获取失败：'+(r.error||'模型端点不可用')); console.warn('model fetch',r); return; }
    const ids=(r.models||[]).map(x=>x.id||x.model||x.name||x).filter(Boolean).slice(0,100);
    if(!ids.length){ toast('模型端点返回成功，但列表为空'); return; }
    const box=document.getElementById('pvModels'); box.innerHTML='';
    ids.forEach(id=>pvAddModel(id));
    toast(r.degraded ? (r.warning||'该套餐不开放模型枚举，已使用固定模型') : ('已载入 '+ids.length+' 个模型'), true);
  }catch(e){ toast('获取失败: '+e); }
};
window.pvAddModel=function(id){
  const box=document.getElementById('pvModels'); if(!box) return;
  if(box.querySelector('.pv-fhint')) box.innerHTML='';
  const row=document.createElement('div');
  row.className='pv-model-row';
  row.innerHTML=`<input class="pv-input mono" placeholder="model-id" value="${esc(id||'')}" style="flex:1"><button class="btn btn-ghost btn-sm" onclick="this.parentElement.remove()">×</button>`;
  box.appendChild(row);
};
window.pvFormatJson=function(){ pvUpdateJson(true); };
function pvUpdateJson(force){
  const j=document.getElementById('pvJson'); if(!j) return;
  const obj={baseUrl:document.getElementById('nf_base').value.trim()||'',
    apiKey:'', api:(document.getElementById('nf_provider').value==='anthropic')?'anthropic-messages':'openai-completions',
    models:[...document.querySelectorAll('#pvModels .pv-model-row input')].map(x=>x.value.trim()).filter(Boolean)};
  j.textContent=JSON.stringify(obj,null,2);
}
document.addEventListener('input',function(e){
  if(e.target && ['nf_base','nf_provider'].includes(e.target.id)) pvUpdateJson();
});
function closePresetModal(){
  const old=document.getElementById('presetModalRoot');
  if(old){
    const box=old.querySelector('.modal-box');
    if(box && !box.classList.contains('mf-pop-out')){
      box.classList.add('mf-pop-out');          // 渐进渐出退场
      setTimeout(()=>old.remove(), 130);
    } else old.remove();
  }
  setTimeout(()=>{
    if(!document.getElementById('presetModalRoot')){
      _mfUnlockScroll();
      if(old && old._pf && old._pf.focus){ try{ old._pf.focus(); }catch(e){} }   // 焦点归还
    }
  }, 140);
}
function setCancel(){ closePresetModal(); }
window.setCancel=setCancel;
window.setNewForm=function(){ openPresetModal(null); };
window.tplApply=function(name){
  if(!name){ openPresetModal(null); return; }
  const t=(window.PROVIDER_CATALOG||[]).find(x=>x.name===name); if(!t) return;
  openPresetModal(t);
};
function nfData(){
  const adv = document.getElementById('pvAdv');
  const gv = id => { const el=document.getElementById(id); return el?el.value.trim():''; };
  let extra = { authfield: gv('nf_authfield'), fallback_model: gv('nf_fb') };
  // 模型映射：行键为小写角色名（与运行时步骤 key 一致）
  const mmap = {};
  if(adv){ adv.querySelectorAll('.pv-map-r').forEach(row=>{
    const roleEl = row.querySelector('.pv-map-role'); if(!roleEl) return;
    const role = roleEl.textContent.trim();
    const realEl = row.querySelector('input.mono'); if(!realEl) return;
    const v = realEl.value.trim();
    if(v) mmap[role] = v;
  }); }
  extra.model_map = mmap;
  // 路由设置（OpenAI / Gemini）
  const roOpenai = document.getElementById('nf_route_openai');
  const roGemini = document.getElementById('nf_route_gemini');
  extra.routing = { openai: roOpenai?roOpenai.checked:true, gemini: roGemini?roGemini.checked:false };
  // 自定义 User-Agent / 本地代理请求覆盖
  const uaText = gv('nf_ua_text');
  if(uaText) extra.user_agent = uaText;
  else extra.user_agent = '';   // 默认：留空即跟随代理默认
  const proxyOv = gv('nf_proxy_override');
  if(proxyOv) extra.local_proxy_override = proxyOv;
  if(!Object.keys(extra.model_map).length && !extra.fallback_model) delete extra.model_map;
  const dispEl=document.getElementById('nf_disp');
  const noteEl=document.getElementById('nf_note');
  const disp=dispEl?dispEl.value.trim():'';
  // 预设名 slug：中文等非 ASCII 名会被整段替换成空串，若直接回退 'my-provider'，
  // 目录里 8 个纯中文供应商（深度求索/阿里云百炼/豆包…）添加第二个时必然报「预设名已存在」。
  // 顺序：ASCII slug → 目录 rawName（如 DeepSeek→deepseek）→ 编辑器在编辑态保持原名 → 显示名。
  let name=disp.toLowerCase().replace(/[^a-z0-9-]+/g,'-').replace(/^-+|-+$/g,'');
  if(!name){
    const _E=window.PV_ENTRY||null;
    const _raw=(_E&&_E.rawName)?String(_E.rawName).toLowerCase().replace(/[^a-z0-9-]+/g,'-').replace(/^-+|-+$/g,''):'';
    const _origP=window.PV_EDIT_ID?PRESETS.find(x=>x.id===window.PV_EDIT_ID):null;
    name=_origP?_origP.name:(_raw||disp||'my-provider');
  }
  extra.logo = (window.PV_ENTRY&&window.PV_ENTRY.logo) || window.PV_SLUG || '';
  const E = window.PV_ENTRY||null;
  if(E){ extra.agents=E.agents||[]; extra.cat=E.cat||''; extra.key_url=E.key_url||extra.key_url||'';
         if(E.site) extra.site=E.site; }
  const siteEl2=document.getElementById('nf_site');
  if(siteEl2 && siteEl2.value.trim()) extra.site = siteEl2.value.trim();
  if(window.PV_KEYURL) extra.key_url = window.PV_KEYURL;
  if(disp) extra.display_name = disp;
  if(noteEl && noteEl.value.trim()) extra.note = noteEl.value.trim();
  // 编辑态：表单未覆盖的既有 extra 字段（用量查询配置 usage_url、厂商元数据 agents/cat、
  // logo 等）原样保留，防止「编辑一次预设就把这些配置清空」。
  const _orig = window.PV_ORIG_EXTRA;
  if(_orig && typeof _orig==='object'){
    ['usage','usage_url','agents','cat'].forEach(k=>{
      if(_orig[k]!==undefined && extra[k]===undefined) extra[k]=_orig[k];
    });
    if(_orig.logo && !extra.logo) extra.logo=_orig.logo;
  }
  return {provider:gv('nf_provider'), name:name,
    api_base:gv('nf_base'), api_key:gv('nf_key'),
    model:(document.querySelector('#pvModels .pv-model-row input')||{}).value?.trim?.()||'',
    extra:extra};
}
window.testNew=async function(){
  const d=nfData(); if(!d.name){ toast('请填写预设名称'); return; }
  toast('正在测试…');
  const r=await api('/api/providers/test',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});
  toast((r.ok?'连接成功：':'连接失败：')+r.msg, r.ok);
};
window.saveNew=async function(){
  const d=nfData(); if(!d.name){ toast('请填写预设名称'); return; }
  const editId=window.PV_EDIT_ID;
  const method=editId?'PUT':'POST';
  const url=editId?'/api/providers/'+editId:'/api/providers';
  const r=await api(url,{method,headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});
  if(r.detail){ toast(r.detail); return; }
  PRESETS=r.presets; DEFAULT_P=r.default; renderPresets();
  closePresetModal(); updateTnModel(); toast(editId?'预设已更新':'预设已添加',true);
};


/* 厂商识别（CC Switch 式图标）：按 base/model 关键词映射品牌色与首字 */
function brandFor(p){
  const b=(p.api_base||'').toLowerCase(), m=(p.model||'').toLowerCase(), n=(p.name||'');
  if(b.includes('bigmodel')||m.includes('glm')) return {t:'Z', c:'#3b5bfd'};
  if(b.includes('deepseek')||m.includes('deepseek')) return {t:'D', c:'#4d6bfe'};
  if(p.provider==='anthropic'||m.includes('claude')) return {t:'A', c:'#d97757'};
  if(b.includes('openai.com')||/^gpt|^o[13]/.test(m)) return {t:'G', c:'#10a37f'};
  if(b.includes('moonshot')||m.includes('kimi')) return {t:'K', c:'#16191e'};
  if(b.includes('dashscope')||m.includes('qwen')) return {t:'T', c:'#615ced'};
  if(b.includes('volces')||m.includes('doubao')) return {t:'B', c:'#0d5ef4'};
  if(b.includes('minimax')) return {t:'M', c:'#f23f5d'};
  if(b.includes('siliconflow')) return {t:'S', c:'#7c5cff'};
  if(b.includes('groq')) return {t:'Q', c:'#f55036'};
  if(b.includes('gemini')||m.includes('gemini')) return {t:'Ge', c:'#4285f4'};
  if(b.includes('longcat')) return {t:'L', c:'#00b899'};
  if(b.includes('xiaomimimo')||m.includes('mimo')) return {t:'Mi', c:'#ff6900'};
  if(b.includes('opencode')) return {t:'OC', c:'#1b1c20'};
  return {t:(n||'?').slice(0,1).toUpperCase(), c:'#8a8f98'};
}

function renderPresets(){
  const list=document.getElementById('presetList'); if(!list) return;
  if(!PRESETS.length){ list.innerHTML='<div class="pf-empty">暂无预设。点击右上角「新增预设」创建第一个供应商连接</div>'; return; }
  // 稳定顺序：按创建先后（id 升序）排列，切换默认/编辑后不重排、不跳动
  const items=[...PRESETS].sort((a,b)=>(a.id||0)-(b.id||0));
  list.innerHTML=items.map(p=>{
    const isAnthropic=(p.provider||'openai')==='anthropic';
    const isCur=!!p.is_default;
    const uc=USAGE_CACHE[p.id]||null;   // 内存缓存（fetchUsage 写入；默认预设自动刷新）
    const site=(p.extra&&p.extra.site)||'';
    // 供应商名下方直接给蓝色官网链接，不再有「模型 id」小字
    const urlTxt=site||(p.api_base||'');
    const urlRow = urlTxt
      ? `<a class="pf-url" href="${esc(urlTxt)}" target="_blank" rel="noreferrer" title="打开官网">${esc(urlTxt)}</a>`
      : '';
    const dispName=esc((p.extra&&p.extra.display_name)||p.name);
    return `<div class="pf-preset ${isCur?'pf-preset-default':''}">
      <div class="pf-preset-left">
        ${(p.extra&&p.extra.logo)?`<img class="pv-ico-img" src="/static/logos/${p.extra.logo}.png" onerror="this.outerHTML='<span class='pf-brand' style='background:${brandFor(p).c}'>${brandFor(p).t}</span>'" alt="">`:`<span class="pf-brand" style="background:${brandFor(p).c}">${brandFor(p).t}</span>`}
        <div class="pf-preset-main">
          <div class="pf-preset-title">
            <span class="pf-name">${dispName}</span>
          </div>
          <div class="pf-preset-meta">${urlRow}</div>
          ${uc ? usageFooterHtml(p.id, uc) : ''}
        </div>
      </div>
      <div class="pf-preset-ops">
        ${isCur
          ? `<button class="pf-inuse" disabled title="当前流水线正在使用此预设"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" width="12" height="12"><path d="M12 22c5.5 0 10-4.5 10-10S17.5 2 12 2 2 6.5 2 12s4.5 10 10 10Z" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="m7.75 12 2.83 2.83 5.67-5.66" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>使用中</button>`
          : `<button class="pf-op pf-op-start" title="启动（设为流水线默认模型）" aria-label="设为默认" onclick="setDefault(${p.id})"><svg viewBox="0 0 24 24" fill="currentColor" width="12" height="12"><path d="M4 12V8.44c0-4.42 3.13-6.23 6.96-4.02l3.09 1.78 3.09 1.78c3.83 2.21 3.83 5.83 0 8.04l-3.09 1.78-3.09 1.78C7.13 21.79 4 19.98 4 15.56V12Z" stroke-width="1.5" stroke-miterlimit="10" stroke-linecap="round" stroke-linejoin="round"/></svg>启动</button>`}
        <button class="pf-op" title="编辑" aria-label="编辑" onclick="editPreset(${p.id})"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" width="14" height="14"><path d="m13.26 3.6-8.21 8.69c-.31.33-.61.98-.67 1.43l-.37 3.24c-.13 1.17.71 1.97 1.87 1.77l3.22-.55c.45-.08 1.08-.41 1.39-.75l8.21-8.69c1.42-1.5 2.06-3.21-.15-5.3-2.2-2.07-3.87-1.34-5.29.16Z" stroke-width="1.5" stroke-miterlimit="10" stroke-linecap="round" stroke-linejoin="round"/><path d="M11.89 5.05a6.126 6.126 0 0 0 5.45 5.15M3 22h18" stroke-width="1.5" stroke-miterlimit="10" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
        <button class="pf-op" title="复制配置" aria-label="复制配置" onclick="dupPreset(${p.id})"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" width="14" height="14"><path d="M17 13.4v3c0 4-1.6 5.6-5.6 5.6H7.6c-4 0-5.6-1.6-5.6-5.6v-3.8C2 8.6 3.6 7 7.6 7h3" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M17 13.4h-3.2c-2.4 0-3.2-.8-3.2-3.2V7l6.4 6.4ZM11.6 2h4M7 5c0-1.66 1.34-3 3-3h2.62M22 8v6.19c0 1.55-1.26 2.81-2.81 2.81M22 8h-3c-2.25 0-3-.75-3-3V2l6 6Z" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
        <button class="pf-op" title="检测连通" aria-label="检测连通" onclick="testPreset(${p.id})"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" width="14" height="14"><path d="M22 12h-4l-3 8-6-16-3 8H2"/></svg></button>
        <button class="pf-op" title="配置使用量查询" aria-label="配置使用量查询" onclick="usageModal(${p.id})"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" width="14" height="14"><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></svg></button>
        <button class="pf-op pf-op-danger" title="${isCur?'使用中的预设不可删除（先启动其他预设）':'删除'}" aria-label="${isCur?'删除（当前使用中，不可用）':'删除'}" ${isCur?'disabled style="opacity:.35;cursor:not-allowed"':''} onclick="${isCur?'':`setDel(${p.id})`}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" width="14" height="14"><path d="M4 7h16M9 7V5h6v2m-8 0l1 13h8l1-13"/></svg></button>
      </div>
    </div>`;
  }).join('');
  scheduleUsageAuto();
}

/* 编辑预设：弹出编辑弹窗（不再内联展开，交互丝滑、位置固定） */
let EDIT_PID=null;
window.editPreset=function(id){
  const p=PRESETS.find(x=>x.id===id); if(!p) return;
  // 编辑和新增复用同一份完整供应商表单；编辑态隐藏顶部预设选择器，避免误切模板。
  openPresetModal(p,id);
};
window.editPresetClose=function(){ closePresetModal(); };

/* ---------------- 卡片内嵌用量页脚 ---------------- */
const USAGE_CACHE = {};            // id -> {ts, ok, data:{plan,remaining,unit,extra}|{error}}
const USAGE_URLS = {               // 内置用量查询地址（已知供应商优先）
  deepseek: 'https://api.deepseek.com/user/balance',
  moonshot: 'https://api.moonshot.cn/v1/users/me/balance',
};
const USAGE_PARSERS = {            // 解析各家返回体 → {plan, remaining, unit, extra}
  deepseek(body){
    const j = JSON.parse(body);
    const d = j.balance_information || j.data || {};
    return { plan:'DeepSeek 余额', remaining:parseFloat(d.total_balance||d.balance||'0'),
             unit:d.currency||'CNY', extra:'赠 '+ (d.granted_balance||'0') };
  },
  moonshot(body){
    const j = JSON.parse(body);
    const d = j.data || j;
    return { plan:'Kimi 余额', remaining:parseFloat(d.available_balance||d.balance||'0'),
             unit:'CNY', extra:'赠 '+ (d.voucher_balance||'0') };
  },
};
function _relTime(ts){
  const diff = Math.floor((Date.now()-ts)/1000);
  if(diff < 60) return '刚刚';
  if(diff < 3600) return Math.floor(diff/60)+' 分钟前';
  if(diff < 86400) return Math.floor(diff/3600)+' 小时前';
  return Math.floor(diff/86400)+' 天前';
}
function usageFooterHtml(id, uc){
  const head = `<span class="pf-usage-time">⟳ ${_relTime(uc.ts)}</span>
    <button class="pf-usage-rf" title="重新查询" onclick="fetchUsage(${id})">⟳</button>`;
  const body = uc.ok
    ? `<span class="pf-usage-k">余额</span><b class="pf-usage-v">${esc(String(uc.data.remaining))}</b>
       <span class="pf-usage-k">${esc(uc.data.unit||'')}</span>
       ${uc.data.extra?`<span class="pf-usage-k">${esc(uc.data.extra)}</span>`:''}`
    : `<span class="pf-usage-k" style="color:var(--bad,#d9534f)">查询失败：${esc(uc.data.error||'未知错误')}</span>`;
  return `<div class="pf-usage" data-uid="${id}">${head}${body}</div>`;
}
const USAGE_FETCHING = {};
window.fetchUsage = async function(id, silent){
  const p = PRESETS.find(x=>x.id===id); if(!p) return;
  if(!p.api_key){ if(!silent) toast('该预设未配置 API Key'); return; }
  const usage = (p.extra&&p.extra.usage)||'';
  const url = USAGE_URLS[usage];
  if(!url){ if(!silent) toast('该供应商暂无内置用量接口'); return; }
  if(USAGE_FETCHING[id]) return;
  USAGE_FETCHING[id] = true;
  try{
    const r = await api('/api/usage/query',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({url, api_key:p.api_key})});
    let entry = {ts:Date.now(), ok:false, data:{error:(r.error||('HTTP '+r.status))}};
    if(r.ok){
      try{ entry = {ts:Date.now(), ok:true, data:USAGE_PARSERS[usage](r.body)}; }
      catch(e){ entry = {ts:Date.now(), ok:false, data:{error:'返回解析失败'}}; }
    }
    USAGE_CACHE[id] = entry;
    renderPresets();
  }catch(e){
    USAGE_CACHE[id] = {ts:Date.now(), ok:false, data:{error:String(e).slice(0,80)}};
    renderPresets();
  }finally{
    delete USAGE_FETCHING[id];
  }
};
let USAGE_AUTO_TIMER = null;
function scheduleUsageAuto(){
  // 自动查询仅对当前默认预设（60s 内不重复）
  clearTimeout(USAGE_AUTO_TIMER);
  USAGE_AUTO_TIMER = setTimeout(()=>{
    const d = PRESETS.find(x=>x.is_default);
    if(!d || !d.api_key) return;
    const usage = (d.extra&&d.extra.usage)||'';
    if(!USAGE_URLS[usage]) return;
    const c = USAGE_CACHE[d.id];
    if(c && Date.now()-c.ts < 60000) return;
    fetchUsage(d.id, true);
  }, 400);
}
window.setEditToggle=function(id){ EDIT_IDS.has(id)?EDIT_IDS.delete(id):EDIT_IDS.add(id); renderPresets(); };
window.setField=async function(id,key,val){
  const body={}; body[key]=val;
  const r=await api('/api/providers/'+id,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  PRESETS=r.presets; DEFAULT_P=r.default; renderPresets(); toast('已更新',true);
};
window.testPreset=async function(id){
  const p=PRESETS.find(x=>x.id===id); if(!p) return;
  toast('正在测试…');
  const r=await api('/api/providers/test',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({provider:p.provider,api_base:p.api_base,api_key:p.api_key,model:p.model})});
  toast((r.ok?'连接成功：':'连接失败：')+r.msg, r.ok);
};
window.setDefault=async function(id){
  try{
    const r=await api('/api/providers/'+id+'/default',{method:'POST'});
    if(r && !r.detail){ PRESETS=r.presets; DEFAULT_P=r.default; renderPresets(); updateTnModel(); toast('启用成功',true); }
    else toast('没有成功');
  }catch(e){ toast('没有成功'); }
};
window.dupPreset=async function(id){
  const p=PRESETS.find(x=>x.id===id); if(!p) return;
  let base=(p.extra&&p.extra.display_name)||p.name;
  let name=base+' - 副本', n=2;
  while(PRESETS.some(x=>x.name===name)) name=base+' - 副本'+(n++);
  const body={name, provider:p.provider||'openai', api_base:p.api_base||'',
    api_key:p.api_key||'', model:p.model||'', extra:{...(p.extra||{})}};
  if(body.extra.display_name) body.extra.display_name=base+' - 副本';
  const r=await api('/api/providers',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  if(r.detail){ toast(r.detail); return; }
  PRESETS=r.presets; DEFAULT_P=r.default; renderPresets(); toast('已复制配置',true);
};

const USAGE_DEFAULTS={deepseek:'https://api.deepseek.com/user/balance',
  moonshot:'https://api.moonshot.cn/v1/users/me/balance'};
let USAGE_PID=null;
window.usageModal=function(id){
  const p=PRESETS.find(x=>x.id===id); if(!p) return;
  USAGE_PID=id;
  const old=document.getElementById('usageModalRoot'); if(old) old.remove();
  const brand=(p.api_base||'').toLowerCase();
  const detected = Object.keys(USAGE_URLS).find(k=>brand.includes(k)) || '';
  let suggest=(p.extra&&p.extra.usage_url)||'';
  if(!suggest && detected) suggest=USAGE_URLS[detected];
  const disp=esc((p.extra&&p.extra.display_name)||p.name);
  const root=document.createElement('div');
  root.id='usageModalRoot';
  root.innerHTML=`<div class="modal open"><div class="modal-box mf-pop" style="width:600px">
    <div class="modal-top"><div><h3>使用量查询</h3>
      <p class="muted" style="font-size:12px;margin-top:2px">${disp}${detected?`<span class="um-tag">${esc(detected)}</span>`:''}</p></div>
      <button class="modal-x" aria-label="关闭" onclick="document.getElementById('usageModalRoot').remove()">×</button></div>
    <div style="padding:14px 18px">
      <label class="f">查询地址 <small>(GET · Bearer 本预设 Key)</small></label>
      <input class="pf-input mono" id="umUrl" value="${esc(suggest)}" placeholder="https://…/user/balance">
      <div class="hint" style="margin-top:6px">${detected?`已识别供应商 <b>${esc(detected)}</b>，已填入默认查询地址。`:'未识别内置供应商，请手动填写查询地址。'}</div>
      <div class="nrow" style="margin-top:12px;gap:8px">
        <button class="btn btn-primary btn-sm" onclick="usageQuery()">立即查询</button>
        <button class="btn btn-ghost btn-sm" onclick="usageSave()">保存配置到预设</button>
      </div>
      <div id="umRes" style="margin-top:14px"></div>
    </div></div></div>`;
  document.body.appendChild(root);
};
window.usageSave=async function(){
  const url=document.getElementById('umUrl').value.trim();
  const p=PRESETS.find(x=>x.id===USAGE_PID); if(!p) return;
  const extra={...(p.extra||{}), usage_url:url};
  const r=await api('/api/providers/'+USAGE_PID,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({extra})});
  PRESETS=r.presets; DEFAULT_P=r.default; renderPresets();
  toast(url?'查询配置已保存':'已清除查询配置',true);
};
window.usageQuery=async function(){
  const url=document.getElementById('umUrl').value.trim();
  const box=document.getElementById('umRes');
  const p=PRESETS.find(x=>x.id===USAGE_PID); if(!p) return;
  if(!url){ box.innerHTML='<div class="warn-text">请先填写查询地址</div>'; return; }
  box.innerHTML='<div class="loading-bar"></div>';
  const r=await api('/api/usage/query',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({url,api_key:p.api_key||''})}).catch(e=>({ok:false,error:String(e)}));
  if(!r.ok && r.error){ box.innerHTML=`<div class="warn-text">${esc(r.error)}</div>`; return; }
  const usage=(p.extra&&p.extra.usage)||'';
  let parsed=null;
  if(usage && USAGE_PARSERS[usage]){
    try{ parsed=USAGE_PARSERS[usage](r.body); }catch(e){ parsed=null; }
  }
  let pretty=r.body||'';
  try{ pretty=JSON.stringify(JSON.parse(r.body),null,2); }catch(e){}
  let head='';
  if(parsed && parsed.remaining!==undefined && !Number.isNaN(parsed.remaining)){
    head=`<div class="um-bal"><div class="um-bal-label">${esc(parsed.plan||'余额')}</div>
      <div class="um-bal-num">${esc(String(parsed.remaining))}<span class="um-bal-unit">${esc(parsed.unit||'')}</span></div>
      ${parsed.extra?`<div class="um-bal-extra">${esc(parsed.extra)}</div>`:''}</div>`;
  } else {
    head=`<div class="um-status ${r.ok?'um-ok':'um-bad'}">HTTP ${r.status}${r.ok?' · 请求成功':' · 请求失败'}</div>`;
  }
  box.innerHTML=`${head}<details class="um-raw"><summary>原始返回</summary><pre class="code-box" style="max-height:220px;overflow:auto;font-size:11px">${esc(pretty)}</pre></details>`;
};

window.setDel=async function(id){
  if(!(await appConfirm('删除该预设？', {danger:true, okText:'删除'}))) return;
  const r=await api('/api/providers/'+id,{method:'DELETE'});
  PRESETS=r.presets; DEFAULT_P=r.default; renderPresets(); updateTnModel();
};

window.saveOtherCfg=async function(){
  // 图片生成已改为预设列表，此函数不再使用（保留空实现避免旧引用报错）
};

/* ---------------- 图片生成预设（image_presets） ---------------- */
let IMG_PRESETS=[], IMG_DEFAULT=null;
async function loadImgPresets(){
  try{ const r=await api('/api/image-presets'); IMG_PRESETS=r.presets||[]; IMG_DEFAULT=r.default||null; }catch(e){ IMG_PRESETS=[]; IMG_DEFAULT=null; }
}
function imgBrandFor(p){
  const b=(p.api_base||'').toLowerCase(), m=(p.model||'').toLowerCase();
  if(b.includes('openai')||m.includes('gpt-image')||m.includes('dall')) return {t:'G', c:'#10a37f'};
  if(b.includes('deepseek')) return {t:'D', c:'#4d6bfe'};
  if(b.includes('bigmodel')||m.includes('glm')||m.includes('cogview')) return {t:'Z', c:'#3b5bfd'};
  if(b.includes('dashscope')||m.includes('qwen')||m.includes('wanx')) return {t:'T', c:'#615ced'};
  if(b.includes('moonshot')||m.includes('kimi')) return {t:'K', c:'#16191e'};
  if(b.includes('volces')||m.includes('doubao')) return {t:'B', c:'#0d5ef4'};
  if(b.includes('siliconflow')) return {t:'S', c:'#7c5cff'};
  return {t:(p.name||'?').slice(0,1).toUpperCase(), c:'#8a8f98'};
}
function renderImgPresets(){
  const list=document.getElementById('imgPresetList'); if(!list) return;
  if(!IMG_PRESETS.length){ list.innerHTML='<div class="muted" style="font-size:13px;padding:8px 0">暂无图像预设。点击右上角「＋ 新增预设」创建。</div>'; return; }
  const items=[...IMG_PRESETS].sort((a,b)=>(a.id||0)-(b.id||0));
  list.innerHTML=items.map(p=>{
    const lg=imgBrandFor(p);
    const extra=p.extra||{};
    const dispName=esc(extra.display_name||p.name);
    const site=(extra.site||'').trim();
    const base=(p.api_base||'').trim();
    // 优先官网链接，其次端点；两者都不是则显示模型名
    const urlRow = site
      ? `<a class="pf-url" href="${esc(site)}" target="_blank" rel="noreferrer" title="打开官网">${esc(site)}</a>`
      : (/^https?:\/\//i.test(base)
          ? `<a class="pf-url" href="${esc(base)}" target="_blank" rel="noreferrer" title="打开端点">${esc(base)}</a>`
          : `<span class="pf-model-hint">${esc(p.model||'未指定模型')}</span>`);
    return `<div class="pf-preset ${p.is_default?'pf-preset-default':''}">
      <div class="pf-preset-left">
        <span class="pf-brand" style="background:${lg.c}">${lg.t}</span>
        <div class="pf-preset-main">
          <div class="pf-preset-title">
            <span class="pf-name">${dispName}</span>
          </div>
          <div class="pf-preset-meta">${urlRow}</div>
        </div>
      </div>
      <div class="pf-preset-ops">
        ${p.is_default
          ? `<button class="pf-inuse" disabled title="当前图片生成正使用此预设"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" width="12" height="12"><path d="M20 6L9 17l-5-5"/></svg>使用中</button>`
          : `<button class="pf-op pf-op-start" title="设为默认" aria-label="设为默认" onclick="imgSetDefault(${p.id})"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" width="12" height="12"><path d="M4 12V8.44c0-4.42 3.13-6.23 6.96-4.02l3.09 1.78 3.09 1.78c3.83 2.21 3.83 5.83 0 8.04l-3.09 1.78-3.09 1.78C7.13 21.79 4 19.98 4 15.56V12Z" stroke-width="1.5" stroke-miterlimit="10" stroke-linecap="round" stroke-linejoin="round"/></svg>启动</button>`}
        <button class="pf-op" title="编辑" aria-label="编辑" onclick="imgEditOpen(${p.id})"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" width="14" height="14"><path d="M17 3l4 4L8 20l-5 1 1-5z"/></svg></button>
        <button class="pf-op pf-op-danger" title="删除" aria-label="删除" onclick="imgDel(${p.id})"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" width="14" height="14"><path d="M4 7h16M9 7V5h6v2m-8 0l1 13h8l1-13"/></svg></button>
      </div>
    </div>`;
  }).join('');
}
/* 编辑图像预设：弹窗（与模型预设同构：pv-form + 高级选项折叠 + 吸底栏） */
let IMG_EDIT_ID=null;
window.imgEditOpen=function(id){
  const p=IMG_PRESETS.find(x=>x.id===id); if(!p) return;
  IMG_EDIT_ID=id;
  const old=document.getElementById('imgEditRoot'); if(old) old.remove();
  _mfLockScroll();
  const extra=p.extra||{};
  const root=document.createElement('div');
  root.id='imgEditRoot';
  root._pf = document.activeElement;   // 记录打开前焦点，供关闭后归还
  root.innerHTML=`<div class="modal open">
    <div class="modal-box pv-modal mf-pop">
      <div class="modal-top">
        <div class="pv-head"><h3>编辑图像生成预设</h3></div>
        <button class="modal-x" aria-label="关闭" onclick="imgEditClose()">×</button>
      </div>
      <div class="pv-scroll" style="padding:10px 18px 16px">
        <div class="pv-form">
          <div class="pv-row2">
            <div class="pv-f"><label for="ieName" class="pv-label">预设名称 *</label>
              <input class="pv-input" id="ieName" value="${esc(p.name)}" placeholder="如：GPT-Image / 通义万相"></div>
            <div class="pv-f"><label for="ieNote" class="pv-label">备注</label>
              <input class="pv-input" id="ieNote" value="${esc(extra.note||'')}" placeholder="例如：公司账号"></div>
          </div>
          <div class="pv-f"><label for="ieSite" class="pv-label">官网链接</label>
            <input class="pv-input" id="ieSite" value="${esc(extra.site||'')}" placeholder="https://example.com"></div>
          <div class="pv-f"><label for="ieKey" class="pv-label">API Key <small style="color:#71717a;font-weight:400">(留空=不修改)</small></label>
            <input class="pv-input" id="ieKey" type="password" placeholder="sk-..." autocomplete="off"></div>
          <div class="pv-f"><label for="ieBase" class="pv-label">请求地址</label>
            <input class="pv-input mono" id="ieBase" value="${esc(p.api_base||'')}" placeholder="https://…/v1（留空=内置默认服务）">
            <div class="pv-fhint">兼容 OpenAI 图像接口的服务端点，不要以斜杠结尾。</div></div>
          <div class="pv-f"><label for="ieModel" class="pv-label">图像模型</label>
            <input class="pv-input mono" id="ieModel" value="${esc(p.model||'')}" placeholder="gpt-image-2 / wanx2.1-t2i-turbo"></div>
          <div class="pv-f">
            <div class="pv-adv" id="ieAdv">
              <div class="pv-adv-title" onclick="this.parentElement.classList.toggle('open')"><span class="pv-adv-caret">›</span> 高级选项</div>
              <div class="pv-adv-body-wrap">
                <div class="pv-row2">
                  <div class="pv-f"><label for="ieSize" class="pv-label">图片尺寸</label>
                    <select class="pv-input pv-select" id="ieSize">
                      ${['自动','1024x1024','1792x1024','1024x1792','2048x2048'].map(s=>`<option ${(extra.size||'自动')===s?'selected':''}>${s}</option>`).join('')}
                    </select></div>
                  <div class="pv-f"><label for="ieRatio" class="pv-label">图片比例</label>
                    <select class="pv-input pv-select" id="ieRatio">
                      ${['自动','1:1','16:9','9:16','3:4','4:3'].map(s=>`<option ${(extra.ratio||'自动')===s?'selected':''}>${s}</option>`).join('')}
                    </select></div>
                </div>
                <div class="pv-f"><label for="ieQuality" class="pv-label">生成质量</label>
                  <select class="pv-input pv-select" id="ieQuality">
                    ${['自动','standard','hd','high'].map(s=>`<option ${(extra.quality||'自动')===s?'selected':''}>${s}</option>`).join('')}
                  </select></div>
              </div>
            </div></div>
        </div>
      </div>
      <div class="pv-foot">
        <div style="flex:1"></div>
        <button class="btn btn-ghost btn-sm" onclick="imgEditClose()">取消</button>
        <button class="btn btn-accent btn-sm" onclick="imgEditSave()">保存</button>
      </div>
    </div></div>`;
  document.body.appendChild(root);
};
window.imgEditClose=function(){
  const old=document.getElementById('imgEditRoot'); if(old) old.remove();
  if(old && old._pf && old._pf.focus){ try{ old._pf.focus(); }catch(e){} }   // 焦点归还
  _mfUnlockScroll();
};
window.imgEditSave=async function(){
  const name=document.getElementById('ieName').value.trim();
  const base=document.getElementById('ieBase').value.trim();
  const key=document.getElementById('ieKey').value.trim();
  const model=document.getElementById('ieModel').value.trim();
  if(!name){ toast('请填写预设名称'); return; }
  const extra={
    note:document.getElementById('ieNote').value.trim(),
    site:document.getElementById('ieSite').value.trim(),
    size:document.getElementById('ieSize').value,
    ratio:document.getElementById('ieRatio').value,
    quality:document.getElementById('ieQuality').value,
  };
  const body={name, extra};
  body.api_base=base;
  body.model=model;
  if(key) body.api_key=key;
  const r=await api('/api/image-presets/'+IMG_EDIT_ID,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  if(r.detail){ toast(r.detail); return; }
  IMG_PRESETS=r.presets; IMG_DEFAULT=r.default; renderImgPresets(); imgEditClose(); toast('已保存',true);
};
window.imgSetDefault=async function(id){
  try{
    const r=await api('/api/image-presets/'+id+'/default',{method:'POST'});
    if(r && !r.detail){ IMG_PRESETS=r.presets; IMG_DEFAULT=r.default; renderImgPresets(); toast('启用成功',true); }
    else toast('没有成功');
  }catch(e){ toast('没有成功'); }
};
window.imgDel=async function(id){
  if(!(await appConfirm('删除该图像预设？',{danger:true,okText:'删除'}))) return;
  const r=await api('/api/image-presets/'+id,{method:'DELETE'});
  IMG_PRESETS=r.presets; IMG_DEFAULT=r.default; renderImgPresets();
};
/* 新增图像预设弹窗（与模型预设同构：无供应商目录，其余一致） */
window.imgOpenModal=function(){
  const old=document.getElementById('imgModalRoot'); if(old) old.remove();
  _mfLockScroll();
  const root=document.createElement('div');
  root.id='imgModalRoot';
  root._pf = document.activeElement;   // 记录打开前焦点，供关闭后归还
  root.innerHTML=`<div class="modal open">
    <div class="modal-box pv-modal mf-pop">
      <div class="modal-top">
        <div class="pv-head"><h3>添加图像生成预设</h3></div>
        <button class="modal-x" aria-label="关闭" onclick="imgCloseModal()">×</button>
      </div>
      <div class="pv-scroll" style="padding:10px 18px 16px">
        <div class="pv-form">
          <div class="pv-row2">
            <div class="pv-f"><label for="imgNfName" class="pv-label">预设名称 *</label>
              <input class="pv-input" id="imgNfName" placeholder="如：GPT-Image / 通义万相"></div>
            <div class="pv-f"><label for="imgNfNote" class="pv-label">备注</label>
              <input class="pv-input" id="imgNfNote" placeholder="例如：公司账号"></div>
          </div>
          <div class="pv-f"><label for="imgNfSite" class="pv-label">官网链接</label>
            <input class="pv-input" id="imgNfSite" placeholder="https://example.com"></div>
          <div class="pv-f"><label for="imgNfKey" class="pv-label">API Key *</label>
            <input class="pv-input" id="imgNfKey" type="password" placeholder="sk-..." autocomplete="off"></div>
          <div class="pv-f"><label for="imgNfBase" class="pv-label">请求地址</label>
            <input class="pv-input mono" id="imgNfBase" placeholder="https://…/v1（留空=内置默认服务）">
            <div class="pv-fhint">兼容 OpenAI 图像接口的服务端点，不要以斜杠结尾。</div></div>
          <div class="pv-f"><label for="imgNfModel" class="pv-label">图像模型</label>
            <input class="pv-input mono" id="imgNfModel" placeholder="gpt-image-2 / wanx2.1-t2i-turbo"></div>
          <div class="pv-f">
            <div class="pv-adv" id="imgNfAdv">
              <div class="pv-adv-title" onclick="this.parentElement.classList.toggle('open')"><span class="pv-adv-caret">›</span> 高级选项</div>
              <div class="pv-adv-body-wrap">
                <div class="pv-row2">
                  <div class="pv-f"><label for="imgNfSize" class="pv-label">图片尺寸</label>
                    <select class="pv-input pv-select" id="imgNfSize">
                      <option selected>自动</option><option>1024x1024</option><option>1792x1024</option><option>1024x1792</option><option>2048x2048</option>
                    </select></div>
                  <div class="pv-f"><label for="imgNfRatio" class="pv-label">图片比例</label>
                    <select class="pv-input pv-select" id="imgNfRatio">
                      <option selected>自动</option><option>1:1</option><option>16:9</option><option>9:16</option><option>3:4</option><option>4:3</option>
                    </select></div>
                </div>
                <div class="pv-f"><label for="imgNfQuality" class="pv-label">生成质量</label>
                  <select class="pv-input pv-select" id="imgNfQuality">
                    <option selected>自动</option><option>standard</option><option>hd</option><option>high</option>
                  </select></div>
              </div>
            </div>
            <div class="pv-f"><label class="pv-label">配置 JSON</label>
              <div class="pv-json-wrap"><pre class="pv-json" id="imgNfJson"></pre></div>
              <button class="btn btn-ghost btn-sm" onclick="imgNfUpdateJson(true)">格式化</button></div>
            </div>
        </div>
      </div>
      <div class="pv-foot">
        <div style="flex:1"></div>
        <button class="btn btn-ghost btn-sm" onclick="imgCloseModal()">取消</button>
        <button class="btn btn-accent btn-sm" onclick="imgSaveNew()">＋ 添加</button>
      </div>
    </div></div>`;
  document.body.appendChild(root);
  imgNfUpdateJson();
};
window.imgCloseModal=function(){
  const old=document.getElementById('imgModalRoot');
  if(old) old.remove();
  if(old && old._pf && old._pf.focus){ try{ old._pf.focus(); }catch(e){} }
  _mfUnlockScroll();
};
/* 图片预设配置 JSON 实时预览（与模型预设弹窗一致） */
function imgNfUpdateJson(force){
  const j=document.getElementById('imgNfJson'); if(!j) return;
  const gv=id=>{ const el=document.getElementById(id); return el?el.value.trim():''; };
  const obj={
    name:gv('imgNfName')||'', api_base:gv('imgNfBase')||'', api_key:'',
    model:gv('imgNfModel')||'',
    extra:{note:gv('imgNfNote')||'', site:gv('imgNfSite')||'',
      size:$('#imgNfSize').value||'自动', ratio:$('#imgNfRatio').value||'自动',
      quality:$('#imgNfQuality').value||'自动'}};
  j.textContent=JSON.stringify(obj,null,2);
}
document.addEventListener('input',function(e){
  if(e.target && ['imgNfName','imgNfBase','imgNfModel','imgNfNote','imgNfSite','imgNfSize','imgNfRatio','imgNfQuality'].includes(e.target.id)) imgNfUpdateJson();
});
window.imgSaveNew=async function(){
  const name=$('#imgNfName').value.trim();
  const api_base=$('#imgNfBase').value.trim();
  const api_key=$('#imgNfKey').value.trim();
  const model=$('#imgNfModel').value.trim();
  if(!name){ toast('请填写预设名称'); return; }
  if(!api_key){ toast('请填写 API Key'); return; }
  const extra={
    note:$('#imgNfNote').value.trim(),
    site:$('#imgNfSite').value.trim(),
    size:$('#imgNfSize').value,
    ratio:$('#imgNfRatio').value,
    quality:$('#imgNfQuality').value,
  };
  const r=await api('/api/image-presets',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({name,api_base,api_key,model,extra})});
  if(r.detail){ toast(r.detail); return; }
  IMG_PRESETS=r.presets; IMG_DEFAULT=r.default; renderImgPresets();
  imgCloseModal(); toast('已添加',true);
};

/* ---------------- 软件更新 ---------------- */
let UPD_TIMER=null;
async function loadUpdateInfo(){
  try{
    const r=await api('/api/update/info');
    $('#updVer').textContent=r.version||'?';
    if($('#updUrl') && !$('#updUrl').value) $('#updUrl').value=r.update_url||'';
    updDraw(r.status);
    // 启动自动检查可能已在后台下载：进入设置页时接上进度轮询，下载就绪直接亮出安装按钮
    const ph=r.status&&r.status.phase;
    if(ph==='downloading'){
      clearInterval(UPD_TIMER);
      UPD_TIMER=setInterval(async ()=>{
        const st=await api('/api/update/status').catch(()=>null);
        if(!st){ return; }
        updDraw(st);
        if(st.phase==='ready'||st.phase==='error'){ clearInterval(UPD_TIMER); UPD_TIMER=null; }
      }, 800);
    }
  }catch(e){}
}
function updDraw(st){
  if(!st) return;
  $('#updMsg').textContent=st.message||'';
  $('#updVer').textContent=st.current||$('#updVer').textContent;
  const downloading=st.phase==='downloading';
  $('#updBar').style.display=downloading?'flex':'none';
  if(downloading){
    $('#updFill').style.width=(st.progress||0)+'%';
    $('#updPct').textContent=(st.downloaded/1048576).toFixed(1)+' / '+((st.total||0)/1048576).toFixed(1)+' MB';
  }
  // 启动后台自动下载就绪后：不用等用户手点「检查更新」，直接亮出安装按钮
  $('#updApplyBtn').style.display=(st.phase==='ready'||st.phase==='applying')?'':'none';
}
window.updSaveUrl=async function(){
  await post('/api/update/url',{url:$('#updUrl').value.trim()});
  toast('更新自已保存',true);
};
window.updCheck=async function(){
  $('#updMsg').textContent='检查中…';
  clearInterval(UPD_TIMER);
  const st=await post('/api/update/check');
  updDraw(st);
  if(st.phase==='available'){
    toast('发现新版本 '+st.latest,true);
    updDownload();
  }else if(st.phase==='none'){
    toast('已是最新版本 '+st.current,true);
  }
};
function updDownload(){
  post('/api/update/download');
  UPD_TIMER=setInterval(async ()=>{
    const st=await api('/api/update/status');
    updDraw(st);
    if(st.phase==='ready'||st.phase==='error'){ clearInterval(UPD_TIMER); UPD_TIMER=null; }
  }, 800);
}
window.updApply=async function(){
  if(!(await appConfirm('安装更新并重启软件？下载包已就绪。', {okText:'立即安装'}))) return;
  await post('/api/update/apply');
  $('#updMsg').textContent='正在重启安装，窗口将自动关闭…';
};

/* ---------------- 提示词定制弹窗（运行页每步：查看原版 / 追加 / 替换 / 恢复） ---------------- */
let PM_CTX={skill:'', stepKey:''};
let AP_CTX={idx:0, mode:'view'};
/* 全部步骤提示词弹窗：左 1~N 步列表 → 右侧看提示词 / 追加自定义要求（右上角切换） */
window.openAllPrompt = async function(){
  const template=(RUN_WF&&RUN_WF.template)||'competition';
  AP_CTX={idx:0, mode:'view'};
  const root=document.createElement('div');
  root.id='promptModalRoot';
  root.innerHTML=`<div class="modal open"><div class="modal-box ap-modal">
    <div class="modal-top">
      <h3>全部步骤提示词</h3>
      <div class="ap-mode">
        <span class="ap-mode-l">模式</span>
        <button type="button" class="ap-tab on" data-m="view" onclick="apMode('view')">📖 查看</button>
        <button type="button" class="ap-tab" data-m="edit" onclick="apMode('edit')">✏️ 追加自定义要求</button>
      </div>
      <button class="modal-x" aria-label="关闭" onclick="document.getElementById('promptModalRoot').remove()">✕</button>
    </div>
    <div class="ap-cols">
      <div class="ap-list" id="apList"></div>
      <div class="ap-pane" id="apPane"><div class="muted" style="padding:20px">加载中…</div></div>
    </div>
    <div class="modal-foot"><div style="flex:1"></div>
      <button class="btn btn-ghost btn-sm" onclick="document.getElementById('promptModalRoot').remove()">关闭</button></div>
  </div></div>`;
  document.body.appendChild(root);
  root.querySelector('#apList').innerHTML = RUN_STEPS.map((s,i)=>`
    <button type="button" class="ap-item ${i===AP_CTX.idx?'on':''}" data-i="${i}" onclick="apPick(${i})">
      <span class="ap-no">${String(i+1).padStart(2,'0')}</span><span class="ap-lb">${esc(s.label)}</span>
    </button>`).join('');
  await apPick(0);
};
window.apPick = async function(i){
  AP_CTX.idx=i;
  document.querySelectorAll('#promptModalRoot .ap-item').forEach(b=>b.classList.toggle('on', +b.dataset.i===i));
  if(AP_CTX.mode==='edit') return apRenderEdit(i);
  const s=RUN_STEPS[i]; if(!s) return;
  const template=(RUN_WF&&RUN_WF.template)||'competition';
  const pane=document.getElementById('apPane');
  pane.innerHTML='<div class="muted" style="padding:20px">加载中…</div>';
  const r=await api(`/api/skill-prompt?template=${encodeURIComponent(template)}&step_key=${encodeURIComponent(s.key)}&skill=${encodeURIComponent(s.skill)}`).catch(()=>({}));
  pane.innerHTML=`<div class="ap-pane-h"><span class="ap-step">${String(i+1).padStart(2,'0')} · ${esc(s.label)}</span>
      <span class="ap-cstate">${r.customized?'<i class="ap-dot on"></i>已定制':'<i class="ap-dot"></i>未定制'}</span></div>
    <pre class="code-box ap-code">${esc(r.composed||r.base||'（未找到该 skill 的 SKILL.md）')}</pre>`;
};
window.apMode = async function(m){
  AP_CTX.mode=m;
  document.querySelectorAll('#promptModalRoot .ap-mode .ap-tab').forEach(b=>b.classList.toggle('on', b.dataset.m===m));
  if(m==='edit') apRenderEdit(AP_CTX.idx);
  else await apPick(AP_CTX.idx);
};
window.apRenderEdit = async function(i){
  const s=RUN_STEPS[i]; if(!s) return;
  const template=(RUN_WF&&RUN_WF.template)||'competition';
  const pane=document.getElementById('apPane');
  pane.innerHTML='<div class="muted" style="padding:20px">加载中…</div>';
  const r=await api(`/api/skill-prompt?template=${encodeURIComponent(template)}&step_key=${encodeURIComponent(s.key)}&skill=${encodeURIComponent(s.skill)}`).catch(()=>({}));
  pane.innerHTML=`<div class="ap-pane-h"><span class="ap-step">${String(i+1).padStart(2,'0')} · ${esc(s.label)}</span>
      <span class="ap-cstate">${r.customized?'<i class="ap-dot on"></i>已定制':'<i class="ap-dot"></i>未定制'}</span></div>
    <div class="ap-edit-l">追加自定义要求（拼在原版之后，最高优先级）</div>
    <textarea id="apExtra" placeholder="例如：本步骤重点做灵敏度分析；结论必须给出三级情境……" class="ap-ta">${esc((r.override&&r.override.extra_prompt)||'')}</textarea>
    <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:10px">
      ${r.customized?`<button class="btn btn-ghost btn-sm" onclick="apClear(${i})">恢复原版</button>`:''}
      <button class="btn btn-primary btn-sm" onclick="apSave(${i})">保存</button>
    </div>`;
};
window.apSave = async function(i){
  const s=RUN_STEPS[i]; if(!s) return;
  const el=document.getElementById('apExtra');
  await post('/api/skill-override',{template:(RUN_WF&&RUN_WF.template)||'competition',
    step_key:s.key, skill:s.skill, extra_prompt:el?el.value:'', replace_prompt:''}).catch(()=>{});
  toast('已保存：下一次运行本步骤时生效',true);
  apRenderEdit(i);
};
window.apClear = async function(i){
  const s=RUN_STEPS[i]; if(!s) return;
  await api(`/api/skill-override?template=${encodeURIComponent((RUN_WF&&RUN_WF.template)||'competition')}&step_key=${encodeURIComponent(s.key)}`,{method:'DELETE'}).catch(()=>{});
  toast('已恢复原版提示词',true);
  apRenderEdit(i);
};
window.openPromptModal = async function(skill, stepKey){
  PM_CTX={skill, stepKey};
  const template=(RUN_WF&&RUN_WF.template)||'competition';
  const root=document.createElement('div');
  root.id='promptModalRoot';
  root.innerHTML=`<div class="modal open"><div class="modal-box modal-wide" style="width:96vw;max-width:1240px;height:92vh;max-height:92vh;display:flex;flex-direction:column">
    <div class="modal-top"><div><h3>提示词定制 · ${esc(stepKey)}</h3>
      <p class="muted" style="font-size:12px;margin-top:2px">skill: <code>${esc(skill)}</code> · 流水线: ${esc(template)}。可阅读原版，追加自定义要求，或完 替换。</p></div>
      <button class="modal-x" aria-label="关闭" onclick="document.getElementById('promptModalRoot').remove()">✕</button></div>
    <div style="padding:0 18px;overflow:auto;flex:1">
      <label class="f" style="display:block;margin:10px 0 6px">① 原版提示词（skill 内置，只读） <small id="pmBaseState"></small></label>
      <pre class="code-box" id="pmBase" style="max-height:calc(92vh - 420px);min-height:320px;overflow:auto;font-size:12.5px;line-height:1.6">加载中…</pre>
      <label class="f" style="display:block;margin:12px 0 6px">② 追加自定义要求（推荐：拼在原版之后，最高优先级）</label>
      <textarea id="pmExtra" placeholder="例如：本步骤重点做灵敏度分析；图表配色用现代明亮；结论必须给出三级情境……" style="min-height:90px"></textarea>
      <label class="f" style="display:block;margin:12px 0 6px">③ 完 替换（高级：整个换掉原版 skill；留空=不替换）</label>
      <textarea id="pmReplace" placeholder="留空则不替换。填写后将替代原版 SKILL 全文（原版仍附在末尾作参考）" style="min-height:70px"></textarea>
    </div>
    <div class="modal-foot"><button class="btn btn-ghost btn-sm" onclick="pmClear()">恢复原版（清除定制）</button>
      <div style="flex:1"></div>
      <button class="btn btn-ghost btn-sm" onclick="document.getElementById('promptModalRoot').remove()">取消</button>
      <button class="btn btn-primary btn-sm" onclick="pmSave()">保存定制</button></div>
  </div></div>`;
  document.body.appendChild(root);
  // 拉取当前状态
  const r=await api(`/api/skill-prompt?template=${encodeURIComponent(template)}&step_key=${encodeURIComponent(stepKey)}&skill=${encodeURIComponent(skill)}`).catch(()=>({}));
  $('#pmBase').textContent=r.base||'（未找到该 skill 的 SKILL.md）';
  $('#pmBaseState').textContent=`共 ${(r.base||'').length} 字 · 当前${r.customized?'已':'未'}定制`;
  if(r.override){ $('#pmExtra').value=r.override.extra_prompt||''; $('#pmReplace').value=r.override.replace_prompt||''; }
};
window.pmSave = async function(){
  await post('/api/skill-override',{template:(RUN_WF&&RUN_WF.template)||'competition',
    step_key:PM_CTX.stepKey, skill:PM_CTX.skill,
    extra_prompt:$('#pmExtra').value, replace_prompt:$('#pmReplace').value});
  document.getElementById('promptModalRoot').remove();
  toast('已保存，下一次运行本步骤时生效',true); runDraw();
};
window.pmClear = async function(){
  await api(`/api/skill-override?template=${encodeURIComponent((RUN_WF&&RUN_WF.template)||'competition')}&step_key=${encodeURIComponent(PM_CTX.stepKey)}`,{method:'DELETE'});
  document.getElementById('promptModalRoot').remove();
  toast('已恢复原版提示词',true); runDraw();
};

/* ================= 启动（授权锁优先） ================= */
let LICENSED = false;
function renderLock(){
  $('#mainNav').innerHTML='';
  $('#view').innerHTML = `
    <div style="min-height:70vh;display:flex;align-items:center;justify-content:center">
      <div class="card" style="max-width:460px;width:100%;padding:40px 38px;text-align:center">
        <img src="/static/logo.svg" style="width:64px;height:64px;margin-bottom:14px" alt="logo">
        <h2 style="font-size:19px;margin-bottom:6px">ModelFlow 智模流水线</h2>
        <p class="muted" style="font-size:13px;margin-bottom:20px">本软件需授权码激活（一码一机）。<br>购买或获取授权码请联系管理员。</p>
        <input id="licCode" maxlength="5" placeholder="5 位授权码" autocomplete="off"
          style="width:100%;text-align:center;font-size:20px;letter-spacing:10px;font-family:var(--font-mono);text-transform:uppercase;padding:12px">
        <button class="btn btn-primary btn-lg" style="width:100%;margin-top:14px" onclick="licActivate()">激 活</button>
        <p id="licErr" style="color:var(--bad);font-size:13px;margin-top:12px;min-height:18px"></p>
      </div>
    </div>`;
  const inp=$('#licCode');
  inp.focus();
  inp.onkeydown=e=>{ if(e.key==='Enter') licActivate(); };
}
window.licActivate = async function(){
  const code=($('#licCode').value||'').trim().toUpperCase();
  if(!code){ $('#licErr').textContent='请输入授权码'; return; }
  $('#licErr').textContent='验证中…';
  try{
    const r=await post('/api/license/activate',{code});
    if(!r.ok){ $('#licErr').textContent=r.msg||'激活失败'; return; }
    LICENSED=true;
    toast(r.admin?'管理员身份激活成功':'激活成功',true);
    nav.resolve(); renderNav('list');
  }catch(e){ $('#licErr').textContent='网络错误，请重试'; }
};
/* ---------------- 启动准备（本地环境自检遮罩） ---------------- */
let GATE_DONE = false;

function renderGate(rows){
  let root = document.getElementById('gateRoot');
  if(root){ root.remove(); }
  root = document.createElement('div');
  root.id = 'gateRoot';
  root.style.cssText = 'position:fixed;inset:0;z-index:200;background:rgba(24,24,27,.32);backdrop-filter:blur(6px);display:flex;align-items:center;justify-content:center';
  const rowsHtml = rows.map((r,i)=>`
    <div class="gate-row" data-i="${i}">
      <span class="gate-ico" data-st="wait"></span>
      <span class="gate-name">${esc(r.name)}</span>
      <span class="gate-st" data-st="wait">等待中</span>
    </div>`).join('');
  root.innerHTML = `
    <div class="gate-card mf-pop">
      <div class="gate-crumb">启动准备 · 本地环境检查</div>
      <div style="display:flex;align-items:center;gap:12px;margin:10px 0 14px">
        <span class="gate-spin" id="gateSpin"></span>
        <b style="font-size:17px">正在准备本地工作环境</b>
      </div>
      <p class="gate-desc">ModelFlow 的竞赛流水线、论文编译与品牌资自需要本地组件配合。
        打开软件会自动逐项自检，全程数秒。</p>
      <div style="display:flex;justify-content:space-between;font-size:12px;color:#71717a;margin:10px 2px 6px">
        <span>本地组件</span><span id="gateCount">0 / ${rows.length} 已就绪</span>
      </div>
      <div class="gate-rows">${rowsHtml}</div>
      <div class="gate-bar"><div class="gate-bar-fill" id="gateBar" style="width:0%"></div></div>
      <p class="gate-desc" style="margin:12px 2px 2px">本地环境检查完成后才能进入工作区。此过程通常只需数秒，请勿关闭窗口。</p>
    </div>`;
  document.body.appendChild(root);
}
function gateRow(i, st, text){
  const root = document.getElementById('gateRoot'); if(!root) return;
  const row = root.querySelector(`.gate-row[data-i="${i}"]`); if(!row) return;
  const ico = row.querySelector('.gate-ico');
  const stEl = row.querySelector('.gate-st');
  row.dataset.st = st;
  ico.dataset.st = st;
  ico.innerHTML = st==='ready' ? '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3" width="11" height="11"><path d="M20 6L9 17l-5-5"/></svg>'
    : st==='warn' ? '<svg viewBox="0 0 24 24" fill="none" stroke="#b45309" stroke-width="2.4" width="13" height="13"><path d="M12 9v4m0 4h.01M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/></svg>' : '';
  stEl.dataset.st = st;
  stEl.textContent = text;
}
function gateProgress(done, total){
  const root = document.getElementById('gateRoot'); if(!root) return;
  root.querySelector('#gateCount').textContent = `${done} / ${total} 已就绪`;
  root.querySelector('#gateBar').style.width = Math.round(done*100/total) + '%';
}
async function gateCheck(name, run, rows, i){
  gateRow(i, 'run', '检查中');
  let st = 'ready', text = '已就绪';
  try{ const r = await run(); if(r && r.st==='warn'){ st='warn'; text=r.text; } }
  catch(e){ st = 'warn'; text = '未就绪·可选'; }
  gateRow(i, st, text);
  return st;
}

(async ()=>{
  // 启动准备遮罩：先渲染，再逐项真实检查（无 eval——目录走 index.html script 全局量）
  const CHECKS = [
    { name:'本地服务', run: async () => { const h = await api('/api/health'); if(!h.ok) throw 0; if(!h.latex) return {st:'warn', text:'LaTeX 未装·可选'}; return null; } },
    { name:'授权验证', run: async () => { const st = await api('/api/license/status');
        LICENSED = !!st.activated;
        if(!st.activated) return {st:'warn', text:'未激活'};
        return null; } },
    { name:'执行引擎', run: async () => { const r = await api('/api/runtimes'); const c = (r.runtimes||{}).claude_cli;
        if(!c || !c.ok) return {st:'warn', text:'Claude Code 未装·可一键装'};
        return null; } },
    { name:'供应商目录', run: async () => { if((window.PROVIDER_CATALOG||[]).length < 9) throw 0; return null; } },
    { name:'品牌图标库', run: async () => { const r = await fetch('/static/logos/cc/deepseek.svg', {cache:'reload'});
        if(r.status!==200) throw 0; return null; } },
    { name:'MiSans 字体', run: async () => { const r = await fetch('/static/fonts/fonts.css', {cache:'reload'});
        if(r.status!==200) throw 0; return null; } },
    { name:'本地运行时', run: async () => { const r = await api('/api/runtimes');
        const rt = r.runtimes||{};
        const missing = Object.keys(rt).filter(k => !rt[k].ok);
        if(!missing.length) return null;
        return {st:'warn', text:'缺 ' + missing.join('、')};
      } },
    { name:'在线更新自', run: async () => { const info = await api('/api/update/info');
        if(!info.update_url) return {st:'warn', text:'未配置·可选'};
        return null; } },
  ];
  renderGate(CHECKS);
  let done = 0;
  for(let i=0;i<CHECKS.length;i++){
    gateRow(i, 'run', '检查中');
    await new Promise(r=>setTimeout(r, 300));   // 逐行节奏（观感：清单逐项点亮）
    await gateCheck(CHECKS[i].name, CHECKS[i].run, CHECKS, i);
    done++; gateProgress(done, CHECKS.length);
  }
  await new Promise(r=>setTimeout(r, 500));      // 停留一拍再渐出
  const root = document.getElementById('gateRoot');
  if(root){
    root.style.transition = 'opacity .35s ease';
    root.style.opacity = '0';
    await new Promise(r=>setTimeout(r, 360));
    root.remove();
  }
  GATE_DONE = true;
  window.addEventListener('hashchange', ()=>{
    if(!GATE_DONE) return;
    if(!LICENSED){ renderLock(); return; }
    nav.resolve();
    // 若离开 run 页，清定时器并断开 WS
    if(!(location.hash||'').includes('/run/')){ clearInterval(RUN_TIMER); closeRunWs(); }
  });
  if(!LICENSED){
    renderLock();
  }else{
    nav.resolve();
    updateTnModel();
  }
})();

/* ---------- 产物编辑器（覆盖层：文件树 + 编辑 + AI 润色） ---------- */
let MF_ED = {open:false, cur:''};
function openFileEditor(){
  let root = document.getElementById('mfEditorRoot');
  if(root){ root.style.display='flex'; return; }
  root = document.createElement('div');
  root.id = 'mfEditorRoot';
  root.style.cssText = 'position:fixed;inset:0;background:var(--bg);z-index:80;display:flex;flex-direction:column';
  root.innerHTML = `
    <div style="display:flex;align-items:center;gap:10px;padding:10px 16px;border-bottom:1px solid var(--border);background:var(--card)">
      <button class="btn btn-ghost btn-sm" onclick="closeFileEditor()">← 运行页</button>
      <b id="mfEdFile" style="font-size:14px">（左侧选择文件）</b>
      <div style="flex:1"></div>
      <button class="btn btn-ghost btn-sm" onclick="mfAiPolish()">AI 润色本文件</button>
      <button class="btn btn-primary btn-sm" onclick="mfSaveEdit()">保存</button>
    </div>
    <div style="flex:1;display:flex;min-height:0">
      <div id="mfEdTree" style="width:270px;border-right:1px solid var(--border);overflow:auto;padding:12px;background:var(--card)"></div>
      <textarea id="mfEdText" spellcheck="false" style="flex:1;border:0;outline:none;padding:16px;font-family:Consolas,monospace;font-size:13px;line-height:1.6;resize:none;background:var(--bg);color:var(--ink)"></textarea>
    </div>
    <div id="mfEdAi" style="display:none;border-top:1px solid var(--border);max-height:200px;overflow:auto;padding:10px 16px;background:var(--card);font-size:13px;white-space:pre-wrap"></div>`;
  document.body.appendChild(root);
  mfLoadTree();
}
function closeFileEditor(){
  const r = document.getElementById('mfEditorRoot');
  if(r) r.style.display = 'none';
}
async function mfLoadTree(){
  const tree = document.getElementById('mfEdTree'); if(!tree) return;
  try{
    const r = await api('/api/workflows/'+RUN_WF.id+'/files');
    const groups = r.groups||{};
    const keys = Object.keys(groups);
    if(!keys.length){ tree.innerHTML = '<div class="muted" style="font-size:12px">暂无产物文件，先运行工作流</div>'; return; }
    tree.innerHTML = keys.map(k=>`
      <div style="margin-bottom:12px">
        <div style="font-weight:700;font-size:12px;color:var(--muted);padding:2px 0">${esc(k)}</div>
        ${(groups[k]||[]).map(f=>`
          <div data-p="${esc(f.path)}" onclick="mfOpen('${encodeURIComponent(f.path)}',this)"
               style="padding:6px 9px;border-radius:7px;cursor:pointer;font-size:13px;display:flex;justify-content:space-between;gap:8px;align-items:center">
            <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(f.name)}</span>
            <span style="color:var(--muted);font-size:11px;flex-shrink:0">${f.size>=1024?Math.round(f.size/1024)+'K':f.size+'B'}</span>
          </div>`).join('')}
      </div>`).join('');
    for(const k of keys){
      const fs = groups[k]||[];
      const hit = fs.find(x=>/\.(md|txt|tex|json|py|csv)$/i.test(x.name)) || fs[0];
      if(hit){ mfOpen(encodeURIComponent(hit.path)); break; }
    }
  }catch(e){ tree.textContent = '加载失败: ' + e; }
}
async function mfOpen(pEnc, el){
  MF_ED.cur = decodeURIComponent(pEnc||'');
  document.querySelectorAll('#mfEdTree [data-p]').forEach(x=>x.style.background='');
  if(el) el.style.background = 'var(--bg-hover)';
  document.getElementById('mfEdFile').textContent = MF_ED.cur;
  try{
    const r = await fetch('/api/workflows/'+RUN_WF.id+'/file?path='+encodeURIComponent(MF_ED.cur));
    document.getElementById('mfEdText').value = await r.text();
  }catch(e){ document.getElementById('mfEdText').value = '读取失败: '+e; }
}
async function mfSaveEdit(){
  if(!MF_ED.cur){ toast('先在左侧选择文件'); return; }
  const r = await api('/api/editor/save', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({wid:RUN_WF.id, path:MF_ED.cur, content:document.getElementById('mfEdText').value})});
  toast(r.ok?'已保存':'保存失败: '+(r.error||''), !!r.ok);
}
async function mfAiPolish(){
  if(!MF_ED.cur){ toast('先在左侧选择文件'); return; }
  const out = document.getElementById('mfEdAi');
  out.style.display='block'; out.textContent='AI 编辑中，请稍候…';
  try{
    const r = await api('/api/editor/ai', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({wid:RUN_WF.id, path:MF_ED.cur, instruction:'润色优化本文件内容：保持结构不变，提升表述质量与一致性；直接返回修改后的完整文件内容。'})});
    if(r.ok){ document.getElementById('mfEdText').value = r.content||''; out.textContent='AI 修改完成，请检查后点「保存」确认。'; }
    else{ out.textContent = 'AI 失败: '+(r.error||''); }
  }catch(e){ out.textContent = 'AI 请求异常: '+e; }
}


window.runLiveClear = function(){
  RUN_LOG_LINES.length = 0;
  const b = document.getElementById('runLogBody');
  if(b) b.innerHTML = '';
};
// 产物编辑器函数被内联 onclick 引用，需暴露到全局（否则点「✎ 编辑器」无反应）
window.openFileEditor = openFileEditor;
window.closeFileEditor = closeFileEditor;
window.mfOpen = mfOpen;
window.mfSaveEdit = mfSaveEdit;
window.mfAiPolish = mfAiPolish;
})();