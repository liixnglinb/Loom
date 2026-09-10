/* =====================================================================
 * FlowForge 运行控制台（#/run/<id> · #/runs）
 * UI 基准 = 设置页：card + card-h + pv 控件体系，黑白灰+金黄，无图标
 * 实时可视化：SSE 流式渲染每个步骤的生成内容；产物面板 + 对话式局部修订
 * ===================================================================== */
(function(){
'use strict';
const $ = s => document.querySelector(s);
const esc = s => String(s??'').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const _api = (u,o) => fetch(u,o).then(r=>r.json());
const _post = (u,b) => _api(u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b||{})});
let _toastTimer = null;
function toast(msg, ok=false){
  const el = document.getElementById('toast');
  if(!el) return;
  el.textContent = msg||'';
  el.className = 'toast show '+(ok?'ok':'err');
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(()=>{ el.className='toast'; }, 2400);
}
function _lockScroll(on){ document.body.style.overflow = on?'hidden':''; }

/* ---------------- 运行列表 ---------------- */
const ST_ZH = {pending:'待执行', running:'执行中', waiting:'等待确认', done:'已完成',
               failed:'失败', cancelled:'已取消', revising:'修订中'};
window.renderRuns = async function(){
  $('#view').innerHTML = '<div class="loading-bar"></div>';
  const r = await _api('/api/runs').catch(()=>({runs:[]}));
  const runs = r.runs||[];
  const row = u => `
    <div class="pl-card-row" onclick="nav.go('run/${esc(u.id)}')">
      <div class="pl-row-main">
        <div class="pl-row-title">
          <span class="pl-row-name">${esc(u.label||u.pipeline)}</span>
          <code>${esc(u.id)}</code>
          <span class="run-badge rb-${esc(u.status)}">${ST_ZH[u.status]||u.status}</span>
        </div>
        <div class="pl-row-meta">
          <span>${(u.steps||[]).length} 个步骤</span>
          <span>${esc(u.created_at||'')}</span>
        </div>
      </div>
      <div class="pl-row-ops" onclick="event.stopPropagation()">
        <button class="pf-op pf-op-start" onclick="nav.go('run/${esc(u.id)}')">打开</button>
        <button class="pf-op pf-op-danger" onclick="runDelete('${esc(u.id)}')">删除</button>
      </div>
    </div>`;
  $('#view').innerHTML = `
    <div class="pl-wrap">
    <div class="page-head">
      <div><h1>运行记录</h1><div class="sub">每一次流程执行的实例：步骤状态、生成内容、产物文件全程保留</div></div>
    </div>
    <div class="card">
      <div class="card-h"><div><div class="ct">全部运行</div><div class="cs">点击进入运行控制台</div></div></div>
      <div class="set-row">
        ${runs.length ? runs.map(row).join('')
          : `<div class="pf-empty">还没有运行记录 —— 到流程列表点「运行」启动一次</div>`}
      </div>
    </div>
    </div>`;
};
window.runDelete = async function(id){
  if(!confirm('确定删除运行「'+id+'」？工作区产物一并删除。')) return;
  await _api('/api/runs/'+id, {method:'DELETE'}).catch(()=>({}));
  toast('已删除'); renderRuns();
};

/* ---------------- 运行控制台 ---------------- */
let RUN = null;          // 当前 run 对象
let ARTS = {};           // 产物快照
let ES = null;           // EventSource
let SEEN = {};           // 每步已渲染字符数（增量渲染）
let ACTIVE_TAB = 'stream';
let ACTIVE_STEP = null;  // 当前展开的步骤
let REVISER = {};        // 步骤修订进行中标记
let CONVO = [];          // 对话面板消息 [{role,text}]
let _POLL = null;

function runStatusBadge(u){
  return `<span class="run-badge rb-${esc(u.status)}">${ST_ZH[u.status]||esc(u.status)}</span>`;
}

window.renderRunConsole = async function(runId){
  $('#view').innerHTML = '<div class="loading-bar"></div>';
  const d = await _api('/api/runs/'+encodeURIComponent(runId)).catch(()=>null);
  if(!d || !d.run){ toast('运行不存在'); nav.go('runs'); return; }
  RUN = d.run; ARTS = d.artifacts||{};
  SEEN = {}; CONVO = CONVO.filter(m=>m._run===runId);
  drawConsole();
  connectStream(runId);
};

