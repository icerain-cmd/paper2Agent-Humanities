# Paper2Agent-Humanities 사용자 매뉴얼

> **상태:** 실험적 인문학 확장판입니다. 기본 Paper2Agent는 `main`에 있고, Paper2Humanities의 근거 기반 대화 기능은 Draft PR에서 개발·검증 중입니다. 연구 결과를 인용·출판하기 전에는 반드시 원문을 직접 확인하십시오.

## 1. 무엇을 위한 도구인가

Paper2Agent-Humanities는 논문을 단순 요약하는 대신 **각 논문을 자기 문헌 근거에 묶인 Paper Agent로 만들고 여러 논문의 주장·개념·해석을 대화시키는 연구 환경**입니다.

인문학 층은 다음을 구분합니다.

- `SOURCE_QUOTE`: 원문 직접 인용
- `AUTHOR_CLAIM`: 원문으로 확인되는 저자의 주장
- `INTERPRETATION`: 연구자의 해석
- `AI_SYNTHESIS`: AI가 여러 근거를 연결한 종합
- `CRITIQUE`: 비판
- `UNRESOLVED`: 근거 부족·충돌·미해결 문제

핵심은 **AI가 그럴듯하게 말하는 것보다 누가, 어느 문헌에서, 무엇을 실제로 말했는지를 먼저 보존하는 것**입니다.

## 2. 시작하기

### 요구 환경
Git, Python, Claude Code·Codex 등 skill/shell 지원 코딩 에이전트, 분석할 PDF 또는 원문이 필요합니다.

```bash
git clone https://github.com/icerain-cmd/paper2Agent-Humanities.git
cd paper2Agent-Humanities
```

안정적인 원본 기능은 루트 `README.md`와 `skills/paper2agent/SKILL.md`를 따르십시오. Paper2Humanities 실험 기능은 관련 Draft PR을 확인하십시오.

### 권장 순서

1. 권위 있는 논문 원문을 확보합니다.
2. **Paper2Skill을 먼저** 사용해 ingest, 페이지 검토, source hash 확인을 수행합니다.
3. 검토된 source bundle에서 Paper Agent를 만듭니다.
4. 각 명제를 위 여섯 유형으로 구분합니다.
5. `AUTHOR_CLAIM`과 `SOURCE_QUOTE`의 페이지 근거를 검사합니다.
6. 다중 논문 연구에서는 **논문마다 별도 Paper Agent**를 유지합니다.
7. 비판·응답 후 원문 근거를 다시 확인합니다.
8. 종합과 연구질문은 AI 산출물로 취급하고 연구자가 최종 판단합니다.

## 3. 반드시 지킬 연구 경계

### 한 에이전트 = 한 문헌 코퍼스
Paper Agent는 자기 논문의 근거로만 저자를 대변해야 합니다. 다른 논문, 후대 저술, 웹 지식, 모델의 일반 지식을 몰래 섞지 마십시오.

### 판본을 합치지 않는다
같은 저자의 같은 글이라도 판본이 다르면 필요에 따라 독립 source로 관리합니다. 이 프로젝트의 Benjamin 실험도 V2와 V3를 별도 Paper Agent source로 유지했습니다.

### 저자의 주장과 해석을 분리한다
- “저자는 X라고 말한다.” → `AUTHOR_CLAIM`, 원문 근거 필요
- “이 대목은 X로 해석할 수 있다.” → `INTERPRETATION`
- “A와 B를 함께 보면 C가 보인다.” → `AI_SYNTHESIS`

좋은 AI 해석도 자동으로 저자의 주장이 되지 않습니다.

### 모르면 멈춘다
근거가 부족하거나 충돌하면 `UNRESOLVED`로 남깁니다. 빈칸을 그럴듯한 문장으로 채우지 않습니다.

## 4. 기본 연구 워크플로

### A. 한 논문 깊게 읽기
Agent에게 핵심 명제와 페이지, 직접 근거, 개념 정의, 논증의 전제와 결론, 명시적으로 말하지 않은 것, 해석이 필요한 지점을 요구하십시오. 목표는 요약이 아니라 **논증 지도**입니다.

### B. 두 논문 비교하기
공통 연구질문 하나를 정한 뒤 각 Agent가 자기 논문만 근거로 답하게 합니다. 비교 단계에서도 각 문장의 출처를 유지합니다.

