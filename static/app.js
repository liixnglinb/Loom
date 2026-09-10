/* ==========================================================================
 * FlowForge 智模流水线 · 极简单页应用
 * 路由：#/home（首页 = 我创建的流程） / #/skills（技能库） / #/settings（设置）
 * 流程编排与技能编辑器在 editor.js（window.renderPipelines / renderSkills / …）
 * ========================================================================== */
(() => {
'use strict';

/* ---------------- 工具 ---------------- */
const $ = s => document.querySelector(s);
const $$ = s => Array.from(document.querySelectorAll(s));

function esc(s){ return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

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
function del(path){
  return api(path, {method:'DELETE'});
}

let toastTimer=null;
function toast(msg, ok=false){
  const el = $('#toast');
  if(!el) return;
  el.textContent = msg||'';
  el.className = 'toast show '+(ok?'ok':'err');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(()=>{ el.className='toast'; }, 2400);
}

function relDate(str){
  if(!str) return '';
  const d = new Date(str.replace(' ', 'T'));
  if(isNaN(d)) return str;
  const diff = (Date.now()-d.getTime())/1000;
  if(diff < 60) return '刚刚';
  if(diff < 3600) return Math.floor(diff/60)+' 分钟前';
  if(diff < 86400) return Math.floor(diff/3600)+' 小时前';
  if(diff < 86400*30) return Math.floor(diff/86400)+' 天前';
  return str.slice(0,10);
}

/* ---------------- 状态 ---------------- */
const ST = { presets:[], defaultPreset:null };

/* ---------------- 布局（顶部导航） ---------------- */
const NAV = [
  {id:'home', label:'我的流程'},
  {id:'skills', label:'技能库'},
];

function renderNav(active){
  $('#mainNav').innerHTML = NAV.map(n=>
    `<a class="tn-link ${n.id===active?'active':''}" data-v="${n.id}" onclick="nav.go('${n.id}')">${n.label}</a>`).join('');
}

/* ---------------- 路由 ---------------- */
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
  v.classList.remove('mf-enter');
  void v.offsetWidth;
  v.classList.add('mf-enter');
}

let NAV_SEQ=0;
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
    const path = location.pathname;
    if(!raw){
      if(path==='/pipelines') raw='pipelines';
      else if(path==='/skills') raw='skills';
      else if(path==='/settings') raw='settings';
      else if(/^\/pipeline-edit/.test(path)) raw='pipeline-edit';
      else if(/^\/skill-edit/.test(path)) raw='skill-edit';
      else raw='home';
    }
    const [view, ...rest] = raw.split('/');
    const extra = rest.join('/');
    viewTransitionOut().then(async ()=>{
      if(seq!==NAV_SEQ) return;
      if(view==='skills'){ await window.renderSkills(); renderNav('skills'); }
      else if(view==='skill-edit'){ await window.renderSkillEdit(extra); renderNav('skills'); }
      else if(view==='pipelines'){ await window.renderPipelines(); renderNav('home'); }
      else if(view==='pipeline-edit'){ await window.renderPipelineEdit(extra); renderNav('home'); }
      else if(view==='settings'){ await renderSettings(); renderNav(''); }
      else { await renderHome(); renderNav('home'); }
      if(seq===NAV_SEQ) viewTransitionIn();
    });
  },
};
window.nav = nav;
window.addEventListener('hashchange', ()=>nav.resolve());