function drawConsole(){
  const u = RUN;
  const steps = u.steps||[];
  if(ACTIVE_STEP===null && steps.length) ACTIVE_STEP = Math.min(u.cur_step||0, steps.length-1);
  $('#view').innerHTML = `
    <div class="pl-wrap">
    <div class="page-head">
      <div><h1>${esc(u.label||u.pipeline)} ${runStatusBadge(u)}</h1>
        <div class="sub">${esc(u.id)} · 工作区 modex-data/workspaces/${esc(u.id.startsWith('run-')?u.id:'run-'+u.id)}</div></div>
      <div style="display:flex;gap:10px">
        ${u.status==='waiting' ? `<button class="btn btn-primary" onclick="runContinue()">继续执行</button>` : ''}
        ${u.status==='running' ? `<button class="btn btn-ghost" onclick="runCancel()">停止</button>` : ''}
        <button class="btn btn-ghost" onclick="nav.go('runs')">返回列表</button>
      </div>
    </div>

    <div class="run-grid">
      <div class="run-main">
        <!-- 步骤进度 -->
        <div class="card">
          <div class="card-h">
            <div><div class="ct">执行进度</div><div class="cs">步骤 ${Math.min((u.cur_step||0)+ (u.status==='done'?0:0), steps.length)||0} / ${steps.length}${u.waiting_reason==='checkpoint'?' · 检查点等待确认':''}</div></div>
            ${u.status==='done'?'<span class="run-badge rb-done">全部完成</span>':''}
          </div>
          <div class="run-steps">
            ${steps.map((s,i)=>stepRail(s,i)).join('')}
          </div>
        </div>

        <!-- 产物面板 -->
        <div class="card">
          <div class="card-h">
            <div><div class="ct">产物文件</div><div class="cs">步骤输出实时写入工作区，可下载</div></div>
            <button class="btn btn-ghost btn-sm" onclick="runRefreshArts()">刷新</button>
          </div>
          <div class="set-row" id="runArts">
            ${Object.keys(ARTS).length ? Object.keys(ARTS).map(n=>`
              <div class="pl-card-row art-row">
                <div class="pl-row-main">
                  <div class="pl-row-title"><span class="pl-row-name">${esc(n)}</span>
                    <span class="muted" style="font-size:11.5px">${(ARTS[n]||'').length} 字</span></div>
                </div>
                <div class="pl-row-ops">
                  <button class="pf-op" onclick="runViewArt('${esc(n)}')">查看</button>
                  <a class="pf-op" href="/api/runs/${esc(u.id)}/artifacts/${esc(n)}" download>下载</a>
                </div>
              </div>`).join('')
            : `<div class="pf-empty">还没有产物文件</div>`}
          </div>
        </div>
      </div>

      <!-- 右栏：对话 / 局部修改 -->
      <div class="run-side">
        <div class="card">
          <div class="card-h"><div><div class="ct">对话 · 局部修改</div>
            <div class="cs">选择步骤，用自然语言让 AI 修改产物内容</div></div></div>
          <div class="pv-form" style="padding:2px 2px 12px">
            <div class="pv-f"><label class="pv-label">目标步骤</label>
              <select class="pv-input" id="rvStep">
                ${steps.map((s,i)=>`<option value="${i}" ${i===ACTIVE_STEP?'selected':''}>${i+1}. ${esc(s.label||s.key)}${s.out?('（'+esc(s.out)+'）'):''}</option>`).join('')}
              </select></div>
            <div class="pv-f"><label class="pv-label">修改要求</label>
              <textarea class="pv-input" id="rvText" rows="3" placeholder="如：把第二段的数据来源改成国家统计局 2023 年口径，其余不动"></textarea></div>
            <button class="btn btn-primary" onclick="runRevise()">发送修改指令</button>
            <div class="pv-foot-hint" id="rvHint">AI 会输出修改后的完整文件并写回工作区，可随时再次修改。</div>
          </div>
          <div id="runConvo"></div>
        </div>
      </div>
    </div>
    <div style="height:60px"></div>
    </div>`;
  drawConvo();
}

