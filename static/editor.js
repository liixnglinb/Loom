/* FlowForge 配置中心 —— 流程编排器 + Skill 管理器（独立于 app.js）
 * 路由: #/pipelines（流程列表）   #/pipeline-edit/<name|new>（流程编排器）
 *       #/skills（技能列表）     #/skill-edit/<name|new>（技能编辑器）
 * 依赖: 无（自带 $/esc/toast/_api/_post）
 */
(function(){
"use strict";

/* ---------------- 本地工具 ---------------- */
const $ = s => document.querySelector(s);
function esc(s){ return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;'); }
let _toastTimer = null;
function toast(msg, ok=false){
  const el = $('#toast');
  if(!el) return;
  el.textContent = msg||'';
  el.className = 'toast show '+(ok?'ok':'err');
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(()=>{ el.className='toast'; }, 2400);
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
function _put(path, data){
  return _api(path, {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data||{})});
}
function _del(path){
  return _api(path, {method:'DELETE'});
}
function _lockScroll(on){
  document.body.style.overflow = on?'hidden':'';
}

/* ================= 状态 ================= */
let PL_TPLS = [];        // 流程模板
let PL_SKILLS = [];      // skill 元信息 [{name,desc,source,chars}]
let PL_EDIT = null;      // 编辑中的流程
let SK_EDIT = null;      // 编辑中的 skill {name, content, editable, isNew}
const ROLES = [
  {v:'executor',  label:'执行',   hint:'主执行步骤：产出本步文件'},
  {v:'reviewer',  label:'审查',   hint:'检查前序产物，挑问题给修正意见'},
  {v:'editor',    label:'润色',   hint:'对既有文稿做编辑改进'},
];

/* ---------------- 数据加载 ---------------- */
async function plLoad(){
  const [pips, sks] = await Promise.all([
    _api('/api/pipelines').catch(()=>({pipelines:[]})),
    _api('/api/skills').catch(()=>({skills:[]})),
  ]);
  PL_TPLS = pips.pipelines || [];
  PL_SKILLS = sks.skills || [];
}

/* =====================================================================
 * 第一部分：Skill 管理
 * ===================================================================== */

/* ---------------- 技能列表页 ---------------- */
window.renderSkills = async function(){
  $('#view').innerHTML = '<div class="loading-bar"></div>';
  await plLoad();
  const all = PL_SKILLS;
  const card = s => `
    <div class="sk-card sk-card-user" onclick="skView('${esc(s.name)}')">
      <div class="sk-card-top">
        <span class="sk-ico">✦</span>
        <div class="sk-card-main">
          <div class="sk-name">${esc(s.name)}</div>
          <div class="sk-chars">${s.chars>0?(s.chars/1000).toFixed(1)+'k 字':'空'}</div>
        </div>
      </div>
      <p class="sk-desc">${esc(s.desc||'（无简介）')}</p>
    </div>`;
  $('#view').innerHTML = `
    <div class="page-head">
      <div><h1>技能库</h1><div class="sub">skill 是每个步骤注入给 AI 的执行规范 —— 新建、导入标准 skill 包、或随时编辑</div></div>
      <div style="display:flex;gap:10px">
        <button class="btn btn-ghost" onclick="skImportModal()">⬆ 导入</button>
        <button class="btn btn-primary" onclick="nav.go('skill-edit/new')">＋ 新建技能</button>
      </div>
    </div>
    <input type="file" id="skImportFile" accept=".zip,.md" style="display:none" onchange="skImportDo(this)">
    ${all.length?`
      <div class="sk-sec-title"><span class="panel-title">我的技能（${all.length}）</span></div>
      <div class="sk-grid">${all.map(card).join('')}</div>`
    :`
      <div class="empty" style="padding:70px 0;text-align:center">
        <div style="font-size:40px;margin-bottom:14px">✦</div>
        <div style="font-size:15px;font-weight:600;margin-bottom:6px">还没有技能</div>
        <div class="muted" style="margin-bottom:18px">新建一份 Markdown 执行规范，或导入标准 skill 包（zip / SKILL.md）</div>
        <div style="display:flex;gap:10px;justify-content:center">
          <button class="btn btn-ghost" onclick="skImportModal()">⬆ 导入</button>
          <button class="btn btn-primary" onclick="nav.go('skill-edit/new')">＋ 新建技能</button>
        </div>
      </div>`}
  `;
};

/* ---------------- 导入技能 ---------------- */
window.skImportModal = function(){
  const el = document.getElementById('skImportFile');
  if(el) el.click();
};
window.skImportDo = async function(input){
  const f = input.files && input.files[0];
  input.value = '';
  if(!f) return;
  toast('正在导入「'+f.name+'」…');
  const fd = new FormData();
  fd.append('file', f);
  try{
    const r = await fetch('/api/skills/import', {method:'POST', body: fd});
    const d = await r.json().catch(()=>({detail:'HTTP '+r.status}));
    if(d.detail){ toast(d.detail); return; }
    toast('已导入「'+d.name+'」（'+d.files+' 个文件，'+(d.chars/1000).toFixed(1)+'k 字）', true);
    renderSkills();
  }catch(e){ toast('导入失败：'+e); }
};

/* ---------------- 技能详情（弹窗查看） ---------------- */
window.skView = async function(name){
  const d = await _api('/api/skills/'+encodeURIComponent(name)).catch(e=>({detail:e.message}));
  if(d.detail){ toast(d.detail); return; }
  _lockScroll(true);
  const root = document.createElement('div');
  root.id = 'skViewRoot';
  root.innerHTML = `<div class="modal open" onclick="if(event.target===this)skCloseModal()">
    <div class="modal-box sk-view-modal">
      <div class="modal-top">
        <div class="pv-head"><h3>${esc(d.name)}</h3>
          <span class="sk-badge ${d.editable?'sk-badge-user':''}">${d.editable?'自建·可编辑':'内置·只读'}</span></div>
        <button class="modal-x" onclick="skCloseModal()">×</button>
      </div>
      <div class="sk-view-body"><pre class="sk-pre">${esc(d.content)}</pre></div>
      <div class="sk-view-foot">
        <button class="btn btn-ghost btn-sm" onclick="skCloseModal()">关闭</button>
        ${d.editable
          ? `<button class="btn btn-primary btn-sm" onclick="skCloseModal();nav.go('skill-edit/${esc(d.name)}')">编辑</button>
             <button class="btn btn-ghost btn-sm pl-danger" onclick="skDelete('${esc(d.name)}')">删除</button>`
          : `<button class="btn btn-accent btn-sm" onclick="skDuplicate('${esc(d.name)}')">另存为可编辑副本</button>`}
      </div>
    </div>
  </div>`;
  document.body.appendChild(root);
};
window.skCloseModal = function(){
  const r = document.getElementById('skViewRoot');
  if(r) r.remove();
  _lockScroll(false);
};
window.skDuplicate = async function(name){
  skCloseModal();
  const nn = prompt('副本名（英文小写）：', name + '-my');
  if(nn===null) return;
  const r = await _post('/api/skills/'+encodeURIComponent(name)+'/duplicate', {name: nn.trim()})
    .catch(e=>({detail:e.message||'复制失败'}));
  if(r.detail){ toast(r.detail); return; }
  toast('已创建可编辑副本「'+r.name+'」', true);
  nav.go('skill-edit/'+r.name);
};
window.skDelete = async function(name){
  if(!confirm('确定删除自建技能「'+name+'」？引用它的流程步骤会读不到内容。')) return;
  skCloseModal();
  const r = await _del('/api/skills/'+encodeURIComponent(name))
    .catch(e=>({detail:e.message||'删除失败'}));
  if(r.detail){ toast(r.detail); return; }
  toast('已删除'); renderSkills();
};

/* ---------------- 技能编辑器 ---------------- */
window.renderSkillEdit = async function(name){
  $('#view').innerHTML = '<div class="loading-bar"></div>';
  if(name && name !== 'new'){
    const d = await _api('/api/skills/'+encodeURIComponent(name)).catch(e=>({detail:e.message}));
    if(d.detail){ toast(d.detail); nav.go('skills'); return; }
    SK_EDIT = {name: d.name, content: d.content, editable: d.editable, isNew: false};
    if(!d.editable){ toast('内置技能只读 —— 请「另存为可编辑副本」后修改'); }
  }else{
    SK_EDIT = {name:'', content:'', editable:true, isNew:true};
  }
  skDrawEditor();
};

function skDrawEditor(){
  const E = SK_EDIT;
  const readOnly = !E.editable;
  const lines = E.content ? E.content.split('\n').length : 0;
  $('#view').innerHTML = `
    <div class="page-head">
      <div><h1>${E.isNew?'新建技能':(readOnly?'查看技能':'编辑技能')}${E.name?` · ${esc(E.name)}`:''}</h1>
        <div class="sub">SKILL.md 全文就是执行该步骤时注入给 AI 的完整指令 —— 写清楚目标、输入、产出与硬性规则</div></div>
      <div style="display:flex;gap:10px">
        <button class="btn btn-ghost" onclick="skBack()">返回</button>
        ${!readOnly?`<button class="btn btn-primary" onclick="skSave()">保存技能</button>`:''}
      </div>
    </div>
    <div class="card sk-edit-card">
      ${E.isNew?`
      <div class="sk-field">
        <label class="pv-label">技能名（英文小写，步骤里引用它） <b class="req">*</b></label>
        <input class="pv-input mono" id="skName" placeholder="如 my-review-checklist" maxlength="64">
        <div class="sk-hint">只能小写字母/数字/连字符/下划线；在流程编排里以这个名字绑定到步骤</div>
      </div>`:''}
      <div class="sk-field sk-grow">
        <label class="pv-label">技能内容（Markdown） <b class="req">*</b></label>
        <textarea class="pv-input mono sk-content" id="skContent" ${readOnly?'readonly':''}
          placeholder="# 我的技能\n\n## 目标\n这一步要产出什么…\n\n## 输入\n读取哪些前序文件…\n\n## 硬性规则\n- 必须…\n- 禁止…"
          oninput="skSync()">${esc(E.content)}</textarea>
        <div class="sk-hint"><span id="skCount">${lines}</span> 行 · 保存后立即生效</div>
      </div>
    </div>`;
  if(!readOnly) setTimeout(()=>{ const t=document.getElementById('skContent'); if(t && E.isNew) t.focus(); }, 50);
}
window.skSync = function(){
  const t = document.getElementById('skContent');
  const c = document.getElementById('skCount');
  if(t && c) c.textContent = t.value ? t.value.split('\n').length : 0;
  if(t) SK_EDIT.content = t.value;
};
window.skBack = function(){ nav.go('skills'); };
window.skSave = async function(){
  const E = SK_EDIT;
  const content = ($('#skContent') && $('#skContent').value) || E.content || '';
  if(!content.trim()){ toast('技能内容不能为空'); return; }
  if(E.isNew){
    const name = ($('#skName') && $('#skName').value || '').trim();
    if(!name){ toast('请填写技能名'); return; }
    const r = await _post('/api/skills', {name, content}).catch(e=>({detail:e.message||'保存失败'}));
    if(r.detail){ toast(r.detail); return; }
    toast('技能已创建', true);
    nav.go('skills');
  }else{
    const r = await _put('/api/skills/'+encodeURIComponent(E.name), {name:E.name, content})
      .catch(e=>({detail:e.message||'保存失败'}));
    if(r.detail){ toast(r.detail); return; }
    toast('技能已保存', true);
    nav.go('skills');
  }
};

/* =====================================================================
 * 第二部分：流程编排器
 * ===================================================================== */

/* ---------------- 流程列表页 ---------------- */
window.renderPipelines = async function(){
  $('#view').innerHTML = '<div class="loading-bar"></div>';
  await plLoad();
  const card = p => `
    <div class="card pl-card pl-card-custom">
      <div class="pl-card-head">
        <span class="pl-emoji">${p.emoji||'🧩'}</span>
        <div class="pl-card-main">
          <div class="pl-name">${esc(p.label||p.name)}</div>
          <div class="pl-sub"><code>${esc(p.name)}</code> · ${p.steps.length} 步</div>
        </div>
      </div>
      <p class="pl-desc">${esc(p.desc||'')}</p>
      <div class="pl-steps-preview">
        ${p.steps.map((s,i)=>`<span class="pl-step-chip" title="${esc(s.skill)}">${i+1}. ${esc(s.label)}</span>`).join('<span class="pl-arrow">→</span>')}
      </div>
      <div class="pl-actions">
        <button class="btn btn-primary btn-sm" onclick="nav.go('pipeline-edit/${esc(p.name)}')">编辑</button>
        <button class="btn btn-ghost btn-sm" onclick="plDuplicate('${esc(p.name)}')">创建副本</button>
        <button class="btn btn-ghost btn-sm pl-danger" onclick="plDelete('${esc(p.name)}')">删除</button>
      </div>
    </div>`;
  $('#view').innerHTML = `
    <div class="page-head">
      <div><h1>流程编排</h1><div class="sub">步骤数量、名称、每步绑定的技能，全部由你决定 —— 无任何预置模板</div></div>
      <button class="btn btn-primary" onclick="nav.go('pipeline-edit/new')">＋ 创建流程</button>
    </div>
    ${PL_TPLS.length?`<div class="pl-grid">${PL_TPLS.map(card).join('')}</div>`
      :`<div class="empty" style="padding:70px 0;text-align:center">
          <div style="font-size:40px;margin-bottom:14px">🧩</div>
          <div style="font-size:15px;font-weight:600;margin-bottom:6px">还没有流程</div>
          <div class="muted" style="margin-bottom:18px">从零编排：几个步骤、每步一个技能，串成一条流水线</div>
          <button class="btn btn-primary" onclick="nav.go('pipeline-edit/new')">＋ 创建流程</button>
        </div>`}
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
  if(!confirm('确定删除流程「'+name+'」？')) return;
  const r = await _del(`/api/pipelines/${encodeURIComponent(name)}`)
    .catch(e=>({detail:e.message||'删除失败'}));
  if(r.detail){ toast(r.detail); return; }
  toast('已删除');
  renderPipelines();
};

/* ---------------- 流程编辑器 ---------------- */
window.renderPipelineEdit = async function(name){
  $('#view').innerHTML = '<div class="loading-bar"></div>';
  await plLoad();
  if(name && name !== 'new'){
    const p = PL_TPLS.find(x=>x.name===name);
    if(!p){ toast('流程不存在'); nav.go('pipelines'); return; }
    PL_EDIT = JSON.parse(JSON.stringify(p));
  }else{
    PL_EDIT = {name:'', label:'', desc:'', emoji:'🧩', g:'custom',
      steps:[plBlankStep(1)]};
  }
  plDrawEditor();
};

function plBlankStep(n){
  return {key:'step'+n, label:'第'+n+'步', skill:(PL_SKILLS[0]?PL_SKILLS[0].name:''),
    extra_skills:[], out:'STEP'+n+'.md', checkpoint:false, role:'executor', model:''};
}
/* 兼容旧数据：把 "a b c" 空格组合拆成 主技能 + 叠加技能 */
function plNormalizeSteps(){
  for(const s of PL_EDIT.steps){
    const parts = String(s.skill||'').trim().split(/\s+/).filter(Boolean);
    s.skill = parts[0] || '';
    s.extra_skills = Array.isArray(s.extra_skills) ? s.extra_skills
      : parts.slice(1);
  }
}

const EMOJIS = ['🧩','⚡','🏆','🧪','🚀','🎯','📚','🔧','🧠','💡','📊','🛡️','⚗️','🔬','✍️','🧭','⚙️','🌟'];

function plSyncInputs(){
  const E = PL_EDIT; if(!E) return;
  const nameEl = document.getElementById('plName');
  const labelEl = document.getElementById('plLabel');
  const descEl  = document.getElementById('plDesc');
  if(!E.name && nameEl && nameEl.value.trim()) E._draftName = nameEl.value.trim();
  if(labelEl) E.label = labelEl.value;
  if(descEl)  E.desc = descEl.value;
}

function plDrawEditor(){
  plSyncInputs();
  plNormalizeSteps();
  const E = PL_EDIT;
  const isNew = !E.name;
  const skillInfo = n => PL_SKILLS.find(s=>s.name===n) || null;
  const presetNames = (ST_PRESETS||[]).map(p=>p.name);

  /* --- 单个步骤卡片 --- */
  const stepCard = (s,i) => {
    const main = skillInfo(s.skill);
    const keyDup = E.steps.filter(x=>(x.key||'').trim()===s.key.trim()).length > 1;
    const keyBad = !/^[a-z0-9][a-z0-9_-]*$/.test((s.key||'').trim());
    return `
    <div class="step-card" data-i="${i}">
      <div class="step-rail">
        <div class="step-no">${i+1}</div>
        ${i<E.steps.length-1?'<div class="step-line"></div>':''}
      </div>
      <div class="step-body">
        <div class="step-grid">
          <div class="fld fld-wide">
            <label class="fld-l">步骤名称 <b class="req">*</b></label>
            <input class="fi" value="${esc(s.label)}" placeholder="如：赛题分析"
              oninput="plSet(${i},'label',this.value)">
          </div>
          <div class="fld">
            <label class="fld-l">标识 key <b class="req">*</b></label>
            <input class="fi mono ${keyDup||keyBad?'fld-err':''}" value="${esc(s.key)}"
              placeholder="如 analysis" oninput="plSet(${i},'key',this.value)">
            ${keyDup?'<div class="fld-err-t">key 重复，保存前需修改</div>':keyBad?'<div class="fld-err-t">小写字母/数字/连字符/下划线</div>':''}
          </div>
          <div class="fld">
            <label class="fld-l">角色</label>
            <div class="seg">
              ${ROLES.map(r=>`<button class="seg-btn ${s.role===r.v?'on':''}" title="${esc(r.hint)}"
                onclick="plSet(${i},'role','${r.v}');plDrawEditor()">${r.label}</button>`).join('')}
            </div>
          </div>
        </div>
        <div class="step-grid">
          <div class="fld fld-wide">
            <label class="fld-l">主技能 <b class="req">*</b> <a class="fld-link" onclick="nav.go('skills')">查看技能库 →</a></label>
            <select class="fi mono" onchange="plSet(${i},'skill',this.value)">
              <option value="" ${!s.skill?'selected':''}>（选择技能）</option>
              ${PL_SKILLS.map(sk=>`<option value="${esc(sk.name)}" ${s.skill===sk.name?'selected':''}>${esc(sk.name)}${sk.source==='user'?' · 自建':''}</option>`).join('')}
              ${s.skill && !PL_SKILLS.some(sk=>sk.name===s.skill)?`<option value="${esc(s.skill)}" selected>${esc(s.skill)}（已删除的技能）</option>`:''}
            </select>
            ${main?`<div class="fld-hint">${esc(main.desc)}</div>`:''}
          </div>
          <div class="fld">
            <label class="fld-l">产物文件</label>
            <input class="fi mono" value="${esc(s.out||'')}" placeholder="如 ANALYSIS.md"
              oninput="plSet(${i},'out',this.value)">
            <div class="fld-hint">写入工作区，后续步骤可引用</div>
          </div>
        </div>
        <div class="step-adv">
          <button class="step-adv-toggle" onclick="this.parentElement.classList.toggle('open')">
            <span class="adv-arrow">▸</span> 高级选项
            ${(s.model||(s.extra_skills||[]).length)?'<span class="adv-dot"></span>':''}
          </button>
          <div class="step-adv-body">
            <div class="step-grid">
              <div class="fld">
                <label class="fld-l">叠加技能（规范类，可多个）</label>
                <div class="extra-chips">
                  ${(s.extra_skills||[]).map((n,xi)=>`<span class="x-chip">${esc(n)}<b onclick="plExtraDel(${i},${xi})">×</b></span>`).join('')||'<span class="muted" style="font-size:12px">无</span>'}
                  <select class="fi fi-inline" onchange="plExtraAdd(${i},this.value);this.value=''">
                    <option value="">＋ 添加…</option>
                    ${PL_SKILLS.filter(sk=>sk.name!==s.skill && !(s.extra_skills||[]).includes(sk.name))
                      .map(sk=>`<option value="${esc(sk.name)}">${esc(sk.name)}</option>`).join('')}
                  </select>
                </div>
              </div>
              <div class="fld">
                <label class="fld-l">本步模型</label>
                <select class="fi" onchange="plSet(${i},'model',this.value)">
                  <option value="" ${!s.model?'selected':''}>跟随全局默认</option>
                  ${presetNames.map(n=>`<option value="${esc(n)}" ${s.model===n?'selected':''}>预设：${esc(n)}</option>`).join('')}
                  ${s.model && !presetNames.includes(s.model)?`<option value="${esc(s.model)}" selected>${esc(s.model)}</option>`:''}
                </select>
              </div>
            </div>
            <label class="pl-check">
              <input type="checkbox" ${s.checkpoint?'checked':''} onchange="plSet(${i},'checkpoint',this.checked)">
              人工检查点 —— 本步完成后暂停，等我确认再继续
            </label>
          </div>
        </div>
      </div>
      <div class="step-ops">
        <button class="pl-op" title="上移" onclick="plMove(${i},-1)" ${i===0?'disabled':''}>↑</button>
        <button class="pl-op" title="下移" onclick="plMove(${i},1)" ${i===E.steps.length-1?'disabled':''}>↓</button>
        <button class="pl-op pl-op-del" title="删除步骤" onclick="plDel(${i})">✕</button>
      </div>
    </div>`;
  };

  const stepsHtml = E.steps.map(stepCard).join('');
  $('#view').innerHTML = `
    <div class="page-head">
      <div><h1>${isNew?'创建流程':'编辑流程'}${E.label?` · ${esc(E.label)}`:''}</h1>
        <div class="sub">步骤从上到下依次执行；每步绑定一个技能，产物文件写入同一工作区供后续引用</div></div>
      <div style="display:flex;gap:10px">
        <button class="btn btn-ghost" onclick="nav.go('pipelines')">取消</button>
        <button class="btn btn-primary" onclick="plSave()">保存流程</button>
      </div>
    </div>
    <div class="card pl-meta">
      <div class="pl-meta-grid">
        <div class="fld ${isNew?'':'fld-plain'}">
          <label class="fld-l">流程名（英文小写，唯一） <b class="req">*</b></label>
          <input class="fi mono" id="plName" placeholder="如 my-pipeline"
            value="${esc(isNew?(E._draftName||''):E.name)}" ${isNew?'':'disabled'}>
          ${isNew?'<div class="fld-hint">创建后不可改；显示名称随时可改</div>':''}
        </div>
        <div class="fld">
          <label class="fld-l">显示名称 <b class="req">*</b></label>
          <input class="fi" id="plLabel" placeholder="如：我的国赛冲刺流" value="${esc(E.label)}"
            oninput="plEdit('label',this.value)">
        </div>
        <div class="fld fld-emoji">
          <label class="fld-l">图标</label>
          <div class="emoji-grid">
            ${EMOJIS.map(e=>`<button class="emoji-cell ${E.emoji===e?'on':''}" onclick="plEdit('emoji','${e}');plDrawEditor()">${e}</button>`).join('')}
          </div>
        </div>
      </div>
      <div class="fld">
        <label class="fld-l">流程描述</label>
        <textarea class="fi pl-desc-in" id="plDesc" rows="2"
          placeholder="写清这套流程适合什么场景"
          oninput="plEdit('desc',this.value)">${esc(E.desc||'')}</textarea>
      </div>
    </div>
    <div class="pl-steps-head">
      <span class="panel-title">步骤清单 <span class="muted">（${E.steps.length}）</span></span>
      <button class="btn btn-ghost btn-sm" onclick="plAdd()">＋ 添加步骤</button>
    </div>
    <div id="plSteps">${stepsHtml}</div>
    <div style="height:60px"></div>`;
}

/* ---------------- 编辑操作 ---------------- */
window.plEdit = function(k, v){ PL_EDIT[k] = v; };
window.plSet = function(i, k, v){
  PL_EDIT.steps[i][k] = (k==='checkpoint') ? !!v : v;
};
window.plExtraAdd = function(i, name){
  if(!name) return;
  const s = PL_EDIT.steps[i];
  s.extra_skills = s.extra_skills || [];
  if(!s.extra_skills.includes(name)) s.extra_skills.push(name);
  plDrawEditor();
};
window.plExtraDel = function(i, xi){
  PL_EDIT.steps[i].extra_skills.splice(xi,1);
  plDrawEditor();
};
window.plAdd = function(){
  const n = PL_EDIT.steps.length + 1;
  PL_EDIT.steps.push(plBlankStep(n));
  plDrawEditor();
  requestAnimationFrame(()=>{
    const cards = document.querySelectorAll('.step-card');
    const last = cards[cards.length-1];
    if(last) last.scrollIntoView({behavior:'smooth', block:'center'});
  });
};
window.plDel = function(i){
  PL_EDIT.steps.splice(i,1);
  if(!PL_EDIT.steps.length){
    PL_EDIT.steps.push(plBlankStep(1));
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
  let name = E.name || (E._draftName || '').trim() || ($('#plName') && $('#plName').value || '').trim();
  if(!name){ toast('请填写流程名'); return; }
  const label = (($('#plLabel') && $('#plLabel').value) || E.label || '').trim() || name;
  /* 前端先自检一遍，错误直接点名到第几步 */
  const keys = new Set();
  for(let i=0;i<E.steps.length;i++){
    const s = E.steps[i];
    const at = `第 ${i+1} 步`;
    if(!(s.label||'').trim()){ toast(at+'缺步骤名称'); return; }
    const key = (s.key||'').trim();
    if(!/^[a-z0-9][a-z0-9_-]*$/.test(key)){ toast(at+`key「${key||'空'}」不合法（小写字母/数字/连字符/下划线）`); return; }
    if(keys.has(key)){ toast(at+`key「${key}」重复`); return; }
    keys.add(key);
    if(!(s.skill||'').trim()){ toast(at+'「'+(s.label||key)+'」还没有绑定主技能'); return; }
  }
  const payload = {
    name, label,
    desc: E.desc||'', emoji: E.emoji||'', g: E.g||'custom',
    steps: E.steps.map(s=>({
      key:(s.key||'').trim(), label:(s.label||'').trim(),
      skill:[(s.skill||'').trim(), ...(s.extra_skills||[])].join(' ').trim(),
      out:(s.out||'').trim(), checkpoint:!!s.checkpoint,
      role:s.role||'executor', model:(s.model||'').trim(),
    })),
  };
  const isNew = !E.name;
  const url = isNew ? '/api/pipelines' : `/api/pipelines/${encodeURIComponent(E.name)}`;
  const r = await (isNew ? _post(url, payload)
    : _put(url, payload))
    .catch(e=>({detail:e.message||'保存失败'}));
  if(r.detail){ toast(r.detail); return; }
  toast('流程已保存', true);
  nav.go('pipelines');
};

/* 预设名列表（本步模型下拉用；app.js 设置页维护，这里只读获取一次） */
let ST_PRESETS = null;
(async function(){ try{ const r = await _api('/api/providers'); ST_PRESETS = r.presets||[]; }catch(e){} })();

})();