/* ================= 视图：首页（我创建的流程） ================= */
async function renderHome(){
  $('#view').innerHTML = '<div class="loading-bar"></div>';
  const r = await api('/api/pipelines').catch(()=>({pipelines:[]}));
  const tpls = r.pipelines||[];
  const card = p => `
    <div class="card pl-card" onclick="nav.go('pipeline-edit/${esc(p.name)}')">
      <div class="pl-card-head">
        <span class="pl-emoji">${p.emoji||'🧩'}</span>
        <div class="pl-card-main">
          <div class="pl-name">${esc(p.label||p.name)}</div>
          <div class="pl-sub"><code>${esc(p.name)}</code> · ${p.steps.length} 步 · ${relDate(p.updated_at)}</div>
        </div>
      </div>
      <p class="pl-desc">${esc(p.desc||'（无描述）')}</p>
      <div class="pl-steps-preview">
        ${p.steps.map((s,i)=>`<span class="pl-step-chip" title="${esc(s.skill)}">${i+1}. ${esc(s.label)}</span>`).join('<span class="pl-arrow">→</span>')}
      </div>
    </div>`;

  $('#view').innerHTML = `
    <div class="page-head">
      <div><h1>我的流程</h1><div class="sub">把每一步工作交给 AI —— 步骤、绑定技能、产物文件、人工检查点，全部由你编排</div></div>
      <button class="btn btn-primary" onclick="nav.go('pipeline-edit/new')">＋ 创建流程</button>
    </div>
    ${tpls.length ? `<div class="pl-grid">${tpls.map(card).join('')}</div>`
      : `<div class="empty" style="padding:70px 0;text-align:center">
           <div style="font-size:40px;margin-bottom:14px">🧩</div>
           <div style="font-size:15px;font-weight:600;margin-bottom:6px">还没有流程</div>
           <div class="muted" style="margin-bottom:18px">创建你的第一个流程：几个步骤、每步一个技能，串成一条流水线</div>
           <button class="btn btn-primary" onclick="nav.go('pipeline-edit/new')">＋ 创建流程</button>
         </div>`}
  `;
}

/* ================= 视图：设置 ================= */
let PV_FILTER = {q:''};
let PRESETS = [];

async function renderSettings(){
  $('#view').innerHTML = '<div class="loading-bar"></div>';
  const r = await api('/api/providers').catch(()=>({presets:[],default:null}));
  PRESETS = r.presets||[];
  ST.presets = PRESETS;
  ST.defaultPreset = r.default||null;

  $('#view').innerHTML = `
    <div style="max-width:1240px;margin:0 auto">
    <div class="page-head"><div><h1>设置</h1><div class="sub">配置 AI 模型端点（Anthropic / OpenAI 兼容协议）</div></div></div>

    <div class="card">
      <div class="card-h">
        <div><div class="ct">模型预设</div><div class="cs">执行流程时由外部 CLI 使用此处配置的端点</div></div>
        <button class="btn btn-accent" onclick="pfOpenNew()"><span class="btn-plus">＋</span> 新增预设</button>
      </div>
      <div class="set-row" id="presetList"></div>
    </div>

    <div class="card">
      <div class="card-h"><div><div class="ct">关于</div></div></div>
      <div class="setting-row"><div class="k">版本</div><div class="v mono" id="ffVer">…</div></div>
      <div class="muted" style="text-align:center;font-size:12px;color:var(--faint);padding:10px 0 4px">FlowForge 智模流水线</div>
    </div>
    </div>`;
  api('/api/health').then(h=>{ const el=$('#ffVer'); if(el) el.textContent='v'+(h.version||''); }).catch(()=>{});
  drawPresetList();
}

