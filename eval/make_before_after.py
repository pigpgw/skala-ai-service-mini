"""Before/After 비교표를 만든다 — 수치를 손으로 옮겨 적지 않고 원본에서 읽는다.

원본: `artifacts/runs/<run_id>/metrics.json`·`manifest.json` (실행 1회 = 폴더 1개)
출력: `doc/reports/evidence/before_after.md` + `doc/reports/evidence/metrics/<run_id>.json`

왜 스크립트인가
    보고서 표의 숫자가 측정 원본에서 복사된 것임을 보장해야 한다. 손으로 옮겨 적으면
    조건이 다른 숫자가 섞인다. 이 스크립트는 run 폴더에서만 읽고, 각 행에 원본 경로와
    실행 조건을 함께 적는다.

실행:
    .venv/bin/python eval/make_before_after.py \
        --pair artifacts/runs/20261020-152517_fake_before-rag \
               artifacts/runs/20261020-152518_fake_after-rag \
        --label "40문항 분류 정확도 (DATA_PROFILE=extended)"
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
EVIDENCE_DIR = REPO_ROOT / "doc" / "reports" / "evidence"
METRICS_DIR = EVIDENCE_DIR / "metrics"


def _load(run_dir: Path) -> dict:
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    return {"dir": run_dir, "metrics": metrics, "manifest": manifest}


def _row(label: str, before, after, fmt: str = "{}", delta: str = "—") -> str:
    return f"| {label} | {fmt.format(before)} | {fmt.format(after)} | {delta} |"


def _delta(before, after, fmt: str = "{:+.4f}") -> str:
    try:
        return fmt.format(float(after) - float(before))
    except (TypeError, ValueError):
        return "—"


def _trimmed(run: dict) -> dict:
    metrics = run["metrics"]
    manifest = run["manifest"]
    return {
        "run_id": manifest["run_id"],
        "variant": manifest["variant"],
        "mode": manifest["mode"],
        "data_profile": manifest["data_profile"],
        "backend": manifest["backend"],
        "dataset": manifest["dataset"],
        "dataset_sha256": manifest["dataset_sha256"],
        "monitoring_sha256": manifest["monitoring_sha256"],
        "env": manifest["env"],
        "git_commit": manifest["git_commit"],
        "git_dirty": manifest["git_dirty"],
        "started_at": manifest["started_at"],
        "accuracy": metrics.get("accuracy"),
        "macro_f1": metrics.get("macro_f1"),
        "per_category": metrics.get("per_category"),
        "fallback": metrics.get("fallback"),
        "coverage": metrics.get("coverage"),
        "latency": metrics.get("latency"),
        "cost": metrics.get("cost"),
        "retry": metrics.get("retry"),
        "reproducibility": metrics.get("reproducibility"),
        "errors": metrics.get("errors"),
    }


def _section(label: str, before: dict, after: dict) -> list[str]:
    b_metrics, a_metrics = before["metrics"], after["metrics"]
    b_manifest, a_manifest = before["manifest"], after["manifest"]
    b_acc, a_acc = b_metrics["accuracy"], a_metrics["accuracy"]

    lines = [f"### {label}", ""]
    lines += [
        "| 항목 | Before | After | 차이 |",
        "|---|---|---|---|",
        _row("실행(run_id)", b_manifest["run_id"], a_manifest["run_id"]),
        _row("정확도", f"{b_acc['correct']}/{b_acc['total']} = {b_acc['accuracy']:.4f}",
             f"{a_acc['correct']}/{a_acc['total']} = {a_acc['accuracy']:.4f}",
             delta=_delta(b_acc["accuracy"], a_acc["accuracy"])),
    ]
    if "macro_f1" in b_metrics and "macro_f1" in a_metrics:
        lines.append(_row("macro-F1", f"{b_metrics['macro_f1']:.4f}",
                           f"{a_metrics['macro_f1']:.4f}",
                           delta=_delta(b_metrics["macro_f1"], a_metrics["macro_f1"])))
    if "fallback" in b_metrics and "fallback" in a_metrics:
        lines.append(_row("폴백률(keyword)", f"{b_metrics['fallback']['fallback_rate']:.2%}",
                           f"{a_metrics['fallback']['fallback_rate']:.2%}",
                           delta=_delta(b_metrics['fallback']['fallback_rate'],
                                        a_metrics['fallback']['fallback_rate'], "{:+.2%}")))
    if "coverage" in b_metrics and "coverage" in a_metrics:
        lines.append(_row("조사 커버리지(unknown)", f"{b_metrics['coverage']['unknown_rate']:.2%}",
                           f"{a_metrics['coverage']['unknown_rate']:.2%}",
                           delta=_delta(b_metrics['coverage']['unknown_rate'],
                                        a_metrics['coverage']['unknown_rate'], "{:+.2%}")))
    lines.append(_row("지연 p50", f"{b_metrics['latency']['p50_ms']}ms",
                       f"{a_metrics['latency']['p50_ms']}ms",
                       delta=_delta(b_metrics['latency']['p50_ms'],
                                    a_metrics['latency']['p50_ms'], "{:+.2f}ms")))
    lines.append(_row("지연 p95", f"{b_metrics['latency']['p95_ms']}ms",
                       f"{a_metrics['latency']['p95_ms']}ms",
                       delta=_delta(b_metrics['latency']['p95_ms'],
                                    a_metrics['latency']['p95_ms'], "{:+.2f}ms")))
    if "cost" in b_metrics and "cost" in a_metrics:
        lines.append(_row("비용(USD)", f"{b_metrics['cost']['total_usd']:.6f}",
                           f"{a_metrics['cost']['total_usd']:.6f}",
                           delta=_delta(b_metrics['cost']['total_usd'],
                                        a_metrics['cost']['total_usd'], "{:+.6f}")))
    if "retry" in b_metrics and "retry" in a_metrics:
        lines.append(_row("retry 합계", b_metrics["retry"]["total"], a_metrics["retry"]["total"]))

    lines += ["", "**측정 조건**", ""]
    for name, manifest in (("Before", b_manifest), ("After", a_manifest)):
        lines.append(f"- {name}: backend={manifest['backend']}, "
                     f"profile={manifest['data_profile']}, "
                     f"dataset=`{manifest['dataset']}` (sha {manifest['dataset_sha256'][:12]}), "
                     f"git={manifest['git_commit']}, "
                     f"env={json.dumps(manifest['env'], ensure_ascii=False)}")
        server = (manifest.get("classifier") or {}).get("server")
        if server:
            lines.append(f"  - {name} 서버: RAG_ENABLED={server.get('rag_enabled')}, "
                         f"embedder={server.get('rag_embedder')}, "
                         f"docs={server.get('rag_docs')}, "
                         f"index={str(server.get('rag_index_sha256'))[:12]}, "
                         f"min_score={server.get('rag_min_score')}, "
                         f"min_margin={server.get('rag_min_margin')}")
    lines += ["", "**재현 명령**", "", "```bash"]
    for manifest in (b_manifest, a_manifest):
        lines.append(manifest["command"])
    lines += ["```", ""]

    if "per_category" in b_metrics and "per_category" in a_metrics:
        lines += ["| 카테고리 | Before | After |", "|---|---|---|"]
        for name in b_metrics["per_category"]:
            b_cat = b_metrics["per_category"][name]
            a_cat = a_metrics["per_category"].get(name, {"correct": 0, "total": 0})
            lines.append(f"| {name} | {b_cat['correct']}/{b_cat['total']} | "
                         f"{a_cat['correct']}/{a_cat['total']} |")
        lines.append("")

    lines += ["**오분류**", ""]
    for name, run in (("Before", before), ("After", after)):
        errors = run["metrics"].get("errors") or []
        if errors:
            lines.append(f"- {name}: " + ", ".join(
                f"{e['id']}→{e.get('predicted_type')}" for e in errors))
        else:
            lines.append(f"- {name}: 없음")
    lines += ["", f"원본: `{before['dir'].relative_to(REPO_ROOT)}/` · "
                f"`{after['dir'].relative_to(REPO_ROOT)}/`", ""]
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Before/After 비교표 생성")
    parser.add_argument("--pair", action="append", nargs=2, required=True,
                        metavar=("BEFORE_DIR", "AFTER_DIR"))
    parser.add_argument("--label", action="append", default=[],
                        help="쌍마다 붙일 제목 (생략하면 run_id로 자동)")
    parser.add_argument("--out", default=str(EVIDENCE_DIR / "before_after.md"))
    args = parser.parse_args()

    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Before/After 비교 (원본 인용)",
        "",
        f"- 생성 시각: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        "- 이 표의 모든 숫자는 `artifacts/runs/<run_id>/metrics.json`에서 읽었다.",
        "- 같은 조건(동일 입력·동일 데이터·동일 임베더·동일 임계값)에서 2회 실행한 결과다.",
        "",
    ]
    for index, (before_dir, after_dir) in enumerate(args.pair):
        before = _load(REPO_ROOT / before_dir)
        after = _load(REPO_ROOT / after_dir)
        label = (args.label[index] if index < len(args.label)
                 else f"{before['manifest']['variant']} → {after['manifest']['variant']}")
        lines += _section(label, before, after)
        for run in (before, after):
            out = METRICS_DIR / f"{run['manifest']['run_id']}.json"
            out.write_text(json.dumps(_trimmed(run), ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")

    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"saved: {args.out}")
    print(f"saved: {METRICS_DIR}/ ({len(args.pair) * 2}개)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
