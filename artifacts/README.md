# artifacts/ — 생성 산출물 (커밋 안 함)

설계 근거: `doc/artifact_management_design.md` §2·§4·§5.

**핵심 원칙: "다시 만들 수 있는가?"** 다시 만들 수 있으면 여기, 다시 만들 수 없거나
제출 증거로 써야 하면 `doc/`에 둔다.

## 폴더

| 경로 | 내용 | 커밋 |
|---|---|---|
| `runs/<run_id>/` | 실행 1회 = 폴더 1개. `manifest.json`·`requests.jsonl`·`responses.jsonl`·`metrics.json`·`notes.md`·`logs/` | X |
| `eval/` | eval 스크립트가 남기는 원본 결과 | X |
| `captures/<run_id>/` | 시연·발표용 원본 스크린샷 | X |
| `traces/` | LangSmith 내보내기·trace ID 목록 | X |
| `exports/` | PPT/PDF/zip 등 바이너리 | X |
| `tmp/` | 7일 뒤 삭제해도 되는 중간물·초안 | X |

## run_id 규칙

`YYYYMMDD-HHMMSS_<backend>_<variant>` (KST 기준, 예: `20261020-153012_ollama_after-rag`)

- `variant`는 `before-*` / `after-*` 접두어로 시작한다 — 비교 대상을 이름으로 찾기 위해.
- 같은 `run_id` 폴더는 **덮어쓰지 않는다.** 재실행은 새 타임스탬프 폴더를 만든다.

## 정리 기준

- `runs/`의 최종 비교 run(체크리스트에 인용된 것)은 채점 후까지 보존한다.
- 나머지 `runs/`, `tmp/`, `../var/logs/`는 30일(	tmp·로그는 7일) 뒤 정리한다.

## 주의

- `manifest.json`의 `env`는 **허용 목록 방식**이다. API 키·토큰·`.env` 전체 덤프 금지.
- 이 폴더가 비어 있는 것은 정상이다(`.gitignore` 대상이라 `git status`에 안 보인다).
