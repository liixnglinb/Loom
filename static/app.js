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
const ST = { presets:[], defaultPreset:null, agents:[], defaultEngine:'',
             claudeCli:'', codexCli:'', libVersion:'', paths:{}, sandboxOptions:[],
             agentTimeout:'2700', codexSandbox:'workspace-write', effortOptions:['auto'],
             reasoningEffort:'auto', stepRetry:'0', autoContinue:'0', bundledSkills:[],
             skills:[], flows:[], runs:[], version:'' };
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
  const html = items.map(n=>
    `<a class="sb-item ${n.id===active?'active':''}" data-v="${n.id}" data-tip="${esc(n.label)}"
       onclick="nav.go('${n.id}')">
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
        data-tip="${esc(p.label||p.name)}"
        onclick="nav.go('pipeline-edit/${esc(p.name)}')">
        <span class="sb-rico">${ico(p.builtin?'flow':'branch')}</span>
        <span class="sb-rname">${esc(p.label||p.name)}</span>
        <span class="sb-rtag">${esc(t(p.builtin?'sb.tagBuiltin':'sb.tagMine'))}</span></a>`).join('')
      : `<div class="sb-empty">${esc(t('sb.noProject'))}</div>`);

  html += `<div class="sb-group"><span>${esc(t('sb.recent'))}</span>
      ${live?`<span class="sb-gcount">${live}</span>`:''}</div>`
    + (runs.length ? runs.map(u=>{
        const m = RUN_ICON[u.status] || RUN_ICON.pending;
        return `<a class="sb-run ${u.id===cur?'active':''}" data-tip="${esc(u.label||u.pipeline)}"
          onclick="nav.go('run/${esc(u.id)}')">
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
            `sbGo('pipeline-edit/${esc(x.name)}')`, x.builtin?'flow':'branch')).join('')
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
  ST.libVersion = r.library_version||'';
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
  const r = document.getElementById('sbMe').getBoundingClientRect();
  pop.style.left = Math.max(8, Math.min(r.left, window.innerWidth - pop.offsetWidth - 8)) + 'px';
  pop.style.bottom = (window.innerHeight - r.top + 6) + 'px';
};
window.closeFootMenu = function(){
  const pop = document.getElementById('sbPop');
  if(pop){ pop.hidden = true; pop.innerHTML=''; }
};
window.footCycle = async function(key){
  const A = window.APP;
  const CYCLE = { theme:['light','dark','auto'], accent:['blue','gold'], lang:['zh','en'] };
  const list = CYCLE[key]; if(!list) return;
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
  root.innerHTML = `<div class="modal open" onclick="if(event.target===this)taskClose()">
    <div class="modal-box" style="width:min(660px,94vw)">
      <div class="modal-top"><h3>${esc(t('task.title'))}</h3><button class="modal-x" onclick="taskClose()">×</button></div>
      <div class="pv-scroll">
      <div class="pv-form pv-flat">
        <div class="pv-f"><label class="pv-label">${esc(t('task.flow'))}</label>
          ${ffSelect(tpls.map(p=>({v:p.name, label:(p.label||p.name)+' · '+p.steps.length+' '+t('c.steps')})),
                     presetFlow||tpls[0].name, {id:'tkFlow', onChange:'tkHint'})}</div>
        <div class="pv-f"><label class="pv-label">${esc(t('task.brief'))} <b class="req">*</b></label>
          <textarea class="pv-input" id="tkBrief" rows="8" placeholder="${esc(t('task.briefPh'))}" oninput="tkHint()"></textarea>
          <div class="pv-foot-hint" id="tkHintBox">${esc(t('task.briefHint'))}</div></div>
        <div class="pv-f"><label class="pv-label">${esc(t('task.label'))}</label>
          <input class="pv-input" id="tkLabel" placeholder="${esc(t('task.labelPh'))}"></div>
      </div></div>
      <div class="modal-foot">
        <button class="btn btn-ghost" onclick="taskClose()">${esc(t('c.cancel'))}</button>
        <button class="btn btn-primary" onclick="taskStart()">${esc(t('task.start'))}</button>
      </div>
    </div></div>`;
  document.body.appendChild(root);
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
window.plRestore = async function(name){
  if(!confirm(t('list.restoreConfirm',{name}))) return;
  const r = await post(`/api/pipelines/${encodeURIComponent(name)}/restore`).catch(e=>({detail:String(e)}));
  if(r.detail){ toast(r.detail); return; }
  toast(t('list.restoreDone'), true);
  const a=document.getElementById('app');
  if(a && a.dataset.shell==='settings') renderSettings(); else window.renderPipelines();
};

/* ================= 设置：Codex 式两栏外壳 ================= */
const SET_SECTIONS = [
  {grp:'set.grp.pref', items:[['appearance','set.appearance','appearance'],
                              ['shortcuts','set.shortcuts','keyboard']]},
  {grp:'set.grp.exec', items:[['engines','set.engines','agent'],['presets','set.presets','api'],
                              ['runtime','set.runtime','runtime'],['library','set.library','layers']]},
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
const spanel = (rows, label='') => `
  <div class="st-block">${label?`<div class="st-label">${esc(label)}</div>`:''}
    <div class="st-panel">${rows}</div></div>`;
/* 设置页的「多选一」统一用胶囊下拉：一个当前值 + 箭头，展开时不整页重渲染，所以不闪 */
const sseg = (opts, cur, fn, arg) => ffSelect(opts.map(([v,l])=>({v, label:l})), cur,
  {cls:'ff-pill', onChange:(v)=>{ const f=window[fn]; if(f){ if(arg) f(arg,v); else f(v); } }});
const ssel = (opts, cur, fn) => ffSelect(opts.map(([v,l])=>({v,label:l})), cur, {onChange:fn});
const ssw = (on, fn) => `<label class="switch"><input type="checkbox" ${on?'checked':''}
  onchange="swPick(this,'${fn}')"><span class="slider"></span></label>`;
window.swPick = function(el, fn){ const f=window[fn]; if(f) f(el.checked); };
const schips = (items) => `<div class="st-chips">${items.map(x=>
  `<span class="st-chip">${esc(x)}</span>`).join('')}</div>`;
const skey = (k) => `<kbd class="st-kbd">${esc(k)}</kbd>`;

function secAppearance(){
  const A = window.APP;
  const lang = spanel([
    srow(t('ap.language'), t('ap.languageD'),
      sseg([['zh','中文'],['en','English']], A.lang, 'apSet', 'lang'), 'language locale'),
  ].join(''), t('ap.grpLang'));
  const look = spanel([
    srow(t('ap.theme'), t('ap.themeD'),
      sseg(window.AP_OPTS.THEMES.map(v=>[v,t('ap.theme.'+v)]), A.theme, 'apSet', 'theme'), 'theme dark light system'),
    srow(t('ap.font'), t('ap.fontD'),
      ssel(window.AP_OPTS.FONTS.map(v=>[v,t('ap.font.'+v)]), A.font, 'apSetFont'), 'font typeface'),
    srow(t('ap.textSize'), t('ap.textSizeD'),
      sseg(Object.keys(window.AP_OPTS.TEXT_SIZES).map(v=>[v,t('ap.size.'+v)]), A.textSize, 'apSet', 'textSize'), 'text size font'),
    srow(t('ap.zoom'), t('ap.zoomD'),
      sseg(Object.keys(window.AP_OPTS.ZOOMS).map(v=>[v,v]), A.uiZoom, 'apSet', 'uiZoom'), 'zoom scale ui'),
    srow(t('ap.width'), t('ap.widthD'),
      sseg(Object.keys(window.AP_OPTS.WIDTHS).map(v=>[v,t('ap.width.'+v)]), A.contentWidth, 'apSet', 'contentWidth'), 'width content'),
    srow(t('ap.accent'), t('ap.accentD'),
      sseg(window.AP_OPTS.ACCENTS.map(v=>[v,t('ap.accent.'+v)]), A.accent, 'apSet', 'accent'), 'accent colour color blue gold'),
  ].join(''), t('ap.grpLook'));
  const pv = spanel(
    `<div class="st-preview">
       <div class="spv-title">${esc(t('ap.pvTitle'))}</div>
       <div class="spv-body">${esc(t('ap.pvBody'))}</div>
       <div class="spv-code">${esc(t('ap.pvCode'))}</div>
       <div class="spv-meta">${esc(t('ap.pvMeta'))}</div>
     </div>`, t('ap.grpPreview'));
  return lang + look + pv;
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
      return srow(title, t('eng.pathD'),
        `<input class="pv-input mono" style="width:340px" id="path_${a.engine}"
           placeholder="${esc(t('eng.pathPh'))}" value="${esc(cur)}">
         <button class="st-btn" onclick="savePath('${a.engine}')">${esc(t('c.save'))}</button>
         <button class="st-btn" onclick="cancelPath()">${esc(t('c.cancel'))}</button>`, a.engine+' path binary');
    }
    return srow(title, t('eng.pathD'),
      `<span class="st-val">${esc(cur || a.bin || t('eng.auto'))}</span>
       <button class="st-btn" onclick="editPath('${a.engine}')">${esc(t('eng.change'))}</button>`, a.engine+' path binary');
  }).join('');
  return spanel(head + engRows, t('eng.grpEngines')) + spanel(paths, t('eng.grpBinary'));
}

function secPresets(){
  const rows = PRESETS.map(p=>{
    const disp = (p.extra&&p.extra.display_name)||p.name;
    const prov = (p.provider||'openai')==='anthropic'?'Anthropic':'OpenAI';
    const bits = [prov, p.api_base||'—']; if(p.model) bits.push(p.model);
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

function secLibrary(){
  const bundled = ST.bundledSkills||[];
  const skills = ST.skills||[];
  const mine = skills.filter(s=>!bundled.includes(s.name));
  const flows = (ST.flows||[]).filter(p=>p.builtin);
  const head = spanel(
    srow(t('lib.version'), t('lib.versionD'), `<span class="st-val">${esc(ST.libVersion||'—')}</span>`, 'library version')
    + srow(t('lib.skills'), esc(t('lib.skillsD',{n:skills.length}))
        + (mine.length?`<div class="st-d2">${esc(t('lib.mine'))} · ${mine.length}</div>`:''),
        `<button class="st-btn" onclick="revealDir('skills')">${esc(t('dir.open'))}</button>`, 'skills skill library')
    + `<div class="st-rowsub">${schips(skills.map(s=>s.name))}</div>`);
  const flowRows = flows.map(p=>srow(esc(p.label||p.name),
      ((p.steps||[]).length)+' '+t('c.steps')+' · '+esc(p.name),
      `<button class="st-btn" onclick="plRestore('${esc(p.name)}')">${esc(t('lib.restoreOne'))}</button>`,
      'restore factory workflow '+p.name)).join('');
  const flowsBlk = spanel(
    (flowRows || srow(t('lib.flows'), t('lib.flowsD',{n:0}), '', 'workflow templates flows'))
    + srow(t('lib.restore'), t('lib.resetD'),
        `<button class="st-btn st-btn-danger" onclick="resetLibrary()">${esc(t('lib.reset'))}</button>`,
        'restore factory reset builtin'),
    t('lib.flows'));
  return head + flowsBlk;
}

function secDirs(){
  const P = ST.paths||{};
  const row = (k,title,desc) => srow(title, desc,
    `<span class="st-val">${esc(P[k]||'—')}</span>
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
  const rows = [
    ['Ctrl K', t('sc.newTask'), t('sc.newTaskD'), 'shortcut new task'],
    ['Ctrl B', t('sc.toggleSb'), t('sc.toggleSbD'), 'shortcut sidebar toggle'],
    ['Ctrl ,', t('sc.settings'), t('sc.settingsD'), 'shortcut settings'],
    ['Esc', t('sc.close'), t('sc.closeD'), 'shortcut close escape'],
    ['/', t('sc.search'), t('sc.searchD'), 'shortcut search focus'],
    ['Enter', t('sc.send'), t('sc.sendD'), 'shortcut send enter revise'],
  ].map(([k,tt,d,x])=>srow(esc(tt), esc(d), skey(k), x)).join('');
  return spanel(rows, t('sc.grpGlobal'));
}

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
  return spanel(
      srow(t('up.url'), t('up.urlD'),
        `<input class="pv-input mono" style="width:340px" id="upUrl" value="${esc(u.update_url===u.default_url?'':(u.update_url||''))}"
          placeholder="${esc(t('up.urlPh'))}">
         <button class="st-btn" onclick="saveUpdUrl()">${esc(t('c.save'))}</button>`,
        'update manifest url cos')
    + srow(t('up.status'), t('up.statusD',{v:u.local||''}),
        `<span class="st-val">${esc(upStatusText(u))}</span>
         <button class="st-btn" onclick="checkNow()">${ico('refresh')}${esc(t('up.check'))}</button>`,
        'update check version status')
    + srow(t('up.apply'), t('up.applyD'), apply, 'update install apply'),
    t('up.grp'));
}

window.applyUpdate = async function(){
  const u = ST.update || {};
  if(!confirm(t('up.applyGo', {v: u.latest || ''}))) return;
  const r = await post('/api/update/apply').catch(e=>({detail:String(e)}));
  if(r && r.detail){ toast(r.detail); return; }
  toast(t('up.applyStarted'), true);
};

const MB1024 = 1048576;
const fmtBytes = n => n >= MB1024 ? (n/MB1024).toFixed(1)+' MB'
                     : n >= 1024  ? (n/1024).toFixed(0)+' KB' : (n||0)+' B';
function fmtDur(ms){
  const s = Math.round((ms||0)/1000);
  if(s < 60) return s+'s';
  const h = Math.floor(s/3600), m = Math.floor((s%3600)/60);
  return h ? h+'h '+m+'m' : m+'m '+(s%60)+'s';
}
function secStats(){
  const s = ST.stats || {};
  const bs = s.by_status || {};
  const pw = Object.entries(s.per_workflow || {}).sort((a,b)=>b[1]-a[1]);
  const orphans = s.orphans || [];
  const orphanBytes = orphans.reduce((a,o)=>a+(o.bytes||0), 0);
  return spanel(
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
    + srow(t('st.disk'), t('st.diskD',{n:s.workspaces||0}),
        `<span class="st-val">${esc(fmtBytes(s.workspace_bytes))}</span>`, 'stats disk bytes workspace')
    , t('st.grpUsage'))
  + (pw.length ? spanel(
      pw.map(([k,v])=>srow(esc(k), t('st.perFlowD'),
        `<span class="st-val">${v}</span>`, 'stats per workflow')).join(''), t('st.grpFlows')) : '')
  + spanel(
      srow(t('st.orphans'), t('st.orphansD'),
        orphans.length
          ? `<span class="st-state no"><i></i>${orphans.length} · ${esc(fmtBytes(orphanBytes))}</span>`
          : `<span class="st-state ok"><i></i>${esc(t('st.none'))}</span>`,
        'stats orphan leftover cleanup')
    , t('st.grpClean'));
}

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
    + srow(t('dir.data'), '', `<span class="st-val">${esc((ST.paths||{}).data||'—')}</span>`, 'data folder path'),
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
                    runtime:secRuntime, library:secLibrary, dirs:secDirs,
                    shortcuts:secShortcuts, stats:secStats, update:secUpdate, about:secAbout};