function drawPresetList(){
  const list=document.getElementById('presetList'); if(!list) return;
  if(!PRESETS.length){ list.innerHTML='<div class="pf-empty">暂无预设。点击右上角「新增预设」创建第一个模型连接</div>'; return; }
  const items=[...PRESETS].sort((a,b)=>(a.id||0)-(b.id||0));
  const protoBadge = p => (p.provider||'openai')==='anthropic' ? '<span class="pr-tag">Anthropic</span>' : '<span class="pr-tag">OpenAI</span>';
  list.innerHTML=items.map(p=>{
    const isCur=!!p.is_default;
    const url=(p.extra&&p.extra.site)||p.api_base||'';
    const urlRow = url ? `<a class="pf-url" href="${esc(url)}" target="_blank" rel="noreferrer">${esc(url)}</a>` : '';
    const dispName=esc((p.extra&&p.extra.display_name)||p.name);
    const letter=(dispName||'?').slice(0,1).toUpperCase();
    const brand=pfBrandColor(p.name);
    return `<div class="pf-preset ${isCur?'pf-preset-default':''}">
      <div class="pf-preset-left">
        <span class="pf-brand" style="background:${brand}">${esc(letter)}</span>
        <div class="pf-preset-main">
          <div class="pf-preset-title"><span class="pf-name">${dispName}</span>${protoBadge(p)}</div>
          <div class="pf-preset-meta">${urlRow}</div>
        </div>
      </div>
      <div class="pf-preset-ops">
        ${isCur
          ? `<button class="pf-inuse" disabled>使用中</button>`
          : `<button class="pf-op pf-op-start" title="设为默认" onclick="pfSetDefault(${p.id})">▶ 启动</button>`}
        <button class="pf-op" title="编辑" onclick="pfEdit(${p.id})">✎</button>
        <button class="pf-op" title="检测连通" onclick="pfTest(${p.id})">⇌</button>
        <button class="pf-op pf-op-danger" title="${isCur?'使用中的预设不可删除':'删除'}" ${isCur?'disabled style="opacity:.35;cursor:not-allowed"':''} onclick="pfDel(${p.id})">🗑</button>
      </div>
    </div>`;
  }).join('');
}

function pfBrandColor(name){
  const palette={'深':'#2563eb','阿':'#ff6a00','智':'#38bdf8','月':'#111827','豆':'#3b82f6','火':'#f97316','M':'#f43f5e','硅':'#0ea5e9','百':'#2954f5'};
  return palette[(name||'?').slice(0,1)]||'#9aa2ad';
}

/* ---------------- 预设弹窗（新增 / 编辑） ---------------- */
let PF_EDIT=null;   // null=新增；{id,...}=编辑
function pfOpenNew(){ pfOpenModal(null); }
window.pfOpenNew = pfOpenNew;

