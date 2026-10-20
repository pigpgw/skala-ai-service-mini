"""통합 평가 하네스 — 실행 1회 = `artifacts/runs/<run_id>/` 폴더 1개.

왜 이 스크립트가 "정식" 하네스인가
    1~3단계 측정 스크립트(`run_baseline.py`, `run_rag_probe.py`, `run_e2e_probe.py`)는
    각각 자기 목적에 최적화돼 있어 **Before/After를 같은 조건으로 나란히 돌리고 비교하기 어렵다.**
    이 스크립트는 그测量을 한 경로로 묶는다.
        - 실행 조건(백엔드·프로파일·임계값·데이터 해시·git 상태)을 `manifest.json`에 기록
        - 입력 1건 = `requests.jsonl` 1줄, 출력 1건 = `responses.jsonl` 1줄
        - 집계를 `metrics.json` 한 곳에 (accuracy, macro-F1, 혼동행렬, 폴백률, 커버리지, p50/p95)
        - 같은 폴더를 덮어쓰지 않는다 → 재실행은 새 타임스_TIMESTAMP 폴더

모드
    classify : 서버 없이 분류 정확도·F1·지연 측정 (기본)
    e2e      : **기동 중인** 서버(:8100)에 HTTP로 물어 지연·비용·retry 측정

실행 예시
    .venv/bin/python eval/run_eval.py --variant before-rag --profile extended
    .venv/bin/python eval/run_eval.py --variant after-rag  --profile extended --repeat 2
    LLM_BACKEND=fake .venv/bin/python eval/run_eval.py --variant after-rag --mode e2e
"""
from __future__ import annotations

import argparse
import json
import os
import platform
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

import metrics                                          # noqa: E402
from agent.data_profile import monitoring_path as profile_path   # noqa: E402
from common import (                                    # noqa: E402
    INCIDENT_TYPES,
    build_collected,
    load_labels,
    load_monitoring,
    sha256_of,
    validate_labels,
)

# manifest에 기록해도 되는 환경변수만. API 키·토큰은 절대 넣지 않는다.
ENV_ALLOWLIST = (
    "LLM_BACKEND", "SUPERVISOR_VERSION", "DATA_PROFILE",
    "RAG_ENABLED", "RAG_MIN_SCORE", "RAG_MIN_MARGIN", "RAG_TOP_K",
    "RAG_EMBEDDER", "RAG_EMBED_MODEL", "RAG_INDEX_PATH",
    "LANGCHAIN_TRACING_V2", "LANGCHAIN_PROJECT", "PYTHONHASHSEED",
)

RUNS_DIR = REPO_ROOT / "artifacts" / "runs"


# ---------------------------------------------------------------- 유틸

def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True,
                             text=True, check=True)
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _env_snapshot() -> dict:
    return {name: os.environ[name] for name in ENV_ALLOWLIST if name in os.environ}


def _run_id(variant: str) -> str:
    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    backend = os.environ.get("LLM_BACKEND", "fake")
    return f"{stamp}_{backend}_{variant}"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- 분류 측정

def _classify_keyword(query: str, collected: list[dict]) -> dict:
    """개선 전 경로 — `agent/graph.py::_classify_incident_type` (키워드 첫 매칭)."""
    from agent.graph import _classify_incident_type
    started = time.perf_counter()
    incident_type = _classify_incident_type(collected)
    return {
        "predicted_type": incident_type,
        "source": "keyword",
        "reason": "keyword_rule",
        "score": None,
        "margin": None,
        "doc_id": None,
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
    }


def _build_rag_classifier(embedder_name: str | None):
    from agent.rag import RagClassifier, build_embedder, load_or_build
    embedder = build_embedder(embedder_name)
    index = load_or_build(embedder)
    classifier = RagClassifier.from_env(index, embedder)
    return classifier, embedder, index


