import json, hashlib, pathlib, sys
ROOT=pathlib.Path('.').resolve(); P=ROOT/'skills/paper2agent/paper2humanities'
sys.path.insert(0,str(P/'src'))
sys.path.insert(0,str(P/'scripts'))
from paper2humanities import PaperAgent
from paper2humanities.runtime.retrieval import retrieve
from paper2humanities.runtime.attribution import infer_statement_form,infer_attribution_owner
import run_phase3_codex as runner
E=P/'evals/phase3'; F=P/'fixtures'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
checks={}
# Historical artifacts are immutable/exposed; record current hashes, never rewrite them.
for name in ['dev50-live-score.json','dev30-compat-v2-reclassification.json','dev30-compat-v3-reclassification.json','dev30-compat-v5-reclassification.json','holdout30-v5-score.json','dev10-v3-repair-composite-score.json']:
    p=E/name; checks[name]={'sha256':sha(p),'preserved':True}
# DEV9 runtime invariants.
v2=runner.AGENTS['benjamin-artwork-v2']; v3=runner.AGENTS['benjamin-artwork-v3']; lee=runner.AGENTS['lee-aura-2019']
cases=[
 ('003',v2,'V2에서 첫째 기술과 둘째 기술이 인간을 투입하는 방식이 다르다는 저자 주장의 근거','AUTHOR_ATTRIBUTION','b-v2-c-technique-human-use'),
 ('005',v3,'V3에서 제의가치와 전시가치를 작품 수용의 두 극으로 설명하는 근거 페이지','SOURCE_RETRIEVAL','b-v3-c-cult-exhibition'),
 ('006',v2,'V2에서 현대 예술의 사회적 기능을 자연과 인류의 상호작용 연습과 연결하는 근거 페이지','SOURCE_RETRIEVAL','b-v2-c-art-function'),
 ('016_actor',v2,'V2의 자연과 인류의 상호작용 개념을 Lee 2019의 제3기술과 관련해 비판하라','CRITIQUE','b-v2-c-interplay'),
 ('016_target',lee,'V2의 자연과 인류의 상호작용 개념을 Lee 2019의 제3기술과 관련해 비판하라','CRITIQUE','lee-c-transparent'),
]
for key,agent,q,action,expected in cases:
    hits,tr=retrieve(agent,q,action=action); checks['DEV9_'+key]={'pass':expected in tr['selected_statement_ids'],'selected':tr['selected_statement_ids'],'expected':expected}
imm=lee.store.get('lee-c-immersion'); checks['DEV9_021']={'pass': imm.page==17 and bool(imm.evidence_span) and imm.evidence_voice.value=='AUTHOR','page':imm.page,'span':imm.evidence_span}
checks['DEV9_007_008']={'pass': infer_statement_form({'statement_type':'INTERPRETATION','evidence_voice':'EXTERNAL'})=='INTERPRETIVE_STATEMENT' and infer_attribution_owner({'statement_type':'INTERPRETATION','evidence_voice':'EXTERNAL'})=='EXTERNAL'}
# Re-score the actual V5 007/008 accepted attribution judgments under the orthogonal V6 axes.
v5={r['query_id']:r for r in json.load(open(E/'holdout30-v5-responses.json'))['responses']}
for qid in ('H30V5-007','H30V5-008'):
    actual=v5[qid]
    gold={'panel_id':'dev-'+qid,'panel_type':'HOLDOUT30_V6_GOLD','records':[{
      'query_id':qid,'task_family':'FACTUAL','action':'EXTERNAL_ATTRIBUTION','type':'SOURCE_QUOTE',
      'paper':'lee-aura-2019','edition':None,'page':18,'support':['lee-q-benjamin-second-tech'],
      'source_id':'s001-lee-aura-2019','statement_form':'INTERPRETIVE_STATEMENT','attribution_owner':'EXTERNAL'}]}
    scored=runner.score_v6_holdout(gold,{'responses':[actual]},{'response_sha256':'dev','gold_available_during_generation':False})
    checks['DEV9_'+qid[-3:]]={'pass':scored['factual_task_accuracy']==1.0 and not any(scored['hard_gate_counts'].values()),
                              'form':scored['rows'][0]['statement_form'],'owner':scored['rows'][0]['attribution_owner']}
