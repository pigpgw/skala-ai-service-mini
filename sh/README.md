# sh/ — 실행 스크립트

모든 스크립트는 프로젝트 루트에서 실행한다(`bash sh/<name>.sh`). 스크립트 안에서 `cd "$(dirname "$0")/.."`로 루트로 이동하므로 어디서 실행해도 동일하게 동작한다.

## 순서

| 순서 | 명령 | 비용 | 용도 |
|---|---|---|---|
| 1 | `bash sh/setup_venv.sh` | 없음 | `.venv` 생성 + 의존성 설치 (최초 1회) |
| 2 | `bash sh/setup_ollama.sh` | 없음 | 로컬 모델 준비 — 있는 모델은 재사용 |
| 3 | `bash sh/run_agent_ollma.sh` | 없음 | 백엔드만 기동, curl·웹으로 직접 테스트 |
| 3' | `bash sh/run_agent_openai.sh` | **과금** | 실제 OpenAI API (y/N 확인 후 진행) |
| 4 | `bash sh/run_frontend.sh` | 백엔드 따름 | `http://localhost:8600` 채팅 화면 (백엔드가 먼저 필요) |

개발이 어느 정도 정리되면 3 대신 3'로 실제 모델을 쓴다.

## 모델 바꾸기

```bash
OLLAMA_FORCE_REFRESH=1 bash sh/setup_ollama.sh                     # 두 모델 삭제 후 재구성
OLLAMA_FAST_MODEL=qwen3:1.7b OLLAMA_QUALITY_MODEL=qwen3:14b bash sh/setup_ollama.sh
```

모델을 바꾸면 응답 품질·지연이 달라진다. Before/After 측정 조건에 모델 이름을 적는다.

## 확인

```bash
curl -s localhost:8100/health
curl -s localhost:8100/version
curl -sN -G "localhost:8100/chat/stream" --data-urlencode "message=payments-service 응답이 느려요"
```

## 종료

- `run_agent_*.sh`, `run_frontend.sh`는 포어그라운드로 떠 있다. 해당 터미널에서 `Ctrl+C`.
- 다음 기동 스크립트가 `:8100`·`:8600`을 쓰는 프로세스를 자동으로 정리한다.

## 문제 해결

| 증상 | 원인 | 조치 |
|---|---|---|
| 패키지 누락(`ModuleNotFoundError`) | `.venv`가 없어 시스템 `python3`로 떨어짐 | `bash sh/setup_venv.sh` 먼저 실행 |
| `ERROR: .env가 없습니다` | 키 파일 없음 | `cp .env.example .env` 후 키 입력 |
| 프론트는 열리는데 채팅이 전부 에러 | 백엔드(`:8100`)가 안 떠 있음 | 3 또는 3' 먼저 실행 |
| `ollama가 설치되어 있지 않습니다` | Ollama 미설치 | https://ollama.com 설치 후 재실행 |
