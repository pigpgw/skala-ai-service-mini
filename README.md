# skala-ai-service-mini

SKALA AI 서비스 Mini-project 과제 1번 — 기존 Base AI Agent(인시던트 대응 에이전트)를 개선하는 개인 과제 저장소다.
FastAPI(:8100) + LangGraph v2 + MCP 2서버 구조이고, 브라우저 채팅 화면은 Vue 3(CDN)다.
에이전트는 요청 한 건을 route → plan → gate → research → replan_check → analysis → write → validate → finalize 순서로 처리한다.

## 실행

```bash
bash sh/setup_venv.sh      # 최초 1회
bash sh/setup_ollama.sh    # 로컬 모델 준비
bash sh/run_agent_ollma.sh # 백엔드 기동 (:8100)
bash sh/run_frontend.sh    # 채팅 화면 (:8600)
```

자세한 사용법·캡처는 `doc/README.md`(메인 매뉴얼)와 `doc/manual_ollma.md`, `doc/manual_openai.md`를 본다.
실행 순서·비용·종료 방법은 `sh/README.md`에 정리돼 있다.

## 문서

| 문서 | 용도 |
|---|---|
| `doc/README.md` | 메인 매뉴얼 (구조·실행·아키텍처) |
| `doc/evaluation-checklist.md` | 평가 항목 진행 추적 (상태·증거 경로) |
| `doc/artifact_management_design.md` | 폴더·산출물 구조 설계안 |
| `doc/regression_test_queries.md` | Before/After 공통 입력 (고정 질의 세트) |
| `AGENTS.md` | 작업 규칙 (AI 에이전트·사람 공통 계약) |

## 폴더

| 폴더 | 내용 |
|---|---|
| `agent/` | LangGraph 그래프, LLM 백엔드 3종, MCP 클라이언트, 세션 저장소 |
| `data/` | 입력 데이터 (`monitoring.json`, `runbooks/`) — 측정 기준선 |
| `doc/` | 매뉴얼·설계·체크리스트·실행 캡처 |
| `sh/` | 실행 스크립트 |
