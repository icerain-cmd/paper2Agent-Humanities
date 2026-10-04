# T7 — Paper2Agent-Humanities 운영 UI 및 한국어 PDF 등록 복구

**FINAL_STATUS=COMPLETE**

지정한 `/home/leeyongwook/p2a-live-agent-debate`, `feat/live-agent-debate`에서 복구했다. 다른 두 작업본은 수정하지 않았다. 공개 정본 주소는 [https://lab-pc2.taile8e20d.ts.net:8443/](https://lab-pc2.taile8e20d.ts.net:8443/)이며 기존 소유자 인증 후 Debate UI로 열린다. 등록한 새 에이전트는 **이용욱 — 기술생성시대의 매체미학**, ID `paper-e538b7cd3af7190f`다.

## 원인과 수정

1. nginx는 `/`를 backend `/`로 그대로 전달했지만 FastAPI에는 `/debate`만 있었다. backend·proxy·공개 루트가 모두 404였고 `/debate`는 200이었다. nginx 변경 없이 FastAPI `/` → `/debate` 307 redirect를 추가했다. API·SSE·export 경로는 그대로다. 기존 인증 middleware가 루트에도 적용된다.
2. 기존 병렬화는 이미 8페이지/배치·최대 4 worker였다. 실제 64페이지 시험에서 125.61초가 걸려 동기 HTTP 요청과 단일 ‘후보 생성 중’ 표시가 긴 대기로 보였다. UI는 `?background=true`의 202 응답으로 작업을 시작하고 기존 job GET을 1초마다 polling한다. 완료 배치·현재 실행 수·실제 경과 시간을 표시한다. 기존 동기 endpoint 계약도 유지했다.
3. DOI와 제목이 같은 추출 줄에 붙었고 zero-width 문자가 있었다. 이전 fallback은 DOI로 시작하는 줄 전체를 버려 실제 제목을 잃었다. DOI prefix만 분리하고 후속 제목을 보존하며 footnote suffix를 제거했다. DOI는 별도 필드에 저장한다. 내부 PDF Author 값보다 첫 페이지의 명시적 한국어 저자/소속 표기를 우선하되, 일반 영문 제목·저자는 유지한다.
4. UI가 한국어 제목·저자로 한글 Paper ID를 만들었지만 Build는 ASCII ID만 허용했다. 검증은 유지하고, 이 경우 PDF SHA 기반의 안정된 ASCII ID를 사용한다.
5. Codex Node launcher의 자식 프로세스까지 종료해야 하므로 각 배치를 별도 process group으로 실행한다. timeout·배치 실패·진행률 callback 실패 시 해당 그룹을 종료하고 대기 배치를 취소한다. 배치 결과는 원래 배치 순서로 결합하고 temp/output 경로는 독립적이다. 모델 `gpt-6-sol`, 배치 timeout 180초는 그대로다.

백그라운드 작업의 중복 실행을 막고 진행 중 metadata/후보 수정·Build를 거부한다. 상태 파일은 atomic replace로 쓴다. backend 재시작으로 중단된 RUNNING 작업은 FAILED와 재시도 안내로 복구하며 이전 후보를 삭제하지 않는다. 검증 우회나 가짜 page/evidence는 추가하지 않았다.

## 실제 PDF와 브라우저 E2E

원본 cache의 동일 PDF SHA는 `e538b7cd3af7190f7f7afdf2b75ca87e7b89629cc42532cc9cfc61afd83c96d8`이고 원본 파일 해시는 그대로다. 두 실제 시험 모두 extraction은 **64 pages / 64 text pages / 81,320 chars / corruption 0 / PASS**였다.

최종 브라우저 시험은 공개 정본 URL에서 `+ Agent → 논문 PDF → 업로드·Extract → Metadata → 후보 생성 → Review → Build → FINAL VALIDATION → Register`를 직접 실행했다. 제목 `기술생성시대의 매체미학`, 저자 `이용욱`, DOI `10.21793/koreall.2026.133.11`, 자동 Paper ID를 확인했다. 수동으로 유효 ID를 넣어 문제를 우회하지 않았다.

| 항목 | 최종 실측 |
|---|---|
| 시작 시각 | 2026-10-04 12:15:40.808559 UTC |
| 배치 / 실제 최대 병렬 | 8 / 4 |
| HTTP 작업 접수 | 202, 0.06초 |
| 실제 Codex 후보 생성 | 122.16초 |
| 후보 | 150 |
| 승인 / 미검토 / 제외 | 13 / 137 / 0 |
| timeout / failed batch | 0 / 0 |
| 화면 진행률 | 0%, 25%, 50%, 62%, 87% 후 완료 |
| Build·최종 검증 | PASS, reviewed author claims 13개, 오류·경고 0 |
| Register | ACTIVE, `paper-e538b7cd3af7190f` |
| JavaScript 오류 / alert | 0 / 0 |

첫 동기 실측은 125.61초, 후보 147개, 실제 최대 병렬 4, 실패·timeout 0이었다. 두 차례 모두 실제 Codex runtime을 사용했다. 모델 생성 결과가 매번 동일하다고 주장하지 않는다. 최종 150개 span 모두 지정 PDF page의 정확한 부분 문자열임을 확인했고 페이지 순서도 오름차순이었다. 저자 주장 13개를 의미상 원문과 대조해 선택 승인했다. confidence만으로 자동 승인하지 않았다. 미검토 137개는 승인·등록한 근거에 포함하지 않았다.

## 운영 기동과 데이터 보존

작업 시작 시 실행 프로세스와 PID 파일이 달랐고, 수동 실행은 기본 `agent_store`를 사용하면서 서비스 `.env`를 로드하지 않았다. 실제 실행 DB에는 33개 기존 세션이 있었지만 설정된 별도 데이터 폴더는 다른 DB였다. 코드·두 DB·active 디렉터리를 백업했다.

새 등록과 실제 기존 세션을 유지하기 위해 로컬 `debate.env`의 **P2H_DATA_DIR만 현재 실제 데이터 경로**인 `/home/leeyongwook/p2a-live-agent-debate/skills/paper2agent/paper2humanities/agent_store`로 맞췄다. DB·agent_store·원본 PDF를 옮기거나 삭제하지 않았다. 이전 별도 데이터 폴더도 그대로다. 모델·소유자 자격 증명은 바꾸지 않았다. 현재 경로가 앞으로의 정상 서비스 기동 경로다.

표준 controller를 분리된 session으로 기동해 도구 실행 종료에도 backend가 남도록 했다. 기동 후 공개 anonymous root는 401, 기존 owner 인증 root는 307 → `/debate` → 200이다. health는 인증 없이 200이며 기존 세 built-in과 새 등록 에이전트가 모두 로드된다. 인증된 실제 브라우저에서 재시작 후 4 agents·새 논문 표시·JavaScript 오류 0을 확인했다. 초기 수동 실행의 무인증 상태를 최종 운영 상태로 유지한 것은 아니다. 기존 설정에 있던 소유자 인증을 정상 로드했다.

최종 DB는 기존 33개 session ID를 모두 보존하고 실제 회귀 토론 2개만 추가해 35개다. DB schema 변경·session 삭제·built-in 변경·Benjamin V2/V3 corpus 병합은 0이다. nginx 설정과 포트 8765/8766도 그대로다. 인증 파일과 그 백업은 Git에 포함하지 않았다.

백업: `/home/leeyongwook/.local/state/paper2agent-humanities/backups/t7-20261004T120519Z`. 초기 working-tree patch, 기존 두 DB/active, 초기 code, `.env`, 최종 검토 source, 로컬 상세 review 증거를 보존했다. rollback은 여기의 관리 코드·환경 파일로 수행할 수 있으며 현재 운영 DB를 초기 backup으로 덮어쓰지 않아야 신규 등록과 토론이 보존된다.

## 회귀 검증

- 변경 Python 파일 `py_compile`, JavaScript `node --check`, `git diff --check` PASS.
- Paper2Humanities pytest 전체 **180 passed**. 기본 테스트 171개에 경로/auth·DOI/title/byline·batch 병렬 순서/독립 출력·실패 취소/자식 timeout·background 진행/중복/실패 재시도·재시작 복구·한국어 UI ID·callback 실패 guard 9개를 추가했다.
- 한 중간 실행에서 기존 `test_background_start_and_state`의 완료 상태/event 관찰 타이밍 실패가 1회 있었다. 해당 단독 재실행과 이후 전체 suite는 통과했다. 이 작업에서 debate protocol 코드를 변경하지 않았다.
- 실제 built-in `benjamin-artwork-v2` + `lee-aura-2019`의 2-turn 토론을 기동 전후 각각 실행해 COMPLETED를 확인했다. V2/V3는 서로 합치지 않았다.
- 정상 서비스·인증 환경에서도 실제 토론 start → 두 turn 완료 → SSE turn_completed 2건 + debate_completed를 확인했다.
- Markdown / JSON / PDF export 모두 200이며 JSON session identity와 `%PDF` 바이트를 확인했다. 기존 export 구현은 수정하지 않았다.
- 최종 health: status ok, registry_agents 4, registry_rejected 0, database ok, COMPLETED 13 / INTERRUPTED 11 / READY 11, model_runtime available, active_sessions 0.

## 변경 파일과 커밋

Git 추적 코드 변경은 다음 5개다. 여기에 `docs/t7-recovery/` 보고서·측정 JSON·스크린샷·테스트 로그를 추가했다.

- `skills/paper2agent/paper2humanities/src/paper2humanities/api/debate_api.py`
- `skills/paper2agent/paper2humanities/src/paper2humanities/ingestion/candidate_generator.py`
- `skills/paper2agent/paper2humanities/src/paper2humanities/ingestion/service.py`
- `skills/paper2agent/paper2humanities/web/app.js`
- `skills/paper2agent/paper2humanities/tests/test_pdf_ingestion.py`

로컬 운영 설정: `/home/leeyongwook/.config/paper2agent/debate.env`의 데이터 경로만 변경했다.

복구 commit: `46adde6457af1cb51d260f916503d154d0ee6cc4`.

upstream `c7db2a400a61b601987297fbca3723a67252db80`의 newline repairs와 통합한 merge commit: `dbdac823a023af9208934d18d4d5fd7e823364d1`. 로컬 사전 수정은 보존·포함했다. 충돌은 검토한 코드로 통합했고 최종 5개 source 바이트가 E2E/pytest 검토 source와 정확히 같음을 확인했다. reset --hard·clean·force push는 사용하지 않았다.

## 최종 형식

```text
WEB_UI=PASS
ROOT_ROUTE_OR_NGINX_CONTRACT=PASS
HEALTHZ=PASS
MODEL_RUNTIME=AVAILABLE
REGISTRY_EXISTING_AGENTS=PASS
PDF_EXTRACTION_64P=PASS
PDF_METADATA_TITLE=PASS
PDF_CANDIDATE_GENERATION=PASS
PDF_CANDIDATE_GENERATION_NO_HANG=PASS
PDF_AGENT_BUILD=PASS
PDF_FINAL_VALIDATION=PASS
PDF_AGENT_REGISTER=PASS
EXISTING_DEBATE_REGRESSION=PASS
EXPORT_REGRESSION=PASS

ROOT_CAUSE=Missing backend root UI route; DOI-prefixed heading discarded; synchronous 2-minute request without progress; Korean default ID violated ASCII build contract
FILES_CHANGED=5 code/test files + report evidence; local data-dir setting
COMMITS=46adde6457af1cb51d260f916503d154d0ee6cc4; dbdac823a023af9208934d18d4d5fd7e823364d1
WEB_TEST=PASS; canonical authenticated browser and post-restart UI
PDF_TEST=PASS; real identical 64-page PDF, actual Codex, full browser onboarding
CANDIDATE_RUNTIME_SECONDS=122.16
CANDIDATES_TOTAL=150
AGENT_REGISTERED_ID=paper-e538b7cd3af7190f
REGRESSION=180 pytest PASS; existing agents + actual V2 debate/SSE + MD/JSON/PDF PASS
REMAINING_LIMITATIONS=137 candidates remain pending review; other PDFs and model latency not guaranteed; existing async test timing flake observed once
FINAL_STATUS=COMPLETE
```
