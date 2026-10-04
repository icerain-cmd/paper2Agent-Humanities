const state={agents:[],selected:new Set(),sessionId:null,eventSource:null,maxTurns:0,running:false,registry:null,onboarding:{file:null,data:null,id:null},pdf:{file:null,jobId:null,onboardingId:null,candidates:[]}};
const $=s=>document.querySelector(s);

async function api(path,opts={}) {
  const request={...opts};
  if(!(opts.body instanceof FormData))request.headers={"Content-Type":"application/json",...(opts.headers||{})};
  const r=await fetch(path,request);
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
    el.innerHTML='<input type="checkbox" '+(state.selected.has(a.agent_id)?"checked":"")+'><div class="agent-meta"><div class="agent-name">'+escapeHtml(label(a))+'</div><div class="agent-sub">'+escapeHtml(a.edition_id||a.source_id||"")+'</div><div class="agent-concepts">'+concepts+'</div><div class="agent-stats">'+(a.reviewed_grounded_count??0)+' reviewed grounds · '+(a.statement_count??0)+' statements · '+escapeHtml(a.origin||"built_in")+'</div>'+(a.can_disable?'<button type="button" class="disable-agent" data-agent="'+escapeHtml(a.agent_id)+'">비활성화</button>':'')+'</div>';
    el.querySelector("input").addEventListener("change",e=>{
      if(e.target.checked){
        if(state.selected.size>=3){e.target.checked=false;setError("에이전트는 최대 3개까지 선택할 수 있습니다.");return}
        state.selected.add(a.agent_id);
      } else state.selected.delete(a.agent_id);
      setError(""); renderAgents(); updateControls();
    });
    const disableBtn=el.querySelector(".disable-agent");
    if(disableBtn)disableBtn.addEventListener("click",async e=>{
      e.preventDefault();e.stopPropagation();
      if(!confirm("이 등록 Agent를 비활성화할까요?"))return;
      try{
        await api('/api/agents/'+encodeURIComponent(a.agent_id),{method:"DELETE"});
        state.selected.delete(a.agent_id);
        await loadAgents(false);
      }catch(err){setError(err.message)}
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
  $("#add-agent").disabled=state.running;
  document.querySelectorAll(".agent-option input,.disable-agent").forEach(x=>x.disabled=state.running);
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
  loadRecentSessions();
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
async function loadRecentSessions(){
  try{
    const d=await api("/api/debate/sessions?limit=8");
    const box=$("#recent-sessions");box.innerHTML="";
    (d.sessions||[]).forEach(s=>{
      const el=document.createElement("div");el.className="recent-item";
      el.innerHTML='<div class="recent-topic">'+escapeHtml(s.topic)+'</div><div class="recent-meta">'+escapeHtml(s.status)+' · '+s.current_turn+'/'+s.max_turns+'</div>'+(s.status==="INTERRUPTED"?'<button type="button" class="resume-btn">Resume</button>':'');
      const btn=el.querySelector(".resume-btn");
      if(btn)btn.addEventListener("click",()=>resumeSession(s));
      box.appendChild(el);
    });
    if(!(d.sessions||[]).length)box.innerHTML='<div class="registry-note">저장된 세션이 없습니다.</div>';
  }catch(e){setError(e.message)}
}
async function resumeSession(s){
  setError("");
  try{
    state.sessionId=s.session_id;state.maxTurns=s.max_turns;state.running=true;
    state.selected=new Set(s.participant_ids||[]);
    $("#debate-title").textContent=s.topic;$("#turn-progress").textContent=s.current_turn+" / "+s.max_turns;
    $("#timeline").className="timeline";$("#timeline").innerHTML="";
    $("#intervention").disabled=false;$("#intervene-btn").disabled=false;status("RUNNING");
    renderAgents();updateControls();connectStream();
    await api('/api/debate/sessions/'+s.session_id+'/resume',{method:"POST"});
    await loadRecentSessions();
  }catch(e){state.running=false;setError(e.message);status("ERROR");updateControls()}
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
function resetOnboarding(){
  state.onboarding={file:null,data:null,id:null};
  $("#agent-file").value="";
  $("#onboarding-file-name").textContent="";
  $("#validate-agent-btn").disabled=true;
  $("#onboarding-result").hidden=true;
  $("#onboarding-upload-step").hidden=false;
  $("#validation-preview").innerHTML="";
  $("#validation-errors").innerHTML="";
  $("#register-agent-btn").disabled=true;
}
function openOnboarding(){resetOnboarding();$("#onboarding-dialog").showModal()}
function renderValidation(record){
  const v=record.validation||{};
  $("#onboarding-upload-step").hidden=true;
  $("#onboarding-result").hidden=false;
  $("#validation-status").textContent=v.status==="PASS"?"VALIDATION PASS":"VALIDATION FAIL";
  $("#validation-status").className="validation-status "+(v.status==="PASS"?"pass":"fail");
  const p=v.preview,c=v.counts||{};
  $("#validation-preview").innerHTML=p?'<h3>'+escapeHtml(p.author)+' — '+escapeHtml(p.title)+'</h3><div class="preview-meta">'+escapeHtml(p.agent_id)+' · '+escapeHtml(p.edition_id||p.source_id||"")+'</div><div class="preview-counts">'+(c.reviewed_grounded||0)+' reviewed grounds · '+(c.quotes||0)+' quotes · '+(c.author_claims||0)+' author claims</div><div class="preview-concepts">'+(p.concepts||[]).map(x=>'<span class="concept-chip">'+escapeHtml(x)+'</span>').join("")+'</div><div class="preview-statements">'+(p.sample_statements||[]).map(s=>'<div><strong>'+escapeHtml(s.statement_id)+'</strong> · p.'+(s.page||"—")+'<br><span>'+escapeHtml(s.text||"")+'</span></div>').join("")+'</div>':"";
  const errs=[...(v.errors||[]),...(v.warnings||[]).map(x=>"WARN: "+x)];
  $("#validation-errors").innerHTML=errs.map(x=>'<div>'+escapeHtml(x)+'</div>').join("");
  $("#register-agent-btn").disabled=v.status!=="PASS";
}
async function validateSelectedAgent(){
  const file=state.onboarding.file;if(!file)return;
  try{
    const text=await file.text();const data=JSON.parse(text);
    state.onboarding.data=data;
    const up=await api("/api/agents/onboarding/upload",{method:"POST",body:JSON.stringify({agent:data,original_name:file.name})});
    state.onboarding.id=up.onboarding_id;
    const val=await api('/api/agents/onboarding/'+up.onboarding_id+'/validate',{method:"POST"});
    renderValidation(val);
  }catch(e){
    $("#onboarding-result").hidden=false;$("#onboarding-upload-step").hidden=true;
    $("#validation-status").textContent="VALIDATION FAIL";$("#validation-status").className="validation-status fail";
    $("#validation-errors").innerHTML='<div>'+escapeHtml(e.message)+'</div>';
  }
}
async function registerOnboardedAgent(){
  if(!state.onboarding.id)return;
  try{
    const r=await api('/api/agents/onboarding/'+state.onboarding.id+'/register',{method:"POST"});
    await loadAgents(false);
    $("#onboarding-dialog").close();resetOnboarding();
    const id=r.active_manifest.agent_id;
    if(state.selected.size<3)state.selected.add(id);
    renderAgents();updateControls();
  }catch(e){$("#validation-errors").innerHTML+='<div>'+escapeHtml(e.message)+'</div>'}
}
function resetPdfFlow(){
  state.pdf={file:null,jobId:null,onboardingId:null,candidates:[]};
  $("#pdf-file").value="";$("#pdf-file-name").textContent="";
  $("#pdf-upload-btn").disabled=true;
  $("#pdf-upload-step").hidden=false;$("#pdf-extraction-step").hidden=true;
  $("#pdf-candidates-step").hidden=true;$("#pdf-build-step").hidden=true;
  $("#pdf-quality").innerHTML="";$("#candidate-list").innerHTML="";
  $("#pdf-build-result").innerHTML="";$("#pdf-build-errors").innerHTML="";
  $("#register-pdf-agent-btn").disabled=true;
}
function switchOnboardingMode(mode){
  const isPdf=mode==="pdf";
  $("#json-onboarding-flow").hidden=isPdf;
  $("#pdf-onboarding-flow").hidden=!isPdf;
  $("#mode-json").classList.toggle("active",!isPdf);
  $("#mode-pdf").classList.toggle("active",isPdf);
  if(isPdf)resetPdfFlow(); else resetOnboarding();
}
function slugifyId(s){
  return String(s||"").toLowerCase().normalize("NFKD").replace(/[^a-z0-9가-힣]+/g,"-").replace(/^-|-$/g,"").slice(0,120);
}
function updatePdfStep(n){
  document.querySelectorAll(".wizard-steps span").forEach((x,i)=>x.classList.toggle("active",i<n));
}
async function uploadAndExtractPdf(){
  const file=state.pdf.file;if(!file)return;
  $("#pdf-upload-btn").disabled=true;$("#pdf-upload-btn").textContent="분석 중…";
  try{
    const fd=new FormData();fd.append("file",file,file.name);
    const up=await api("/api/agents/from-pdf/upload",{method:"POST",body:fd});
    state.pdf.jobId=up.job_id;
    const ext=await api('/api/agents/from-pdf/'+up.job_id+'/extract',{method:"POST"});
    const q=ext.extraction||{},m=ext.metadata||{};
    $("#pdf-quality").innerHTML='<strong>Extraction '+escapeHtml(q.quality||"UNKNOWN")+'</strong><div>'+q.pages+' pages · '+q.text_pages+' text pages · '+q.characters+' chars · corruption '+q.corruption_rate+'</div>';
    if(q.quality!=="PASS")throw new Error("PDF extraction quality is "+q.quality+". 텍스트 기반 PDF를 사용하세요.");
    $("#pdf-title").value=m.title||"";$("#pdf-author").value=m.author||"";
    $("#pdf-year").value=m.year||"";$("#pdf-journal").value=m.journal||"";$("#pdf-doi").value=m.doi||"";
    $("#pdf-paper-id").value=m.paper_id||slugifyId((m.author||"paper")+"-"+(m.title||"agent"));
    $("#pdf-upload-step").hidden=true;$("#pdf-extraction-step").hidden=false;updatePdfStep(3);
  }catch(e){$("#pdf-quality").innerHTML='<div class="validation-errors">'+escapeHtml(e.message)+'</div>';$("#pdf-extraction-step").hidden=false}
  finally{$("#pdf-upload-btn").textContent="업로드하고 분석"}
}
function metadataPayload(){
  const year=$("#pdf-year").value.trim();
  return {title:$("#pdf-title").value.trim(),author:$("#pdf-author").value.trim(),paper_id:$("#pdf-paper-id").value.trim(),
    year:year?Number(year):null,journal:$("#pdf-journal").value.trim()||null,doi:$("#pdf-doi").value.trim()||null};
}
function renderCandidates(job){
  state.pdf.candidates=job.candidates||[];
  const s=job.candidate_summary||{};
  $("#candidate-summary").textContent=(s.total||0)+" candidates · "+(s.approved||0)+" approved · "+(s.pending||0)+" pending · "+(s.rejected||0)+" rejected";
  $("#build-pdf-agent-btn").disabled=!(s.approved>0);
  const box=$("#candidate-list");box.innerHTML="";
  state.pdf.candidates.forEach(c=>{
    const el=document.createElement("div");el.className="candidate-card "+String(c.decision||"").toLowerCase();
    el.innerHTML='<div class="candidate-head"><span>'+escapeHtml(c.statement_type)+' · p.'+c.pdf_page+'</span><span>'+Math.round((c.confidence||0)*100)+'%</span></div><div class="candidate-text">'+escapeHtml(c.text)+'</div><div class="candidate-evidence">'+escapeHtml(c.evidence_span)+'</div>'+(c.attributed_author?'<div class="candidate-author">attributed: '+escapeHtml(c.attributed_author)+'</div>':'')+'<div class="candidate-actions"><button data-d="APPROVED">승인</button><button data-d="REJECTED">제외</button></div>';
    el.querySelectorAll("button").forEach(b=>b.addEventListener("click",async()=>{
      const updated=await api('/api/agents/from-pdf/'+state.pdf.jobId+'/candidates/'+c.candidate_id,{method:"PATCH",body:JSON.stringify({decision:b.dataset.d})});
      renderCandidates(updated);
    }));
    box.appendChild(el);
  });
}
async function generatePdfCandidates(){
  const meta=metadataPayload();
  if(!meta.title||!meta.author||!meta.paper_id){alert("Title, Author, Paper ID를 확인하세요.");return}
  $("#generate-candidates-btn").disabled=true;$("#generate-candidates-btn").textContent="후보 생성 중…";
  try{
    await api('/api/agents/from-pdf/'+state.pdf.jobId+'/metadata',{method:"PATCH",body:JSON.stringify({metadata:meta})});
    const job=await api('/api/agents/from-pdf/'+state.pdf.jobId+'/generate-candidates',{method:"POST"});
    $("#pdf-extraction-step").hidden=true;$("#pdf-candidates-step").hidden=false;updatePdfStep(4);renderCandidates(job);
  }catch(e){alert(e.message)}
  finally{$("#generate-candidates-btn").disabled=false;$("#generate-candidates-btn").textContent="Statement 후보 생성"}
}
async function approveHighCandidates(){
  try{renderCandidates(await api('/api/agents/from-pdf/'+state.pdf.jobId+'/approve-high-confidence',{method:"POST"}))}
  catch(e){alert(e.message)}
}
async function buildPdfAgent(){
  $("#build-pdf-agent-btn").disabled=true;$("#build-pdf-agent-btn").textContent="Agent Build 중…";
  try{
    const r=await api('/api/agents/from-pdf/'+state.pdf.jobId+'/build-agent',{method:"POST"});
    const onb=r.onboarding;state.pdf.onboardingId=onb.onboarding_id;
    const v=onb.validation||{};
    $("#pdf-build-result").innerHTML='<h3>'+escapeHtml(r.agent.author)+' — '+escapeHtml(r.agent.title)+'</h3><div class="preview-meta">'+escapeHtml(r.agent.paper_id)+' · '+(v.counts?.reviewed_grounded||0)+' reviewed grounds</div><div class="validation-status '+(v.status==="PASS"?"pass":"fail")+'">FINAL VALIDATION '+escapeHtml(v.status||"UNKNOWN")+'</div>';
    $("#pdf-build-errors").innerHTML=[...(v.errors||[]),...(v.warnings||[]).map(x=>"WARN: "+x)].map(x=>'<div>'+escapeHtml(x)+'</div>').join("");
    $("#register-pdf-agent-btn").disabled=v.status!=="PASS";
    $("#pdf-candidates-step").hidden=true;$("#pdf-build-step").hidden=false;updatePdfStep(5);
  }catch(e){alert(e.message)}
  finally{$("#build-pdf-agent-btn").textContent="검토한 후보로 Agent Build"}
}
async function registerPdfAgent(){
  if(!state.pdf.onboardingId)return;
  try{
    const r=await api('/api/agents/onboarding/'+state.pdf.onboardingId+'/register',{method:"POST"});
    await loadAgents(false);$("#onboarding-dialog").close();
    const id=r.active_manifest.agent_id;if(state.selected.size<3)state.selected.add(id);
    renderAgents();updateControls();resetPdfFlow();
  }catch(e){$("#pdf-build-errors").innerHTML+='<div>'+escapeHtml(e.message)+'</div>'}
}

async function init(){
  await loadAgents(false);
  await loadRecentSessions();
  $("#topic").addEventListener("input",updateControls);
  $("#agent-search").addEventListener("input",renderAgents);
  $("#reload-agents").addEventListener("click",()=>loadAgents(true));
  $("#refresh-sessions").addEventListener("click",loadRecentSessions);
  $("#add-agent").addEventListener("click",openOnboarding);
  $("#close-onboarding").addEventListener("click",()=>$("#onboarding-dialog").close());
  $("#mode-json").addEventListener("click",()=>switchOnboardingMode("json"));
  $("#mode-pdf").addEventListener("click",()=>switchOnboardingMode("pdf"));
  $("#reset-onboarding").addEventListener("click",resetOnboarding);
  $("#reset-pdf-flow").addEventListener("click",resetPdfFlow);
  $("#pdf-file").addEventListener("change",e=>{
    const file=e.target.files?.[0]||null;state.pdf.file=file;
    $("#pdf-file-name").textContent=file?(file.name+" · "+Math.ceil(file.size/1024)+" KB"):"";
    $("#pdf-upload-btn").disabled=!file||file.size>25*1024*1024;
  });
  $("#pdf-upload-btn").addEventListener("click",uploadAndExtractPdf);
  $("#generate-candidates-btn").addEventListener("click",generatePdfCandidates);
  $("#approve-high-btn").addEventListener("click",approveHighCandidates);
  $("#build-pdf-agent-btn").addEventListener("click",buildPdfAgent);
  $("#register-pdf-agent-btn").addEventListener("click",registerPdfAgent);
  $("#agent-file").addEventListener("change",e=>{
    const file=e.target.files?.[0]||null;
    state.onboarding.file=file;
    $("#onboarding-file-name").textContent=file?(file.name+" · "+Math.ceil(file.size/1024)+" KB"):"";
    $("#validate-agent-btn").disabled=!file||file.size>10*1024*1024;
  });
  $("#validate-agent-btn").addEventListener("click",validateSelectedAgent);
  $("#register-agent-btn").addEventListener("click",registerOnboardedAgent);
  $("#start-btn").addEventListener("click",startDebate);
  $("#intervene-btn").addEventListener("click",intervene);
  $("#intervention").addEventListener("keydown",e=>{if(e.key==="Enter")intervene()});
}
init();
