# AGENTS.md — doc/ (문서)

상위: 루트 `AGENTS.md`. 상위 과제 지침(`skala-tasks/AGENTS.md`)의 보고서 작성 기본값이 이 폴더에도 적용된다.

## 문서 역할

| 문서 | 역할 | 성격 |
|---|---|---|
| `README.md` | 메인 매뉴얼 — 구조·실행·아키텍처 | 배포판 원본. 내 판단을 섞지 않는다 |
| `evaluation-checklist.md` | 평가 항목 진행 추적 | 갱신 대상. 상태와 증거 경로를 함께 적는다 |
| `artifact_management_design.md` | 폴더·산출물 구조 설계안 | 설계 + 실행 기록. P0~P3 실행 완료 |
| `manual_ollma.md`, `manual_openai.md` | 백엔드별 사용법 + 실행 캡처 | 참고 |
| `regression_test_queries.md` | Before/After 공통 입력(고정 질의 세트) | 측정 기준선 |
| `rag_design.md` | E1 RAG 설계·임계값·측정 결과 | 설계 + 측정 결과 |
| `reports/evidence/index.md` | 주장 ↔ 증거 ↔ 재현 명령 대조표 | 제출용 근거 |
| `reports/evidence/before_after.md` | Before/After 표 (원본에서 자동 생성) | 제출용 근거 |
| `reports/evidence/metrics/*.json` | 원본에서 잘라낸 요약 수치 | 커밋 대상(원본은 `artifacts/`) |
| `reports/result_report.md` · `.pdf` | 최종 결과 보고서(제출본) | 제출용. 수치는 `evidence/`에서 인용 |
| `reports/presentation_outline.md` | 발표 구성안·시간 배분·예상 질문 | 발표 준비 |
| `reports/presentation.html` · `presentation.pdf` | 발표 슬라이드(16:9, 10장) | 제출용 |
| `reports/images/*.png` | 보고서에 넣는 시연 캡처 | 커밋 대상(원본은 `artifacts/captures/`) |
| `design/architecture.html` | 개선 시스템 아키텍처 다이어그램 (archify) | 제출용 |
| `tools/md2html.py` | Markdown → HTML (보고서 PDF 생성) | 도구 |
| `tools/build_pptx.py` | 발표 HTML → PPTX | 도구 |
| `tools/capture_ui.mjs` | 실제 브라우저로 시연 화면 캡처 | 도구 |
| `image_usecase/`, `image_usecase_openai/` | 매뉴얼 캡처 이미지(JPEG, 2026-10-20 압축) | 경로 유지 — `doc/README.md` 트리를 건드리지 않기 위해 |

`README.md`는 강사 제공 매뉴얼이라 내용을 임의로 바꾸지 않는다. 내 판단·실측은 `evaluation-checklist.md`와 별도 보고서에 쓴다. 매뉴얼과 내 문서가 충돌하면 **코드와 실행 결과를 우선**하고, 차이를 체크리스트에 남긴다.

## 수치 인용 규칙

- 모든 수치는 측정 원본 파일 경로와 함께 적는다. 원본 없는 숫자는 쓰지 않는다.
- before/after 표에는 측정 조건(백엔드, 모델, 입력 세트, 실행 시각)을 함께 적는다.
- 다른 조건에서 나온 수치를 같은 조건의 비교처럼 쓰지 않는다.
- 아직 측정하지 않은 항목은 빈칸으로 두고 `[확인 필요]`로 표시한다.

## 작성·보관 규칙

- 초안·중간 산출물은 커밋하지 않는다. 설계안 P0 이후에는 `artifacts/tmp/`에 두고, 확정된 문서만 `doc/`에 둔다.
- 캡처 파일명은 발표 순서를 드러내게 붙인다: `NN_<장면>.png`.
- 이미지 참조 경로를 바꾸면 그 이미지를 쓰는 문서의 링크도 함께 고친다(P1에서 `manual_*.md` 수정 필요).
- 이 폴더는 측정 원본 저장소가 아니다. 원본 JSON·trace는 `artifacts/`에 두고 문서는 경로만 링크한다.

## 금지

- 실행하지 않은 명령의 결과를 캡처·수치처럼 기록
- 측정하지 않은 개선율·정확도·비용 절감 서술
- 실패한 시도 지우고 성공만 남기기 (실패 원인도 학습 근거로 남긴다)
- 아이콘 사용, 과장된 표현 (`skala-tasks/AGENTS.md` 보고서 기본값)
