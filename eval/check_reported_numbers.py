"""발표·보고서에 적힌 숫자가 측정 원본과 일치하는지 검사한다.

왜 필요한가
    발표 화면에 숫자 하나 틀리면 credibility가 통째로 무너진다. 사람이 눈으로
    대조하면 빠지기 쉽다(특히 Before/After 표). 이 스크립트는
    "문서에 적힌 값 == 측정 원본의 값"을 기계적으로 확인한다.

검사 원본
    - `doc/reports/evidence/metrics/<run_id>.json` (커밋된 요약본)
    - 없으면 `artifacts/runs/<run_id>/manifest.json` (측정 원본)
    둘 다 없으면 해당 주장은 "원본 미보유"로 건너뛴다(조용히 통과시키지 않는다).

검사 대상 문서
    발표 슬라이드(doc/reports/presentation.html), 보고서(result_report.md),
    스프레드시트 본문(spreadsheet_input.md), 루트 README.md, 체크리스트

실행
    .venv/bin/python eval/check_reported_numbers.py
    .venv/bin/python eval/check_reported_numbers.py --out eval/reported_numbers_check.json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
SUMMARY_DIR = REPO_ROOT / "doc" / "reports" / "evidence" / "metrics"
RUNS_DIR = REPO_ROOT / "artifacts" / "runs"

RUN_BEFORE = "20261020-152756_fake_before-rag"
RUN_AFTER = "20261020-152756_fake_after-rag"
RUN_BASE_BEFORE = "20261020-152800_fake_before-rag"
RUN_BASE_AFTER = "20261020-152800_fake_after-rag"
RUN_E2E_BEFORE = "20261020-153204_fake_before-rag"
RUN_E2E_AFTER = "20261020-153211_fake_after-rag"

DOCS = {
    "슬라이드": REPO_ROOT / "doc" / "reports" / "presentation.html",
    "보고서": REPO_ROOT / "doc" / "reports" / "result_report.md",
    "스프레드시트본문": REPO_ROOT / "doc" / "reports" / "spreadsheet_input.md",
    "README": REPO_ROOT / "README.md",
    "체크리스트": REPO_ROOT / "doc" / "evaluation-checklist.md",
}

# (주장, 원본 run_id, 원본에서 값을 뽑는 경로, 포맷, 반드시 포함해야 하는 문서들)
# ※ 같은 값이라도 문서마다 표기가 다를 수 있다("0.00%" vs "0%"). 그래서
#   허용 표기(alts)를 함께 둔다. 값이 아니라 **값의 표기**를 검사하는 것이다.
CLAIMS = [
    ("40문항 정확도 Before", RUN_BEFORE, "accuracy.accuracy", "{:.4f}",
     ["슬라이드", "보고서", "스프레드시트본문", "README", "체크리스트"]),
    ("40문항 정확도 After", RUN_AFTER, "accuracy.accuracy", "{:.4f}",
     ["슬라이드", "보고서", "스프레드시트본문", "README", "체크리스트"]),
    ("macro-F1 Before", RUN_BEFORE, "macro_f1", "{:.4f}",
     ["슬라이드", "보고서", "스프레드시트본문", "README", "체크리스트"]),
    ("macro-F1 After", RUN_AFTER, "macro_f1", "{:.4f}",
     ["슬라이드", "보고서", "스프레드시트본문", "README", "체크리스트"]),
    ("E2E 정확도 Before", RUN_E2E_BEFORE, "accuracy.accuracy", "{:.4f}",
     ["슬라이드", "보고서", "스프레드시트본문", "체크리스트"]),
    ("E2E 정확도 After", RUN_E2E_AFTER, "accuracy.accuracy", "{:.4f}",
     ["슬라이드", "보고서", "스프레드시트본문", "체크리스트"]),
    ("분류 지연 p50 After", RUN_AFTER, "latency.p50_ms", "{:.2f}",
     ["슬라이드", "보고서", "스프레드시트본문", "README", "체크리스트"]),
    # E2E 요청 p50은 5분 발표 슬라이드에는 상세하지 않으므로 보고서·체크리스트에만 둔다
    ("E2E 요청 p50 Before", RUN_E2E_BEFORE, "latency.p50_ms", "{:.2f}",
     ["보고서", "스프레드시트본문", "체크리스트"]),
    ("E2E 요청 p50 After", RUN_E2E_AFTER, "latency.p50_ms", "{:.2f}",
     ["보고서", "스프레드시트본문", "체크리스트"]),
    # 주의: base/extended는 데이터 프로파일 차이라 **같은 40문항 집합**을 돌린
    # base 프로파일 실행(152800 두 개)과 extended 프로파일 실행(152756 두 개)이
    # 서로 다른 run이다. extended의 coverage는 RUN_AFTER(=extended)에서 봐야 한다.
    ("조사 커버리지 unknown (base 6시스템)", RUN_BASE_BEFORE, "coverage.unknown_rate", "{:.2%}",
     ["슬라이드", "보고서", "스프레드시트본문", "README", "체크리스트"]),
    ("조사 커버리지 unknown (extended 12시스템)", RUN_AFTER, "coverage.unknown_rate", "{:.2%}",
     ["슬라이드", "보고서", "스프레드시트본문", "체크리스트"], ["0%"]),
    ("RAG 폴백률", RUN_AFTER, "fallback.fallback_rate", "{:.2%}",
     ["슬라이드", "보고서", "스프레드시트본문", "체크리스트"]),
    ("재현성 동일", RUN_AFTER, "reproducibility.identical", "{}",
     ["체크리스트"]),
    ("회귀 질의 통과 (라우팅 수정 후)", "regression_queries", "passed+total", "{}",
     ["슬라이드", "보고서", "스프레드시트본문", "README", "체크리스트"]),
    ("회귀 질의 통과 (라우팅 수정 전)", "regression_queries_before", "passed+total", "{}",
     ["보고서", "스프레드시트본문", "체크리스트"]),
]


def _load(source: str) -> dict | None:
    """원본 후보: evidence/metrics/<id>.json → eval/<id>.json → artifacts/runs/<id>/manifest.json"""
    candidates = [
        SUMMARY_DIR / f"{source}.json",
        REPO_ROOT / "eval" / f"{source}.json",
        RUNS_DIR / source / "manifest.json",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return json.loads(candidate.read_text(encoding="utf-8"))
    return None


def _dig(payload: dict, path: str):
    """'a.b' → 값, 'a+b' → 두 값을 '/'로 연결(예: passed+total → '10/10')."""
    if "+" in path:
        left, right = (_dig(payload, part) for part in path.split("+", 1))
        if left is None or right is None:
            return None
        return f"{left}/{right}"
    node = payload
    for key in path.split("."):
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node


def _normalise(value: str) -> str:
    return value.replace(",", "")


def main() -> int:
    parser = argparse.ArgumentParser(description="문서에 적힌 수치 ↔ 측정 원본 일치 검사")
    parser.add_argument("--out", default=str(HERE / "reported_numbers_check.json"))
    args = parser.parse_args()

    texts = {name: path.read_text(encoding="utf-8") for name, path in DOCS.items()
             if path.is_file()}
    rows = []
    failures = []

    for claim in CLAIMS:
        label, run_id, json_path, fmt, expected_docs = claim[:5]
        alts = claim[5] if len(claim) > 5 else []
        payload = _load(run_id)
        value = _dig(payload, json_path) if payload else None
        if value is None:
            rows.append({"claim": label, "status": "SKIP", "detail": "원본 미보유(측정 원본 필요)"})
            failures.append(label)
            continue
        if isinstance(value, bool):        # 재현성 판정은 True/False가 아니라
            rendered = "identical" if value else "different"   # identical/different로 표기
        else:
            rendered = fmt.format(value)
        accepted = [rendered, *alts]
        missing = [name for name in expected_docs
                   if name in texts
                   and not any(value in _normalise(texts[name]) for value in accepted)]
        status = "PASS" if not missing else "FAIL"
        rows.append({
            "claim": label,
            "status": status,
            "source_run": run_id,
            "source_path": json_path,
            "value": rendered,
            "missing_in": missing,
        })
        if missing:
            failures.append(f"{label} ({rendered}) → {', '.join(missing)}")

    result = {
        "schema_version": 1,
        "stage": "발표·보고서 수치 일치 검사",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "checked_documents": sorted(texts),
        "total": len(rows),
        "passed": sum(1 for row in rows if row["status"] == "PASS"),
        "failed": sum(1 for row in rows if row["status"] == "FAIL"),
        "skipped": sum(1 for row in rows if row["status"] == "SKIP"),
        "rows": rows,
    }
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8")

    print(f"{'주장':<28} {'상태':<6} 값")
    print("-" * 72)
    for row in rows:
        value = row.get("value", row.get("detail", ""))
        print(f"{row['claim']:<28} {row['status']:<6} {value}"
              + (f"  ← {', '.join(row['missing_in'])}" if row.get("missing_in") else ""))
    print("-" * 72)
    print(f"통과 {result['passed']} / {result['total']}"
          + (f" · 실패 {result['failed']}" if result["failed"] else "")
          + (f" · 원본 미보유 {result['skipped']}" if result["skipped"] else ""))
    print(f"saved: {args.out}")
    return 1 if result["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
