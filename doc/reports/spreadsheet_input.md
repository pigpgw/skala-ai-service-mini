# Google Spread 입력용 — 결과 보고서 붙여넣기 본문

과제 1번(Base AI Agent 기능 개선/추가) · 광주 3반 79번 박건우 · 2026-10-22

아래 본문을 스프레드시트 셀에 그대로 붙여 넣는다(마크다운 표는 붙여넣으면 표로 인식된다).
긴 보고서는 `doc/reports/result_report.md`(PDF)를 링크로 함께 남긴다.

---

## 1. 과제 정보

- 과제 선택: 1번 — Base AI Agent 기능 개선/추가
- 대상 코드: all_total_vue_student (FastAPI + LangGraph v2 + MCP 2서버 인시던트 대응 에이전트)
- 개선 방향: RAG 기반 RunBook 선택 · 데이터 확장 · 평가 하네스 구축
- Git 주소: https://github.com/pigpgw/skala-ai-service-mini
- 보고서 원문: doc/reports/result_report.md (PDF 동봉)

## 2. 무엇을 개선했나

1. RAG 기반 RunBook 선택
   - 기존: 키워드 규칙을 순서대로 보다가 처음 맞는 것을 고름(질의문을 보지 않음, 규칙 순서가 증상 우선순위와 무관)
   - 개선: 런북 10종을 임베딩해 의미 검색(질의 + 시스템 + 상태 + 알림을 입력). 유사도 하한·1·2위 격차를 못 넘으면 기존 keyword 경로로 폴백
   - 근거 노출: /health.rag, /chat metadata, SSE ReplanCheck 이벤트
2. 데이터 확장
   - 모니터링 시스템 6종 → 12종, 런북 6종 → 10종(신규 유형 4종: queue-backlog, cert-expiry, connection-pool, replication-lag)
   - 파일 선택은 agent/data_profile.py 한 곳에서만(DATA_PROFILE=base|extended). 기존 monitoring.json은 기준선으로 보존
3. 평가 하네스
   - 실행 1회 = artifacts/runs/<run_id>/ 폴더 1개(manifest·metrics·requests/responses jsonl)
   - accuracy·macro-F1·혼동행렬·지연 percentile을 eval/metrics.py로 계산, 테스트 50개(unit·integration)

## 3. 측정 결과

조건: fake 백엔드, DATA_PROFILE=extended, 임베더 qwen3-embedding:0.6b, 임계값 0.50/0.03, 10문서 인덱스.
Before와 After는 같은 입력·같은 데이터·같은 임계값에서 실행했다.

| 지표 | Before (keyword) | After (RAG) | 차이 |
|---|---|---|---|
| 40문항 분류 정확도 | 13/40 = 0.3250 | 34/40 = 0.8500 | +0.5250 |
| macro-F1 | 0.2836 | 0.8521 | +0.5685 |
| E2E 5문항 (실서버 :8100) | 1/5 = 0.2000 | 5/5 = 1.0000 | +0.8000 |
| 폴백률(keyword로 내려간 비율) | 100.00% | 15.00% | −85.00%p |
| 분류 지연 p50 | 0.0ms | 32.43ms | +32.43ms |
| E2E 요청 지연 p50 | 750.76ms | 819.73ms | +68.97ms |
| 비용 | 0.000000 USD | 0.000000 USD | 0 (로컬 백엔드) |
| 재현성(2회 반복) | - | 예측 동일 | - |

신규 유형 F1: queue-backlog 0.000 → 1.000, cert-expiry 0.000 → 1.000,
connection-pool 0.000 → 1.000, replication-lag 0.000 → 0.857

원본: artifacts/runs/20261020-152756_fake_before-rag, artifacts/runs/20261020-152756_fake_after-rag,
artifacts/runs/20261020-153204_fake_before-rag, artifacts/runs/20261020-153211_fake_after-rag

## 4. 결과에서 읽은 것 (한계 포함)

- 데이터 확장(6 → 12시스템)은 분류 정확도를 올리지 못했다: base 34/40 ≡ extended 34/40.
  대신 40문항이 조회한 모니터링 80회 중 데이터가 없어 못 본 15회가 0회가 됐다(unknown 18.75% → 0%).
- margin 게이트(0.03)는 보수적으로 2문항을 포기했다. 임계값을 0으로 풀면 36/40이지만 그 2문항은 1·2위
  유사도 차이가 0.0155·0.0000인 동점이라 유지했다.
- RAG의 비용은 임베딩 1회 호출이다(+32.43ms, 실서버 요청 시간의 약 9%).
- 40문항 라벨을 직접 만들어 자기 평가가 된다. 질의 의존도가 높은 20문항을 따로 두고 카테고리별로 보고했다.

## 5. 추가 확인할 것

- 실제 장애 티켓·운영 로그로 라벨 세트 재구축
- 동시 요청 부하에서의 지연 측정
- 실 OpenAI 백엔드로 비용·지연 재측정

## 6. 제출 전 확인한 것

- 문서에 적힌 수치 13개가 측정 원본과 일치함을 기계 대조로 확인 (eval/check_reported_numbers.py, 13/13)
- 테스트 50개 통과, E2E 5개 항목 PASS, 같은 조건 2회 실행 결과 동일(재현성)
- 시연 순서 4단계 실측(총 3초) — 기록: doc/reports/rehearsal_log.md

## 7. 참고 링크

- Git: https://github.com/pigpgw/skala-ai-service-mini
- 근거 대조표(수치 ↔ 원본 파일 ↔ 재현 명령): doc/reports/evidence/index.md
- 제출 산출물 색인: doc/reports/index.md
- 아키텍처 다이어그램: doc/design/architecture.html
- 발표자료: doc/reports/presentation.pdf (PPTX 동봉)
