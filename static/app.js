/* ==========================================================================
 * Loom 织流 · 外壳与视图
 * 路由：#/home 工作流控制台 · #/skills 技能库 · #/runs 运行记录 · #/settings 设置
 * 文案全部走 window.t()，外观（语言/明暗/字体/字号/缩放/宽度）走 window.APP
 * ========================================================================== */
(() => {
'use strict';

/* ---------------- 工具 ---------------- */
const $ = s => document.querySelector(s);
const t = window.t;
function esc(s){ return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;'); }
/* 往内联事件里塞字符串参数要转义两次（HTML 属性 + JS 字面量）；弹窗打开时锁背景滚动。
   这两个原来在 editor.js / run.js 各有一份，现在统一从这里走。 */
const jsq = s => String(s==null?'':s).replace(/\\/g,'\\\\').replace(/"/g,'&quot;').replace(/'/g,"\\'");
window.jsq = jsq;
const _lockScroll = on => { document.body.style.overflow = on ? 'hidden' : ''; };
window._lockScroll = _lockScroll;

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
function del(path){ return api(path, {method:'DELETE'}); }

let toastTimer=null;
function toast(msg, ok=false){
  const el = $('#toast');
  if(!el) return;
  el.textContent = msg||'';
  el.className = 'toast show '+(ok?'ok':'err');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(()=>{ el.className='toast'; }, 2600);
}
window.ffToast = toast;

function relDate(str){
  if(!str) return '';
  const d = new Date(str.replace(' ', 'T'));
  if(isNaN(d)) return str;
  const diff = (Date.now()-d.getTime())/1000;
  if(diff < 60) return t('c.justNow');
  if(diff < 3600) return t('c.minAgo',{n:Math.floor(diff/60)});
  if(diff < 86400) return t('c.hourAgo',{n:Math.floor(diff/3600)});
  if(diff < 86400*30) return t('c.dayAgo',{n:Math.floor(diff/86400)});
  return str.slice(0,10);
}
window.ffRelDate = relDate;

/* ---------------- 状态 ---------------- */
const ST = { agents:[], defaultEngine:'',
             claudeCli:'', codexCli:'', paths:{}, sandboxOptions:[],
             agentTimeout:'2700', codexSandbox:'workspace-write', effortOptions:['auto'],
             reasoningEffort:'auto', stepRetry:'0', autoContinue:'0',
             skills:[], flows:[], runs:[], caps:null, version:'' };
window.ST = ST;

const RUN_ST = () => ({pending:t('st.pending'), running:t('st.running'), waiting:t('st.waiting'),
  done:t('st.done'), failed:t('st.failed'), cancelled:t('st.cancelled'), revising:t('st.revising')});
window.RUN_ST = RUN_ST;
const ENG_ZH = () => ({claude:t('eng.claude'), codex:t('eng.codex')});
window.ENGINE_LABEL = e => (e ? ((ENG_ZH()[e]||e)) : t('ed.engineDefault'));

/* ---------------- 外壳：侧栏 / 顶栏 ---------------- */
const ico = window.icon;

function renderNav(active){
  const nb = $('#sbNew');
  if(nb){
    nb.innerHTML = `${ico('plus')}<span>${esc(t('nav.newTask'))}</span>
        <span class="sb-kbd">Ctrl K</span>`;
    nb.dataset.tip = t('nav.newTask');
  }
  const fb = $('#sbSearchBtn');
  if(fb){ fb.innerHTML = ico('search'); fb.dataset.tip = t('sb.search');
          fb.setAttribute('aria-label', t('sb.search')); }
  /* 设置走左下角入口；工作台已并入「新建任务」弹层，不再单列 */
  const items = [
    {id:'pipelines', icon:'flow',     label:t('nav.workflows')},
    {id:'skills',    icon:'skill',    label:t('nav.skills')},
    {id:'runs',      icon:'runs',     label:t('nav.runs')},
  ];
  /* 用真 href 而不是 onclick：无 href 的 <a> 拿不到键盘焦点，Tab 直接跳过整条主导航。
     aria-label 是因为折叠轨道会把 <span> 整个 display:none 掉，折上就没了可访问名。 */
  const html = items.map(n=>
    `<a class="sb-item ${n.id===active?'active':''}" href="#/${n.id}" data-v="${n.id}"
       data-tip="${esc(n.label)}" aria-label="${esc(n.label)}"
       ${n.id===active?'aria-current="page"':''}>
      ${ico(n.icon)}<span>${esc(n.label)}</span></a>`).join('');
  const box = $('#mainNav');
  if(box && box.dataset.sig !== html){ box.innerHTML = html; box.dataset.sig = html; }
  paintBrand();
  /* 换语言时这两处的文案没人刷：它们不在 renderNav 的重绘链上，只在启动 / 轮询里写 */
  paintFootMe(); paintUpdate();
}

/* 品牌位 = 侧栏折叠开关。回首页不再挂这儿：主导航第一项就是它，两处入口不如一处。 */
function paintBrand(){
  const b = $('#sbBrand'); if(!b) return;
  const collapsed = document.documentElement.dataset.sidebar === 'collapsed';
  b.dataset.tip = t('sb.toggle');
  b.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
  b.setAttribute('aria-label', t('sb.toggle'));
}
window.sbToggle = async function(){
  const cur = document.documentElement.dataset.sidebar === 'collapsed';
  await window.setAppearance({sidebar: cur ? 'expanded' : 'collapsed'});
  hideTip(); paintBrand();
};

/* ---------------- 悬停提示 ----------------
   原生 title 有一秒延迟、样式跟着系统，折叠成轨道后全靠它补标签不够用。
   带 data-tip-any 的（只有图标的按钮）两种宽度下都提示，其余只在轨道下提示，
   免得展开时给本来就写着文字的行再糊一层。 */
let TIP_EL = null;
function tipWants(el){
  return el.dataset.tip && el.matches('[data-tip-any], html[data-sidebar="collapsed"] [data-tip]');
}
function showTip(el){
  const tip = $('#ffTip'); if(!tip) return;
  tip.textContent = el.dataset.tip; tip.hidden = false;
  const r = el.getBoundingClientRect(), b = tip.getBoundingClientRect();
  const rail = document.documentElement.dataset.sidebar==='collapsed' && el.closest('.sidebar');
  let left = rail ? r.right + 8 : r.left;
  let top  = rail ? r.top + r.height/2 - b.height/2 : r.bottom + 6;
  // 贴底的那一排（热力图最后一行）往下放就出屏了，翻到格子上方
  if (!rail && top + b.height > window.innerHeight - 8) top = r.top - b.height - 6;
  left = Math.max(8, Math.min(left, window.innerWidth - b.width - 8));
  top  = Math.max(8, Math.min(top, window.innerHeight - b.height - 8));
  tip.style.left = left + 'px'; tip.style.top = top + 'px';
}
function hideTip(){ TIP_EL = null; const tip = $('#ffTip'); if(tip) tip.hidden = true; }
function tipHover(el){
  if(!el || !tipWants(el)){ if(TIP_EL) hideTip(); return; }
  if(el === TIP_EL) return;
  TIP_EL = el; showTip(el);
}
document.addEventListener('pointerover', (e)=>{
  tipHover(e.target && e.target.closest ? e.target.closest('[data-tip]') : null);
});
document.addEventListener('focusin', (e)=>{
  tipHover(e.target && e.target.closest ? e.target.closest('[data-tip]') : null);
});
document.addEventListener('focusout', hideTip);
document.addEventListener('pointerdown', hideTip);
window.addEventListener('blur', hideTip);
window.addEventListener('scroll', hideTip, true);

/* 顶栏：视图渲染时写 window.__chrome，由 paintChrome 落地 */
window.__chrome = {title:'', icon:'flow', actions:''};
function paintChrome(){
  const c = window.__chrome || {title:'', icon:'flow'};
  const tt = $('#tbTitle');
  if(tt) tt.innerHTML = `${ico(c.icon||'flow')}<span>${esc(c.title||'')}</span>`;
  const ta = $('#tbActions');
  if(ta) ta.innerHTML = c.actions||'';
}
window.paintChrome = paintChrome;

/* 侧栏下半区：全部流程 + 最近运行（Codex 的「项目 / 最近」分组） */
const RUN_ICON = {
  running:  {ic:'spinner', cls:'sb-live',   sp:1},
  revising: {ic:'spinner', cls:'sb-live',   sp:1},
  waiting:  {ic:'pause',   cls:'sb-wait',   sp:0},
  failed:   {ic:'warn',    cls:'sb-bad',    sp:0},
  done:     {ic:'',        cls:'',          sp:0},
  cancelled:{ic:'',        cls:'',          sp:0},
  pending:  {ic:'circle',  cls:'sb-idle',   sp:0},
};

async function renderSidebarLists(){
  const box = $('#sbLists');
  if(!box) return;
  const [pr, rr] = await Promise.all([
    api('/api/pipelines').catch(()=>({pipelines:[]})),
    api('/api/runs?limit=8').catch(()=>({runs:[]})),
  ]);
  const flows = (pr.pipelines||[]).filter(p=>p.runs>0);   /* 项目 = 真跑过的流程 */
  const runs = rr.runs||[];
  ST.sbFlows = pr.pipelines||[]; ST.sbRuns = runs;
  const cur = (location.hash.split('/')[2]||'');
  const live = runs.filter(u=>u.status==='running'||u.status==='revising'||u.status==='waiting').length;

  let html = `<div class="sb-group"><span>${esc(t('sb.flows'))}</span>
      <button class="sb-gadd" data-tip-any="1" data-tip="${esc(t('sb.newFlow'))}"
        aria-label="${esc(t('sb.newFlow'))}"
        onclick="nav.go('pipeline-edit/new')">${ico('plus')}</button></div>`
    + (flows.length ? flows.map(p=>`<a class="sb-run ${('pipeline-edit/'+p.name)===cur?'active':''}"
        href="#/pipeline-edit/${esc(p.name)}" data-tip="${esc(p.label||p.name)}"
        aria-label="${esc(p.label||p.name)}"
        ${('pipeline-edit/'+p.name)===cur?'aria-current="page"':''}>
        <span class="sb-rico">${ico('flow')}</span>
        <span class="sb-rname">${esc(p.label||p.name)}</span></a>`).join('')
      : `<div class="sb-empty">${esc(t('sb.noProject'))}</div>`);

  html += `<div class="sb-group"><span>${esc(t('sb.recent'))}</span>
      ${live?`<span class="sb-gcount">${live}</span>`:''}</div>`
    + (runs.length ? runs.map(u=>{
        const m = RUN_ICON[u.status] || RUN_ICON.pending;
        return `<a class="sb-run ${u.id===cur?'active':''}" data-tip="${esc(u.label||u.pipeline)}"
          href="#/run/${esc(u.id)}" aria-label="${esc(u.label||u.pipeline)}"
          ${u.id===cur?'aria-current="page"':''}>
          <span class="sb-rico ${m.cls}">${m.ic?(m.sp?ico(m.ic,'sp'):ico(m.ic)):'&nbsp;'}</span>
          <span class="sb-rname">${esc(u.label||u.pipeline)}</span>
          <span class="sb-rtag">${esc(RUN_ST()[u.status]||u.status)}</span></a>`;
      }).join('')
      : `<div class="sb-empty">${esc(t('home.recentEmpty'))}</div>`);
  if(box.dataset.sig !== html){ box.innerHTML = html; box.dataset.sig = html; }
  const ab = $('#sbActBtn');
  if(ab){ ab.innerHTML = ico('bell') + (live?`<span class="sb-badge">${live}</span>`:'');
          ab.classList.toggle('on', !!live);
          ab.dataset.tip = live? t('sb.liveN',{n:live}) : t('sb.noLive');
          ab.setAttribute('aria-label', ab.dataset.tip); }
}

/* 侧栏搜索：流程 + 运行一起找 */
function sbHit(label, sub, onPick, icon){
  return `<button class="sb-fi" onclick="${onPick}"><span class="sb-rico">${ico(icon)}</span>
    <span class="sb-fmain"><b>${esc(label)}</b><i>${esc(sub)}</i></span></button>`;
}
window.sbSearch = function(e){
  if(e) e.stopPropagation();
  const p = document.getElementById('sbFind');
  if(!p) return;
  if(!p.hidden){ p.hidden = true; return; }
  const draw = (q)=>{
    const k = (q||'').trim().toLowerCase();
    const fl = (ST.sbFlows||[]).filter(x=>!k || ((x.label||'')+' '+x.name).toLowerCase().includes(k));
    const ru = (ST.sbRuns||[]).filter(x=>!k || ((x.label||'')+' '+x.pipeline).toLowerCase().includes(k));
    const body = (fl.length||ru.length)
      ? fl.slice(0,6).map(x=>sbHit(x.label||x.name, t('sb.stepsN',{n:(x.steps||[]).length}),
            `sbGo('pipeline-edit/${esc(x.name)}')`, 'flow')).join('')
        + ru.slice(0,6).map(x=>sbHit(x.label||x.pipeline, RUN_ST()[x.status]||x.status,
            `sbGo('run/${esc(x.id)}')`, 'runs')).join('')
      : `<div class="sb-empty">${esc(t('sb.noHit'))}</div>`;
    p.innerHTML = `<div class="sb-fbox">${ico('search')}
        <input id="sbFQ" placeholder="${esc(t('sb.search'))}" value="${esc(q||'')}"
          oninput="sbSearchType(this.value)"></div>
       <div class="sb-fres">${body}</div>`;
  };
  window.sbSearchType = (v)=>{ const q=document.getElementById('sbFQ'); const pos=q?q.selectionStart:0;
    draw(v); const n=document.getElementById('sbFQ'); n.focus(); try{n.setSelectionRange(pos,pos);}catch(_){} };
  window.sbGo = (hash)=>{ p.hidden = true; nav.go(hash); };
  draw('');
  p.hidden = false;
  const r = document.getElementById('sbSearchBtn').getBoundingClientRect();
  p.style.left = Math.max(8, r.left - 4) + 'px';
  p.style.top = (r.bottom + 6) + 'px';
  setTimeout(()=>{ const n=document.getElementById('sbFQ'); if(n) n.focus(); }, 30);
};

window.sbActivity = function(e){
  if(e) e.stopPropagation();
  const p = document.getElementById('sbFind');
  if(p && !p.hidden){ p.hidden = true; }
  const runs = (ST.sbRuns||[]).filter(u=>u.status!=='done'&&u.status!=='cancelled');
  nav.go(runs.length ? 'run/'+runs[0].id : 'runs');
};
window.renderSidebarLists = renderSidebarLists;

async function loadAgents(){
  const r = await api('/api/agents').catch(()=>null);
  if(!r) return;
  ST.agents = r.agents||[];
  ST.defaultEngine = r.default_engine||'';
  ST.claudeCli = r.claude_cli||'';
  ST.codexCli = r.codex_cli||'';
  const ready = ST.agents.filter(a=>a.found);
  paintFootMe(ready);
}
window.loadAgents = loadAgents;

/* ---------------- 左下角配置浮层 ---------------- */
function paintFootMe(ready){
  const el = document.getElementById('sbMeName');
  if(!el) return;
  ready = ready || ST.agents.filter(a=>a.found);
  el.textContent = ready.length ? ready.map(a=>a.engine).join(' · ')
                                : t('home.engineNone');
  const av = document.getElementById('sbMeAv');
  if(av){ av.innerHTML = ico('settings'); }
  const me = document.getElementById('sbMe');
  if(me){ me.dataset.tip = t('nav.settings'); me.setAttribute('aria-label', t('nav.settings')); }
  const ch = document.getElementById('sbMeChev');
  if(ch) ch.innerHTML = ico('chevronUp');
}
function footRows(){
  const A = window.APP;
  const ready = ST.agents.filter(a=>a.found);
  return `
    <button class="sb-prow" onclick="footCycle('theme')">${ico('appearance')}
      <span>${esc(t('foot.theme'))}</span>
      <span class="sb-pv">${esc(t('ap.theme.'+A.theme))}</span>${ico('chevronRight','ic-chev')}</button>
    <button class="sb-prow" onclick="footCycle('accent')">${ico('spark')}
      <span>${esc(t('foot.accent'))}</span>
      <span class="sb-pv">${esc(t('ap.accent.'+(A.accent||'blue')))}</span>${ico('chevronRight','ic-chev')}</button>
    <button class="sb-prow" onclick="footCycle('lang')">${ico('lang')}
      <span>${esc(t('foot.lang'))}</span>
      <span class="sb-pv">${esc(A.lang==='en'?'English':'简体中文')}</span>${ico('chevronRight','ic-chev')}</button>
    <button class="sb-prow" onclick="closeFootMenu();nav.go('settings','engines')">${ico('agent')}
      <span>${esc(t('foot.engines'))}</span>
      <span class="sb-pv"><i class="sb-pdot ${ready.length?'ok':'no'}"></i>${ready.length}/${ST.agents.length||2}</span>
      ${ico('chevronRight','ic-chev')}</button>
    <div class="sb-sep"></div>
    <button class="sb-prow" onclick="closeFootMenu();nav.go('settings')">${ico('settings')}
      <span>${esc(t('nav.settings'))}</span><span class="sb-pkbd">Ctrl ,</span></button>`;
}
window.footMenu = function(e){
  if(e) e.stopPropagation();
  const pop = document.getElementById('sbPop');
  if(!pop) return;
  if(!pop.hidden){ closeFootMenu(); return; }
  pop.innerHTML = footRows();
  pop.hidden = false;
  document.getElementById('sbMe').setAttribute('aria-expanded', 'true');
  const r = document.getElementById('sbMe').getBoundingClientRect();
  pop.style.left = Math.max(8, Math.min(r.left, window.innerWidth - pop.offsetWidth - 8)) + 'px';
  pop.style.bottom = (window.innerHeight - r.top + 6) + 'px';
};
window.closeFootMenu = function(){
  const pop = document.getElementById('sbPop');
  if(pop){ pop.hidden = true; pop.innerHTML=''; }
  const me = document.getElementById('sbMe');
  if(me) me.setAttribute('aria-expanded', 'false');
};
window.footCycle = async function(key){
  const A = window.APP;
  const CYCLE = { theme:['light','dark','auto'], accent:['blue','gold'], lang:['zh','en'] };
  const list = CYCLE[key]; if(!list) return;
  // 这条路径直接 nav.resolve() 重绘整页，绕开了 nav.go 上那道未保存守卫 ——
  // 在流程编辑器里换个主题就能把没存的步骤改动冲没。所以先问守卫，再动设置。
  if(window.navGuardAsk && !window.navGuardAsk()) return;
  const next = list[(list.indexOf(String(A[key] ?? list[0])) + 1) % list.length];
  await window.setAppearance({[key]: next});
  const pop = document.getElementById('sbPop');
  if(pop && !pop.hidden) pop.innerHTML = footRows();
  nav.resolve();
};

/* ---------------- 左下角：更新 ----------------
   只有「有东西可点」的时候才占位：idle / checking / 已是最新 一律隐藏，
   免得一个永远灰着的按钮骗人。 */
let UP = null, UP_POLL = null;
const mb = n => (n/1048576).toFixed(1) + ' MB';

function upView(s){
  if(!s || !s.configured) return null;
  const pct = s.size ? Math.min(99, Math.floor((s.got||0)*100/s.size)) : 0;
  if(s.phase === 'available')
    return {text: t('up.avail'), tip: t('up.tipAvail', {v: s.latest, cur: s.local}),
            tone: '', ic:'download', p: 0};
  if(s.phase === 'downloading')
    return {text: pct + '%', tip: t('up.tipDl', {got: mb(s.got||0), size: mb(s.size)}),
            tone: 'dl', ic:'download', p: pct};
  if(s.phase === 'ready')
    return {text: t('up.ready'), tip: t('up.tipReady', {p: s.path || ''}),
            tone: 'ok', ic:'checkCircle', p: 100};
  if(s.phase === 'error')
    return {text: t('up.failed'), tip: t('up.tipErr', {e: s.error || ''}),
            tone: 'err', ic:'warn', p: 0};
  return null;
}

/* 轨道宽度下放不下「已下载」三个字，所以文字和图标各渲染一份，CSS 挑着显示 */
function paintUpdate(){
  const b = $('#sbUpdate'); if(!b) return;
  const v = upView(UP);
  if(!v){ b.hidden = true; b.innerHTML = ''; b.dataset.tip = ''; return; }
  b.hidden = false;
  b.className = 'sb-update' + (v.tone ? ' is-' + v.tone : '');
  b.innerHTML = (v.tone === 'dl' ? '<span class="sb-up-bar"></span>' : '')
              + `<span class="sb-up-ic">${ico(v.ic||'download')}</span>`
              + '<span class="sb-up-tx">' + esc(v.text) + '</span>';
  b.dataset.tip = v.tip;
  b.setAttribute('aria-label', v.tip);
  b.style.setProperty('--p', (v.p || 0) + '%');
}

function upPoll(){
  if(UP_POLL){ clearInterval(UP_POLL); UP_POLL = null; }
  if(!UP || UP.phase !== 'downloading') return;
  UP_POLL = setInterval(async ()=>{
    const s = await api('/api/update').catch(()=>null);
    if(!s) return;
    UP = s; paintUpdate();
    if(s.phase !== 'downloading'){ clearInterval(UP_POLL); UP_POLL = null; }
  }, 400);
}

window.sbUpdateClick = async function(e){
  if(e) e.stopPropagation();
  if(!UP) return;
  if(UP.phase === 'available'){
    const n = UP.active_runs || 0;
    if(n > 0 && !confirm(t('up.busyConfirm', {n}))) return;
    UP = await post('/api/update/download').catch(()=>({phase:'error', error:t('up.reqFail')}));
    paintUpdate(); upPoll();
    if(UP.phase === 'error') toast(UP.error);
    return;
  }
  if(UP.phase === 'error'){
    UP = await post('/api/update/check').catch(()=>UP); paintUpdate(); return;
  }
  if(UP.phase === 'ready'){
    if(!confirm(t('up.applyGo', {v: UP.latest || ''}))) return;
    const n = UP.active_runs || 0;
    if(n > 0 && !confirm(t('up.busyConfirm', {n}))) return;
    const r = await post('/api/update/apply').catch(e=>({detail:String(e)}));
    if(r && r.detail){ toast(r.detail); return; }
    toast(t('up.applyStarted'), true);
    return;
  }
  if(UP.phase === 'downloading'){ toast(t('up.downloading')); }
};

async function upInit(){
  const s = await api('/api/update').catch(()=>null);
  if(!s || !s.configured) return;
  UP = s;
  if(s.phase === 'idle' || s.phase === 'error'){
    UP = await post('/api/update/check').catch(()=>UP);
    /* 开机自动检查失败不该在左下角挂一个红胶囊骂人：
       用户没问的时候保持安静，设置页里照样能看到具体错在哪。 */
    if(UP && UP.phase === 'error'){ UP = Object.assign({}, UP, {phase:'idle'}); }
  }
  paintUpdate();
  if(UP && UP.phase === 'downloading') upPoll();
}
window.upInit = upInit;
window.paintUpdate = paintUpdate;
document.addEventListener('click', (e)=>{
  const pop = document.getElementById('sbPop');
  if(pop && !pop.hidden && !e.target.closest('#sbPop') && !e.target.closest('#sbMe')) closeFootMenu();
  const fd = document.getElementById('sbFind');
  if(fd && !fd.hidden && !e.target.closest('#sbFind') && !e.target.closest('#sbSearchBtn')) fd.hidden = true;
});

/* ---------------- 路由 ---------------- */
function viewTransitionOut(){
  const v = document.getElementById('view');
  if(!v) return Promise.resolve();
  v.classList.remove('mf-enter');
  return Promise.resolve();
}
function viewTransitionIn(){
  const v = document.getElementById('view');
  if(!v) return;
  v.classList.remove('mf-enter');
  void v.offsetWidth;
  v.classList.add('mf-enter');
}

let NAV_SEQ=0;
/* 永远不把已有内容清空：旧页面一直留到新页面算好之后一次性换掉。
   换页时短暂显示上一页，比整页白一下再长出来要稳。 */
function viewLoading(){
  const v = $('#view'); if(!v || v.children.length) return;
  v.innerHTML = '<div class="loading-bar"></div>';
}
window.viewLoading = viewLoading;

const nav = {
  go(id, extra){
    // editor.js 注册的未保存守卫；没有编辑器在场时它永远返回 true
    if(window.navGuardAsk && !window.navGuardAsk()) return;
    let hash = '#/'+id;
    if(extra) hash += '/'+extra;
    if(location.hash === hash){ nav.resolve(); return; }
    location.hash = hash;
  },
  resolve(){
    const seq=++NAV_SEQ;
    let raw = (location.hash||'').replace(/^#\/?/,'');
    if(!raw) raw = 'pipelines';
    const [view, ...rest] = raw.split('/');
    const extra = rest.join('/');
    viewTransitionOut().then(async ()=>{
      if(seq!==NAV_SEQ) return;
      window.__chrome = {title:'', icon:'flow', actions:''};
      const v = $('#view'); if(v) v.classList.remove('with-composer');
      if(view!=='settings') delete $('#app').dataset.shell;
      const run = async (fn, key)=>{ await fn(); renderNav(key); paintChrome(); };
      if(view==='skills') await run(window.renderSkills,'skills');
      else if(view==='skill-edit') await run(()=>window.renderSkillEdit(extra),'skills');
      else if(view==='pipelines') await run(window.renderPipelines,'pipelines');
      else if(view==='pipeline-edit') await run(()=>window.renderPipelineEdit(extra),'pipelines');
      else if(view==='settings') await run(()=>renderSettings(extra),'settings');
      else if(view==='runs') await run(window.renderRuns,'runs');
      else if(view==='run') await run(()=>window.renderRunConsole(extra),'runs');
      else await run(window.renderPipelines,'pipelines');   /* 含旧的 #/home：一律落到工作流 */
      if(seq===NAV_SEQ){ viewTransitionIn(); renderSidebarLists(); }
    });
  },
};
window.nav = nav;
window.addEventListener('hashchange', ()=>nav.resolve());

/* ---------------- 下任务 ---------------- */
window.taskModal = async function(presetFlow){
  const pr = await api('/api/pipelines').catch(()=>({pipelines:[]}));
  const tpls = pr.pipelines||[];
  if(!tpls.length){ toast(t('task.noFlow')); nav.go('pipeline-edit/new'); return; }
  document.body.style.overflow='hidden';
  const root = document.createElement('div');
  root.id='taskModalRoot';
  const cur = tpls.find(p=>p.name===(presetFlow||tpls[0].name)) || tpls[0];
  const cps = (cur.steps||[]).filter(st=>st.checkpoint).length;
  root.innerHTML = `<div class="modal open" role="dialog" aria-label="${esc(t('task.title'))}"
      onclick="if(event.target===this)taskClose()">
    <div class="tk-stage">
      <h2 class="tk-greet">${esc(t('tk.greet'))}</h2>
      <div class="tk-card">
        <div class="tk-top">
          ${ffSelect(tpls.map(p=>({v:p.name, label:(p.label||p.name)+' · '+p.steps.length+' '+t('c.steps')})),
                     presetFlow||tpls[0].name, {id:'tkFlow', onChange:'tkHint'})}
          <span class="tk-meta">${cps ? esc(t('tk.cps',{n:cps})) : esc(t('tk.noCp'))}</span>
        </div>
        <div class="tk-field">
          <textarea class="tk-input" id="tkBrief" rows="4" placeholder="${esc(t('task.briefPh'))}"
            oninput="tkHint()"></textarea>
        </div>
        <div class="tk-foot">
          <input class="tk-name" id="tkLabel" placeholder="${esc(t('task.labelPh'))}">
          <button class="cp-send" onclick="taskStart()" aria-label="${esc(t('task.start'))}"
            title="${esc(t('task.start'))}">${ico('send')}</button>
        </div>
      </div>
      <div class="tk-hint" id="tkHintBox">${esc(t('task.briefHint'))}</div>
      <div class="tk-sugs" id="tkSugs">
        <div class="tk-sug-head"><span>${esc(t('tk.tryThese'))}</span><span class="spacer"></span>
          <button class="tk-op" onclick="tkShuffle()">${esc(t('tk.shuffle'))}</button>
          <button class="tk-op" aria-label="${esc(t('c.close'))}" onclick="tkHideSugs()">${ico('close')}</button></div>
        <div id="tkSugList"></div>
      </div>
    </div></div>`;
  document.body.appendChild(root);
  tkPaintSugs();          // 必须在挂进文档之后：里面靠 getElementById 找容器，提前调是查空的
  setTimeout(()=>{ const b=document.getElementById('tkBrief'); if(b) b.focus(); }, 60);
};
function tkHint(){
  const hint = document.getElementById('tkHintBox');
  if(!hint) return;
  const brief = ((document.getElementById('tkBrief')||{}).value||'').trim();
  hint.textContent = (brief.length>0 && brief.length<20) ? t('task.briefShort') : t('task.briefHint');
  hint.style.color = (brief.length>0 && brief.length<20) ? 'var(--warn)' : '';
}
window.tkHint = tkHint;
const TK_SUG_KEYS = ['tk.sug1','tk.sug2','tk.sug3','tk.sug4','tk.sug5','tk.sug6'];
const TK_SUG_ICONS = ['search','file','chart','play','edit','flag'];
let TK_SUG_OFF = 0;
function tkPaintSugs(){
  const box = document.getElementById('tkSugList'); if(!box) return;
  box.innerHTML = [0,1,2].map(i => {
    const k = TK_SUG_KEYS[(TK_SUG_OFF+i) % TK_SUG_KEYS.length];
    const ic = TK_SUG_ICONS[(TK_SUG_OFF+i) % TK_SUG_ICONS.length];
    return `<button class="tk-sug" onclick="tkUseSug(this)"><span>${ico(ic)}</span>${esc(t(k))}</button>`;
  }).join('');
}
window.tkShuffle = function(){ TK_SUG_OFF = (TK_SUG_OFF+3) % TK_SUG_KEYS.length; tkPaintSugs(); };
window.tkHideSugs = function(){ const b=document.getElementById('tkSugs'); if(b) b.remove(); };
window.tkUseSug = function(btn){
  const ta = document.getElementById('tkBrief'); if(!ta) return;
  ta.value = btn.textContent.trim(); ta.focus(); tkHint();
};
window.taskClose = function(){
  const r=document.getElementById('taskModalRoot'); if(r) r.remove();
  document.body.style.overflow='';
};
window.taskStart = async function(){
  const flow = (document.getElementById('tkFlow')||{}).value||'';
  const brief = ((document.getElementById('tkBrief')||{}).value||'').trim();
  const label = ((document.getElementById('tkLabel')||{}).value||'').trim();
  if(!brief){ toast(t('task.needBrief')); return; }
  const r = await post('/api/pipelines/'+encodeURIComponent(flow)+'/run', {brief, label})
    .catch(e=>({detail:String(e)}));
  if(r.detail){ toast(r.detail); return; }
  taskClose();
  toast(t('task.started'), true);
  nav.go('run/'+r.run.id);
};
window.plRun = async function(name){ taskModal(name); };

/* ================= 设置：Codex 式两栏外壳 ================= */
const SET_SECTIONS = [
  {grp:'set.grp.pref', items:[['appearance','set.appearance','appearance'],
                              ['shortcuts','set.shortcuts','keyboard']]},
  {grp:'set.grp.exec', items:[['engines','set.engines','agent'],['presets','set.presets','api'],
                              ['runtime','set.runtime','runtime'],['caps','set.caps','layers']]},
  {grp:'set.grp.data', items:[['dirs','set.dirs','folder'],['stats','set.stats','chart'],
                              ['update','set.update','download'],['about','set.about','info']]},
];
let SET_SECTION = 'appearance';
let SET_Q = '';
let PATH_EDIT = '';

const srow = (title, desc, ctl, extra='') => `
  <div class="st-row" data-k="${esc(((title||'')+' '+(desc||'')+' '+extra).toLowerCase())}">
    <div class="st-row-main"><div class="st-t">${title}</div>
      ${desc?`<div class="st-d">${desc}</div>`:''}</div>
    <div class="st-ctl">${ctl||''}</div>
  </div>`;
/* 统计页用"卡片内标题"，别的分区用"卡片上方那行分组标签" —— 参考图里那张屏没有分组标签 */
const stCard = (title, rows) => `<div class="st-block"><div class="st-panel">`
  + (title ? `<div class="st-pttl">${esc(title)}</div>` : '') + rows + `</div></div>`;
const spanel = (rows, label='', actions='') => `
  <div class="st-block">${label || actions ? `<div class="st-labelrow">
      ${label ? `<div class="st-label">${esc(label)}</div>` : '<span></span>'}
      ${actions ? `<div class="st-label-acts">${actions}</div>` : ''}</div>` : ''}
    <div class="st-panel">${rows}</div></div>`;
/* 标题带说明在上、输入框整行铺开在卡片内；宽度归容器，不用内联 style 凑 */
const stIn = (title, desc, id, val, ph, saveFn, extra='', mono=true, acts='') => `
  <div class="st-row" data-k="${esc(((title||'')+' '+(desc||'')+' '+extra).toLowerCase())}">
    <div class="st-row-main"><div class="st-t">${title}</div>
      ${desc?`<div class="st-d">${desc}</div>`:''}</div>
    <div class="st-ctl"><button class="st-btn" onclick="${saveFn}">${esc(t('c.save'))}</button>${acts}</div>
  </div>
  <div class="st-rowsub"><input class="st-input${mono?' mono':''}" id="${id}"
    placeholder="${esc(ph||'')}" value="${esc(val||'')}"></div>`;
/* 一整块控件（磁贴 / 色板）放不下右侧的，就自己占一行铺在标题下面 */
const sblk = (title, desc, body, extra='') => `
  <div class="st-row st-row-col" data-k="${esc(((title||'')+' '+(desc||'')+' '+extra).toLowerCase())}">
    <div class="st-row-main"><div class="st-t">${title}</div>
      ${desc?`<div class="st-d">${desc}</div>`:''}</div>${body}</div>`;
/* 设置页的「多选一」：跟 ssel 同一个盒子形状，只是还能带一个参数（语言/引擎按行切换） */
const sseg = (opts, cur, fn, arg) => ffSelect(opts.map(([v,l])=>({v, label:l})), cur,
  {onChange:(v)=>{ const f=window[fn]; if(f){ if(arg) f(arg,v); else f(v); } }});
const ssel = (opts, cur, fn) => ffSelect(opts.map(([v,l])=>({v,label:l})), cur, {onChange:fn});
const ssw = (on, fn) => `<label class="switch"><input type="checkbox" ${on?'checked':''}
  onchange="swPick(this,'${fn}')"><span class="slider"></span></label>`;
window.swPick = function(el, fn){ const f=window[fn]; if(f) f(el.checked); };
const schips = (items) => `<div class="st-chips">${items.map(x=>
  `<span class="st-chip">${esc(x)}</span>`).join('')}</div>`;
const skey = (k) => `<kbd class="st-kbd">${esc(k)}</kbd>`;

/* 1rem 的基准像素，和 style.css 里 html{font-size:calc(13px * var(--text-scale))} 对齐
   （tests/test_static_contract.py 钉住两边一致）。滑块读数要说「人话」就得靠它换算。 */
const ROOT_PX = 13;
const SL_OPTS = {
  textSize: () => Object.keys(window.AP_OPTS.TEXT_SIZES),
  uiZoom: () => Object.keys(window.AP_OPTS.ZOOMS),
  contentWidth: () => Object.keys(window.AP_OPTS.WIDTHS),
};
const SL_LBL = { textSize:'ap.textSize', uiZoom:'ap.zoom', contentWidth:'ap.width' };
function apValText(key, v){
  const O = window.AP_OPTS;
  if(key==='textSize') return t('ap.size.'+v)+' · '+Math.round(ROOT_PX*O.TEXT_SIZES[v])+'px';
  if(key==='uiZoom') return v;
  return v==='full' ? t('ap.width.full') : t('ap.width.'+v)+' · '+O.WIDTHS[v];
}
const sslider = (key, cur) => {
  const opts = SL_OPTS[key]();
  const i = Math.max(0, opts.indexOf(cur));
  return `<div class="st-slider">
    <input type="range" class="st-range" min="0" max="${opts.length-1}" step="1" value="${i}"
      aria-label="${esc(t(SL_LBL[key]))}" data-sk="${key}"
      oninput="slPick('${key}',this.value)" onchange="slPick('${key}',this.value,1)">
    <span class="st-slider-val" data-sv="${key}">${esc(apValText(key, cur))}</span></div>`;
};
/* 拖动只改内存（oninput），松手才落盘（onchange）：落盘走 apSet，不重渲染整页。 */
window.slPick = function(key, i, commit){
  const v = SL_OPTS[key]()[Number(i)];
  if(!v) return;
  const out = document.querySelector('[data-sv="'+key+'"]');
  if(out) out.textContent = apValText(key, v);
  if(commit) window.apSet(key, v); else window.previewAppearance({[key]: v});
};

const apTiles = () => `<div class="st-tiles" id="stTiles">${window.AP_OPTS.THEMES.map(v=>{
  const on = window.APP.theme===v;
  return `<button type="button" class="st-tile${on?' active':''}" data-v="${v}"
    aria-pressed="${on?'true':'false'}" onclick="apTile('${v}')">
    <span class="st-tile-prev" data-prev="${v}"></span>
    <span class="st-tile-name">${esc(t('ap.theme.'+v))}</span></button>`;}).join('')}</div>`;
const apSwatches = () => `<div class="st-swatches" id="stAcc">${window.AP_OPTS.ACCENTS.map(v=>{
  const on = window.APP.accent===v;
  return `<button type="button" class="st-swatch${on?' active':''}" data-v="${v}"
    aria-pressed="${on?'true':'false'}" onclick="apAccent('${v}')">
    <i class="sw-dot sw-${v}"></i><span>${esc(t('ap.accent.'+v))}</span></button>`;}).join('')}</div>`;
/* 磁贴/色板点了不能重渲染：整页重绘会丢滚动位置，也让 CSS 变量看起来「闪」了一下 */
window.apTile = function(v){ pickIn('#stTiles', 'st-tile', 'theme', v); };
window.apAccent = function(v){ pickIn('#stAcc', 'st-swatch', 'accent', v); };
function pickIn(sel, cls, key, v){
  document.querySelectorAll(sel+' .'+cls).forEach(b=>{
    const on = b.dataset.v===v;
    b.classList.toggle('active', on);
    b.setAttribute('aria-pressed', on ? 'true' : 'false');
  });
  window.apSet(key, v);
}
window.apReset = async function(){
  await window.setAppearance({theme:'dark', font:'default', accent:'blue',
    textSize:'m', uiZoom:'100%', contentWidth:'medium'});
  toast(t('ap.resetDone'), true);
  renderSettings(SET_SECTION);
};

function secAppearance(){
  const A = window.APP;
  const lang = spanel([
    srow(t('ap.language'), t('ap.languageD'),
      sseg([['zh','中文'],['en','English']], A.lang, 'apSet', 'lang'), 'language locale'),
  ].join(''), t('ap.grpLang'));
  const look = spanel([
    sblk(t('ap.theme'), t('ap.themeD'), apTiles(), 'theme dark light system 明暗'),
    srow(t('ap.font'), t('ap.fontD'),
      ssel(window.AP_OPTS.FONTS.map(v=>[v,t('ap.font.'+v)]), A.font, 'apSetFont'), 'font typeface'),
    sblk(t('ap.accent'), t('ap.accentD'), apSwatches(), 'accent colour color blue gold'),
  ].join(''), t('ap.grpLook'));
  const size = spanel([
    srow(t('ap.textSize'), t('ap.textSizeD'), sslider('textSize', A.textSize), 'text size font 字号'),
    srow(t('ap.zoom'), t('ap.zoomD'), sslider('uiZoom', A.uiZoom), 'zoom scale ui 缩放'),
    srow(t('ap.width'), t('ap.widthD'), sslider('contentWidth', A.contentWidth), 'width content 宽度'),
  ].join(''), t('ap.grpSize'));
  const pv = spanel(
    `<div class="st-preview">
       <div class="spv-title">${esc(t('ap.pvTitle'))}</div>
       <div class="spv-body">${esc(t('ap.pvBody'))}</div>
       <div class="spv-code">${esc(t('ap.pvCode'))}</div>
       <div class="spv-meta">${esc(t('ap.pvMeta'))}</div>
     </div>`, t('ap.grpPreview'),
    `<button class="st-btn" onclick="apReset()">${esc(t('ap.reset'))}</button>`);
  return lang + look + size + pv;
}

function secEngines(){
  const engRows = ST.agents.map(a=>{
    const isDef = ST.defaultEngine===a.engine;
    const bits = [];
    if(a.version) bits.push(t('eng.ver',{v:a.version}));
    if(a.needs) bits.push(t('eng.need',{n:a.needs}));
    const ctl = a.found
      ? `<span class="st-state ok"><i></i>${esc(t('eng.ready'))}</span>
         ${isDef?`<span class="sk-badge sk-badge-user">${esc(t('eng.defaultTag'))}</span>`:''}`
      : `<span class="st-state no"><i></i>${esc(t('eng.missing'))}</span>`;
    return srow(t('eng.'+a.engine), esc(t('eng.'+a.engine+'D'))
      + (bits.length?`<div class="st-d2">${esc(bits.join(' · '))}</div>`:''), ctl, a.engine+' cli binary agent default');
  }).join('');
  const head = srow(t('eng.default'), t('eng.defaultD'),
    sseg([['', t('eng.auto')]].concat(ST.agents.map(a=>[a.engine,t('eng.'+a.engine)]))
      , ST.defaultEngine, 'setDefaultEngine'), 'default engine');
  const paths = ST.agents.map(a=>{
    const cur = a.engine==='claude'?(ST.claudeCli||''):(ST.codexCli||'');
    const title = esc(t('eng.pathFor',{e:t('eng.'+a.engine)}));
    if(PATH_EDIT===a.engine){
      return stIn(title, t('eng.pathD'), 'path_'+a.engine, cur, t('eng.pathPh'),
                  "savePath('"+a.engine+"')", a.engine+' path binary', true,
                  `<button class="st-btn" onclick="cancelPath()">${esc(t('c.cancel'))}</button>`);
    }
    return srow(title, t('eng.pathD'),
      `<span class="st-val st-val-path">${esc(cur || a.bin || t('eng.auto'))}</span>
       <button class="st-btn" onclick="editPath('${a.engine}')">${esc(t('eng.change'))}</button>`, a.engine+' path binary');
  }).join('');
  return spanel(head + engRows, t('eng.grpEngines')) + spanel(paths, t('eng.grpBinary'));
}

function secPresets(){
  const rows = PRESETS.map(p=>{
    const disp = (p.extra&&p.extra.display_name)||p.name;
    const prov = (p.provider||'openai')==='anthropic'?'Anthropic':'OpenAI';
    const bits = [prov, p.api_base||'—']; if(p.model) bits.push(p.model);
    if(p.key_hint) bits.push(p.key_hint);   // 清单里不再有 api_key，只回末四位
    return srow(esc(disp), esc(bits.join(' · ')),
      `${p.is_default?`<span class="sk-badge sk-badge-user">${esc(t('pr.inUse'))}</span>`
        :`<button class="st-btn" onclick="pfSetDefault(${p.id})">${esc(t('eng.setDefault'))}</button>`}
       <button class="st-btn" onclick="pfTest(${p.id})">${esc(t('pr.test'))}</button>
       <button class="st-btn" onclick="pfEdit(${p.id})">${esc(t('c.edit'))}</button>
       <button class="st-btn st-btn-danger" ${p.is_default?'disabled':''} onclick="pfDel(${p.id})">${esc(t('c.delete'))}</button>`,
      disp+' preset endpoint key model protocol');
  }).join('');
  const list = spanel((rows || srow(t('pre.none'), t('pre.desc'), '', 'preset none empty'))
    + srow(t('pr.add'), '',
        `<button class="st-btn" onclick="pfOpenNew()"><span class="btn-plus">＋</span> ${esc(t('pr.add'))}</button>`,
        'preset add new endpoint'), t('pre.grpList'));
  const gate = spanel(
    srow(t('pre.gate'), t('pre.gateD'),
      schips(['claude ↔ Anthropic', 'codex ↔ OpenAI']), 'protocol gate anthropic openai'),
    t('pre.grpGate'));
  return list + gate;
}

function secRuntime(){
  const mins = [['300','5'],['600','10'],['900','15'],['1800','30'],['2700','45'],['3600','60'],['7200','120']]
    .map(([v,l])=>[v, l+' '+t('rt.timeoutMin')]);
  const sb = (ST.sandboxOptions||['workspace-write']).map(v=>[v,v]);
  const ef = (ST.effortOptions||['auto']).map(v=>[v,t('rt.effort.'+v)]);
  const rt = [0,1,2,3].map(v=>[String(v), v? t('rt.retryTimes',{n:v}) : t('rt.retryNone')]);
  return spanel(
    srow(t('rt.timeout'), t('rt.timeoutD'), ssel(mins, ST.agentTimeout||'2700', 'saveTimeout'), 'timeout limit seconds step')
    + srow(t('rt.retry'), t('rt.retryD'), sseg(rt, ST.stepRetry||'0', 'saveRetry'), 'retry fail times')
    + srow(t('rt.effort'), t('rt.effortD'), sseg(ef, ST.reasoningEffort||'auto', 'saveEffort'), 'reasoning effort think codex')
    + srow(t('rt.sandbox'), t('rt.sandboxD'), ssel(sb, ST.codexSandbox, 'saveSandbox'), 'sandbox codex permission')
    + srow(t('rt.auto'), t('rt.autoD'), ssw(ST.autoContinue==='1', 'saveAutoContinue'), 'checkpoint auto continue pause'),
    t('rt.grpPolicy'));
}

function secDirs(){
  const P = ST.paths||{};
  const row = (k,title,desc) => srow(title, desc,
    `<span class="st-val st-val-path">${esc(P[k]||'—')}</span>
     <button class="st-btn" onclick="revealDir('${k}')">${esc(t('dir.open'))}</button>`, title+' folder path directory');
  return spanel(
    row('data',t('dir.data'),t('dir.dataD'))
    + row('skills',t('dir.skills'),t('dir.skillsD'))
    + row('workspaces',t('dir.workspaces'),t('dir.workspacesD'))
    + srow(t('dir.runs'), t('dir.runsD',{n:(ST.runs||[]).length}),
        `<button class="st-btn" onclick="setExit('runs')">${esc(t('c.view'))}</button>`, 'runs history record'),
    t('dir.grpFolders'));
}

function secShortcuts(){
  /* 作用域是真实差异，不是装饰：Ctrl K/B/, 和 Esc 在哪都能按，/ 只在设置页生效，
     Enter 只在输入框里有意义。以前混成一张表，得读说明文字才知道作用范围。
     没有做「操作」列 —— 键位是 app.js 里硬编码的，不能重绑，放假按钮没意义。 */
  const rows = [
    ['Ctrl K', t('sc.newTask'), t('sc.newTaskD'), 'g', 'shortcut new task'],
    ['Ctrl B', t('sc.toggleSb'), t('sc.toggleSbD'), 'g', 'shortcut sidebar toggle'],
    ['Ctrl ,', t('sc.settings'), t('sc.settingsD'), 'g', 'shortcut settings'],
    ['Esc', t('sc.close'), t('sc.closeD'), 'g', 'shortcut close escape'],
    ['/', t('sc.search'), t('sc.searchD'), 's', 'shortcut search focus'],
    ['Enter', t('sc.send'), t('sc.sendD'), 'i', 'shortcut send enter revise'],
  ].map(([k,tt,d,sc,x])=>`<div class="sc-tr" data-k="${esc((tt+' '+k+' '+x+' '+t('sc.scope.'+sc)).toLowerCase())}">
      <div class="sc-td"><span class="sc-name">${esc(tt)}</span>
        <span class="sc-desc">${esc(d)}</span></div>
      <div class="sc-td sc-td-k"><span class="st-keys">${k.split(' ').map(skey).join('')}</span></div>
      <div class="sc-td sc-td-s"><span class="sc-scope sc-scope-${sc}">${esc(t('sc.scope.'+sc))}</span></div>
    </div>`).join('');
  return `<div id="scBox">
    <div class="st-scq">${ico('search')}
      <input id="scQ" placeholder="${esc(t('sc.searchPh'))}" oninput="scFilter(this.value)"
        ${SET_Q.trim() ? 'disabled' : ''}></div>
    <div class="sc-card">
      <div class="sc-tr sc-thead">
        <div class="sc-td">${esc(t('sc.colCmd'))}</div>
        <div class="sc-td sc-td-k">${esc(t('sc.colKey'))}</div>
        <div class="sc-td sc-td-s">${esc(t('sc.colScope'))}</div>
      </div>
      ${rows}
    </div>
    <div class="st-empty st-hidden">${esc(t('sc.noHit'))}</div></div>`;
}
/* 键位页自己的过滤器：整页搜索会把别的分区一起摊开，找一个 Esc 不该看六张卡 */
window.scFilter = function(q){
  const box = document.getElementById('scBox');
  if(!box) return;
  if(SET_Q.trim()) return;   // 整页搜索在管这张表（框渲染时就 disable 了），两个过滤器别抢同一批行
  const s = (q||'').trim().toLowerCase();
  let n = 0;
  box.querySelectorAll('.sc-tr:not(.sc-thead)').forEach(r=>{
    const on = !s || (r.dataset.k||'').includes(s);
    r.classList.toggle('st-hidden', !on);
    if(on) n++;
  });
  const e = box.querySelector('.st-empty');
  if(e) e.classList.toggle('st-hidden', n>0);
};

function upStatusText(s){
  if(!s) return t('up.unknown');
  const m = {checking:t('up.checking'), available:t('up.hasNew',{v:s.latest}),
             current:t('up.isCurrent',{v:s.local}), downloading:t('up.downloadingPct',
               {p: s.size?Math.floor((s.got||0)*100/s.size):0}),
             ready:t('up.readyTip',{p:s.path||''}), error:t('up.errPrefix',{e:s.error||''})};
  return m[s.phase] || t('up.idle');
}

function secUpdate(){
  const u = ST.update || {};
  const apply = u.frozen
    ? `<button class="st-btn" onclick="applyUpdate()" ${u.phase==='ready'?'':'disabled'}>${esc(t('up.apply'))}</button>`
    : `<span class="st-state no"><i></i>${esc(t('up.applyNo'))}</span>`;
  /* 下载中给一条真刻度条：数字来自 got/size，和左下角胶囊同一份状态，不是装饰 */
  const pct = u.phase==='ready' ? 100
    : (u.phase==='downloading' && u.size) ? Math.floor((u.got||0)*100/u.size) : -1;
  const bar = pct < 0 ? '' : `<div class="st-prog"><i style="width:${pct}%"></i></div>`;
  return spanel(
      stIn(t('up.url'), t('up.urlD'), 'upUrl',
        (u.update_url===u.default_url ? '' : (u.update_url||'')), t('up.urlPh'),
        'saveUpdUrl()', 'update manifest url cos')
    + srow(t('up.status'), t('up.statusD',{v:u.local||''}),
        `<span class="st-val">${esc(upStatusText(u))}</span>${bar}
         <button class="st-btn" onclick="checkNow()">${ico('refresh')}${esc(t('up.check'))}</button>`,
        'update check version status progress')
    + srow(t('up.apply'), t('up.applyD'), apply, 'update install apply'),
    t('up.grp'));
}

window.applyUpdate = async function(){
  const u = ST.update || {};
  if(!confirm(t('up.applyGo', {v: u.latest || ''}))) return;
  const r = await post('/api/update/apply').catch(e=>({ok:false, detail:String(e)}));
  // 成功时后端也带 detail（"正在安装并退出…"），所以只能按 ok 判，不能按有没有 detail 判
  if(r && r.ok === false){ toast(r.detail, false); return; }
  toast((r && r.detail) || t('up.applyStarted'), true);
};

const MB1024 = 1048576;
const fmtBytes = n => n >= MB1024 ? (n/MB1024).toFixed(1)+' MB'
                     : n >= 1024  ? (n/1024).toFixed(0)+' KB' : (n||0)+' B';
function fmtDur(ms){
  const s = Math.round((ms||0)/1000);
  if ((window.APP && window.APP.lang) === 'en') {
    if (s < 60) return s+'s';
    const h = Math.floor(s/3600), m = Math.floor((s%3600)/60);
    return h ? h+'h '+m+'m' : m+'m '+(s%60)+'s';
  }
  // 中文里 "7h 2m" 读不成一句话；参考图写的是 "7 小时 2 分钟"
  if (s < 60) return s + ' ' + t('unit.sec');
  const h = Math.floor(s/3600), m = Math.floor((s%3600)/60), sec = s % 60;
  if (h) return m ? h+' '+t('unit.hour')+' '+m+' '+t('unit.min') : h+' '+t('unit.hour');
  return sec ? m+' '+t('unit.min')+' '+sec+' '+t('unit.sec') : m+' '+t('unit.min');
}
/* 亿/万只在中文用，英文走 K/M —— 直接写死一套单位会在另一语言里读不通 */
function fmtTok(n){
  n = n || 0;
  const zh = (window.APP && window.APP.lang) !== 'en';
  if (zh) {
    if (n >= 1e8) return (n/1e8).toFixed(1) + ' ' + t('unit.yi');
    if (n >= 1e4) return (n/1e4).toFixed(1) + ' ' + t('unit.wan');
    return String(n);
  }
  if (n >= 1e6) return (n/1e6).toFixed(1) + 'M';
  if (n >= 1e3) return (n/1e3).toFixed(1) + 'K';
  return String(n);
}
/* 热力图：一格一天，按列铺、每列 7 格。起始补空格把日期对齐到周日，
   否则格子会随数据量左右错位，看不出周节律。 */
/* 统计页的两个视图开关只作用于这一分区，不写进外观通道（那是要落库的全局偏好），
   所以刷新页面回到默认。切档与切范围都只重渲染这块，不重新拉接口。 */
let ST_MODE = 'day';
let ST_RANGE = 7;
const HM_WEEKS = 52;        /* 52 列 × 15px 节距 = 780，正好铺满设置页那张卡的宽度。
                               锚点取"今天那一周的周日"往回数 51 周，列数恒定 52；
                               以前按天数换算再补一周，非周日收尾时会多出第 53 列把网格顶出卡片。 */

const stSeg = (opts, cur, fn) => `<div class="st-seg" role="group">`
  + opts.map(([v, l]) => `<button type="button" class="st-segb"
      aria-pressed="${v === cur ? 'true' : 'false'}" onclick="${fn}('${v}')">${esc(l)}</button>`)
      .join('') + `</div>`;

const hmKey = d => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;

function stDateLong(iso){
  const p = iso.split('-');
  return (window.APP && window.APP.lang) === 'en'
    ? `${t('mon.'+(+p[1]-1))} ${+p[2]}, ${p[0]}`
    : `${p[0]}年${+p[1]}月${+p[2]}日`;
}

/* 三档共用同一套格子，只有读数不同 —— 周视图塌成一行反而看不出周节律，所以整列同色。
   后端按本地日期入库（time.strftime("%Y-%m-%d")），这里绝不能用 toISOString ——
   那是 UTC，UTC+8 下每格都会读成前一天，"今天"永远是空的。 */
function hmValues(daily, mode){
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const start = new Date(today); start.setDate(start.getDate() - (HM_WEEKS - 1) * 7);
  start.setDate(start.getDate() - start.getDay());
  const cols = [];
  for (let w = 0; w < HM_WEEKS; w++){
    const one = [];
    for (let i = 0; i < 7; i++){
      const d = new Date(start); d.setDate(d.getDate() + w*7 + i);
      one.push(d > today ? null : hmKey(d));
    }
    cols.push(one);
  }
  const day = {}, week = {}, cum = {};
  let run = 0;
  cols.forEach(one => {
    let wk = 0;
    one.forEach(iso => { if(!iso) return;
      const v = ((daily||{})[iso]||{}).tokens || 0;
      day[iso] = v; wk += v; run += v; cum[iso] = run; });
    one.forEach(iso => { if(iso) week[iso] = wk; });
  });
  return { cols, val: mode === 'week' ? week : mode === 'cum' ? cum : day };
}

function tokenHeat(daily, mode){
  const m = mode || 'day';
  const hv = hmValues(daily, m);
  const cols = hv.cols, val = hv.val;
  const vals = Object.values(val).filter(v => v > 0).sort((a, b) => a - b);
  const q = f => vals.length ? vals[Math.min(vals.length-1, Math.floor(vals.length*f))] : 0;
  const t1 = q(.25), t2 = q(.5), t3 = q(.75);
  const lvl = v => !v ? 0 : v <= t1 ? 1 : v <= t2 ? 2 : v <= t3 ? 3 : 4;
  const grid = cols.map(one => '<div class="hm-col">' + one.map(iso => {
    if (!iso) return '<i class="hm-cell hm-out"></i>';
    const v = val[iso] || 0, e = (daily||{})[iso] || {};
    // 悬停走自研提示：原生 title 有一秒延迟、样式跟系统、而且只能一行。
    // 两行之间用 &#10; 分隔 —— 属性值里的裸换行会被归一化成空格。
    const l1 = m === 'week' ? `${stDateLong(one[0])} – ${stDateLong(one[6] || one[0])}` : stDateLong(iso);
    const l2 = m === 'cum' ? `${esc(t('st.cumTo'))} ${fmtTok(v)} tokens`
                           : `${fmtTok(v)} tokens · ${e.turns || 0} ${esc(t('st.msgs'))}`;
    return `<i class="hm-cell ${'hm-l'+lvl(v)}" data-tip-any="1" data-tip="${esc(l1)}&#10;${l2}"></i>`;
  }).join('') + '</div>').join('');
  // 月份轴和列在同一个循环里产出。以前是两套循环各数各的，
  // 27 对 27 只是巧合，谁动一边轴就会整体错位。
  // 标签槽只有 12px（文字靠 nowrap 溢出），所以两档之间至少隔两列才放得下 ——
  // 一年里唯一撞车的就是窗口起点：9 月中开、下一周就跨进 10 月。
  const axis = []; let lastM = -1, lastCol = -9;
  cols.forEach((one, w) => {
    const sun = one[0];
    const mo = sun ? +sun.split('-')[1] - 1 : -1;
    if (sun && mo !== lastM && w - lastCol >= 2){
      axis.push(`<span class="hm-mo">${esc(t('mon.'+mo))}</span>`);
      lastM = mo; lastCol = w;
    } else axis.push('<span class="hm-mo"></span>');
  });
  // 网格和轴必须在同一个横向滚动容器里，否则网格一滚，轴留在原地就对不上列了
  return `<div class="hm-wrap"><div class="hm-grid">${grid}</div>
      <div class="hm-axis">${axis.join('')}</div></div>`;
}

function stNoData(){
  return `<div class="st-nodata"><b>${esc(t('st.noData'))}</b>
    <span>${esc(t('st.noDataD'))}</span></div>`;
}

/* 手写 SVG 柱状：不引图表库（无构建步骤 + 离线跑），viewBox 归一到 100×46 由 CSS 拉宽 */
function stTrend(daily, range){
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const days = [];
  for (let i = range - 1; i >= 0; i--){ const d = new Date(today); d.setDate(d.getDate() - i); days.push(hmKey(d)); }
  const vals = days.map(k => ((daily||{})[k]||{}).tokens || 0);
  if (!vals.some(v => v > 0)) return stNoData();
  const mx = Math.max.apply(null, vals.concat([1]));
  const bw = 100 / days.length;
  const bars = days.map((k, i) => {
    const h = vals[i] > 0 ? Math.max(1.6, 46 * vals[i] / mx) : 0.8;
    return `<rect class="${vals[i] > 0 ? 'st-tb' : 'st-tb0'}" x="${(i*bw + bw*0.16).toFixed(2)}" `
      + `y="${(46-h).toFixed(2)}" width="${(bw*0.68).toFixed(2)}" height="${h.toFixed(2)}"></rect>`;
  }).join('');
  return `<svg class="st-chart" viewBox="0 0 100 46" preserveAspectRatio="none" role="img" `
    + `aria-label="${esc(t('st.trendAria'))}">${bars}</svg>`
    + `<div class="st-cx"><span>${esc(stDateLong(days[0]))}</span>`
    + `<span>${esc(stDateLong(days[days.length-1]))}</span></div>`;
}

function stModels(list){
  const rows = (list || []).filter(b => b && (b.tokens || b.steps));
  if (!rows.length) return stNoData();
  const mx = Math.max.apply(null, rows.map(b => b.tokens || 0).concat([1]));
  const total = rows.reduce((a, b) => a + (b.tokens || 0), 0) || 1;
  return rows.map(b => `<div class="st-mrow">
      <span class="st-mname mono">${esc((b.engine || '?') + ' · ' + (b.model || t('st.noModelInjected')))}</span>
      <span class="st-mtrack"><i style="width:${Math.max(1, (b.tokens||0)/mx*100).toFixed(1)}%"></i></span>
      <span class="st-mval">${esc(fmtTok(b.tokens))} · ${Math.round((b.tokens||0)/total*100)}%</span></div>`).join('');
}


function secStats(){
  const s = ST.stats || {};
  const bs = s.by_status || {};
  const pw = Object.entries(s.per_workflow || {}).sort((a,b)=>b[1]-a[1]);
  const orphans = s.orphans || [];
  const orphanBytes = orphans.reduce((a,o)=>a+(o.bytes||0), 0);
  const tk = s.tokens || {};
  const strip = `<div class="st-strip">
    <div><b>${esc(fmtTok(s.tokens_total))}</b><span>${esc(t('st.tokTotal'))}</span></div>
    <div><b>${esc(fmtTok(s.peak_day_tokens))}</b><span>${esc(t('st.peakDay'))}</span></div>
    <div><b>${esc(fmtDur(s.peak_step_ms))}</b><span>${esc(t('st.peakStep'))}</span></div>
    <div><b>${(s.streak_now||0)+' '+t('unit.day')}</b><span>${esc(t('st.streakNow'))}</span></div>
    <div><b>${(s.streak_best||0)+' '+t('unit.day')}</b><span>${esc(t('st.streakBest'))}</span></div>
  </div>`;
  const heat = stCard('',
      `<div class="st-cardtop"><div class="hm-title">${esc(t('st.heat'))}</div>`
        + stSeg([['day', t('st.modeDay')], ['week', t('st.modeWeek')], ['cum', t('st.modeCum')]],
                ST_MODE, 'stSetMode') + `</div>`
      + tokenHeat(s.daily || {}, ST_MODE));
  const rangeRow = `<div class="st-rangerow"><span>${esc(t('st.range'))}</span>`
    + stSeg([['7', t('st.last7')], ['30', t('st.last30')]], String(ST_RANGE), 'stSetRange')
    + `</div>`;
  const trend = stCard(t('st.trend'), stTrend(s.daily || {}, ST_RANGE));
  const models = stCard(t('st.models'), stModels(s.by_model));
  const usage = stCard(t('st.grpUsage'),
      srow(t('st.runs'), t('st.runsD',{done:bs.done||0, failed:bs.failed||0,
          running:(bs.running||0)+(bs.revising||0), waiting:bs.waiting||0,
          cancelled:bs.cancelled||0}),
        `<span class="st-val">${s.runs||0}</span>`, 'stats runs total status')
    + srow(t('st.steps'), t('st.stepsD',{d:s.steps_done||0, t:s.steps_total||0}),
        `<span class="st-val">${s.steps_done||0} / ${s.steps_total||0}</span>`, 'stats steps')
    + srow(t('st.tools'), t('st.toolsD',{n:s.tool_calls||0, t:s.agent_turns||0}),
        `<span class="st-val">${s.tool_calls||0}</span>`, 'stats tool calls turns')
    + srow(t('st.time'), t('st.timeD'),
        `<span class="st-val">${esc(fmtDur(s.duration_ms))}</span>`, 'stats duration time')
    + srow(t('st.cost'), t('st.costD'),
        `<span class="st-val">${(s.cost_usd||0).toFixed(4)}</span>`, 'stats cost usd money')
    + srow(t('st.tokens'), t('st.tokensD'),
        `<span class="st-val">${esc(fmtTok(s.tokens_total))}</span>`, 'stats token tokens usage')
    + srow(t('st.tokIO'), t('st.tokIOD'),
        `<span class="st-val">${esc(fmtTok(tk.in))} / ${esc(fmtTok(tk.out))}</span>`, 'token input output')
    + srow(t('st.tokCache'), t('st.tokCacheD'),
        `<span class="st-val">${esc(fmtTok(tk.cache_read))}</span>`, 'token cache read')
    + srow(t('st.tokReason'), t('st.tokReasonD'),
        `<span class="st-val">${esc(fmtTok(tk.reason))}</span>`, 'token reasoning thought')
    + srow(t('st.disk'), t('st.diskD',{n:s.workspaces||0}),
        `<span class="st-val">${esc(fmtBytes(s.workspace_bytes))}</span>`, 'stats disk bytes workspace')
  );
  const foot = `<div class="st-foot"><button class="st-btn" onclick="stReload()">`
    + `${ico('refresh')}${esc(t('c.refresh'))}</button></div>`;
  return `<div class="st-stats">` + strip + heat + rangeRow + trend + models + usage
  + (pw.length ? stCard(t('st.grpFlows'),
      pw.map(([k,v])=>srow(esc(k), t('st.perFlowD'),
        `<span class="st-val">${v}</span>`, 'stats per workflow')).join('')) : '')
  + stCard(t('st.grpClean'),
      srow(t('st.orphans'), t('st.orphansD'),
        orphans.length
          ? `<span class="st-state no"><i></i>${orphans.length} · ${esc(fmtBytes(orphanBytes))}</span>`
          : `<span class="st-state ok"><i></i>${esc(t('st.none'))}</span>`,
        'stats orphan leftover cleanup')
  ) + foot + `</div>`;
}

/* ---------------- Agent 能力：两家 CLI 自己的配置面（只读盘点） ----------------
   只回名字与条数：那些文件里就是真密钥（settings.json 的 env、config.toml 的 bearer
   token），所以 mcp / hooks / plugins 连预览口都不开。改动请走各自的官方入口。 */
let CAPS_ENGINE = '';
const capsEngine = () => CAPS_ENGINE || ST.defaultEngine || 'claude';
const CAPS_PREVIEW = {memory:1, skills:1, commands:1, agents:1};

function secCaps(){
  const eng = capsEngine();
  const d = (ST.caps || {})[eng] || {items: []};
  const head = `<div class="st-block"><div class="st-panel">
      <div class="st-cardtop"><div class="hm-title">${esc(t('caps.title'))}</div>`
    + stSeg([['claude', t('eng.claude')], ['codex', t('eng.codex')]], eng, 'capsSetEngine')
    + `</div><div class="st-note">${esc(t('caps.note'))}</div></div></div>`;
  return head + (d.items || []).map(it => {
    const label = t('caps.' + it.key);
    const open = it.found
      ? `<button class="st-btn" onclick="capsOpen('${jsq(eng)}','${jsq(it.key)}')">`
        + esc(t('dir.open')) + `</button>` : '';
    let rows;
    if (!it.count){
      rows = srow(label, t('caps.none') + ' · ' + it.path, '', 'capabilities none cli ' + label);
    } else if (CAPS_PREVIEW[it.key]){
      rows = it.entries.map(e => srow(esc(e.name), fmtBytes(e.bytes) + ' · ' + it.path,
        `<button class="st-btn" onclick="capsView('${jsq(eng)}','${jsq(it.key)}','${jsq(e.name)}')">`
        + esc(t('c.view')) + `</button>`, 'capabilities ' + label)).join('');
    } else {
      rows = it.entries.map(e => srow(esc(e.name), t('caps.nameOnly'), '',
                                      'capabilities ' + label)).join('');
    }
    return spanel(rows, label, open);
  }).join('');
}

window.capsSetEngine = function(v){ CAPS_ENGINE = v; secRepaint('caps'); };
window.capsOpen = async function(eng, key){
  const url = '/api/reveal?which=agent&engine=' + encodeURIComponent(eng)
            + '&key=' + encodeURIComponent(key);
  const r = await post(url).catch(e => ({detail: String(e)}));
  if (r && r.detail) toast(r.detail);
};
window.capsView = async function(eng, key, name){
  const url = '/api/agents/capabilities/' + encodeURIComponent(eng) + '/'
            + encodeURIComponent(key) + (name ? '/' + encodeURIComponent(name) : '');
  const d = await api(url).catch(e => ({detail: String((e && e.message) || e)}));
  if (d.detail){ toast(d.detail); return; }
  _lockScroll(true);
  const root = document.createElement('div');
  root.id = 'capsViewRoot';
  root.innerHTML = `<div class="modal open" onclick="if(event.target===this)capsClose()">
    <div class="modal-box sk-view-modal">
      <div class="modal-top"><div class="pv-head"><h3>${esc(name || key)}</h3>
        <span class="muted-sm mono">${esc(d.path)}</span></div>
        <button class="modal-x" onclick="capsClose()">×</button></div>
      <div class="sk-view-body"><div class="ws-md">${window.mdToHtml(d.text || '')}</div>
        ${d.truncated ? `<div class="st-note">${esc(t('caps.truncated'))}</div>` : ''}</div>
      <div class="sk-view-foot"><span class="spacer"></span>
        <button class="btn btn-ghost btn-sm" onclick="capsClose()">${esc(t('c.close'))}</button>
      </div></div></div>`;
  document.body.appendChild(root);
};
window.capsClose = function(){
  const r = document.getElementById('capsViewRoot');
  if (r) r.remove();
  _lockScroll(false);
};

/* 只重渲染当前这一块：切档、切范围、刷新、换引擎都走这里 ——
   整页重渲染会重新拉那八个接口，还会把滚动位置还回顶部。
   搜索结果态下分区在 [data-sec] 里，标题得一起补回去。 */
function secRepaint(id){
  const inSearch = !!(id && id !== SET_SECTION);
  const host = inSearch ? document.querySelector('#stBody [data-sec="' + id + '"]')
                        : document.getElementById('stSec');
  if (!host){ renderSettings(SET_SECTION); return; }
  const sec = id || SET_SECTION;
  host.innerHTML = (inSearch ? `<div class="st-h2">${esc(secTitle(sec))}</div>` : '')
    + sectionBody(sec);
  // 页头那枚 chip 在 #stSec 外面，只换分区它会留下上一次的读数（切引擎后还写着旧引擎）
  const chip = document.querySelector('.st-hchip');
  if (chip && SEC_CHIP[sec]) chip.textContent = String(SEC_CHIP[sec]() || '');
  if (SET_Q.trim()) applySearch();
}
window.stSetMode = function(v){ ST_MODE = v; secRepaint('stats'); };
window.stSetRange = function(v){ ST_RANGE = +v || 7; secRepaint('stats'); };
window.stReload = async function(){
  const st = await api('/api/stats').catch(()=>null);
  if (st) ST.stats = st;
  secRepaint('stats');
  toast(t('st.reloaded'), true);
};

function secAbout(){
  const ready = ST.agents.filter(a=>a.found).map(a=>t('eng.'+a.engine));
  return spanel(
    srow(t('brand.full'), esc(t('brand.sub')+' · '+t('about.name')),
      `<span class="st-val">v${esc(ST.version||'')}</span>`, 'version about app loom')
    + srow(t('about.api'), t('about.port',{p:location.port||'8000'}),
        `<span class="st-state ok"><i></i>FastAPI</span>`, 'server api local')
    + srow(t('about.engines'), t('about.enginesD',{n:ready.length})+' · '+esc(ready.join(' / ')),
        '', 'engines detected cli')
    + srow(t('about.counts'), t('about.countsD',{s:(ST.skills||[]).length,p:(ST.flows||[]).length,
        r:(ST.runs||[]).length,pre:PRESETS.length}), '', 'counts skills workflows runs presets')
    + srow(t('dir.data'), '', `<span class="st-val st-val-path">${esc((ST.paths||{}).data||'—')}</span>`, 'data folder path'),
    t('about.grpInfo'));
}

window.saveUpdUrl = async function(){
  const url = ((document.getElementById('upUrl')||{}).value||'').trim();
  const r = await post('/api/update/url', {url}).catch(e=>({detail:String(e)}));
  if(r.detail){ toast(r.detail); return; }
  ST.update = r; UP = r; paintUpdate();
  toast(t('up.saved', {v: r.latest || '—'}), true);
  renderSettings(SET_SECTION);
};
window.checkNow = async function(){
  const r = await post('/api/update/check').catch(()=>null);
  if(!r){ toast(t('up.reqFail')); return; }
  ST.update = r; UP = r; paintUpdate();
  if(r.phase==='error'){ toast(r.error||t('up.failed')); }
  else { toast(t('up.checked',{s:upStatusText(r)}), true); }
  renderSettings(SET_SECTION);
};

const SEC_RENDER = {appearance:secAppearance, engines:secEngines, presets:secPresets,
                    runtime:secRuntime, caps:secCaps, dirs:secDirs,
                    shortcuts:secShortcuts, stats:secStats, update:secUpdate, about:secAbout};
const SEC_FLAT = () => SET_SECTIONS.flatMap(g=>g.items);
/* 页头那枚 chip 只报"这一屏现在生效的是什么"，且只挂有真实数据源的分区 ——
   没数据可报的分区就不挂，免得造一个永远不变的装饰。 */
const SEC_CHIP = {
  appearance: () => t('ap.theme.'+(window.APP.theme || 'dark')),
  engines: () => { const a = ST.agents || []; const f = a.filter(x=>x.found).length;
                   return f ? t('set.chipEngines',{n:f}) : t('set.chipNone'); },
  caps: () => t('eng.' + capsEngine()),
  update: () => ST.version ? 'v' + ST.version : '',
  about:  () => ST.version ? 'v' + ST.version : '',
};
const secTitle = id => { const s = SEC_FLAT().find(x=>x[0]===id); return s? t(s[1]) : ''; };

function settingsMain(){
  if(SET_Q.trim()){
    return `<div class="st-h1">${esc(t('set.search'))}</div>
      <div class="st-hsub">${esc(SET_Q.trim())}</div>`
      + SET_SECTIONS.flatMap(g=>g.items).map(([id])=>
          `<div data-sec="${id}"><div class="st-h2">${esc(secTitle(id))}</div>${sectionBody(id)}</div>`).join('');
  }
  const sub = t('set.'+SET_SECTION+'D');
  const chip = (SEC_CHIP[SET_SECTION] || (() => ''))();
  const meta = (chip || sub) ? `<div class="st-hmeta">
      ${chip?`<span class="st-hchip">${esc(chip)}</span>`:''}
      ${sub?`<div class="st-hsub">${esc(sub)}</div>`:''}</div>` : '';
  return `<div class="st-h1">${esc(secTitle(SET_SECTION))}</div>
    ${meta}<div id="stSec">${sectionBody(SET_SECTION)}</div>`;
}
function sectionBody(id){ return (SEC_RENDER[id]||secAppearance)(); }


window.renderSettings = async function(section){
  viewLoading();
  if(section && section!=='settings') SET_SECTION = section;
  const [r, ag, sk, pl, rn, hp, up, st, cp] = await Promise.all([
    api('/api/providers').catch(()=>({presets:[],default:null})),
    api('/api/agents').catch(()=>null),
    api('/api/skills').catch(()=>({skills:[]})),
    api('/api/pipelines').catch(()=>({pipelines:[]})),
    api('/api/runs').catch(()=>({runs:[]})),
    api('/api/health').catch(()=>({})),
    api('/api/update').catch(()=>null),
    api('/api/stats').catch(()=>null),
    api('/api/agents/capabilities').catch(()=>null),
  ]);
  ST.update = up || null; ST.stats = st || null; ST.caps = cp || null;
  PRESETS = r.presets||[];   // ST 里不再镜像一份：清单只有 PRESETS 这一个消费者
  ST.skills = sk.skills||[]; ST.flows = pl.pipelines||[]; ST.runs = rn.runs||[];
  if(ag){
    ST.agents = ag.agents||[]; ST.defaultEngine = ag.default_engine||'';
    ST.claudeCli = ag.claude_cli||''; ST.codexCli = ag.codex_cli||'';
    ST.paths = ag.paths||{};
    ST.agentTimeout = ag.agent_timeout; ST.codexSandbox = ag.codex_sandbox;
    ST.sandboxOptions = ag.sandbox_options||[];
    ST.effortOptions = ag.effort_options||['auto'];
    ST.reasoningEffort = ag.reasoning_effort||'auto';
    ST.stepRetry = ag.step_retry||'0'; ST.autoContinue = ag.auto_continue||'0';
  }
  ST.version = hp.version||'';

  const navHtml = SET_SECTIONS.map(g=>`<div class="st-grp">${esc(t(g.grp))}</div>`
    + g.items.map(([id,key,ic])=>`<button type="button" class="st-item ${(!SET_Q&&id===SET_SECTION)?'active':''}"
        data-nav="${id}" data-k="${esc((t(key)+' '+key).toLowerCase())}" onclick="setGo('${id}')">
        ${ico(ic)}<span>${esc(t(key))}</span></button>`).join('')).join('');

  const keep = document.querySelector('.st-main');
  const keepTop = keep ? keep.scrollTop : 0;
  $('#app').dataset.shell = 'settings';
  $('#view').classList.remove('with-composer');
  $('#view').innerHTML = `
    <div class="st-shell">
      <aside class="st-side">
        <button type="button" class="st-back" onclick="setExit()">${ico('chevronLeft')}<span>${esc(t('set.back'))}</span></button>
        <div class="st-search">${ico('search')}<input id="stQ" placeholder="${esc(t('set.search'))}"
          value="${esc(SET_Q)}" oninput="setQuery(this.value)"></div>
        <div id="stNav">${navHtml}</div>
      </aside>
      <div class="st-main"><div class="st-inner" id="stBody">${settingsMain()}</div></div>
    </div>`;
  if(SET_Q) applySearch();
  const m = document.querySelector('.st-main');
  if(m && keepTop) m.scrollTop = keepTop;
};

function applySearch(){
  const q = SET_Q.trim().toLowerCase();
  const body = document.getElementById('stBody');
  if(!body) return;
  let hitRows = 0, hitSecs = 0;
  body.querySelectorAll('[data-sec]').forEach(sec=>{
    let inSec = 0;
    const blocks = [...sec.querySelectorAll('.st-block')];
    if(!blocks.length){
      // 键位表是张表，没有 .st-block/.st-row 外壳。照下面的走法它永远 0 命中，
      // 结果整段被搜索藏掉 —— 所以这类分区直接认行上的 data-k。
      const trs = [...sec.querySelectorAll('.sc-tr[data-k]')];
      const shown = trs.filter(r=>!q || (r.dataset.k||'').includes(q)).length;
      trs.forEach(r=>r.classList.toggle('st-hidden',
        !!q && !(r.dataset.k||'').includes(q)));
      if(shown){ inSec = 1; hitRows += shown; }
    }
    blocks.forEach(bl=>{
      const rows = [...bl.querySelectorAll('.st-row')];
      if(!rows.length){
        // 热力图、实时预览这类卡里一行 .st-row 都没有，没法按行过滤。
        // 一律留下是不行的：那样随便敲一串乱码它也算命中，"没有匹配"永远出不来。
        // 折中是拿卡自己的标题文案比一次 —— "token" 命中热力图标题，"zzzz" 谁都不命中。
        const k = [...bl.querySelectorAll('.st-label,.hm-title,.spv-title,.st-t,.st-d')]
          .map(e=>e.textContent).join(' ').toLowerCase();
        const on = !q || k.includes(q);
        bl.classList.toggle('st-hidden', !on);
        if(on){ inSec++; hitRows++; }
        return;
      }
      let shown = 0;
      rows.forEach(r=>{
        const on = !q || (r.dataset.k||'').includes(q);
        r.classList.toggle('st-hidden', !on);
        // 整行铺开的输入框是标签行的"下半身"，行藏了它必须跟着藏，否则裸留一个框
        const sub = r.nextElementSibling;
        if(sub && sub.classList.contains('st-rowsub')) sub.classList.toggle('st-hidden', !on);
        if(on) shown++;
      });
      bl.classList.toggle('st-hidden', shown===0);
      if(shown){ inSec++; hitRows++; }
    });
    sec.classList.toggle('st-hidden', inSec===0);
    if(inSec) hitSecs++;
  });
  const empty = body.querySelector('.st-noresult');
  if(!hitRows && !empty){
    const d = document.createElement('div');
    d.className = 'st-empty st-noresult'; d.textContent = t('set.noHit');
    body.appendChild(d);
  } else if(hitRows && empty) empty.remove();
  const sub = body.querySelector('.st-hsub');
  if(sub && q) sub.textContent = SET_Q.trim()+' · '+t('set.hits',{n:hitSecs});
  const live = new Set([...body.querySelectorAll('[data-sec]:not(.st-hidden)')].map(e=>e.dataset.sec));
  document.querySelectorAll('#stNav .st-item').forEach(it=>
    it.classList.toggle('st-hidden', !!q && !live.has(it.dataset.nav)));
}

window.setGo = function(id){ SET_SECTION = id; SET_Q = ''; PATH_EDIT=''; renderSettings(id); };
window.setExit = function(view){ const a=document.getElementById('app'); if(a) delete a.dataset.shell;
  SET_Q=''; PATH_EDIT=''; nav.go(view||'pipelines'); };
window.setQuery = function(v){ SET_Q = v||'';
  const body = document.getElementById('stBody'); if(!body) return;
  body.innerHTML = settingsMain();
  if(SET_Q.trim()) applySearch();
  else document.querySelectorAll('#stNav .st-item').forEach(i=>{
    i.classList.remove('st-hidden');
    i.classList.toggle('active', i.dataset.nav===SET_SECTION);
  });
};

window.apSet = async function(key, val){
  await window.setAppearance({[key]: val});
  if(key !== 'lang') return;          // 主题/字号/缩放/宽度都是 CSS 变量，即时生效
  renderNav(document.querySelector('#mainNav .sb-item.active')?.dataset.v || 'settings');
  renderSettings();
};
window.apSetFont = function(v){ window.apSet('font', v); };

window.editPath = function(eng){ PATH_EDIT = eng; renderSettings();
  setTimeout(()=>{ const el=document.getElementById('path_'+eng); if(el){ el.focus(); el.select(); } },60); };
window.cancelPath = function(){ PATH_EDIT=''; renderSettings(); };
window.savePath = async function(eng){
  const el = document.getElementById('path_'+eng);
  const body = eng==='claude' ? {claude_cli:(el?el.value:'').trim()} : {codex_cli:(el?el.value:'').trim()};
  PATH_EDIT='';
  const r = await post('/api/agents', body).catch(e=>({detail:String(e)}));
  if(r.detail){ toast(r.detail); }
  else toast(t('eng.saved'), true);
  renderSettings();
};
window.setDefaultEngine = async function(eng){
  const r = await post('/api/agents', {default_engine:eng}).catch(e=>({detail:String(e)}));
  if(r.detail){ toast(r.detail); return; }
  toast(t('eng.saved'), true);
  await loadAgents(); renderSettings();
};
async function postAgents(body){
  const r = await post('/api/agents', body).catch(e=>({detail:String(e)}));
  if(r.detail) toast(r.detail); else toast(t('eng.saved'), true);
  return r;
}
window.saveTimeout = async function(v){
  if(!await postAgents({agent_timeout:v})) return;
  ST.agentTimeout = v;
};
window.saveSandbox = async function(v){
  if(!await postAgents({codex_sandbox:v})) return;
  ST.codexSandbox = v;
};
window.saveRetry = async function(v){
  if(!await postAgents({step_retry:v})) return;
  ST.stepRetry = v;
};
window.saveEffort = async function(v){
  if(!await postAgents({reasoning_effort:v})) return;
  ST.reasoningEffort = v;
};
window.saveAutoContinue = async function(on){
  if(!await postAgents({auto_continue:on?'1':'0'})) return;
  ST.autoContinue = on?'1':'0';
};
window.revealDir = async function(k){
  const r = await post('/api/reveal?which='+encodeURIComponent(k)).catch(e=>({detail:String(e)}));
  if(r.detail) toast(r.detail);
};
/* ---------------- 预设（列表已并入设置 › API 接入） ---------------- */
let PRESETS = [];

/* ---------------- 预设弹窗 ---------------- */
let PF_EDIT=null;
function pfOpenNew(){ pfOpenModal(null); }
window.pfOpenNew = pfOpenNew;

function pfOpenModal(p){
  PF_EDIT = p;
  document.body.style.overflow='hidden';
  const cat = window.PROVIDER_CATALOG||[];
  const grid = cat.map(t2=>{
    const letter=(t2.name||'?').slice(0,1).toUpperCase();
    return `<div class="pv-item ${p&&p.name===t2.name?'pv-sel':''}" data-name="${esc(t2.name)}" onclick="pfPick('${esc(t2.name)}')">
      <span class="pv-ico">${esc(letter)}</span><span class="pv-name">${esc(t2.name)}</span></div>`;
  }).join('') + `<div class="pv-item pv-item-custom" data-name="__custom__" onclick="pfPickCustom()">
      <span class="pv-ico pv-ico-custom">＋</span><span class="pv-name">${esc(t('pr.custom'))}</span></div>`;

  const root=document.createElement('div');
  root.id='pfModalRoot';
  root.innerHTML=`<div class="modal open" onclick="if(event.target===this)pfCloseModal()">
    <div class="modal-box pv-modal">
      <div class="modal-top"><div class="pv-head"><h3>${p?esc(t('pr.editTitle')):esc(t('pr.newTitle'))}</h3></div>
        <button class="modal-x" onclick="pfCloseModal()">×</button></div>
      <div class="pv-scroll">
        ${p?'':`<div class="pv-search-wrap"><input class="pv-input" id="pfQ" placeholder="${esc(t('pr.searchVendor'))}" oninput="pfDrawQ()"></div>
        <div class="pv-grid" id="pfGrid">${grid}</div><div class="pv-divider"></div>`}
        <div class="pv-form pv-flat">
          <div class="pv-row2">
            <div class="pv-f"><label class="pv-label">${esc(t('pr.displayName'))} <b class="req">*</b></label>
              <input class="pv-input" id="pfDisp" value="${esc((p&&((p.extra&&p.extra.display_name)||p.name))||'')}"></div>
            <div class="pv-f"><label class="pv-label">${esc(t('pr.protocol'))}</label>
              ${ffSelect([{v:'anthropic',label:'Anthropic Messages'},{v:'openai',label:'OpenAI compatible'}],
                (!p||p.provider==='anthropic')?'anthropic':'openai', {id:'pfProvider'})}</div>
          </div>
          <div class="pv-f"><label class="pv-label">${esc(t('pr.base'))} <b class="req">*</b></label>
            <input class="pv-input mono" id="pfBase" placeholder="https://api.example.com/anthropic" value="${esc(p?p.api_base:'')}"></div>
          <div class="pv-f"><label class="pv-label">${esc(t('pr.key'))} ${p?`<span class="muted">${esc(t('pr.keyKeep'))}</span>`:'<b class="req">*</b>'}</label>
            <input class="pv-input mono" id="pfKey" type="password" value=""></div>
          <div class="pv-f"><label class="pv-label">${esc(t('pr.model'))}</label>
            <div style="display:flex;gap:8px">
              <input class="pv-input mono" id="pfModel" placeholder="claude-sonnet-4-5 / deepseek-chat" value="${esc(p?p.model:'')}" style="flex:1">
              <button class="btn btn-ghost btn-sm" onclick="pfFetchModels()">${esc(t('pr.fetchModels'))}</button>
            </div>
            <div class="pv-fhint" id="pfModelHint">${esc(t('pr.wireHint'))}</div></div>
          <div class="pv-fhint">${esc(t('pr.baseHint'))}</div>
        </div>
      </div>
      <div class="modal-foot">
        <button class="btn btn-ghost" onclick="pfCloseModal()">${esc(t('c.cancel'))}</button>
        <button class="btn btn-primary" onclick="pfSave()">${p?esc(t('pr.saveEdit')):esc(t('pr.saveNew'))}</button>
      </div>
    </div></div>`;
  document.body.appendChild(root);
  window.PF_PICKED = p ? {name:p.name, api_base:p.api_base, provider:p.provider} : null;
}
window.pfCloseModal=function(){
  const r=document.getElementById('pfModalRoot'); if(r) r.remove();
  document.body.style.overflow='';
};
window.pfDrawQ=function(){
  const q=(document.getElementById('pfQ')||{}).value||'';
  const grid=document.getElementById('pfGrid'); if(!grid) return;
  const items=(window.PROVIDER_CATALOG||[]).filter(x=>!q||x.name.toLowerCase().includes(q.toLowerCase()));
  grid.innerHTML=items.map(x=>`<div class="pv-item" data-name="${esc(x.name)}" onclick="pfPick('${esc(x.name)}')">
    <span class="pv-ico">${esc((x.name||'?').slice(0,1).toUpperCase())}</span><span class="pv-name">${esc(x.name)}</span></div>`).join('')
    +`<div class="pv-item pv-item-custom" onclick="pfPickCustom()"><span class="pv-ico pv-ico-custom">＋</span>
      <span class="pv-name">${esc(t('pr.custom'))}</span></div>`;
};
window.pfPick=function(name){
  const x=(window.PROVIDER_CATALOG||[]).find(v=>v.name===name); if(!x) return;
  window.PF_PICKED={name:x.name, api_base:x.api_base||'', provider:x.provider||'anthropic', site:x.site||''};
  const grid=document.getElementById('pfGrid');
  if(grid) grid.querySelectorAll('.pv-item').forEach(el=>el.classList.toggle('pv-sel',el.dataset.name===x.name));
  const disp=document.getElementById('pfDisp'); if(disp&&!disp.value.trim()) disp.value=x.name;
  const prov=document.getElementById('pfProvider');
  if(prov) window.ffSetValue('pfProvider', x.provider==='anthropic'?'anthropic':'openai',
                             x.provider==='anthropic'?'Anthropic Messages':'OpenAI compatible');
  const base=document.getElementById('pfBase'); if(base) base.value=x.api_base||'';
};
window.pfPickCustom=function(){
  window.PF_PICKED=null;
  const grid=document.getElementById('pfGrid');
  if(grid) grid.querySelectorAll('.pv-item').forEach(el=>el.classList.toggle('pv-sel',el.dataset.name==='__custom__'));
};
window.pfFetchModels=async function(){
  const base=(document.getElementById('pfBase')||{}).value||'';
  const key=(document.getElementById('pfKey')||{}).value||'';
  if(!base){ toast(t('pr.needBase')); return; }
  toast(t('pr.modelsFetching'));
  try{
    const provider=(document.getElementById('pfProvider')||{}).value||'anthropic';
    const r=await post('/api/models/list',{api_base:base, api_key:key, provider,
      id:(PF_EDIT&&PF_EDIT.id)||0});   // 编辑已存预设时密钥不在前端，让服务端按 id 自己取
    if(!r.ok){ toast(t('pr.modelsFail',{err:r.error||''})); return; }
    const ids=(r.models||[]).map(x=>x.id||x.model||x.name||x).filter(Boolean).slice(0,200);
    const hint=document.getElementById('pfModelHint');
    if(hint) hint.textContent = ids.length
      ? (ids.slice(0,30).join(' · ') + (ids.length>30?` …${ids.length}`:''))
      : t('pr.modelsEmpty');
    if(ids.length) toast(t('pr.modelsLoaded',{n:ids.length}), true);
  }catch(e){ toast(t('pr.modelsFail',{err:e})); }
};
window.pfSave=async function(){
  const name=(document.getElementById('pfDisp')||{}).value||'';
  const provider=(document.getElementById('pfProvider')||{}).value||'anthropic';
  const api_base=(document.getElementById('pfBase')||{}).value||'';
  const api_key=(document.getElementById('pfKey')||{}).value||'';
  const model=(document.getElementById('pfModel')||{}).value||'';
  if(!name.trim()){ toast(t('pr.needName')); return; }
  if(!api_base.trim()){ toast(t('pr.needBase')); return; }
  const picked=window.PF_PICKED;
  /* extra 整列是覆盖写的。这个表单只拥有 display_name 和 site 两个键，
     别把没在界面上露面的 model_map / fallback_model（端点/模型阶梯靠它们）一起擦掉。 */
  const kept=(PF_EDIT && typeof PF_EDIT.extra==='object' && PF_EDIT.extra) ? PF_EDIT.extra : {};
  const body={name:name.trim(), provider, api_base:api_base.trim(), model:model.trim(),
              extra:{...kept, display_name:name.trim(), site:(picked&&picked.site)||''}};
  let r;
  if(PF_EDIT){ r=await put('/api/providers/'+PF_EDIT.id, {...body, api_key}).catch(e=>({detail:String(e)})); }
  else { r=await post('/api/providers', {...body, api_key}).catch(e=>({detail:String(e)})); }
  if(r.detail){ toast(r.detail); return; }
  toast(PF_EDIT?t('pr.saved'):t('pr.created'), true);
  pfCloseModal(); renderSettings();
};
window.pfEdit=function(id){
  const p=PRESETS.find(x=>x.id===id); if(!p) return;
  pfOpenModal({...p});
};
window.pfDel=async function(id){
  if(!confirm(t('pr.delConfirm'))) return;
  const r=await del('/api/providers/'+id).catch(e=>({detail:String(e)}));
  if(r.detail){ toast(r.detail); return; }
  toast(t('pr.deleted')); renderSettings();
};
window.pfSetDefault=async function(id){
  const r=await post('/api/providers/'+id+'/default').catch(e=>({detail:String(e)}));
  if(r.detail){ toast(r.detail); return; }
  toast(t('pr.defaultSet'), true); renderSettings();
};
window.pfTest=async function(id){
  const p=PRESETS.find(x=>x.id===id); if(!p) return;
  toast(t('pr.testing'));
  const r=await post('/api/providers/test',{id, provider:p.provider, model:p.model})
    .catch(e=>({ok:false,msg:String(e)}));
  toast(r.ok?t('pr.testOk',{msg:r.msg?('：'+r.msg):''}):t('pr.testFail',{msg:r.msg||''}), !!r.ok);
};

/* ---------------- 下拉按钮（统一的 split-button 菜单） ----------------
   渲染一个隐藏 input 镜像（沿用传入的 id），所以老代码里 .value 的读法不受影响。 */
const FF_SEL = {};
let FF_N = 0;

function ffSelect(opts, cur, cfg){
  cfg = cfg || {};
  const id = cfg.id || ('ffs'+(++FF_N));
  const key = 'ff'+id;
  FF_SEL[key] = {opts, id, onChange:cfg.onChange, arg:cfg.arg, action:!!cfg.action};
  const hit = opts.find(o=>String(o.v)===String(cur));
  const label = hit ? hit.label : (cfg.placeholder || (opts[0] && opts[0].label) || '');
  return `<span class="ff-selw${cfg.mono?' ff-mono':''}${cfg.cls?' '+cfg.cls:''}">
    <input type="hidden" id="${esc(id)}" value="${esc(cur==null?'':cur)}">
    <button type="button" class="ff-sel" data-k="${esc(key)}" onclick="ffOpen(event,'${esc(key)}')">
      <span class="ff-sv">${esc(label)}</span>
      <span class="ff-sdiv"></span>
      <span class="ff-sc">${ico('chevron')}</span>
    </button></span>`;
}

function ffMenuEl(){
  let m = document.getElementById('ffMenu');
  if(!m){ m = document.createElement('div'); m.id='ffMenu'; m.className='ff-menu'; m.hidden = true;
          document.body.appendChild(m); }
  return m;
}
window.ffClose = function(){
  const m=ffMenuEl(); m.hidden=true; m.innerHTML='';
  document.querySelectorAll('.ff-selw.open').forEach(e=>e.classList.remove('open'));
};
/* 从代码里改选中值必须走这里。隐藏 input 和按钮上那行 .ff-sv 文字是两个东西：
   只写 input，按钮会一直显示着上一项 —— 切步骤、选供应商都就是这么错给用户的。 */
window.ffSetValue = function(id, v, label){
  const hid = document.getElementById(id); if(!hid) return;
  hid.value = v;
  const sv = hid.parentElement && hid.parentElement.querySelector('.ff-sv');
  if(sv && label != null) sv.textContent = label;
};

window.ffOpen = function(e, key){
  e.stopPropagation();
  const cfg = FF_SEL[key]; if(!cfg) return;
  const m = ffMenuEl();
  if(!m.hidden && m.dataset.k===key){ ffClose(); return; }
  const btn = e.currentTarget;
  const cur = cfg.action ? null : (btn.parentElement.querySelector('input[type=hidden]')||{}).value;
  m.dataset.k = key;
  m.innerHTML = cfg.opts.map(o=>`<button type="button" class="ff-mi${String(o.v)===String(cur)?' on':''}"
      data-v="${esc(o.v)}">${esc(o.label)}${o.note?`<i>${esc(o.note)}</i>`:''}</button>`).join('');
  m.hidden = false;
  const r = btn.getBoundingClientRect();
  const mw = m.offsetWidth, mh = m.offsetHeight;
  let left = Math.min(r.left, window.innerWidth - mw - 10);
  if(left < 10) left = 10;
  let top = r.bottom + 6;
  if(top + mh > window.innerHeight - 10) top = Math.max(10, r.top - mh - 6);
  m.style.left = left+'px'; m.style.top = top+'px';
  btn.parentElement.classList.add('open');
  const pick = m.querySelector('.ff-mi.on') || m.querySelector('.ff-mi');
  if(pick && pick.scrollIntoView) pick.scrollIntoView({block:'nearest'});
  m.querySelectorAll('.ff-mi').forEach(el=>el.addEventListener('click', (ev)=>{
    ev.stopPropagation();
    const v = el.dataset.v;
    if(!cfg.action){
      const hid = document.getElementById(cfg.id); if(hid) hid.value = v;
      btn.querySelector('.ff-sv').textContent = el.textContent;
    }
    ffClose();
    if(typeof cfg.onChange === 'function') cfg.onChange(v, cfg.arg);
    else if(cfg.onChange && window[cfg.onChange]) window[cfg.onChange](v, cfg.arg);
  }));
};

document.addEventListener('click', (e)=>{
  const m = document.getElementById('ffMenu');
  if(m && !m.hidden && !e.target.closest('#ffMenu') && !e.target.closest('.ff-sel')) ffClose();
});
window.ffSelect = ffSelect;

/* 动作菜单：和 ffSelect 共用 .ff-menu 外壳与那套开合逻辑，
   但项目是「点一下就去做」而不是「选一个值」。 */
window.ffActionMenu = function(e, items){
  e.stopPropagation();
  const m = ffMenuEl();
  if(!m.hidden && m.dataset.k === '__act'){ ffClose(); return; }
  const btn = e.currentTarget || e.target;   /* 图标按钮里点到的可能是内部 <svg> */
  m.dataset.k = '__act';
  m.innerHTML = items.map(it=>`<button type="button" class="ff-mi${it.danger?' ff-mi-danger':''}"
      data-act="${esc(it.v)}">${esc(it.label)}</button>`).join('');
  m.hidden = false;
  const r = btn.getBoundingClientRect(), mw = m.offsetWidth, mh = m.offsetHeight;
  let left = Math.min(r.right - mw, window.innerWidth - mw - 10);   /* 右对齐触发按钮 */
  if(left < 10) left = 10;
  let top = r.bottom + 6;
  if(top + mh > window.innerHeight - 10) top = Math.max(10, r.top - mh - 6);
  m.style.left = left + 'px'; m.style.top = top + 'px';
  m.querySelectorAll('.ff-mi').forEach(el=>el.addEventListener('click', (ev)=>{
    ev.stopPropagation();
    const it = items.find(x=>x.v === el.dataset.act);
    ffClose();
    if(it && it.run) it.run();
  }));
};

/* ---------------- 全局快捷键 ---------------- */
const isTyping = (el) => !!el && (el.tagName==='INPUT' || el.tagName==='TEXTAREA' || el.isContentEditable);

document.addEventListener('keydown', (e)=>{
  if(e.repeat) return;   // 长按 Ctrl B 原来会一路连发，每次都打一次 setAppearance POST
  const mod = e.ctrlKey || e.metaKey;
  const inSettings = ()=>{ const a=document.getElementById('app'); return !!(a && a.dataset.shell==='settings'); };
  if(mod && !e.altKey){
    const k = (e.key||'').toLowerCase();
    /* Ctrl K / Ctrl B 在浏览器形态下会被 Chrome/Edge 抢走（聚焦地址栏、切书签栏），
       preventDefault 拦不住 —— 所以带不带 Shift 都认，浏览器里用 Ctrl+Shift+K 这条。
       打包成桌面壳后没有这个竞争，两种按法都通。逗号那条浏览器不抢，维持原样。 */
    if(k==='k'){ e.preventDefault(); window.taskModal(); return; }
    if(k==='b'){ e.preventDefault(); window.sbToggle(); return; }
    if(k===',' && !e.shiftKey){ e.preventDefault(); nav.go('settings'); return; }
  }
  if(e.key==='Escape'){
    const fd = document.getElementById('sbFind');
    if(fd && !fd.hidden){ e.preventDefault(); fd.hidden = true; return; }
    const pop = document.getElementById('sbPop');
    if(pop && !pop.hidden){ e.preventDefault(); closeFootMenu(); return; }
    const m = document.querySelector('.modal.open');
    if(m){ const x = m.querySelector('.modal-x'); if(x){ e.preventDefault(); x.click(); } return; }
    if(inSettings()){ e.preventDefault(); window.setExit(); }
    return;
  }
  if(e.key==='/' && !mod && !isTyping(e.target) && inSettings()){
    const q = document.getElementById('stQ');
    if(q){ e.preventDefault(); q.focus(); q.select(); }
  }
});

/* ---------------- 启动 ---------------- */
async function boot(){
  await window.loadAppearance();
  await loadAgents();
  renderNav('pipelines');
  nav.resolve();
  upInit();
}
if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', boot);
else boot();

})();
