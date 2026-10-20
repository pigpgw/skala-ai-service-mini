# AGENTS.md — sh/ (실행 스크립트)

상위: 루트 `AGENTS.md`. 이 폴더는 실행·준비 스크립트만 둔다. 스크립트를 고치면 과제 매뉴얼(`doc/README.md`)의 안내와 어긋나지 않는지 확인한다.

## 기존 스크립트

| 파일 | 역할 | 과금 |
|---|---|---|
| `setup_venv.sh` | `.venv` 생성 + `requirements.txt` 설치 | 없음 |
| `setup_ollama.sh` | 로컬 모델 준비 (`OLLAMA_FORCE_REFRESH=1`이면 두 모델 삭제 후 재구성) | 없음 |
| `run_agent_ollma.sh` | 백엔드 기동 (`:8100`, `LLM_BACKEND=ollama`) | 없음 |
| `run_agent_openai.sh` | 백엔드 기동 (`LLM_BACKEND=openai`) | **과금** |
| `run_frontend.sh` | `web_demo_server.py` 기동 (`:8600`) — 백엔드가 먼저 떠 있어야 함 | 없음 |
| `make_student_zip.sh` | 배포 zip 생성 (`.env`·생성물 제외) | 없음 |

## 작성 규칙

- 첫 줄은 `#!/usr/bin/env bash`, 이어서 `set -euo pipefail`.
- 경로는 항상 프로젝트 루트 기준으로 잡는다: `cd "$(dirname "$0")/.."`.
- `.venv`가 있으면 PATH 앞에 꽂는다: `[ -x ".venv/bin/python3" ] && export PATH="$PWD/.venv/bin:$PATH"`. 계속 venv를 요구하면 안내 후 종료한다.
- `.env`가 없으면 `cp .env.example .env` 안내를 출력하고 종료한다. 키 이름 외의 값을 출력하지 않는다.
- 기존 포트를 쓰는 프로세스는 `lsof -ti:8100 | xargs kill -9`로 정리한 뒤 띄운다 (`:8600`도 동일).
- 기동 후에는 `/health`를 폴링해서 준비 완료를 확인하고, 다음에 실행할 명령(예: `run_frontend.sh`)을 안내로 출력한다.
- 파일은 프로젝트 루트 기준 상대 경로만 참조한다. 폴더를 통째로 옮겨도 동작해야 한다(외부 절대경로 의존 금지).
- 종료는 `Ctrl+C`로 안내한다. 백그라운드 프로세스는 `trap`으로 정리한다.

### 새 스크립트 골격

```bash
#!/usr/bin/env bash
#
# <한 줄 설명>
#
# 실행:
#   bash sh/<name>.sh
#
set -euo pipefail
cd "$(dirname "$0")/.."

[ -x ".venv/bin/python3" ] && export PATH="$PWD/.venv/bin:$PATH"
[ -f .env ] || { echo "ERROR: .env가 없습니다 — cp .env.example .env 후 키를 채워주세요."; exit 1; }
```

## 이름 규칙

| 접두어 | 용도 |
|---|---|
| `setup_*` | 환경 준비 (여러 번 실행해도 안전해야 함) |
| `run_agent_*` | 백엔드 기동 (백엔드 이름을 접미어로) |
| `run_*` | 그 외 실행 (프론트엔드·도구) |
| `make_*` | 산출물 생성 |

## 금지

- `.env` 내용, API 키, 토큰 출력
- `rm -rf`를 프로젝트 루트나 홈을 향해 실행
- 측정 결과 파일을 스크립트가 덮어쓰기 (측정은 실행별 새 파일로 남긴다)
- 과금 스크립트에서 y/N 확인 제거

## 세션 DB 경로 (2026-10-20, 설계 P2)

`session.db`는 루트가 아니라 **`var/session.db`**에 있다(런타임 상태는 `var/`에 모은다).
`run_agent_ollma.sh`·`run_agent_openai.sh`는 기동 전에 `rm -f var/session.db`로 초기화한다.
경로를 되돌리려면 이 두 스크립트와 `agent/session_store.py`의 `DB_PATH`를 **같은 작업에서** 고친다.

## 배포 zip 제외 규칙 (2026-10-20, 설계 P2)

`make_student_zip.sh`는 `.env`·`.venv`·`__pycache__`·`session.db`·`*.log`에 더해
`artifacts`(측정 원본)·`var`(런타임 상태)·`.archify`(도구 작업물)·`.pytest_cache`·`.git`·`doc/reports`(제출 산출물)도 제외한다.
제외 대상을 늘릴 때는 여기를 함께 갱신한다.
