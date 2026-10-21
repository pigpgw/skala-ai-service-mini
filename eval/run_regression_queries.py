"""회귀 질의 세트 실행 — 과제 PDF 9쪽의 "아래 예시들로 테스트" 요구를 그대로 수행한다.

무엇을 하는가
    `doc/regression_test_queries.md`의 10개 질의를 **실제 서버에** 순서대로 던지고,
    각 질의의 기대 결과(라우팅·판정 유형·조회 대상 시스템·알림 내용)를 확인한다.
    10번은 "서버 재시작 후에도 기억하는가"가 목적이므로 서버를 실제로 재시작한다.

왜 별도 스크립트인가
    E2E 검증기(`run_e2e_probe.py`)는 "RAG가 잘 고르는가"를 보는 도구고,
    이 스크립트는 "기존 동작이 깨지지 않았는가"를 보는 도구다. 목적이 달라 분리한다.

실행
    .venv/bin/python eval/run_regression_queries.py            # 서버를 직접 띄우고 수행
    .venv/bin/python eval/run_regression_queries.py --out eval/regression_queries.json
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
for path in (str(REPO_ROOT), str(HERE)):
    if path not in sys.path:
        sys.path.insert(0, path)

import httpx   # noqa: E402

# (번호, 질의, 라우팅, 기대 incident_type, 조회되어야 하는 시스템, unknown이어야 하는 시스템, 답변에 있어야 하는 문자열)
# 기대 incident_type은 문자열 또는 허용 목록(증상이 둘인 질의는 두 런북이 모두 정당).
QUERIES = [
    (1, "payments-service 결제 응답이 느려지고 CPU가 치솟았어요, 원인 확인해주세요",
     "incident", ["cpu-spike", "high-latency"], ["payments-service"], [], []),
    (2, "cache-service 메모리 사용률이 계속 올라가고 있어요",
     "incident", "memory-leak", ["cache-service"], [], []),
    (3, "log-service 디스크 공간이 부족하다는 알림이 왔어요",
     "incident", "disk-full", ["log-service"], [], []),
    (4, "gateway-service에서 payments-service로 가는 요청이 타임아웃 나고 있어요",
     "incident", "network-timeout", ["gateway-service", "payments-service"], [], []),
    (5, "web-01 CPU 급증, auth-service 커넥션 풀도 같이 확인해줘",
     "incident", "high-latency", ["web-01", "auth-service"], [], []),
    (6, "payments-service랑 cache-service 둘 다 저하됐는데 공통 원인이 있는지 분석해줘",
     "incident", None, ["payments-service", "cache-service"], [], []),
    (7, "로그인 응답이 느려요, 원인 확인해주세요",
     "incident", "high-latency", ["auth-service"], [], []),
    (8, "billing-service 응답이 느려요",
     "incident", None, ["billing-service"], ["billing-service"], []),
    (9, "안녕, 너는 누구야?",
     "chat", None, [], [], []),
]

MEMORY_FIRST = "제 이름은 민수입니다"
MEMORY_SECOND = "제 이름이 뭐였죠?"
MEMORY_EXPECT = "민수"


class Server:
    """검증용 서버를 직접 띄운다(외부 서버를 쓸 때는 --base-url)."""

    def __init__(self, profile: str, rag_enabled: bool):
        self.profile = profile
        self.rag_enabled = rag_enabled
        self.process: subprocess.Popen | None = None

    def start(self) -> None:
        env = {
            **os.environ,
            "LLM_BACKEND": "fake",
            "SUPERVISOR_VERSION": "v2",
            "DATA_PROFILE": self.profile,
            "RAG_ENABLED": "true" if self.rag_enabled else "false",
            "LANGCHAIN_TRACING_V2": "false",
        }
        self.process = subprocess.Popen(
            [sys.executable, "server.py"], cwd=REPO_ROOT, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(80):
            try:
                if httpx.get("http://127.0.0.1:8100/health", timeout=1.0).status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(0.5)
        raise RuntimeError("서버 기동 실패")

    def stop(self) -> None:
        if self.process is not None:
            self.process.kill()
            self.process.wait(timeout=10)
            self.process = None
            time.sleep(1.0)


def _chat(base_url: str, message: str, thread_id: str) -> dict:
    started = time.perf_counter()
    response = httpx.post(f"{base_url}/chat",
                          json={"message": message, "thread_id": thread_id},
                          timeout=120.0)
    response.raise_for_status()
    body = response.json()
    metadata = body.get("metadata") or {}
    return {
        "message": message,
        "route": metadata.get("route"),
        "incident_type": metadata.get("incident_type"),
        "classifier_source": metadata.get("classifier_source"),
        "classifier_reason": metadata.get("classifier_reason"),
        "rag_score": metadata.get("rag_score"),
        "rag_margin": metadata.get("rag_margin"),
        "systems_queried": metadata.get("systems_queried"),
        "systems_unknown": metadata.get("systems_unknown"),
        "retry_count": metadata.get("retry_count"),
        "replan_rounds": metadata.get("replan_rounds"),
        "latency_ms": round((time.perf_counter() - started) * 1000, 1),
        "reply": body.get("reply", ""),
        "reply_len": len(body.get("reply", "")),
    }


def _check(row: dict, expectations: tuple) -> list[str]:
    _, _, route, incident_type, systems, unknown, contains = expectations
    problems = []
    if row["route"] != route:
        problems.append(f"route {row['route']!r} ≠ {route!r}")
    if incident_type:
        allowed = incident_type if isinstance(incident_type, (list, tuple)) else [incident_type]
        if row["incident_type"] not in allowed:
            problems.append(f"incident_type {row['incident_type']!r} ∉ 허용 {allowed}")
    # metadata의 systems_queried는 '몇 개'만 준다. 실제 조회된 시스템 이름은
    # 답변문("1) 모니터링: payments-service 상태=degraded ...")에서 확인한다.
    for name in systems:
        if f"{name} 상태=" not in row["reply"]:
            problems.append(f"'{name}' 이 조회 결과에 없음")
    if len(systems) and (row["systems_queried"] or 0) < len(systems):
        problems.append(f"systems_queried {row['systems_queried']} < 기대 {len(systems)}")
    for name in unknown:
        if name not in (row["systems_unknown"] or []):
            problems.append(f"'{name}' 이 unknown이 아님 ({row['systems_unknown']})")
    for text in contains:
        if text not in row["reply"]:
            problems.append(f"답변에 '{text}' 없음")
    if not row["reply"].strip():
        problems.append("답변이 비어 있음")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="회귀 질의 세트 실행")
    parser.add_argument("--out", default=str(HERE.parent / "artifacts" / "eval" / "regression_queries.json"))
    parser.add_argument("--profile", default="extended", choices=["base", "extended"])
    parser.add_argument("--rag", default="on", choices=["on", "off"],
                        help="RAG on/off — off로 돌리면 keyword 기준선 경로가 그대로인지 확인된다")
    parser.add_argument("--base-url", default=None,
                        help="기존 서버를 쓸 때 (없으면 스크립트가 직접 띄우고 재시작한다)")
    args = parser.parse_args()

    rag_enabled = args.rag == "on"
    base_url = args.base_url or "http://127.0.0.1:8100"
    server: Server | None = None
    if not args.base_url:
        server = Server(args.profile, rag_enabled)
        server.start()

    rows: list[dict] = []
    try:
        for expectations in QUERIES:
            number = expectations[0]
            row = _chat(base_url, expectations[1], f"t-regression-{number}")
            problems = _check(row, expectations)
            rows.append({"id": number, "purpose": expectations[1][:40],
                         "problems": problems, "pass": not problems, **row})

        # 10번 — 서버 재시작 후 세션 기억 유지
        first = _chat(base_url, MEMORY_FIRST, "t-regression-10")
        if server is not None:
            server.stop()
            server.start()
        second = _chat(base_url, MEMORY_SECOND, "t-regression-10")
        problems = []
        if MEMORY_EXPECT not in second["reply"]:
            problems.append(f"재시작 후 '{MEMORY_EXPECT}' 기억 못 함 (답변: {second['reply'][:60]})")
        rows.append({
            "id": 10, "purpose": "서버 재시작 후 세션 기억",
            "problems": problems, "pass": not problems,
            "first_reply": first["reply"][:120], **second,
        })
    finally:
        if server is not None:
            server.stop()

    result = {
        "schema_version": 1,
        "stage": "회귀 질의 세트 (과제 PDF 9쪽 요구 수행)",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "query_set": "doc/regression_test_queries.md",
        "conditions": {
            "llm_backend": "fake",
            "data_profile": args.profile,
            "rag_enabled": rag_enabled,
            "supervisor_version": "v2",
            "server_restart_between": "10번 질의의 두 메시지 사이",
        },
        "total": len(rows),
        "passed": sum(1 for row in rows if row["pass"]),
        "failed": sum(1 for row in rows if not row["pass"]),
        "items": rows,
    }
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8")

    print(f"{'#':<3} {'route':<9} {'incident_type':<16} {'조회':<26} {'unknown':<20} "
          f"{'latency':>8}  ok")
    print("-" * 100)
    for row in rows:
        print(f"{row['id']:<3} {str(row['route']):<9} {str(row['incident_type']):<16} "
              f"{str(row.get('systems_queried')):<26} {str(row.get('systems_unknown')):<20} "
              f"{row.get('latency_ms', 0):>7}ms  {'O' if row['pass'] else 'X'}")
        for problem in row["problems"]:
            print(f"     └ {problem}")
    print("-" * 100)
    print(f"통과 {result['passed']}/{result['total']}")
    print(f"saved: {args.out}")
    return 0 if result["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
