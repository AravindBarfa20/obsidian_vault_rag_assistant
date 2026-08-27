"""Transparent retrieval and no-answer evaluation harness.

Measures the retrieval behaviours that can be checked deterministically over a
labelled set without spending generation quota:

  * retrieval recall@k   -- did the expected note appear in the selected set?
  * top-source accuracy  -- was the expected note ranked first?
  * context term coverage -- did the selected evidence contain labelled facts?
  * no-answer accuracy   -- did negative questions fail the relevance gate?

Set GEMINI_API_KEY to evaluate real embeddings; omit it for the deterministic
offline provider. Answer generation is tested separately because citation
presence is not the same as claim-level faithfulness.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.api.dependencies import Container
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.ingestion.pipeline import ingest_vault

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "eval" / "dataset.json"


def _pct(numerator: int, denominator: int) -> str:
    return f"{(100.0 * numerator / denominator):.0f}%" if denominator else "n/a"


def run() -> dict:
    settings = get_settings()
    configure_logging("WARNING")
    container = Container(settings)
    ingest_vault(settings.vault_dir, container.store, container.embedder, settings)
    retriever = container.retriever

    cases = json.loads(DATASET.read_text())["cases"]
    answerable = [c for c in cases if c["expected_source"]]
    unanswerable = [c for c in cases if not c["expected_source"]]

    hit_at_k = top_source_correct = context_covered = no_answer_correct = 0
    rows: list[dict] = []

    for case in cases:
        result = retriever.retrieve(case["question"], top_k=settings.top_k)
        top_source = result.chunks[0].source if result.chunks else None
        retrieved = {chunk.source for chunk in result.chunks}

        if case["expected_source"] is None:
            correct = not result.has_grounding
            no_answer_correct += int(correct)
            rows.append(
                {"id": case["id"], "type": "no-answer",
                 "top_relevance": round(result.top_relevance, 4), "pass": correct}
            )
            continue

        expected = case["expected_source"]
        in_topk = expected in retrieved
        top_ok = top_source == expected
        terms = case.get("reference_terms", [])
        context_text = " ".join(chunk.text.lower() for chunk in result.chunks)
        has_reference_terms = (
            all(term.lower() in context_text for term in terms)
            if terms else result.has_grounding
        )

        hit_at_k += int(in_topk)
        top_source_correct += int(top_ok)
        context_covered += int(has_reference_terms)
        rows.append(
            {"id": case["id"], "expected": expected, "top": top_source,
             "in_topk": in_topk, "top_ok": top_ok,
             "context_terms": has_reference_terms,
             "top_relevance": round(result.top_relevance, 4)}
        )

    n_ans = len(answerable)
    summary = {
        "cases": len(cases),
        "answerable_cases": n_ans,
        "no_answer_cases": len(unanswerable),
        "retrieval_recall@k": _pct(hit_at_k, n_ans),
        "top_source_accuracy": _pct(top_source_correct, n_ans),
        "context_term_coverage": _pct(context_covered, n_ans),
        "no_answer_accuracy": _pct(no_answer_correct, len(unanswerable)),
        "embedding_model": container.embedder.model_name,
    }
    return {"summary": summary, "rows": rows}


def main() -> None:
    report = run()
    print("\n=== RAG evaluation ===")
    for key, value in report["summary"].items():
        print(f"{key:22}: {value}")
    print("\n--- per case ---")
    for row in report["rows"]:
        print(row)


if __name__ == "__main__":
    main()