def _measure_classify(labels: dict, monitoring: dict, variant: str,
                      embedder_name: str | None) -> tuple[list[dict], list[dict], dict]:
    """(요청 목록, 응답 목록, 분류기 메타)."""
    requests: list[dict] = []
    responses: list[dict] = []

    classifier = None
    meta: dict = {"method": "keyword"}
    if variant == "after-rag":
        classifier, embedder, index = _build_rag_classifier(embedder_name)
        meta = {
            "method": "rag",
            "embedder": getattr(embedder, "name", "unknown"),
            "embedder_dim": getattr(embedder, "dim", None),
            "index_docs": [doc.id for doc in index.docs],
            "index_doc_count": len(index.docs),
            "index_sha256": index.index_sha256,
            "index_built_at": index.built_at,
            "index_cache_hit": index.cache_hit,
            "thresholds": {
                "RAG_ENABLED": classifier.enabled,
                "RAG_MIN_SCORE": classifier.min_score,
                "RAG_MIN_MARGIN": classifier.min_margin,
                "top_k": classifier.top_k,
            },
        }

    for item in labels["items"]:
        collected = build_collected(item["query"], monitoring)
        requests.append({
            "id": item["id"],
            "query": item["query"],
            "category": item["category"],
            "expected_type": item["expected_type"],
            "systems": item["systems"],
        })
        if classifier is None:
            outcome = _classify_keyword(item["query"], collected)
        else:
            result = classifier.classify(item["query"], collected)
            outcome = {
                "predicted_type": result.incident_type,
                "source": result.source,
                "reason": result.reason,
                "score": result.score,
                "margin": result.margin,
                "doc_id": result.doc_id,
                "elapsed_ms": result.elapsed_ms,
            }
        responses.append({
            "id": item["id"],
            "category": item["category"],
            "predicted_type": outcome["predicted_type"],
            "expected_type": item["expected_type"],
            "correct": outcome["predicted_type"] == item["expected_type"],
            "source": outcome["source"],
            "reason": outcome["reason"],
            "score": outcome["score"],
            "margin": outcome["margin"],
            "doc_id": outcome["doc_id"],
            "elapsed_ms": outcome["elapsed_ms"],
        })
    return requests, responses, meta


# ---------------------------------------------------------------- E2E 측정

