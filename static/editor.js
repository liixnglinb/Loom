/* FlowForge 流水线编排器 —— 配置驱动模板编辑（独立于 app.js，避免侵入）
 * 路由: #/pipelines（列表） / #/pipeline-edit/<name>（编辑器，name 为 new 时新建）
 * 依赖 app.js 已加载的公共设施: $, $$, esc, toast, api, post, nav, viewTransitionIn
 */
(function(){
"use strict";

/* ---------------- 本地工具（app.js 的 $/esc/toast 是模块内私有，这里自带实现） ---------------- */
const $ = s => document.querySelector(s);
const $$ = s => Array.from(document.querySelectorAll(s));
function esc(s){ return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;'); }
let _toastTimer = null;
function toast(msg, ok=false){
  const el = $('#toast');
  if(!el) return;
  el.textContent = msg||'';
  el.className = 'toast show '+(ok?'ok':'err');
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(()=>{ el.className='toast'; }, 2000);
}
async function _api(path, opts){
  const r = await fetch(path, opts);
  const ct = r.headers.get('content-type')||'';
  if(ct.includes('application/json')) return r.json();
  if(!r.ok) throw new Error('HTTP '+r.status);
  return r.text();
}
function _post(path, data){
  return _api(path, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data||{})});
}

/* ---------------- 状态 ---------------- */
let PL_TPLS = [];        // 全部模板
let PL_SKILLS = [];      // 可绑定 skill 名列表
let PL_PRESETS = [];     // API 预设（模型下拉）
let PL_EDIT = null;      // 当前编辑中的模板 {name,label,desc,emoji,g,builtin,steps:[...]}

/* ---------------- 数据加载 ---------------- */
async function plLoad(){
  try{
    const [pips, sks, provs] = await Promise.all([
      _api('/api/pipelines'),
      _api('/api/skills').catch(()=>({skills:[]})),
      _api('/api/providers').catch(()=>({presets:[]})),
    ]);
    PL_TPLS = pips.pipelines || [];
    PL_SKILLS = (sks.skills || []).map(s=>s.name);
    PL_PRESETS = provs.presets || [];
  }catch(e){ PL_TPLS=[]; }
}

/* ---------------- 视图：模板列表 ---------------- */
window.renderPipelines = async function(){
  $('#view').innerHTML = '<div class="loading-bar"></div>';
  await plLoad();
  const builtin = PL_TPLS.filter(p=>p.builtin);
  const custom  = PL_TPLS.filter(p=>!p.builtin);
  const card = p => `
    <div class="card pl-card ${p.builtin?'':'pl-card-custom'}">
      <div class="pl-card-head">
        <span class="pl-emoji">${p.emoji||'🧩'}</span>
        <div class="pl-card-main">
          <div class="pl-name">${esc(p.label||p.name)} ${p.builtin?'<span class="pl-badge">内置</span>':''}</div>
          <div class="pl-sub"><code>${esc(p.name)}</code> · ${p.steps.length} 步</div>
        </div>
      </div>
      <p class="pl-desc">${esc(p.desc||'')}</p>
      <div class="pl-steps-preview">
        ${p.steps.map((s,i)=>`<span class="pl-step-chip" title="${esc(s.skill)}">${i+1}. ${esc(s.label)}</span>`).join('<span class="pl-arrow">→</span>')}
      </div>
      <div class="pl-actions">
        ${p.builtin
          ? `<button class="btn btn-ghost btn-sm" onclick="plDuplicate('${esc(p.name)}')">另存为副本编辑</button>`
          : `<button class="btn btn-primary btn-sm" onclick="nav.go('pipeline-edit/${esc(p.name)}')">编辑</button>
             <button class="btn btn-ghost btn-sm pl-danger" onclick="plDelete('${esc(p.name)}')">删除</button>`}
      </div>
    </div>`;
  $('#view').innerHTML = `
    <div class="page-head">
      <div><h1>流水线编排</h1><div class="sub">自定义模板：步骤数量、名称、每步绑定的 skill 与模型，全部由你决定</div></div>
      <button class="btn btn-primary" onclick="nav.go('pipeline-edit/new')">＋ 新建模板</button>
    </div>
    <div class="pl-grid">
      ${builtin.map(card).join('')}
      ${custom.map(card).join('')}
    </div>
    ${custom.length===0?`<div class="muted" style="text-align:center;padding:24px">还没有自建模板 —— 把内置模板「另存为副本」，或从零新建一个。</div>`:''}
  `;
};

window.plDuplicate = async function(name){
  const base = PL_TPLS.find(p=>p.name===name); if(!base) return;
  let nn = name + '-copy', k = 2;
  while(PL_TPLS.some(p=>p.name===nn)) nn = `${name}-copy${k++}`;
  const label = prompt('副本名称：', base.label + ' 副本');
  if(label===null) return;
  const r = await _post(`/api/pipelines/${encodeURIComponent(name)}/duplicate`,
    {name: nn, label, steps: base.steps}).catch(e=>({detail:e.message||'复制失败'}));
  if(r.detail){ toast(r.detail); return; }
  toast('已创建副本「'+label+'」');
  nav.go('pipeline-edit/'+r.name);
};

window.plDelete = async function(name){
  if(!confirm('确定删除模板「'+name+'」？已创建的工作流不受影响。')) return;
  const r = await _api(`/api/pipelines/${encodeURIComponent(name)}`, {method:'DELETE'})
    .catch(e=>({detail:e.message||'删除失败'}));
  if(r.detail){ toast(r.detail); return; }
  toast('已删除');
  renderPipelines();
};

/* ---------------- 视图：模板编辑器 ---------------- */
window.renderPipelineEdit = async function(name){
  $('#view').innerHTML = '<div class="loading-bar"></div>';
  await plLoad();
  if(name && name !== 'new'){
    const p = PL_TPLS.find(x=>x.name===name);
    if(!p){ toast('模板不存在'); nav.go('pipelines'); return; }
    PL_EDIT = JSON.parse(JSON.stringify(p));   // 深拷贝编辑
    if(PL_EDIT.builtin) PL_EDIT.builtin = 0;   // 编辑内置时视为副本流程（保存要求改名）
  }else{
    PL_EDIT = {name:'', label:'', desc:'', emoji:'🧩', g:'custom', builtin:0,
      steps:[{key:'step1', label:'第一步', skill:(PL_SKILLS[0]||''), out:'OUTPUT.md',
              checkpoint:false, role:'executor', check:'', model:''}]};
  }
  plDrawEditor();
};

function plSyncInputs(){
  /* 重绘会重建 DOM —— 先把输入框里未保存的值回写状态，避免丢失 */
  const E = PL_EDIT; if(!E) return;
  const nameEl = document.getElementById('plName');
  const labelEl = document.getElementById('plLabel');
  const emojiEl = document.getElementById('plEmoji');
  const groupEl = document.getElementById('plGroup');
  if(!E.name && nameEl && nameEl.value.trim()) E._draftName = nameEl.value.trim();
  if(labelEl) E.label = labelEl.value;
  if(emojiEl) E.emoji = emojiEl.value;
  if(groupEl) E.g = groupEl.value;
}
function plDrawEditor(){
  plSyncInputs();
  const E = PL_EDIT;
  const isNew = !E.name;
  const skillOpts = sel => PL_SKILLS.map(s=>`<option value="${esc(s)}" ${s===sel?'selected':''}>${esc(s)}</option>`).join('');
  const stepRow = (s,i) => `
    <div class="pl-step" data-i="${i}">
      <div class="pl-step-no">${i+1}</div>
      <div class="pl-step-body">
        <div class="pl-row">
          <input class="fi" placeholder="步骤名称（如：赛题分析）" value="${esc(s.label)}" oninput="plSet(${i},'label',this.value)" style="flex:1.4">
          <input class="fi mono" placeholder="key（英文标识，唯一）" value="${esc(s.key)}" oninput="plSet(${i},'key',this.value)" style="flex:1">
          <select class="fi" onchange="plSet(${i},'role',this.value)" title="角色">
            ${['executor','reviewer','editor'].map(r=>`<option value="${r}" ${s.role===r?'selected':''}>${r}</option>`).join('')}
          </select>
        </div>
        <div class="pl-row">
          <select class="fi mono" onchange="plSet(${i},'skill',this.value)" style="flex:2" title="绑定的 SKILL（可多选的组合写在自定义里）">
            ${s.skill && !PL_SKILLS.includes(s.skill.split(' ')[0])
              ? `<option value="${esc(s.skill)}" selected>${esc(s.skill)}（自定义组合）</option>` : ''}
            ${skillOpts((s.skill||'').split(' ')[0])}
          </select>
          <input class="fi" placeholder="产物文件（如 OUT.md）" value="${esc(s.out||'')}" oninput="plSet(${i},'out',this.value)" style="flex:1">
          <select class="fi" onchange="plSet(${i},'model',this.value)" title="本步使用的模型（默认=跟随全局）">
            <option value="">默认（跟随全局）</option>
            ${PL_PRESETS.map(p=>`<option value="${esc(p.name)}" ${s.model===p.name?'selected':''}>预设：${esc(p.name)}</option>`).join('')}
            ${s.model && !PL_PRESETS.some(p=>p.name===s.model) ? `<option value="${esc(s.model)}" selected>${esc(s.model)}</option>`:''}
          </select>
        </div>
        <div class="pl-row pl-row-sub">
          <label class="pl-check"><input type="checkbox" ${s.checkpoint?'checked':''} onchange="plSet(${i},'checkpoint',this.checked)"> 人工检查点（此步后暂停）</label>
          <input class="fi mono" placeholder="自检脚本（可空，如 step_audit.py prob）" value="${esc(s.check||'')}" oninput="plSet(${i},'check',this.value)" style="flex:1">
          <span class="pl-skill-hint" title="skill 组合（空格分隔多个）：">多 skill 组合：</span>
          <input class="fi mono" placeholder="skill-a skill-b" value="${esc(s.skill||'')}" oninput="plSet(${i},'skill',this.value)" style="flex:1.2">
        </div>
      </div>
      <div class="pl-step-ops">
        <button class="pl-op" title="上移" onclick="plMove(${i},-1)" ${i===0?'disabled':''}>↑</button>
        <button class="pl-op" title="下移" onclick="plMove(${i},1)" ${i===E.steps.length-1?'disabled':''}>↓</button>
        <button class="pl-op pl-op-del" title="删除步骤" onclick="plDel(${i})">✕</button>
      </div>
    </div>`;
  $('#view').innerHTML = `
    <div class="page-head">
      <div><h1>${isNew?'新建模板':'编辑模板'}${E.label?` · ${esc(E.label)}`:''}</h1>
        <div class="sub">步骤顺序即执行顺序；每步产出文件写入工作区，后续步骤可引用</div></div>
      <div style="display:flex;gap:10px">
        <button class="btn btn-ghost" onclick="nav.go('pipelines')">取消</button>
        <button class="btn btn-primary" onclick="plSave()">保存模板</button>
      </div>
    </div>
    <div class="card pl-meta">
      <div class="pl-row">
        <input class="fi" id="plName" placeholder="模板名（英文小写，如 my-pipeline）" value="${esc(isNew?'':E.name)}" ${isNew?'':'disabled'} style="flex:1">
        <input class="fi" id="plLabel" placeholder="显示名称（如：我的国赛冲刺流）" value="${esc(E.label)}" oninput="plEdit('label',this.value)" style="flex:1.6">
        <input class="fi" id="plEmoji" placeholder="图标 emoji" value="${esc(E.emoji)}" oninput="plEdit('emoji',this.value)" style="flex:.5;max-width:110px">
        <select class="fi" id="plGroup" onchange="plEdit('g',this.value)" style="max-width:150px">
          <option value="comp" ${E.g==='comp'?'selected':''}>竞赛类</option>
          <option value="custom" ${E.g==='custom'?'selected':''}>自定义</option>
          <option value="research" ${E.g==='research'?'selected':''}>学术研究</option>
        </select>
      </div>
      <textarea class="fi pl-desc-in" rows="2" placeholder="模板描述（创建工作流时会展示）" oninput="plEdit('desc',this.value)">${esc(E.desc||'')}</textarea>
    </div>
    <div class="pl-steps-head">
      <span class="panel-title">步骤清单（${E.steps.length}）</span>
      <button class="btn btn-ghost btn-sm" onclick="plAdd()">＋ 添加步骤</button>
    </div>
    <div id="plSteps">${E.steps.map(stepRow).join('')}</div>`;
}

/* ---------------- 编辑操作 ---------------- */
window.plEdit = function(k, v){
  PL_EDIT[k] = v;
  const el = {label:'plLabel', emoji:'plEmoji', desc:null, g:'plGroup'}[k];
  if(el){
    const node = document.getElementById(el);
    if(node && node.value !== v) node.value = v;   // 编程式修改同步到输入框
  }
};
window.plSet = function(i, k, v){
  PL_EDIT.steps[i][k] = (k==='checkpoint') ? !!v : v;
  if(k==='key'){ /* 实时无校验，保存时统一校验 */ }
};
window.plAdd = function(){
  const n = PL_EDIT.steps.length + 1;
  PL_EDIT.steps.push({key:'step'+n, label:'第'+n+'步', skill:(PL_SKILLS[0]||''),
    out:'STEP'+n+'.md', checkpoint:false, role:'executor', check:'', model:''});
  plDrawEditor();
};
window.plDel = function(i){
  PL_EDIT.steps.splice(i,1);
  if(!PL_EDIT.steps.length){
    PL_EDIT.steps.push({key:'step1', label:'第一步', skill:(PL_SKILLS[0]||''), out:'OUTPUT.md',
      checkpoint:false, role:'executor', check:'', model:''});
  }
  plDrawEditor();
};
window.plMove = function(i, d){
  const j = i + d;
  if(j<0 || j>=PL_EDIT.steps.length) return;
  const a = PL_EDIT.steps;
  [a[i], a[j]] = [a[j], a[i]];
  plDrawEditor();
};

/* ---------------- 保存 ---------------- */
window.plSave = async function(){
  const E = PL_EDIT;
  plSyncInputs();
  let name = E.name || E._draftName || ($('#plName') && $('#plName').value || '').trim();
  if(!name){ toast('请填写模板名'); return; }
  const payload = {
    name, label: (($('#plLabel') && $('#plLabel').value) || E.label || '').trim() || name,
    desc: E.desc||'', emoji: E.emoji||'', g: E.g||'custom',
    steps: E.steps.map(s=>({
      key:(s.key||'').trim(), label:(s.label||'').trim(),
      skill:(s.skill||'').trim(), out:(s.out||'').trim(),
      checkpoint:!!s.checkpoint, role:s.role||'executor',
      check:(s.check||'').trim(), model:(s.model||'').trim(),
    })),
  };
  const isNew = !E.name;
  const url = isNew ? '/api/pipelines' : `/api/pipelines/${encodeURIComponent(E.name)}`;
  const r = await (isNew ? _post(url, payload)
    : _api(url, {method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify({...payload, name:undefined})}))
    .catch(e=>({detail:e.message||'保存失败'}));
  if(r.detail){ toast(r.detail); return; }
  toast('模板已保存');
  nav.go('pipelines');
};


})();