function pfOpenModal(p, pid){
  PF_EDIT = p ? {pid, ...p} : null;
  _lockScroll(true);
  const cat = window.PROVIDER_CATALOG||[];
  const grid = cat.map(t=>{
    const letter=(t.name||'?').slice(0,1).toUpperCase();
    const logo = t.logo ? `<img class="pv-ico-img" src="/static/logos/${esc(t.logo)}.png" onerror="this.outerHTML='<span class=&quot;pv-ico&quot;>${esc(letter)}</span>'" alt="">` : `<span class="pv-ico">${esc(letter)}</span>`;
    return `<div class="pv-item ${p&&p.name===t.name?'pv-sel':''}" data-name="${esc(t.name)}" onclick="pfPick('${esc(t.name)}')">${logo}<span class="pv-name">${esc(t.name)}</span></div>`;
  }).join('') + `<div class="pv-item pv-item-custom ${(!p||p.__custom__)?'pv-sel':''}" data-name="__custom__" onclick="pfPickCustom()"><span class="pv-ico pv-ico-custom">＋</span><span class="pv-name">自定义预设</span></div>`;

  const root=document.createElement('div');
  root.id='pfModalRoot';
  root.innerHTML=`<div class="modal open" onclick="if(event.target===this)pfCloseModal()">
    <div class="modal-box pv-modal" style="width:min(760px,94vw)">
      <div class="modal-top">
        <div class="pv-head"><h3>${p?'编辑预设':'新增预设'}</h3></div>
        <button class="modal-x" onclick="pfCloseModal()">×</button>
      </div>
      <div class="pv-scroll" style="padding:14px 18px">
        ${p?'':`
        <div class="pv-search-wrap"><input class="pv-input" id="pfQ" placeholder="搜索供应商…" oninput="pfDrawQ()"></div>
        <div class="pv-grid" id="pfGrid">${grid}</div>
        <div class="pv-divider"></div>`}
        <div class="pv-form">
          <div class="pv-row2">
            <div class="pv-f"><label class="pv-label">显示名称 <b class="req">*</b></label>
              <input class="pv-input" id="pfDisp" placeholder="如 深度求索" value="${esc((p&&(p.extra&&p.extra.display_name||p.name))||'')}"></div>
            <div class="pv-f"><label class="pv-label">协议</label>
              <select class="pv-input" id="pfProvider">
                <option value="anthropic" ${!p||p.provider==='anthropic'?'selected':''}>Anthropic Messages</option>
                <option value="openai" ${p&&p.provider==='openai'?'selected':''}>OpenAI 兼容</option>
              </select></div>
          </div>
          <div class="pv-f"><label class="pv-label">API 端点 (Base URL) <b class="req">*</b></label>
            <input class="pv-input mono" id="pfBase" placeholder="https://api.example.com/anthropic" value="${esc(p?p.api_base:'')}"></div>
          <div class="pv-f"><label class="pv-label">API Key ${p?'<span class="muted" style="font-weight:400">(留空保留原 Key)</span>':'<b class="req">*</b>'}</label>
            <input class="pv-input mono" id="pfKey" type="password" placeholder="${p?'':'sk-…'}" value=""></div>
          <div class="pv-f"><label class="pv-label">模型</label>
            <div style="display:flex;gap:8px;align-items:center">
              <input class="pv-input mono" id="pfModel" placeholder="如 claude-sonnet-4-5 / deepseek-chat" value="${esc(p?p.model:'')}" style="flex:1">
              <button class="btn btn-ghost btn-sm" onclick="pfFetchModels()">获取模型列表</button>
            </div></div>
          <div id="pfModels" class="pv-model-row" style="display:none"></div>
          <div class="pv-fhint" id="pfModelHint"></div>
          <div class="pv-foot-hint">端点需与所选协议匹配：Anthropic 协议填 …/anthropic 形式地址；OpenAI 兼容填 …/v1 形式地址。</div>
        </div>
      </div>
      <div class="modal-foot">
        <button class="btn btn-ghost" onclick="pfCloseModal()">取消</button>
        <button class="btn btn-primary" onclick="pfSave()">${p?'保存修改':'创建预设'}</button>
      </div>
    </div>
  </div>`;
  document.body.appendChild(root);
  if(p){ window.PF_PICKED={name:p.name, api_base:p.api_base, provider:p.provider}; }
  else window.PF_PICKED=null;
}
window.pfCloseModal=function(){
  const r=document.getElementById('pfModalRoot');
  if(r) r.remove();
  _lockScroll(false);
};
function _lockScroll(on){
  document.body.style.overflow = on?'hidden':'';
}

window.pfDrawQ=function(){
  const q=(document.getElementById('pfQ')||{}).value||'';
  const grid=document.getElementById('pfGrid'); if(!grid) return;
  const cat=window.PROVIDER_CATALOG||[];
  const items=cat.filter(t=>!q||t.name.toLowerCase().includes(q.toLowerCase()));
  grid.innerHTML=items.map(t=>{
    const letter=(t.name||'?').slice(0,1).toUpperCase();
    return `<div class="pv-item" data-name="${esc(t.name)}" onclick="pfPick('${esc(t.name)}')"><span class="pv-ico">${esc(letter)}</span><span class="pv-name">${esc(t.name)}</span></div>`;
  }).join('')+`<div class="pv-item pv-item-custom" data-name="__custom__" onclick="pfPickCustom()"><span class="pv-ico pv-ico-custom">＋</span><span class="pv-name">自定义预设</span></div>`;
};

window.pfPick=function(name){
  const t=(window.PROVIDER_CATALOG||[]).find(x=>x.name===name); if(!t) return;
  window.PF_PICKED={name:t.name, api_base:t.api_base||'', provider:t.provider||'anthropic'};
  const grid=document.getElementById('pfGrid');
  if(grid) grid.querySelectorAll('.pv-item').forEach(el=>el.classList.toggle('pv-sel',el.dataset.name===t.name));
  const disp=document.getElementById('pfDisp'); if(disp&&!disp.value.trim()) disp.value=t.name;
  const prov=document.getElementById('pfProvider'); if(prov) prov.value=t.provider==='anthropic'?'anthropic':'openai';
  const base=document.getElementById('pfBase'); if(base) base.value=t.api_base||'';
  const kl=document.getElementById('pfKeylink'); if(kl&&t.key_url){ kl.href=t.key_url; kl.style.display='inline-block'; }
};
window.pfPickCustom=function(){
  window.PF_PICKED=null;
  const grid=document.getElementById('pfGrid');
  if(grid) grid.querySelectorAll('.pv-item').forEach(el=>el.classList.toggle('pv-sel',el.dataset.name==='__custom__'));
};