function stepRail(s, i){
  const st = s.status||'pending';
  const active = i===ACTIVE_STEP;
  const open = active && (st==='running'||st==='revising'||st==='done'||st==='failed');
  return `
  <div class="run-step ${open?'open':''} ${'rs-'+st}" data-i="${i}">
    <div class="run-step-head" onclick="runToggleStep(${i})">
      <div class="step-no-sm ${'sn-'+st}">${i+1}</div>
      <div class="run-step-main">
        <div class="run-step-name">${esc(s.label||s.key)} ${REVISER[i]?'<span class="run-badge rb-revising">修订中</span>':''}</div>
        <div class="run-step-meta">
          <code>${esc(s.key)}</code>${s.skill?`<span>${esc(s.skill)}</span>`:''}
          ${s.out?`<span>产物 ${esc(s.out)}</span>`:''}
          ${s.checkpoint?'<span>检查点</span>':''}
          <span class="run-badge rb-${esc(st)}">${ST_ZH[st]||st}</span>
        </div>
      </div>
    </div>
    <div class="run-step-body" ${open?'':'style="display:none"'}>
      <pre class="run-delta" id="delta-${i}">${esc((s.delta||'').slice(-8000))}</pre>
    </div>
  </div>`;
}

/* ---------------- SSE ---------------- */
function connectStream(runId){
  if(ES){ ES.close(); ES=null; }
  const es = new EventSource('/api/runs/'+encodeURIComponent(runId)+'/stream');
  ES = es;
  es.onmessage = e => {
    let ev; try{ ev = JSON.parse(e.data); }catch(_){ return; }
    handleEvent(ev, runId);
  };
  es.onerror = () => { /* EventSource 自动重连 */ };
}

function handleEvent(ev, runId){
  if(!RUN || RUN.id!==runId) return;
  if(ev.type==='state'){
    // state 快照：权威状态。delta 非空时覆盖本地（去重防重连重复）；空则保留流式缓冲
    const prevStatus = RUN.status;
    const remote = ev.run;
    if(remote){
      (remote.steps||[]).forEach((rs,i)=>{
        const local = RUN.steps && RUN.steps[i];
        if(rs.delta && rs.delta.length){
          rs._buf = rs.delta;
        }else if(local && local.delta && !local._buf){
          rs._buf = local.delta;   // 保留流式中途已收的增量
        }
      });
      RUN = remote;
      refreshProgress(); refreshHeader();
      if(prevStatus!==RUN.status && ['done','failed','cancelled','waiting'].includes(RUN.status)){
        drawConsole();
      }
    }
    return;
  }
  if(ev.type==='delta'){
    const i = ev.index;
    SEEN[i] = (SEEN[i]||0) + ev.text.length;
    if(RUN.steps && RUN.steps[i]){
      RUN.steps[i].delta = (RUN.steps[i].delta||'') + ev.text;
      RUN.steps[i].status = 'running';
    }
    updateDeltaPane(i);
    markStepBadge(i, 'running');
  }
  else if(ev.type==='step_start'){
    if(RUN.steps && RUN.steps[ev.index]){ RUN.steps[ev.index].status='running'; RUN.steps[ev.index].delta=''; RUN.steps[ev.index]._buf=''; }
    SEEN[ev.index]=0;
    RUN.cur_step = ev.index;
    openStep(ev.index);
    markStepBadge(ev.index, 'running');
    refreshProgress();
  }
  else if(ev.type==='step_done'){
    if(RUN.steps && RUN.steps[ev.index]){ RUN.steps[ev.index].status='done'; if(ev.step && ev.step.delta) RUN.steps[ev.index]._buf = ev.step.delta; }
    markStepBadge(ev.index, 'done');
    toast(`第 ${ev.index+1} 步完成（${ev.chars} 字）`, true);
  }
  else if(ev.type==='checkpoint'){
    toast('检查点：等待你确认后继续', true);
  }
  else if(ev.type==='revise_delta'){
    REVISER[ev.index] = true;
    if(RUN.steps && RUN.steps[ev.index]){
      RUN.steps[ev.index].status='revising';
      RUN.steps[ev.index].delta = (RUN.steps[ev.index].delta||'') + ev.text;
      RUN.steps[ev.index]._buf = RUN.steps[ev.index].delta;
    }
    markStepBadge(ev.index, 'revising');
    updateDeltaPane(ev.index);
  }
  else if(ev.type==='revise_done'){
    REVISER[ev.index] = false;
    markStepBadge(ev.index, 'done');
    CONVO.push({_run:RUN.id, role:'assistant', text:`已按要求改写「${(RUN.steps[ev.index]||{}).label||''}」，可继续追加要求。`});
    drawConvo();
    runRefreshArts(true);
  }
  else if(ev.type==='error'){
    toast('出错了：'+(ev.message||''), false);
    if(ev.index!==undefined) markStepBadge(ev.index, 'failed');
  }
  else if(ev.type==='done'){
    refreshHeader();
  }
}

