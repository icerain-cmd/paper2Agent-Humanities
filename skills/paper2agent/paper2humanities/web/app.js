const state={agents:[],selected:new Set(),sessionId:null,eventSource:null,maxTurns:0,running:false,registry:null};
const $=s=>document.querySelector(s);

async function api(path,opts={}) {
  const r=await fetch(path,{headers:{"Content-Type":"application/json"},...opts});
  const j=await r.json().catch(()=>({}));
  if(!r.ok) throw new Error(j.detail||"Request failed");
  return j;
}
function escapeHtml(s=""){return String(s).replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[m]))}
function label(a){return a.display_name||a.agent_id}
function filteredAgents(){
  const q=($("#agent-search")?.value||"").trim().toLowerCase();
  if(!q)return state.agents;
  return state.agents.filter(a=>[
    a.display_name,a.author,a.title,a.agent_id,a.source_id,...(a.concepts||[])
  ].filter(Boolean).join(" ").toLowerCase().includes(q));
}
function renderAgents(){
  const box=$("#agent-list"); box.innerHTML="";
  const rows=filteredAgents();
  rows.forEach(a=>{
    const el=document.createElement("label");
    el.className="agent-option"+(state.selected.has(a.agent_id)?" selected":"");
    const concepts=(a.concepts||[]).slice(0,4).map(x=>'<span class="concept-chip">'+escapeHtml(x)+'</span>').join("");
    el.innerHTML='<input type="checkbox" '+(state.selected.has(a.agent_id)?"checked":"")+'><div class="agent-meta"><div class="agent-name">'+escapeHtml(label(a))+'</div><div class="agent-sub">'+escapeHtml(a.edition_id||a.source_id||"")+'</div><div class="agent-concepts">'+concepts+'</div><div class="agent-stats">'+(a.reviewed_grounded_count??0)+' reviewed grounds · '+(a.statement_count??0)+' statements</div></div>';
    el.querySelector("input").addEventListener("change",e=>{
      if(e.target.checked){
        if(state.selected.size>=3){e.target.checked=false;setError("에이전트는 최대 3개까지 선택할 수 있습니다.");return}
        state.selected.add(a.agent_id);
      } else state.selected.delete(a.agent_id);
      setError(""); renderAgents(); updateControls();
    });
    box.appendChild(el);
  });
  if(!rows.length)box.innerHTML='<div class="registry-note">검색 결과가 없습니다.</div>';
}
function updateRegistryNote(){
  const r=state.registry||{};
  const rejected=(r.rejected||[]).length;
  $("#registry-note").textContent=(r.loaded??state.agents.length)+" agents loaded"+(rejected?(" · "+rejected+" rejected"):"");
}
function updateControls(){
  $("#agent-count").textContent=state.selected.size+" selected";
  $("#start-btn").disabled=state.running||state.selected.size<2||!$("#topic").value.trim();
  $("#topic").disabled=state.running;
  $("#turns").disabled=state.running;
  $("#agent-search").disabled=state.running;
  $("#reload-agents").disabled=state.running;
  document.querySelectorAll(".agent-option input").forEach(x=>x.disabled=state.running);
}
function setError(msg){const b=$("#error-box");b.hidden=!msg;b.textContent=msg||""}
function status(v){$("#session-status").textContent=v}
function speakerName(id){const a=state.agents.find(x=>x.agent_id===id);return a?label(a):id}
function addThinking(d){
  removeThinking();
  const el=document.createElement("div");el.id="thinking";el.className="thinking-card";
  el.innerHTML='<span class="thinking-dot">●</span> '+escapeHtml(speakerName(d.speaker_agent_id))+'가 근거를 검토하고 있습니다…';
  $("#timeline").appendChild(el);$("#timeline").scrollTop=$("#timeline").scrollHeight;
}
function removeThinking(){const e=$("#thinking");if(e)e.remove()}
function addIntervention(d){
  const el=document.createElement("div");el.className="intervention-event";
  el.textContent='사용자 개입 · '+d.text;
  $("#timeline").appendChild(el);$("#timeline").scrollTop=$("#timeline").scrollHeight;
}
function addTurn(t){
  removeThinking();
  const wrap=document.createElement("article");wrap.className="turn-card";
  const ev=(t.evidence||[]).map(e=>'<div class="evidence-item"><div class="evidence-title">'+escapeHtml(e.statement_id)+' · p.'+e.page+'</div><div class="evidence-span">'+escapeHtml(e.evidence_span||e.text||"")+'</div></div>').join("");
  wrap.innerHTML='<div class="turn-top"><div class="speaker">'+escapeHtml(speakerName(t.speaker_agent_id))+'</div><div class="action">'+escapeHtml(t.action)+'</div></div><div class="turn-text">'+escapeHtml(t.text)+'</div><div class="turn-foot"><span class="verify '+escapeHtml(t.verification_status)+'">'+escapeHtml(t.verification_status)+'</span>'+(t.evidence?.length?'<button class="evidence-toggle">근거 '+t.evidence.length+'개 보기</button>':'')+'</div><div class="evidence-box">'+ev+'</div>';
  const btn=wrap.querySelector(".evidence-toggle");if(btn)btn.onclick=()=>wrap.querySelector(".evidence-box").classList.toggle("open");
  $("#timeline").appendChild(wrap);$("#timeline").scrollTop=$("#timeline").scrollHeight;
}
function finish(statusText){
  removeThinking();state.running=false;status(statusText);
  $("#intervention").disabled=true;$("#intervene-btn").disabled=true;updateControls();
}
function connectStream(){
  if(state.eventSource)state.eventSource.close();
  const es=new EventSource('/api/debate/sessions/'+state.sessionId+'/stream');state.eventSource=es;
  es.addEventListener("agent_thinking",e=>addThinking(JSON.parse(e.data)));
  es.addEventListener("user_intervention",e=>addIntervention(JSON.parse(e.data)));
  es.addEventListener("turn_completed",e=>{
    const t=JSON.parse(e.data);addTurn(t);
    const n=parseInt(t.turn_id.split("-")[1],10);$("#turn-progress").textContent=n+" / "+state.maxTurns;
  });
  es.addEventListener("debate_completed",e=>{finish("COMPLETED");es.close()});
  es.addEventListener("debate_failed",e=>{finish("FAILED");setError(JSON.parse(e.data).error);es.close()});
  es.onerror=()=>{if(state.running)status("RECONNECTING")};
}
async function loadAgents(reload=false){
  setError("");
  try{
    const d=await api(reload?"/api/debate/agents/reload":"/api/debate/agents",reload?{method:"POST"}:{});
    state.agents=d.agents;state.registry=d.registry;
    const ids=new Set(state.agents.map(a=>a.agent_id));
    state.selected=new Set([...state.selected].filter(x=>ids.has(x)));
    renderAgents();updateRegistryNote();updateControls();
  }catch(e){setError(e.message)}
}
async function startDebate(){
  setError("");
  try{
    const topic=$("#topic").value.trim();const max_turns=Number($("#turns").value);
    const s=await api("/api/debate/sessions",{method:"POST",body:JSON.stringify({agent_ids:[...state.selected],topic,max_turns})});
    state.sessionId=s.session_id;state.maxTurns=max_turns;state.running=true;
    $("#debate-title").textContent=topic;$("#turn-progress").textContent="0 / "+max_turns;
    $("#timeline").className="timeline";$("#timeline").innerHTML="";
    $("#intervention").disabled=false;$("#intervene-btn").disabled=false;status("RUNNING");updateControls();
    connectStream();
    await api('/api/debate/sessions/'+state.sessionId+'/start',{method:"POST"});
  }catch(e){state.running=false;setError(e.message);status("ERROR");updateControls()}
}
async function intervene(){
  const text=$("#intervention").value.trim();if(!text||!state.sessionId||!state.running)return;
  try{await api('/api/debate/sessions/'+state.sessionId+'/intervene',{method:"POST",body:JSON.stringify({text})});$("#intervention").value=""}
  catch(e){setError(e.message)}
}
async function init(){
  await loadAgents(false);
  $("#topic").addEventListener("input",updateControls);
  $("#agent-search").addEventListener("input",renderAgents);
  $("#reload-agents").addEventListener("click",()=>loadAgents(true));
  $("#start-btn").addEventListener("click",startDebate);
  $("#intervene-btn").addEventListener("click",intervene);
  $("#intervention").addEventListener("keydown",e=>{if(e.key==="Enter")intervene()});
}
init();
