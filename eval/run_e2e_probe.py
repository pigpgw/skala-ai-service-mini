"""2단계 E2E 검증 — 실제 서버(:8100)에 HTTP로 물어 RAG 연결을 확인한다.

확인 항목
    1. `/health`의 rag 블록 — 임베더·인덱스·임계값·캐시 사용 여부
    2. `/chat` metadata — incident_type, classifier_source, reason, score, margin
    3. `/chat/stream` — ReplanCheck 이벤트에 같은 근거가 실려 나오는가
    4. chat 라우트(잡담)는 RAG와 무관하게 동작하는가

서버는 이 스크립트가 띄우지 않는다. 실행 전에 별도로 기동하고, 끝나면 내린다
(`RAG_ENABLED` A/B를 같은 스크립트로 재현하기 위해서다).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
BASE = "http://127.0.0.1:8100"

# 고정 입력은 `eval/e2e_cases.json` 한 곳에 둔다 — run_eval.py도 같은 파일을 읽는다.
_CASES_DOC = json.loads((HERE / "e2e_cases.json").read_text(encoding="utf-8"))

CASES = _CASES_DOC["chat_cases"]
CHAT_CASE = _CASES_DOC["chat_route_case"]
STREAM_CASE = _CASES_DOC["stream_case"]


def _post_chat(case: dict) -> dict:
    response = httpx.post(f"{BASE}/chat",
                          json={"message": case["message"], "thread_id": case["thread"]},
                          timeout=120.0)
    response.raise_for_status()
    body = response.json()
    meta = body["metadata"]
    return {
        "id": case["id"],
        "message": case["message"],
        "expect": case.get("expect"),
        "route": meta["route"],
        "incident_type": meta["incident_type"],
        "classifier_source": meta["classifier_source"],
        "classifier_reason": meta["classifier_reason"],
        "rag_score": meta["rag_score"],
        "rag_margin": meta["rag_margin"],
        "retry_count": meta["retry_count"],
        "replan_rounds": meta["replan_rounds"],
        "systems_queried": meta["systems_queried"],
        "systems_unknown": meta["systems_unknown"],
        "correct": (meta["incident_type"] == case["expect"]) if case.get("expect") else None,
        "reply_len": len(body["reply"]),
    }


def _stream_case(case: dict) -> dict:
    events = []
    final = None
    with httpx.stream("GET", f"{BASE}/chat/stream",
                      params={"message": case["message"], "thread_id": case["thread"]},
                      timeout=120.0) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line.startswith("data: "):
                continue
            payload = line[len("data: "):]
            if payload.strip() == "[DONE]":
                break
            try:
                event = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "FinalAnswer":
                final = event
            else:
                events.append(event)
    replan = next((e for e in events if e.get("type") == "ReplanCheck"), {})
    return {
        "id": case["id"],
        "event_types": [e.get("type") for e in events],
        "replan_check": {k: replan.get(k) for k in
                         ("round", "is_sufficient", "target", "incident_type",
                          "classifier_source", "classifier_reason", "rag_score", "rag_margin")},
        "final": {k: final.get(k) for k in
                  ("incident_type", "classifier_source", "rag_score", "rag_margin")} if final else None,
        "correct": (replan.get("target") == case["expect"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="2단계 E2E 검증")
    parser.add_argument("--out", default=str(HERE.parent / "artifacts" / "eval" / "e2e_probe.json"))
    parser.add_argument("--tag", default="rag-on")
    args = parser.parse_args()

    health = httpx.get(f"{BASE}/health", timeout=10.0).json()
    rag = health.get("rag") or {}
    data_profile = health.get("data_profile") or {}

    chat_rows = [_post_chat(case) for case in CASES]
    chat_route = _post_chat(CHAT_CASE)
    stream_row = _stream_case(STREAM_CASE)

    profile_name = data_profile.get("profile")
    expected_systems = {"base": 6, "extended": 12}.get(profile_name)
    new_system_case = next(row for row in chat_rows if row["id"] == "E04")
    coverage_ok = (
        (profile_name == "extended" and not new_system_case["systems_unknown"])
        or (profile_name == "base" and "search-service" in new_system_case["systems_unknown"])
    )

    checks = {
        "health_reports_rag": {
            "enabled": rag.get("enabled"),
            "embedder": rag.get("embedder"),
            "docs": rag.get("docs"),
            "cache_hit": rag.get("cache_hit"),
            "error": rag.get("error"),
            "pass": rag.get("error") is None,
        },
        "data_profile_reaches_mcp": {
            "profile": profile_name,
            "file": data_profile.get("file"),
            "system_count": data_profile.get("system_count"),
            "E04_unknown": new_system_case["systems_unknown"],
            "pass": (data_profile.get("system_count") == expected_systems
                     and coverage_ok),
        },
        "incident_cases": {
            "correct": sum(1 for r in chat_rows if r["correct"]),
            "total": len(chat_rows),
            "pass": all(r["correct"] for r in chat_rows),
        },
        "chat_route_unaffected": {
            "route": chat_route["route"],
            "incident_type": chat_route["incident_type"],
            "pass": chat_route["route"] == "chat" and chat_route["incident_type"] is None,
        },
        "stream_carries_evidence": {
            "has_replan_event": bool(stream_row["replan_check"].get("target")),
            "source": stream_row["replan_check"].get("classifier_source"),
            "correct": stream_row["correct"],
            "pass": bool(stream_row["replan_check"].get("target")) and stream_row["correct"],
        },
    }

    result = {
        "schema_version": 1,
        "stage": "2단계 E2E (graph·server 연결)",
        "tag": args.tag,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "base_url": BASE,
        "health": {
            "llm_backend": health.get("llm_backend"),
            "supervisor_version": health.get("supervisor_version"),
            "creation_count": health.get("creation_count"),
            "rag": rag,
            "data_profile": data_profile,
        },
        "chat_cases": chat_rows,
        "chat_route_case": chat_route,
        "stream_case": stream_row,
        "checks": checks,
    }
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8")

    print(f"tag={args.tag} llm={health.get('llm_backend')} "
          f"profile={profile_name}({data_profile.get('system_count')}시스템) "
          f"rag.enabled={rag.get('enabled')} embedder={rag.get('embedder')} "
          f"docs={rag.get('docs')} cache_hit={rag.get('cache_hit')}")
    print(f"{'ID':<4} {'expect':<16} {'incident_type':<16} {'source':<8} {'reason':<14} "
          f"{'score':>6} {'margin':>6} retry replan ok")
    print("-" * 104)
    for r in chat_rows:
        score = "-" if r["rag_score"] is None else f"{r['rag_score']:.4f}"
        margin = "-" if r["rag_margin"] is None else f"{r['rag_margin']:.4f}"
        print(f"{r['id']:<4} {r['expect']:<16} {str(r['incident_type']):<16} "
              f"{str(r['classifier_source']):<8} {str(r['classifier_reason']):<14} "
              f"{score:>6} {margin:>6} {r['retry_count']:>5} {r['replan_rounds']:>6} "
              f"{'O' if r['correct'] else 'X'}")
    print(f"{chat_route['id']:<4} {'(chat)':<16} {str(chat_route['incident_type']):<16} "
          f"route={chat_route['route']}")
    print(f"S01  stream ReplanCheck target={stream_row['replan_check'].get('target')} "
          f"source={stream_row['replan_check'].get('classifier_source')} "
          f"final.incident_type={(stream_row['final'] or {}).get('incident_type')}")
    print()
    for name, check in checks.items():
        print(f"[{'PASS' if check['pass'] else 'FAIL'}] {name}")
    print(f"saved: {args.out}")
    return 0 if all(c["pass"] for c in checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
