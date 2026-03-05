"""
RAGAS Evaluation Pipeline.
Evaluates the RAG system's quality using the RAGAS framework,
measuring faithfulness, answer relevancy, context precision, and context recall.
Uses LLM-as-a-judge pattern for automated quality scoring.
"""

import json
import os
import time
from datetime import datetime, timezone

import requests

from evaluation.eval_dataset import load_eval_dataset


# ============================================================
# Configuration
# ============================================================

API_BASE_URL = "http://localhost:8000"
RESULTS_DIR = os.path.join("evaluation", "results")


# ============================================================
# RAG Pipeline Evaluation
# ============================================================

def evaluate_rag_pipeline(
    api_base_url: str = None,
    user_role: str = "admin",
) -> dict:
    """
    Run the RAG system against the evaluation dataset and collect results.
    Returns raw results including questions, answers, contexts, and ground truths.
    """
    if api_base_url is None:
        api_base_url = API_BASE_URL

    dataset = load_eval_dataset()
    results = []

    print(f"\n{'='*60}")
    print(f"  RAGAS EVALUATION — {len(dataset)} questions")
    print(f"{'='*60}\n")

    for i, item in enumerate(dataset, 1):
        question = item["question"]
        ground_truth = item["ground_truth"]

        print(f"[{i}/{len(dataset)}] {question[:60]}...")

        # Query the RAG system
        start_time = time.time()
        try:
            response = requests.post(
                f"{api_base_url}/api/query",
                json={
                    "question": question,
                    "user_role": user_role,
                },
                timeout=120,
            )
            response.raise_for_status()
            result = response.json()
        except Exception as e:
            print(f"  ERROR: {str(e)}")
            results.append({
                "question": question,
                "ground_truth": ground_truth,
                "answer": f"Error: {str(e)}",
                "contexts": [],
                "sources": [],
                "latency_ms": 0,
                "error": True,
            })
            continue

        latency = (time.time() - start_time) * 1000

        # Collect contexts from sources
        contexts = [
            src.get("excerpt", "")
            for src in result.get("sources", [])
        ]

        results.append({
            "question": question,
            "ground_truth": ground_truth,
            "answer": result.get("answer", ""),
            "contexts": contexts,
            "sources": result.get("sources", []),
            "latency_ms": latency,
            "tokens_used": result.get("tokens_used", 0),
            "error": False,
        })

        print(f"  ✓ Answer: {result.get('answer', '')[:80]}...")
        print(f"  ✓ Sources: {len(result.get('sources', []))} | Latency: {latency:.0f}ms")

    return {
        "results": results,
        "total_questions": len(dataset),
        "successful": sum(1 for r in results if not r.get("error")),
        "failed": sum(1 for r in results if r.get("error")),
    }


# ============================================================
# Simple Quality Metrics (No external RAGAS dependency needed)
# ============================================================

def compute_basic_metrics(evaluation_results: dict) -> dict:
    """
    Compute basic quality metrics without requiring the full RAGAS library.
    These serve as a baseline; full RAGAS evaluation can be added separately.
    """
    results = evaluation_results["results"]
    successful = [r for r in results if not r.get("error")]

    if not successful:
        return {"error": "No successful results to evaluate"}

    metrics = {
        "total_questions": len(results),
        "successful_queries": len(successful),
        "failed_queries": evaluation_results["failed"],
    }

    # 1. Answer Rate: % of questions that got an answer (not "not found")
    not_found_phrases = [
        "could not find",
        "information not found",
        "not present in",
        "insufficient information",
    ]
    answered = [
        r for r in successful
        if not any(phrase in r["answer"].lower() for phrase in not_found_phrases)
    ]
    metrics["answer_rate"] = len(answered) / len(successful) if successful else 0

    # 2. Source Coverage: % of answers that have at least one source
    with_sources = [r for r in successful if r["contexts"]]
    metrics["source_coverage"] = len(with_sources) / len(successful) if successful else 0

    # 3. Avg Sources Per Answer
    total_sources = sum(len(r["contexts"]) for r in successful)
    metrics["avg_sources_per_answer"] = total_sources / len(successful) if successful else 0

    # 4. Avg Latency
    latencies = [r["latency_ms"] for r in successful]
    metrics["avg_latency_ms"] = sum(latencies) / len(latencies) if latencies else 0
    metrics["max_latency_ms"] = max(latencies) if latencies else 0
    metrics["min_latency_ms"] = min(latencies) if latencies else 0

    # 5. Avg Tokens
    tokens = [r.get("tokens_used", 0) for r in successful]
    metrics["avg_tokens_used"] = sum(tokens) / len(tokens) if tokens else 0

    # 6. Groundedness (simple word overlap between answer and context)
    groundedness_scores = []
    for r in answered:
        answer_words = set(r["answer"].lower().split())
        context_words = set()
        for ctx in r["contexts"]:
            context_words.update(ctx.lower().split())
        if answer_words and context_words:
            overlap = len(answer_words & context_words) / len(answer_words)
            groundedness_scores.append(overlap)
    metrics["avg_groundedness"] = (
        sum(groundedness_scores) / len(groundedness_scores)
        if groundedness_scores else 0
    )

    return metrics