### C. 논문 에이전트 토론
권장 흐름은 다음과 같습니다.

1. **POSITION** — 각 논문의 입장과 근거
2. **CRITIQUE** — 상대 입장의 전제·공백·긴장 지적
3. **REBUTTAL** — 자기 문헌 근거 안에서 응답
4. **REVISION** — 수정 가능한 지점과 유지할 지점 구분
5. **CLOSING** — 합의점, 잔여 이견, 새 연구질문

“벤야민이라면 이렇게 말했을 것이다” 같은 자유 역할극보다 **“이 판본에서 확인되는 근거에 따르면”**이라는 방식이 연구용으로 안전합니다.

### D. 2~3개 논문 토론
하나의 쟁점을 중심으로 발언시키고 source identity를 유지하십시오. synthesis agent는 심판이 아닙니다. 승패 대신 공통 문제, 잔여 차이, 문헌의 빈 공간, 추가 검증 주장, 후속 연구질문을 정리하게 합니다.

## 5. 인문학자가 슬기롭게 사용하는 방법

### 1) 내 논문을 먼저 공격하게 하라
자신의 논문을 Agent로 만들고 고전 또는 경쟁 이론의 Agent에게 비판하게 하십시오. 익숙해서 보이지 않던 전제와 개념적 비약을 발견하는 데 유용합니다.

### 2) ‘누가 옳은가’보다 ‘어디서 갈라지는가’를 물어라
인문학에서는 승패보다 **개념이 갈라지는 정확한 지점**이 더 중요한 연구 성과가 될 수 있습니다.

### 3) 아투라(Atura)의 순간을 기록하라
토론 중 예상하지 못한 연결이나 순간적 통찰이 나타나면 결론으로 즉시 채택하지 말고 연구 메모로 저장하십시오.

기록할 것:
- 어떤 문장·개념의 충돌에서 발생했는가
- 어떤 source가 계기였는가
- AI가 제안했는가, 연구자가 발견했는가
- 원문으로 검증 가능한가
- 어떤 추가 문헌이 필요한가

**통찰의 발생과 통찰의 검증은 별개의 단계입니다.**

### 4) 불일치를 보존하라
억지 합의를 요구하지 마십시오. 화해하지 않는 두 이론의 차이를 `UNRESOLVED`로 남기는 편이 더 생산적일 수 있습니다.

### 5) 답보다 질문을 생산하라
토론 끝에 다음을 물으십시오: 두 문헌이 답하지 않은 질문은 무엇인가? 같은 개념을 다르게 정의하는가? 한 이론이 다른 이론의 맹점을 드러내는가? 판본·시대 변화가 논증을 바꾸는가?

### 6) AI를 저자 시뮬레이터가 아니라 연구 환경으로 사용하라
Paper Agent는 실제 저자의 의식이나 의도를 재현하지 않습니다. **검토된 문헌을 근거로 제한된 발화를 생성하는 연구 인터페이스**입니다.

## 6. 연구 전 체크리스트

- [ ] 인용문과 페이지가 실제 원문과 일치하는가?
- [ ] `AUTHOR_CLAIM`이 해석을 저자의 말처럼 바꾸지 않았는가?
- [ ] 판본이 섞이지 않았는가?
- [ ] 다른 논문의 주장이 해당 저자의 주장으로 들어가지 않았는가?
- [ ] AI synthesis를 학계의 합의처럼 표현하지 않았는가?
- [ ] 반론에 대한 답이 해당 논문의 근거 안에 있는가?
- [ ] 근거 부족을 `UNRESOLVED`로 남겼는가?
- [ ] 새 연구질문의 선행연구·독창성을 별도로 검증했는가?
- [ ] 최종 해석과 판단을 연구자가 검토했는가?


## 7. 따라하기: 실제 Live Debate 실행

현재 범용 Live Debate 실행기는 `main`이 아니라 **`feat/live-agent-debate` 브랜치**에 있습니다. 아래 절차는 현재 저장소에서 실제 확인된 파일과 옵션만 사용합니다.

### 7.1 저장소와 실험 브랜치 준비

```bash
git clone https://github.com/icerain-cmd/paper2Agent-Humanities.git
cd paper2Agent-Humanities
git switch feat/live-agent-debate
```