const SEC_FLAT = () => SET_SECTIONS.flatMap(g=>g.items);
const secTitle = id => { const s = SEC_FLAT().find(x=>x[0]===id); return s? t(s[1]) : ''; };

function settingsMain(){
  if(SET_Q.trim()){
    return `<div class="st-h1">${esc(t('set.search'))}</div>
      <div class="st-hsub">${esc(SET_Q.trim())}</div>`
      + SET_SECTIONS.flatMap(g=>g.items).map(([id])=>
          `<div data-sec="${id}"><div class="st-h2">${esc(secTitle(id))}</div>${sectionBody(id)}</div>`).join('');
  }
  const sub = t('set.'+SET_SECTION+'D');
  return `<div class="st-h1">${esc(secTitle(SET_SECTION))}</div>
    ${sub?`<div class="st-hsub">${esc(sub)}</div>`:''}${sectionBody(SET_SECTION)}`;
}
function sectionBody(id){ return (SEC_RENDER[id]||secAppearance)(); }


window.renderSettings = async function(section){
  viewLoading();
  if(section && section!=='settings') SET_SECTION = section;
  const [r, ag, sk, pl, rn, hp, up, st] = await Promise.all([
    api('/api/providers').catch(()=>({presets:[],default:null})),
    api('/api/agents').catch(()=>null),
    api('/api/skills').catch(()=>({skills:[]})),
    api('/api/pipelines').catch(()=>({pipelines:[]})),
    api('/api/runs').catch(()=>({runs:[]})),
    api('/api/health').catch(()=>({})),
    api('/api/update').catch(()=>null),
    api('/api/stats').catch(()=>null),
  ]);
  ST.update = up || null; ST.stats = st || null;
  PRESETS = r.presets||[]; ST.presets = PRESETS; ST.defaultPreset = r.default||null;
  ST.skills = sk.skills||[]; ST.flows = pl.pipelines||[]; ST.runs = rn.runs||[];
  if(ag){
    ST.agents = ag.agents||[]; ST.defaultEngine = ag.default_engine||'';
    ST.claudeCli = ag.claude_cli||''; ST.codexCli = ag.codex_cli||'';
    ST.libVersion = ag.library_version||''; ST.paths = ag.paths||{};
    ST.agentTimeout = ag.agent_timeout; ST.codexSandbox = ag.codex_sandbox;
    ST.sandboxOptions = ag.sandbox_options||[];
    ST.effortOptions = ag.effort_options||['auto'];
    ST.reasoningEffort = ag.reasoning_effort||'auto';
    ST.stepRetry = ag.step_retry||'0'; ST.autoContinue = ag.auto_continue||'0';
    ST.bundledSkills = ag.bundled_skills||[];
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
    sec.querySelectorAll('.st-block').forEach(bl=>{
      let shown = 0;
      bl.querySelectorAll('.st-row').forEach(r=>{
        const on = !q || (r.dataset.k||'').includes(q);
        r.classList.toggle('st-hidden', !on);
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
window.resetLibrary = async function(){
  if(!confirm(t('lib.resetConfirm'))) return;
  const r = await post('/api/library/reset').catch(e=>({detail:String(e)}));
  if(r.detail){ toast(r.detail); return; }
  toast(t('lib.resetDone',{n:r.skills_copied, m:(r.pipelines_reset||[]).length}), true);
  await loadAgents(); renderSettings();
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
  const prov=document.getElementById('pfProvider'); if(prov) prov.value=x.provider==='anthropic'?'anthropic':'openai';
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
    const r=await post('/api/models/list',{api_base:base, api_key:key, provider});
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
  const body={name:name.trim(), provider, api_base:api_base.trim(), model:model.trim(),
              extra:{display_name:name.trim(), site:(picked&&picked.site)||''}};
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
  const r=await post('/api/providers/test',{provider:p.provider, api_base:p.api_base, api_key:p.api_key, model:p.model})
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
  const mod = e.ctrlKey || e.metaKey;
  const inSettings = ()=>{ const a=document.getElementById('app'); return !!(a && a.dataset.shell==='settings'); };
  if(mod && !e.shiftKey && !e.altKey){
    const k = (e.key||'').toLowerCase();
    if(k==='k'){ e.preventDefault(); window.taskModal(); return; }
    if(k==='b'){ e.preventDefault(); window.sbToggle(); return; }
    if(k===','){ e.preventDefault(); nav.go('settings'); return; }
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