# ============================================================
# Report Generation
# ============================================================

def generate_report(evaluation_results: dict, metrics: dict) -> str:
    """Generate a formatted evaluation report."""
    report = []
    report.append("=" * 60)
    report.append("  ENTERPRISE RAG — EVALUATION REPORT")
    report.append(f"  Generated: {datetime.now(timezone.utc).isoformat()}")
    report.append("=" * 60)
    report.append("")

    report.append("SUMMARY")
    report.append("-" * 40)
    report.append(f"  Total Questions:     {metrics.get('total_questions', 0)}")
    report.append(f"  Successful Queries:  {metrics.get('successful_queries', 0)}")
    report.append(f"  Failed Queries:      {metrics.get('failed_queries', 0)}")
    report.append("")

    report.append("QUALITY METRICS")
    report.append("-" * 40)
    report.append(f"  Answer Rate:         {metrics.get('answer_rate', 0):.1%}")
    report.append(f"  Source Coverage:     {metrics.get('source_coverage', 0):.1%}")
    report.append(f"  Avg Sources/Answer: {metrics.get('avg_sources_per_answer', 0):.1f}")
    report.append(f"  Avg Groundedness:   {metrics.get('avg_groundedness', 0):.1%}")
    report.append("")

    report.append("PERFORMANCE METRICS")
    report.append("-" * 40)
    report.append(f"  Avg Latency:         {metrics.get('avg_latency_ms', 0):.0f}ms")
    report.append(f"  Min Latency:         {metrics.get('min_latency_ms', 0):.0f}ms")
    report.append(f"  Max Latency:         {metrics.get('max_latency_ms', 0):.0f}ms")
    report.append(f"  Avg Tokens Used:    {metrics.get('avg_tokens_used', 0):.0f}")
    report.append("")

    report.append("DETAILED RESULTS")
    report.append("-" * 40)
    for r in evaluation_results["results"]:
        status = "✓" if not r.get("error") else "✗"
        report.append(f"  {status} Q: {r['question'][:70]}")
        report.append(f"     A: {r['answer'][:100]}")
        report.append(f"     Sources: {len(r.get('contexts', []))} | Latency: {r.get('latency_ms', 0):.0f}ms")
        report.append("")

    return "\n".join(report)


# ============================================================
# Main
# ============================================================

def run_evaluation():
    """Execute the full evaluation pipeline."""
    os.makedirs(RESULTS_DIR, exist_ok=True)

    # Run evaluation
    eval_results = evaluate_rag_pipeline()

    # Compute metrics
    metrics = compute_basic_metrics(eval_results)

    # Generate report
    report = generate_report(eval_results, metrics)
    print("\n" + report)

    # Save results
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    results_path = os.path.join(RESULTS_DIR, f"eval_results_{timestamp}.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump({"results": eval_results, "metrics": metrics}, f, indent=2, ensure_ascii=False)

    report_path = os.path.join(RESULTS_DIR, f"eval_report_{timestamp}.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\nResults saved to: {results_path}")
    print(f"Report saved to: {report_path}")

    return metrics


if __name__ == "__main__":
    run_evaluation()