Codex가 설치되어 있고 모델을 호출할 수 있는 환경이 필요합니다. 실행기는 PATH의 `codex`를 먼저 찾고, 없으면 `~/.local/bin/codex`를 확인합니다.

### 7.2 현재 등록된 샘플 Paper Agent 확인

현재 Live Debate 브랜치의 fixture에는 다음 연구용 Agent가 포함되어 있습니다.

- `benjamin-artwork-v2-agent.json`
- `benjamin-artwork-v3-agent.json`
- `lee-aura-2019-agent.json`
- `lee-aura-2019-phase2-agent.json`

fixture 위치:

```text
skills/paper2agent/paper2humanities/fixtures/
```

Benjamin V2와 V3는 서로 다른 판본이므로 별도 Agent로 유지됩니다.

### 7.3 벤야민–이용욱 토론 실행

저장소 루트에서 다음 형식으로 실행합니다.

```bash
python skills/paper2agent/paper2humanities/scripts/run_live_debate.py \
  --agents benjamin-artwork-v2 lee-aura-2019 \
  --topic "기술적 복제와 아우라의 변형은 어떻게 이해해야 하는가?" \
  --turns 8 \
  --json-out debate-result.json
```

실행기의 기본 모델은 현재 코드상 `gpt-6-sol`, 기본 토론 길이는 **전체 8턴**입니다. `--turns 8`은 각 Agent가 8번씩 말한다는 뜻이 아니라 **세션 전체 발언 수가 8개**라는 뜻입니다.

다른 모델을 사용할 수 있는 환경이라면:

```bash
python skills/paper2agent/paper2humanities/scripts/run_live_debate.py \
  --agents benjamin-artwork-v3 lee-aura-2019 \
  --topic "집중과 산만, 기술 매체의 수용 방식은 어떻게 연결되는가?" \
  --turns 10 \
  --model <사용 가능한 모델 ID> \
  --json-out debate-result.json
```

터미널에는 각 턴마다 Agent, 행동 유형, 발언, 근거 ID와 페이지가 표시됩니다. 충분한 근거가 없으면 `ABSTAIN`이 표시될 수 있습니다. 이는 실패가 아니라 근거 경계를 지키는 정상 동작입니다.

### 7.4 결과 저장과 연구노트 만들기

`--json-out`으로 저장한 JSON은 토론 세션의 연구 기록입니다. 원본을 보존하고 별도의 연구노트에서 다음을 기록하는 방식을 권장합니다.

```text
연구질문:
사용한 Agent / 판본:
토론 세션 파일:
핵심 충돌:
가장 강한 반론:
내 논문의 수정 필요 지점:
Atura 후보:
추가 원문 검증:
추가 선행연구:
최종 연구자 판단:
```

특히 **Atura 후보**는 토론 결과의 결론과 분리하십시오. 순간적 통찰은 연구 가설의 시작점이지 검증 완료된 지식이 아닙니다.

### 7.5 웹 인터페이스 실행

Live Debate 브랜치에는 로컬 API와 웹 UI도 포함되어 있습니다. API 실행 스크립트는 다음과 같습니다.

```bash
python skills/paper2agent/paper2humanities/scripts/serve_debate_api.py \
  --host 127.0.0.1 \
  --port 8765
```

기본 포트는 `8765`입니다. 관련 웹 자산은 다음 위치에 있습니다.

```text
skills/paper2agent/paper2humanities/web/
```

이 기능 역시 현재 실험 브랜치 기능이므로 공개 서비스용 안정판으로 간주하지 마십시오.

## 8. 내 논문을 Paper Agent로 추가하려면

여기서는 **자동화된 것과 아직 연구자가 해야 하는 것을 구분하는 것이 중요합니다.**

현재 저장소에는 이미 구축된 fixture Agent를 선택해 Live Debate를 실행하는 범용 runtime이 있습니다. 그러나 임의의 인문학 PDF를 넣으면 완성된 Humanities Agent가 자동 등록되는 단일 명령은 아직 `main`의 안정 기능으로 제공되지 않습니다.

따라서 새 논문은 다음 절차로 추가하는 것이 안전합니다.

### 8.1 원문을 먼저 Paper2Skill로 검증

논문 PDF를 바로 역할극 프롬프트에 넣지 마십시오. Paper2Skill의 source verification을 먼저 거쳐 페이지와 source identity를 확인합니다.

코딩 에이전트에게는 다음과 같은 요청을 사용할 수 있습니다.