# Re-score the actual V5 H025 alternative grounded path as a scholarly task.
actual=v5['H30V5-025']
gold={'panel_id':'dev-H30V5-025','panel_type':'HOLDOUT30_V6_GOLD','records':[{
  'query_id':'H30V5-025','task_family':'SCHOLARLY','action':'RESEARCH_GAP','type':'AI_SYNTHESIS',
  'paper':'lee-aura-2019','edition':None,'page':17,'support':['lee-q-digital-aura','b-v3-c-aura-withers'],
  'source_id':'s001-lee-aura-2019','required_papers':[{'paper_id':'lee-aura-2019','edition_id':None},{'paper_id':'benjamin-artwork-v3','edition_id':'benjamin-artwork-v3'}]}]}
scored=runner.score_v6_holdout(gold,{'responses':[actual]},{'response_sha256':'dev','gold_available_during_generation':False})
checks['DEV9_025']={'pass':scored['scholarly_task_validity']==1.0 and not any(scored['hard_gate_counts'].values()),
                    'support_ids':actual['turn']['support_ids']}
# 029: pageless interpretation may retrieve as hint but cannot become selected evidence.
class A:
 def available(self): return True
 def generate_typed_turn(self,**kw):
  from paper2humanities.runtime.model_adapter import ModelResult
  p=kw['payload']; t={'text':'insufficient','statement_type':'UNRESOLVED','evidence_voice':'UNKNOWN','support_ids':[],'pages':[],'relation_type':'UNRESOLVED','actor_paper':v3.paper_id,'actor_edition_id':v3.edition_id,'action':p['dialogue_action'],'semantic_support':'UNSUPPORTED','evidence_sufficiency':'INSUFFICIENT','qualification':None,'evidence_span':None,'claims':[]}
  return ModelResult(json.dumps(t), 'test','test',{'attempts':1},'x')
_,tr,_=runner.live_turn(A(),v3,'Benjamin V3의 정신분산과 Lee 2019의 몰입을 함께 검토하는 연구질문 하나를 제시하라.','RESEARCH_QUESTION',{},supporting_agents=(lee,))
checks['DEV9_029']={'pass':'lee-i-distance' not in tr['selected_statement_ids'] and 'lee-c-immersion' in tr['selected_statement_ids'] and not tr['missing_required_sources'],'selected':tr['selected_statement_ids'],'hints':[x['statement_id'] for x in tr['retrieval_hints']]}
# Zero-overlap stays empty.
hits,tr0=retrieve(v2,'quasar nebula astrophysics',limit=50); checks['ZERO_OVERLAP']={'pass':not hits and not tr0['selected_statement_ids']}
# No query-specific hardcoding in runtime/scripts.
needle=['H30V5-003','H30V5-005','H30V5-006','H30V5-016','H30V5-021','H30V5-025','H30V5-029']
production_paths=list((P/'src'/'paper2humanities'/'runtime').rglob('*.py'))+[P/'scripts'/'run_phase3_codex.py']
code='\n'.join(path.read_text(errors='ignore') for path in production_paths)
checks['NO_QUERY_ID_HARDCODING']={'pass':not any(x in code for x in needle),
                                  'production_files_scanned':[str(path.relative_to(P)) for path in production_paths]}
report={'schema_version':1,'task':'V6_PRE_FREEZE_DEV_REGRESSION','historical_artifacts_policy':'preserve exposed historical scores; do not rescore/overwrite V5','checks':checks}
report['pass']=all(v.get('pass',True) for v in checks.values())
(E/'v6-pre-freeze-dev-regression.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'pass':report['pass'],'failed':[k for k,v in checks.items() if v.get('pass') is False]},ensure_ascii=False))
