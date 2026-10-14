"""Evaluation script — runs golden set and reports metrics.

Usage:
    py scripts/run_eval.py [--golden eval/golden_set.jsonl] [--output eval/reports/]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import httpx


async def run_eval(golden_path: Path, api_base: str, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    items = [json.loads(line) for line in golden_path.read_text().splitlines() if line.strip()]

    recall_hits = 0
    mrr_sum = 0.0
    abstention_correct = 0
    abstention_total = 0
    citation_valid_total = 0
    citation_total = 0

    async with httpx.AsyncClient(base_url=api_base, timeout=120) as client:
        for item in items:
            resp = await client.post("/api/v1/chat", json={"message": item["question"]})
            if not resp.is_success:
                print(f"  FAILED: {item['id']}")
                continue

            data = resp.json()
            answer = data.get("answer", "")
            citations = data.get("citations", [])
            cited_sources = {c.get("source") for c in citations}

            expected_ids: list[str] = item.get("expected_doc_ids", [])
            item_type: str = item.get("type", "")

            # Recall@8
            if any(d in str(citations) for d in expected_ids):
                recall_hits += 1

            # MRR
            for rank, citation in enumerate(citations, start=1):
                if any(d in json.dumps(citation) for d in expected_ids):
                    mrr_sum += 1.0 / rank
                    break

            # Abstention
            if item_type == "unanswerable":
                abstention_total += 1
                if "couldn't find" in answer.lower() or "not found" in answer.lower():
                    abstention_correct += 1

            # Citation validity (basic: all [n] map to returned citations)
            import re
            cited_nums = set(int(m) for m in re.findall(r"\[(\d+)\]", answer))
            valid_nums = set(c["n"] for c in citations)
            if cited_nums:
                citation_total += len(cited_nums)
                citation_valid_total += len(cited_nums & valid_nums)

    n = len(items)
    metrics = {
        "total": n,
        "recall_at_8": recall_hits / n if n else 0,
        "mrr": mrr_sum / n if n else 0,
        "abstention_accuracy": (abstention_correct / abstention_total) if abstention_total else None,
        "citation_validity": (citation_valid_total / citation_total) if citation_total else None,
    }

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    report_json = output_dir / f"eval_{ts}.json"
    report_json.write_text(json.dumps(metrics, indent=2))

    print("\n=== Evaluation Results ===")
    for k, v in metrics.items():
        print(f"  {k}: {v:.3f}" if isinstance(v, float) else f"  {k}: {v}")
    print(f"\nReport saved to: {report_json}")

    # Exit non-zero if key thresholds regress
    if metrics["recall_at_8"] < 0.85:
        print("⚠️  Recall@8 below target (0.85)")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="CyberSense evaluation")
    parser.add_argument("--golden", default="eval/golden_set.jsonl")
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--output", default="eval/reports")
    args = parser.parse_args()

    asyncio.run(run_eval(Path(args.golden), args.api, Path(args.output)))


if __name__ == "__main__":
    main()