```text
이 논문을 Paper2Skill로 처리해라.
페이지 검토와 source hash를 보존하고, 인문학 연구용 Paper Agent를 만들기 위한
reviewed source bundle을 준비해라. 저자 주장과 해석을 구분하고
확인할 수 없는 페이지나 주장은 만들어내지 마라.

논문: <PDF 또는 접근 가능한 원문>
작업 폴더: <PROJECT_DIR>
```

### 8.2 Paper Agent의 최소 조건

새 Agent를 토론에 넣기 전에 최소한 다음이 있어야 합니다.

- 고유한 `paper_id / agent_id`
- 정확한 저자·논문·판본 정보
- 검토된 evidence index
- 근거 statement ID
- 실제 페이지 정보
- `AUTHOR_CLAIM`과 `INTERPRETATION`의 구분
- 허용된 corpus 범위

논문의 저자가 나 자신이라 해도 같은 기준을 적용하십시오.

### 8.3 등록 후 먼저 단독 검증

바로 다중 토론을 시작하지 말고 먼저 새 Agent에게 자기 논문에 대한 질문을 던집니다.

1. 핵심 명제 세 개와 근거 페이지를 제시하라.
2. 이 논문이 명시적으로 주장하지 않는 것을 세 가지 말하라.
3. 해석이 필요한 문장과 저자의 직접 주장을 구분하라.
4. 근거가 없는 질문에는 답하지 말고 `UNRESOLVED` 또는 abstain하라.

이 단계에서 잘못된 저자 귀속이나 가짜 페이지가 나오면 토론에 투입하지 마십시오.

### 8.4 두 Agent로 시작하고 세 Agent로 확장

처음에는 **2개 Agent + 하나의 명확한 쟁점**이 가장 좋습니다. 토론이 안정된 뒤 세 번째 논문을 추가하십시오.

좋은 주제:
- 두 논문의 핵심 개념이 정확히 어디에서 갈라지는가?
- A의 이론은 B가 설명하지 못하는 무엇을 설명하는가?
- B의 비판을 받아들이면 A의 어떤 명제가 수정되어야 하는가?

좋지 않은 주제:
- 누가 더 위대한가?
- 두 사람이라면 오늘날 AI를 어떻게 평가할까?
- 자유롭게 토론해라.

후자는 문헌 근거보다 역할극과 모델의 일반 지식이 개입할 가능성이 큽니다.

## 9. 토론을 논문 연구로 전환하는 법

Live Debate 자체가 연구 결과는 아닙니다. 다음 세 단계를 거쳐야 합니다.

**발견 → 검증 → 연구자 판단**

### 발견
Agent 간 충돌에서 새로운 연결, 반론, Atura 후보를 찾습니다.

### 검증
해당 턴의 evidence ID와 페이지를 실제 원문에서 다시 읽습니다. 필요하면 관련 선행연구를 추가 조사합니다.

### 연구자 판단
그 연결이 단순한 언어적 유사성인지, 실제 개념적 관계인지 판단합니다. 논문에 사용할 경우 AI 토론 문장을 그대로 권위로 인용하지 말고 원문과 선행연구를 근거로 자신의 논증을 다시 구성합니다.

이 과정을 거치면 Paper2Agent-Humanities는 ‘AI가 대신 논문을 쓰는 도구’가 아니라 **연구자가 문헌 사이의 마찰을 설계하고 새로운 질문을 발견하는 연구 환경**으로 기능합니다.

## 10. 현재 구현 상태와 인용

Paper2Humanities는 upstream core를 덮어쓰지 않는 sidecar 확장으로 개발 중입니다. 현재 `main`은 원본 Paper2Agent에 가깝고 Humanities 기능은 Draft PR에 단계적으로 쌓여 있습니다. 따라서 이 문서는 현재 연구 철학과 검증된 워크플로를 안내하며, 모든 실험 기능이 `main`에서 단일 명령으로 제공된다는 뜻은 아닙니다.

연구에 사용할 때는 원본 Paper2Agent/Nature 논문을 적절히 인용하고, Humanities 확장을 사용했다면 commit/branch, source 판본, 모델, 프롬프트·프로토콜, 인간 검토 절차도 기록하십시오.

**AI가 생성한 토론은 문헌을 대체하지 않습니다. 가장 중요한 근거는 언제나 원문입니다.**