function updateDeltaPane(i){
  const el = document.getElementById('delta-'+i);
  const s = RUN.steps && RUN.steps[i];
  if(el && s){ el.textContent = (s.delta||'').slice(-8000); autoScroll(el); }
}

function autoScroll(el){
  if(!el) return;
  const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
  if(nearBottom) el.scrollTop = el.scrollHeight;
}

function openStep(i){
  ACTIVE_STEP = i;
  document.querySelectorAll('.run-step').forEach(el=>{
    const idx = Number(el.dataset.i);
    const open = idx===i;
    el.classList.toggle('open', open);
    const body = el.querySelector('.run-step-body');
    if(body) body.style.display = open?'':'none';
  });
  const el = document.getElementById('delta-'+i);
  if(el) el.scrollTop = el.scrollHeight;
}

window.runToggleStep = function(i){
  const el = document.querySelector(`.run-step[data-i="${i}"]`);
  if(!el) return;
  const open = !el.classList.contains('open');
  el.classList.toggle('open', open);
  const body = el.querySelector('.run-step-body');
  if(body) body.style.display = open?'':'none';
  if(open) ACTIVE_STEP = i;
};

function markStepBadge(i, st){
  const el = document.querySelector(`.run-step[data-i="${i}"]`);
  if(el){
    el.classList.remove('rs-pending','rs-running','rs-done','rs-failed','rs-cancelled','rs-revising');
    el.classList.add('rs-'+st);
    const no = el.querySelector('.step-no-sm');
    if(no){ no.className = 'step-no-sm sn-'+st; }
  }
  const badge = el ? el.querySelector('.run-badge') : null;
  if(badge){ badge.className = 'run-badge rb-'+st; badge.textContent = ST_ZH[st]||st; }
}

function refreshProgress(){
  const u = RUN;
  const el = document.querySelector('.run-steps');
  if(el && u.steps) el.innerHTML = u.steps.map((s,i)=>stepRail(s,i)).join('');
  const cs = document.querySelector('.run-main .card .cs');
  if(cs) cs.textContent = `步骤 ${(u.cur_step||0)} / ${(u.steps||[]).length}${u.waiting_reason==='checkpoint'?' · 检查点等待确认':''}`;
}

function refreshHeader(){
  const h1 = document.querySelector('#view h1');
  if(h1 && RUN){ h1.innerHTML = esc(RUN.label||RUN.pipeline)+' '+runStatusBadge(RUN); }
  const ph = document.querySelector('.page-head > div:last-child');
  // 按钮区重绘
  const phEl = document.querySelector('.page-head');
  if(phEl && RUN){
    const btns = `
      ${RUN.status==='waiting' ? `<button class="btn btn-primary" onclick="runContinue()">继续执行</button>` : ''}
      ${RUN.status==='running' ? `<button class="btn btn-ghost" onclick="runCancel()">停止</button>` : ''}
      <button class="btn btn-ghost" onclick="nav.go('runs')">返回列表</button>`;
    const wrap = phEl.querySelector('div[style]');
    if(wrap) wrap.innerHTML = btns;
  }
}