def _measure_e2e(base_url: str, timeout: float) -> tuple[list[dict], list[dict], dict]:
    import httpx

    # 서버 측 조건을 함께 기록한다. RAG_ENABLED은 서버 프로세스의 환경이므로
    # 클라이언트 env만으로는 "같은 조건"을 증명할 수 없다.
    health = httpx.get(f"{base_url}/health", timeout=10.0).json()
    rag_info = health.get("rag") or {}
    server_state = {
        "llm_backend": health.get("llm_backend"),
        "supervisor_version": health.get("supervisor_version"),
        "rag_enabled": rag_info.get("enabled"),
        "rag_embedder": rag_info.get("embedder"),
        "rag_docs": rag_info.get("docs"),
        "rag_index_sha256": rag_info.get("index_sha256"),
        "rag_cache_hit": rag_info.get("cache_hit"),
        "rag_min_score": rag_info.get("min_score"),
        "rag_min_margin": rag_info.get("min_margin"),
        "data_profile": (health.get("data_profile") or {}).get("profile"),
    }

    cases_doc = json.loads((HERE / "e2e_cases.json").read_text(encoding="utf-8"))
    requests: list[dict] = []
    responses: list[dict] = []

    def post_chat(case: dict) -> dict:
        started = time.perf_counter()
        response = httpx.post(f"{base_url}/chat",
                              json={"message": case["message"], "thread_id": case["thread"]},
                              timeout=timeout)
        response.raise_for_status()
        body = response.json()
        elapsed = round((time.perf_counter() - started) * 1000, 2)
        meta = body.get("metadata") or {}
        return {
            "id": case["id"],
            "category": "e2e",
            "message": case["message"],
            "expect": case.get("expect"),
            "route": meta.get("route"),
            "incident_type": meta.get("incident_type"),
            "classifier_source": meta.get("classifier_source"),
            "classifier_reason": meta.get("classifier_reason"),
            "rag_score": meta.get("rag_score"),
            "rag_margin": meta.get("rag_margin"),
            "retry_count": meta.get("retry_count"),
            "replan_rounds": meta.get("replan_rounds"),
            "systems_queried": meta.get("systems_queried"),
            "systems_unknown": meta.get("systems_unknown"),
            "cost_usd": body.get("cost_usd", 0.0),
            "reply_len": len(body.get("reply", "")),
            "latency_ms": elapsed,
            "correct": (meta.get("incident_type") == case["expect"])
            if case.get("expect") else None,
        }

    def stream_case(case: dict) -> dict:
        started = time.perf_counter()
        replan: dict = {}
        final = None
        with httpx.stream("GET", f"{base_url}/chat/stream",
                          params={"message": case["message"], "thread_id": case["thread"]},
                          timeout=timeout) as response:
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
                if event.get("type") == "ReplanCheck":
                    # round 0 이벤트에 'target', round 1 이벤트에 'incident_type'가 있다.
                    # 하나만 고르면 근거가 빠지므로 합친다.
                    replan = {**replan, **event}
                elif event.get("type") == "FinalAnswer":
                    final = event
        elapsed = round((time.perf_counter() - started) * 1000, 2)
        return {
            "id": case["id"],
            "category": "e2e",
            "message": case["message"],
            "expect": case.get("expect"),
            "replan_target": replan.get("target"),
            "classifier_source": replan.get("classifier_source"),
            "final_incident_type": (final or {}).get("incident_type"),
            "latency_ms": elapsed,
            "correct": replan.get("target") == case.get("expect"),
        }

    for case in cases_doc["chat_cases"]:
        requests.append({"id": case["id"], "query": case["message"], "thread_id": case["thread"]})
        responses.append(post_chat(case))

    route_case = cases_doc["chat_route_case"]
    requests.append({"id": route_case["id"], "query": route_case["message"],
                     "thread_id": route_case["thread"]})
    responses.append(post_chat(route_case))

    stream = cases_doc["stream_case"]
    requests.append({"id": stream["id"], "query": stream["message"], "thread_id": stream["thread"]})
    responses.append(stream_case(stream))

    meta = {"method": "e2e", "base_url": base_url, "cases": len(responses),
            "server": server_state}
    return requests, responses, meta


# ---------------------------------------------------------------- 노트