window.pfFetchModels=async function(){
  const base=(document.getElementById('pfBase')||{}).value||'';
  const key=(document.getElementById('pfKey')||{}).value||'';
  if(!base){ toast('先填 API 端点'); return; }
  toast('正在获取模型列表…');
  try{
    const provider=(document.getElementById('pfProvider')||{}).value||'anthropic';
    const r=await post('/api/models/list',{api_base:base, api_key:key, provider});
    if(!r.ok){ toast('获取失败：'+(r.error||'端点不可用')); return; }
    const ids=(r.models||[]).map(x=>x.id||x.model||x.name||x).filter(Boolean).slice(0,200);
    const hint=document.getElementById('pfModelHint');
    if(hint) hint.textContent=ids.length?('可选模型：'+ids.slice(0,40).join(' · ')+(ids.length>40?` …共 ${ids.length} 个`:'')):'端点返回成功，但列表为空';
    if(ids.length) toast('已载入 '+ids.length+' 个模型', true);
  }catch(e){ toast('获取失败: '+e); }
};

window.pfSave=async function(){
  const name=(document.getElementById('pfDisp')||{}).value||'';
  const provider=(document.getElementById('pfProvider')||{}).value||'anthropic';
  const api_base=(document.getElementById('pfBase')||{}).value||'';
  const api_key=(document.getElementById('pfKey')||{}).value||'';
  const model=(document.getElementById('pfModel')||{}).value||'';
  if(!name.trim()){ toast('请填显示名称'); return; }
  if(!api_base.trim()){ toast('请填 API 端点'); return; }
  const picked=window.PF_PICKED;
  const body={name:name.trim(), provider, api_base:api_base.trim(), model:model.trim(),
              extra:{display_name:name.trim(), site:(picked&&picked.site)||''}};
  if(picked&&picked.api_base&&!api_key&&!PF_EDIT) body.api_base=picked.api_base;
  let r;
  if(PF_EDIT){
    r=await put('/api/providers/'+PF_EDIT.pid, {...body, api_key}).catch(e=>({detail:String(e)}));
  }else{
    r=await post('/api/providers', {...body, api_key}).catch(e=>({detail:String(e)}));
  }
  if(r.detail){ toast(r.detail); return; }
  toast(PF_EDIT?'已保存':'预设已创建', true);
  pfCloseModal();
  renderSettings();
};

window.pfEdit=function(id){
  const p=PRESETS.find(x=>x.id===id); if(!p) return;
  pfOpenModal({...p, __custom__:true}, id);
};
window.pfDel=async function(id){
  if(!confirm('确定删除该预设？')) return;
  const r=await del('/api/providers/'+id).catch(e=>({detail:String(e)}));
  if(r.detail){ toast(r.detail); return; }
  toast('已删除'); renderSettings();
};
window.pfSetDefault=async function(id){
  const r=await post('/api/providers/'+id+'/default').catch(e=>({detail:String(e)}));
  if(r.detail){ toast(r.detail); return; }
  toast('已设为默认预设', true); renderSettings();
};
window.pfTest=async function(id){
  const p=PRESETS.find(x=>x.id===id); if(!p) return;
  toast('正在检测连通…');
  const r=await post('/api/providers/test',{provider:p.provider, api_base:p.api_base, api_key:p.api_key, model:p.model}).catch(e=>({ok:false,msg:String(e)}));
  toast(r.ok?('连通正常'+(r.msg?'：'+r.msg:'')):('检测失败：'+(r.msg||'')), !!r.ok);
};

/* ---------------- 启动 ---------------- */
function boot(){
  renderNav('home');
  nav.resolve();
}
if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', boot);
else boot();

})();