window.runContinue = async function(){
  const r = await _post('/api/runs/'+RUN.id+'/continue');
  if(r.detail){ toast(r.detail); return; }
  toast('已继续执行', true);
};
window.runCancel = async function(){
  const r = await _post('/api/runs/'+RUN.id+'/cancel');
  if(r.detail){ toast(r.detail); return; }
  toast('已发送停止信号');
};
window.runRefreshArts = async function(silent){
  const d = await _api('/api/runs/'+RUN.id+'/artifacts').catch(()=>null);
  if(!d) return;
  ARTS = d.artifacts||{};
  const box = document.getElementById('runArts');
  if(box) box.innerHTML = Object.keys(ARTS).length ? Object.keys(ARTS).map(n=>`
      <div class="pl-card-row art-row">
        <div class="pl-row-main">
          <div class="pl-row-title"><span class="pl-row-name">${esc(n)}</span>
            <span class="muted" style="font-size:11.5px">${(ARTS[n]||'').length} 字</span></div>
        </div>
        <div class="pl-row-ops">
          <button class="pf-op" onclick="runViewArt('${esc(n)}')">查看</button>
          <a class="pf-op" href="/api/runs/${esc(RUN.id)}/artifacts/${esc(n)}" download>下载</a>
        </div>
      </div>`).join('')
    : `<div class="pf-empty">还没有产物文件</div>`;
  if(!silent) toast('产物已刷新', true);
};
window.runViewArt = function(n){
  const text = ARTS[n]||'';
  _lockScroll(true);
  const root = document.createElement('div');
  root.id = 'runArtRoot';
  root.innerHTML = `<div class="modal open" onclick="if(event.target===this)runCloseArt()">
    <div class="modal-box sk-view-modal">
      <div class="modal-top"><div class="pv-head"><h3>${esc(n)}</h3></div>
        <button class="modal-x" onclick="runCloseArt()">×</button></div>
      <div class="sk-view-body"><pre class="sk-pre">${esc(text)}</pre></div>
      <div class="sk-view-foot">
        <button class="btn btn-ghost btn-sm" onclick="runCloseArt()">关闭</button>
        <a class="btn btn-primary btn-sm" href="/api/runs/${esc(RUN.id)}/artifacts/${esc(n)}" download>下载</a>
      </div>
    </div></div>`;
  document.body.appendChild(root);
};
window.runCloseArt = function(){
  const r = document.getElementById('runArtRoot');
  if(r) r.remove();
  _lockScroll(false);
};

/* ---------------- 对话式局部修订 ---------------- */
window.runRevise = async function(){
  const sel = document.getElementById('rvStep');
  const txt = document.getElementById('rvText');
  if(!sel || !txt) return;
  const idx = Number(sel.value);
  const instruction = (txt.value||'').trim();
  if(!instruction){ toast('请填写修改要求'); return; }
  CONVO.push({_run:RUN.id, role:'user', text:instruction});
  txt.value='';
  drawConvo();
  const r = await _post('/api/runs/'+RUN.id+'/revise', {index: idx, instruction});
  if(r.detail){ toast(r.detail); CONVO.push({_run:RUN.id, role:'assistant', text:'修改失败：'+r.detail}); drawConvo(); return; }
  CONVO.push({_run:RUN.id, role:'assistant', text:'正在修改，生成内容会在步骤面板实时显示…'});
  drawConvo();
};

function drawConvo(){
  const box = document.getElementById('runConvo');
  if(!box) return;
  const items = CONVO.filter(m=>m._run===RUN.id);
  box.innerHTML = items.length ? `<div class="convo-list">${items.map(m=>`
    <div class="convo-msg ${m.role==='user'?'cm-user':'cm-ai'}"><div class="cm-role">${m.role==='user'?'你':'AI'}</div>
      <div class="cm-text">${esc(m.text)}</div></div>`).join('')}</div>` : '';
  box.scrollTop = box.scrollHeight;
}

/* 离开页面时断流 */
window.addEventListener('hashchange', ()=>{
  if(ES && !location.hash.startsWith('#/run/')){ ES.close(); ES=null; }
});

})();