def _notes_text(variant: str, profile: str, mode: str, metrics: dict, extra: str = "") -> str:
    lines = [
        f"# run notes — {variant} ({mode}, profile={profile})",
        "",
        "이 파일은 하네스가 **자동 생성한 초안**이다. 사람이 해석을 덧붙인 뒤 커밋한다.",
        "",
        "## 측정 요약",
        "",
    ]
    if mode == "classify":
        lines += [
            f"- 정확도: {metrics['accuracy']['correct']}/{metrics['accuracy']['total']} "
            f"= {metrics['accuracy']['accuracy']:.4f}",
            f"- macro-F1: {metrics['macro_f1']:.4f}",
            f"- 폴백률(keyword): {metrics['fallback']['fallback_rate']:.4f} "
            f"({metrics['fallback']['fallback']}/{metrics['fallback']['total']})",
            f"- 조회 커버리지: unknown {metrics['coverage']['unknown_rate']:.2%} "
            f"({metrics['coverage']['unknown_lookups']}/{metrics['coverage']['system_lookups']})",
            f"- 분류 지연: p50 {metrics['latency']['p50_ms']}ms / "
            f"p95 {metrics['latency']['p95_ms']}ms",
        ]
    else:
        lines += [
            f"- 사건 케이스 정확도: {metrics['accuracy']['correct']}/"
            f"{metrics['accuracy']['total']} = {metrics['accuracy']['accuracy']:.4f}",
            f"- 요청 지연: p50 {metrics['latency']['p50_ms']}ms / "
            f"p95 {metrics['latency']['p95_ms']}ms",
            f"- 총 비용: ${metrics['cost']['total_usd']:.6f}",
            f"- retry 합계: {metrics['retry']['total']}",
        ]
    lines += [
        "",
        "## 오분류",
        "",
    ]
    errors = metrics.get("errors") or []
    if errors:
        lines += [f"- {row['id']}: 기대 `{row['expected_type']}` → 실제 `{row['predicted_type']}`"
                  for row in errors]
    else:
        lines.append("- 없음")
    lines += ["", "## 사람이 덧붙일 해석", "", extra.strip() or "(작성 필요)", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------- main

def main() -> int:
    parser = argparse.ArgumentParser(description="통합 평가 하네스")
    parser.add_argument("--variant", required=True,
                        help="before-* 또는 after-* 접두어 필수 (예: after-rag)")
    parser.add_argument("--mode", default="classify", choices=["classify", "e2e"])
    parser.add_argument("--profile", default="extended", choices=["base", "extended"])
    parser.add_argument("--labels", default=str(HERE / "labels_extended.json"))
    parser.add_argument("--embedder", default=None, help="auto|ollama|hashing")
    parser.add_argument("--repeat", type=int, default=1,
                        help="같은 조건으로 몇 번 반복할지(재현성 확인). 기본 1")
    parser.add_argument("--base-url", default="http://127.0.0.1:8100")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--notes", default="", help="notes.md에 덧붙일 문장")
    parser.add_argument("--out-dir", default=str(RUNS_DIR))
    args = parser.parse_args()

    if not (args.variant.startswith("before-") or args.variant.startswith("after-")):
        print("variant은 'before-' 또는 'after-' 로 시작해야 합니다 "
              "(규칙: doc/artifact_management_design.md §5)", file=sys.stderr)
        return 2

    started_at = datetime.now().astimezone().isoformat(timespec="seconds")
    run_id = _run_id(args.variant)
    run_dir = Path(args.out_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "logs").mkdir(exist_ok=True)

    monitoring = load_monitoring(profile=args.profile)
    labels = load_labels(args.labels)
    problems = validate_labels(labels, monitoring)
    if problems:
        print("라벨 검증 실패 — 측정하지 않습니다.", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 2

    requests: list[dict] = []
    responses: list[dict] = []
    classifier_meta: dict = {}
    prediction_sets: list[dict[str, str]] = []

    for repeat in range(1, max(1, args.repeat) + 1):
        if args.mode == "classify":
            reqs, resps, meta = _measure_classify(labels, monitoring, args.variant, args.embedder)
        else:
            reqs, resps, meta = _measure_e2e(args.base_url, args.timeout)
        classifier_meta = meta
        for request in reqs:
            requests.append({**request, "repeat": repeat})
        for response in resps:
            responses.append({**response, "repeat": repeat})
        prediction_sets.append({row["id"]: row.get("predicted_type") for row in resps})

    primary = [row for row in responses if row.get("repeat", 1) == 1]
    primary_requests = [row for row in requests if row.get("repeat", 1) == 1]

    if args.mode == "classify":
        correct, accuracy = metrics.accuracy(primary)
        summary = {
            "accuracy": {"correct": correct, "total": len(primary), "accuracy": accuracy},
            "macro_f1": metrics.macro_f1(primary, INCIDENT_TYPES),
            "per_type": metrics.per_type_scores(primary, INCIDENT_TYPES),
            "per_category": metrics.category_scores(primary),
            "confusion": metrics.confusion_matrix(primary, INCIDENT_TYPES),
            "fallback": metrics.fallback_rate(primary),
            "coverage": metrics.coverage([
                build_collected(item["query"], monitoring) for item in labels["items"]]),
            "latency": metrics.latency_summary([row["elapsed_ms"] for row in primary]),
        }
        errors = [{"id": row["id"], "expected_type": row["expected_type"],
                   "predicted_type": row["predicted_type"], "source": row["source"],
                   "reason": row["reason"], "score": row["score"], "margin": row["margin"]}
                  for row in primary if not row["correct"]]
    else:
        scored = [row for row in primary if row.get("expect")]
        correct, accuracy = metrics.accuracy(scored)
        summary = {
            "accuracy": {"correct": correct, "total": len(scored), "accuracy": accuracy},
            "per_case": primary,
            "latency": metrics.latency_summary([row["latency_ms"] for row in primary]),
            "cost": {"total_usd": round(sum(row.get("cost_usd", 0.0) for row in primary), 6)},
            "retry": {"total": sum(int(row.get("retry_count") or 0) for row in primary)},
            "unknown_systems": sorted({name for row in primary
                                       for name in (row.get("systems_unknown") or [])}),
        }
        errors = [{"id": row["id"], "expected_type": row.get("expect"),
                   "predicted_type": row.get("incident_type") or row.get("replan_target"),
                   "source": row.get("classifier_source"), "reason": row.get("classifier_reason"),
                   "score": row.get("rag_score"), "margin": row.get("rag_margin")}
                  for row in scored if not row["correct"]]

    summary["reproducibility"] = metrics.reproducibility(prediction_sets)
    summary["errors"] = errors

    manifest = {
        "run_id": run_id,
        "started_at": started_at,
        "ended_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "variant": args.variant,
        "mode": args.mode,
        "backend": os.environ.get("LLM_BACKEND", "fake"),
        "supervisor_version": os.environ.get("SUPERVISOR_VERSION", "v2"),
        "data_profile": args.profile,
        "dataset": str(Path(args.labels).relative_to(REPO_ROOT)),
        "dataset_sha256": sha256_of(Path(args.labels)),
        "monitoring_file": str(profile_path(args.profile).relative_to(REPO_ROOT)),
        "monitoring_sha256": sha256_of(profile_path(args.profile)),
        "command": " ".join([".venv/bin/python", "eval/run_eval.py", *sys.argv[1:]]),
        "env": _env_snapshot(),
        "python": platform.python_version(),
        "git_commit": _git("rev-parse", "--short", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain", "--untracked-files=no")),
        "repeat": args.repeat,
        "classifier": classifier_meta,
        "metrics": {
            "accuracy": summary["accuracy"],
            "macro_f1": summary.get("macro_f1"),
            "p50_latency_ms": summary["latency"]["p50_ms"],
            "p95_latency_ms": summary["latency"]["p95_ms"],
            "fallback_rate": summary.get("fallback", {}).get("fallback_rate"),
            "unknown_rate": summary.get("coverage", {}).get("unknown_rate"),
            "cost_usd": summary.get("cost", {}).get("total_usd"),
        },
        "notes": args.notes or "",
    }

    _write_jsonl(run_dir / "requests.jsonl", requests)
    _write_jsonl(run_dir / "responses.jsonl", responses)
    (run_dir / "metrics.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (run_dir / "notes.md").write_text(
        _notes_text(args.variant, args.profile, args.mode, summary, args.notes),
        encoding="utf-8")

    print(f"run_id = {run_id}")
    print(f"dir    = {run_dir.relative_to(REPO_ROOT)}")
    print(f"variant={args.variant} mode={args.mode} profile={args.profile} "
          f"backend={manifest['backend']} repeat={args.repeat}")
    print(f"accuracy={summary['accuracy']['correct']}/{summary['accuracy']['total']} "
          f"= {summary['accuracy']['accuracy']:.4f}"
          + (f"  macro_f1={summary['macro_f1']:.4f}" if "macro_f1" in summary else ""))
    print(f"latency p50={summary['latency']['p50_ms']}ms p95={summary['latency']['p95_ms']}ms")
    if "fallback" in summary:
        print(f"fallback={summary['fallback']['fallback']}/{summary['fallback']['total']} "
              f"({summary['fallback']['fallback_rate']:.2%})  "
              f"unknown={summary['coverage']['unknown_lookups']}/"
              f"{summary['coverage']['system_lookups']} "
              f"({summary['coverage']['unknown_rate']:.2%})")
    print(f"reproducibility identical={summary['reproducibility']['identical']}")
    if errors:
        print("오분류: " + ", ".join(f"{row['id']}({row['predicted_type']})" for row in errors))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
