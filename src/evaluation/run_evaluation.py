"""
Quantitative evaluation of the retrieval system.

Metrics: Precision@K, Recall@K, Reciprocal Rank (MRR).
Relevance judged at DOCUMENT level.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "retrieval"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "test" / "evaluation"))

from retrieve import retrieve
from eval_dataset import EVAL_QUERIES

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVAL_OUTPUT_DIR = PROJECT_ROOT / "data" / "evaluation"

EVAL_TOP_K = int(os.getenv("EVAL_TOP_K", "5"))


def evaluate_query(query_spec: dict, top_k: int = EVAL_TOP_K) -> dict:
    query_text = query_spec["query"]
    relevant_document_ids = set(query_spec.get("relevant_document_ids", []))

    results = retrieve(query_text, top_k=top_k)

    retrieved_document_ids_in_order = [r["document_id"] for r in results]

    relevance_flags = [
        doc_id in relevant_document_ids for doc_id in retrieved_document_ids_in_order
    ]

    num_relevant_retrieved = sum(relevance_flags)
    distinct_relevant_found = {
        doc_id for doc_id in retrieved_document_ids_in_order
        if doc_id in relevant_document_ids
    }

    precision_at_k = num_relevant_retrieved / top_k if top_k else 0.0

    recall_at_k = (
        len(distinct_relevant_found) / len(relevant_document_ids)
        if relevant_document_ids else None
    )

    reciprocal_rank = 0.0
    for rank, is_relevant in enumerate(relevance_flags, start=1):
        if is_relevant:
            reciprocal_rank = 1.0 / rank
            break

    return {
        "id": query_spec["id"],
        "query": query_text,
        "relevant_document_ids": sorted(relevant_document_ids),
        "retrieved": [
            {
                "chunk_id": r["chunk_id"],
                "document_id": r["document_id"],
                "similarity": r["similarity"],
                "is_relevant": is_rel,
            }
            for r, is_rel in zip(results, relevance_flags)
        ],
        "precision_at_k": precision_at_k,
        "recall_at_k": recall_at_k,
        "reciprocal_rank": reciprocal_rank,
        "ground_truth_missing": len(relevant_document_ids) == 0,
    }


def run_evaluation(top_k: int = EVAL_TOP_K) -> list[dict]:
    print("=" * 70)
    print("Retrieval Evaluation")
    print("=" * 70)
    print(f"Queries : {len(EVAL_QUERIES)}")
    print(f"Top-K   : {top_k}")
    print("=" * 70)

    all_results = []

    for query_spec in EVAL_QUERIES:
        print(f"\n[{query_spec['id']}] {query_spec['query']}")

        if not query_spec.get("relevant_document_ids"):
            print("  [WARNING] No ground truth defined for this query.")

        result = evaluate_query(query_spec, top_k=top_k)
        all_results.append(result)

        recall_display = (
            f"{result['recall_at_k']:.2f}" if result["recall_at_k"] is not None else "N/A"
        )
        print(f"  Precision@{top_k}: {result['precision_at_k']:.2f}  "
              f"Recall@{top_k}: {recall_display}  "
              f"Reciprocal Rank: {result['reciprocal_rank']:.2f}")

        for item in result["retrieved"]:
            mark = "✓" if item["is_relevant"] else " "
            print(f"    [{mark}] {item['chunk_id']:30s} "
                  f"(doc={item['document_id']}) sim={item['similarity']:.4f}")

    return all_results


def summarize(all_results: list[dict]) -> dict:
    queries_with_ground_truth = [r for r in all_results if not r["ground_truth_missing"]]

    if not queries_with_ground_truth:
        return {
            "mean_precision_at_k": None,
            "mean_recall_at_k": None,
            "mean_reciprocal_rank": None,
            "queries_with_ground_truth": 0,
            "queries_total": len(all_results),
        }

    mean_precision = sum(r["precision_at_k"] for r in queries_with_ground_truth) / len(queries_with_ground_truth)
    mean_recall = sum(r["recall_at_k"] for r in queries_with_ground_truth) / len(queries_with_ground_truth)
    mean_rr = sum(r["reciprocal_rank"] for r in queries_with_ground_truth) / len(queries_with_ground_truth)

    return {
        "mean_precision_at_k": mean_precision,
        "mean_recall_at_k": mean_recall,
        "mean_reciprocal_rank": mean_rr,
        "queries_with_ground_truth": len(queries_with_ground_truth),
        "queries_total": len(all_results),
    }


def write_outputs(all_results: list[dict], summary: dict, top_k: int) -> tuple[Path, Path]:
    EVAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results_path = EVAL_OUTPUT_DIR / "results.json"
    with results_path.open("w", encoding="utf-8") as f:
        json.dump({"top_k": top_k, "summary": summary, "queries": all_results},
                   f, ensure_ascii=False, indent=2)

    report_path = EVAL_OUTPUT_DIR / "report.md"
    lines = [
        "# Retrieval Evaluation Report",
        "",
        f"Top-K: {top_k}",
        f"Queries evaluated: {summary['queries_total']} "
        f"({summary['queries_with_ground_truth']} with ground truth)",
        "",
        "## Summary",
        "",
    ]

    if summary["mean_precision_at_k"] is not None:
        lines.extend([
            f"- Mean Precision@{top_k}: {summary['mean_precision_at_k']:.3f}",
            f"- Mean Recall@{top_k}: {summary['mean_recall_at_k']:.3f}",
            f"- Mean Reciprocal Rank: {summary['mean_reciprocal_rank']:.3f}",
        ])
    else:
        lines.append("- No ground truth defined.")

    lines.extend(["", "## Per-query results", ""])

    for r in all_results:
        recall_display = f"{r['recall_at_k']:.2f}" if r["recall_at_k"] is not None else "N/A"
        lines.extend([
            f"### {r['id']}: {r['query']}",
            "",
            f"- Relevant docs: {r['relevant_document_ids'] or '(none)'}",
            f"- Precision@{top_k}: {r['precision_at_k']:.2f}",
            f"- Recall@{top_k}: {recall_display}",
            f"- Reciprocal Rank: {r['reciprocal_rank']:.2f}",
            "",
            "| Rank | Chunk | Document | Similarity | Relevant? |",
            "|---|---|---|---|---|",
        ])
        for rank, item in enumerate(r["retrieved"], start=1):
            lines.append(
                f"| {rank} | {item['chunk_id']} | {item['document_id']} | "
                f"{item['similarity']:.4f} | {'✓' if item['is_relevant'] else ''} |"
            )
        lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")

    return results_path, report_path


def main() -> None:
    all_results = run_evaluation(top_k=EVAL_TOP_K)
    summary = summarize(all_results)

    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    if summary["mean_precision_at_k"] is not None:
        print(f"Mean Precision@{EVAL_TOP_K}: {summary['mean_precision_at_k']:.3f}")
        print(f"Mean Recall@{EVAL_TOP_K}   : {summary['mean_recall_at_k']:.3f}")
        print(f"Mean Reciprocal Rank      : {summary['mean_reciprocal_rank']:.3f}")
    else:
        print("[WARNING] No ground truth defined.")
    print(f"Queries with ground truth : {summary['queries_with_ground_truth']}/{summary['queries_total']}")

    results_path, report_path = write_outputs(all_results, summary, EVAL_TOP_K)
    print(f"\nResults written to: {results_path}")
    print(f"Report written to : {report_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
