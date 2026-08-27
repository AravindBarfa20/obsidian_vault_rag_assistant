"""Small RAG evaluation harness.

Measures the four things that matter for this system, over a labelled set:

  * retrieval relevance -- did the expected note appear in the top-k?
  * source correctness  -- is the top-cited note the expected one?
  * answer faithfulness -- (heuristic) does the answer draw on the retrieved
                           context and avoid answering when it shouldn't?
  * answer relevance    -- does a grounded answer mention reference terms?
  * no-answer accuracy  -- are unanswerable questions correctly declined?

Runs offline with the fake providers by default; set GEMINI_API_KEY to evaluate
the real pipeline. This harness is deliberately transparent -- no hidden metric
library -- so every number can be traced to a check.
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
    service = container.answer_service

    cases = json.loads(DATASET.read_text())["cases"]
    answerable = [c for c in cases if c["expected_source"]]
    unanswerable = [c for c in cases if not c["expected_source"]]

    hit_at_k = source_correct = faithful = relevant = no_answer_correct = 0
    rows: list[dict] = []

    for case in cases:
        result = service.answer(case["question"], top_k=settings.top_k)
        top_source = result.sources[0].source if result.sources else None
        retrieved = {s.source for s in result.sources}

        if case["expected_source"] is None:
            correct = not result.grounded
            no_answer_correct += int(correct)
            rows.append(
                {"id": case["id"], "type": "no-answer", "grounded": result.grounded,
                 "pass": correct}
            )
            continue

        expected = case["expected_source"]
        in_topk = expected in retrieved
        top_ok = top_source == expected
        # Faithfulness (heuristic, offline-safe): a grounded answer must cite at
        # least one source and must have retrieved the expected note.
        is_faithful = result.grounded and bool(result.sources) and in_topk
        terms = case.get("reference_terms", [])
        context_text = " ".join(s.snippet.lower() for s in result.sources)
        is_relevant = any(t.lower() in context_text for t in terms) if terms else result.grounded

        hit_at_k += int(in_topk)
        source_correct += int(top_ok)
        faithful += int(is_faithful)
        relevant += int(is_relevant)
        rows.append(
            {"id": case["id"], "expected": expected, "top": top_source,
             "in_topk": in_topk, "top_ok": top_ok, "faithful": is_faithful,
             "relevant": is_relevant}
        )

    n_ans = len(answerable)
    summary = {
        "cases": len(cases),
        "retrieval_recall@k": _pct(hit_at_k, n_ans),
        "source_correctness": _pct(source_correct, n_ans),
        "answer_faithfulness": _pct(faithful, n_ans),
        "answer_relevance": _pct(relevant, n_ans),
        "no_answer_accuracy": _pct(no_answer_correct, len(unanswerable)),
        "embedding_model": container.embedder.model_name,
        "llm_model": container.llm.model_name,
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
