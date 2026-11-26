import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import UUID

from app.evaluation.metrics import ranking_metrics
from app.rag.retrieval import retrieve_chunks
from app.schemas import RetrievalStrategy
from app.storage.documents import StoredChildChunk


DATASET_PATH = Path(__file__).with_name("retrieval_cases.json")
METRIC_NAMES = ("precision_at_k", "recall_at_k", "mrr_at_k", "ndcg_at_k")
SYNTHETIC_DOCUMENT_ID = UUID("00000000-0000-4000-8000-000000000001")


def _load_dataset(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    dataset = json.loads(raw)
    if not isinstance(dataset, dict) or dataset.get("synthetic_only") is not True:
        raise ValueError("Evaluation dataset must declare synthetic_only: true")
    if not isinstance(dataset.get("dataset_id"), str) or not dataset["dataset_id"]:
        raise ValueError("Evaluation dataset must include a non-empty dataset_id")
    if not isinstance(dataset.get("cases"), list) or not dataset["cases"]:
        raise ValueError("Evaluation dataset must include at least one case")
    return dataset, hashlib.sha256(raw).hexdigest()


def _load_case_chunks(case: dict[str, Any]) -> tuple[str, set[str], list[StoredChildChunk]]:
    question = case.get("question")
    chunks = case.get("chunks")
    relevant_ids = case.get("relevant_chunk_ids")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Each evaluation case must include a non-empty question")
    if not isinstance(chunks, list) or not chunks:
        raise ValueError(f"Evaluation case {question!r} must include chunks")
    if (
        not isinstance(relevant_ids, list)
        or not relevant_ids
        or not all(isinstance(chunk_id, str) and chunk_id for chunk_id in relevant_ids)
    ):
        raise ValueError(
            f"Evaluation case {question!r} must include relevant_chunk_ids"
        )

    child_chunks: list[StoredChildChunk] = []
    seen_ids: set[str] = set()
    for chunk in chunks:
        if not isinstance(chunk, dict):
            raise ValueError(f"Evaluation case {question!r} contains an invalid chunk")
        chunk_id = chunk.get("chunk_id")
        text = chunk.get("text")
        if not isinstance(chunk_id, str) or not chunk_id or chunk_id in seen_ids:
            raise ValueError(
                f"Evaluation case {question!r} contains a missing or duplicate chunk_id"
            )
        if not isinstance(text, str) or not text.strip():
            raise ValueError(
                f"Evaluation chunk {chunk_id!r} must include non-empty text"
            )
        seen_ids.add(chunk_id)
        child_chunks.append(
            StoredChildChunk(
                chunk_id=chunk_id,
                document_id=SYNTHETIC_DOCUMENT_ID,
                parent_chunk_id=f"parent-{chunk_id}",
                text=text,
                page_number=None,
                section_title=chunk.get("section_title"),
                filename="synthetic-evaluation-corpus",
            )
        )
    if not set(relevant_ids).issubset(seen_ids):
        raise ValueError(
            f"Evaluation case {question!r} refers to relevant chunks absent from its corpus"
        )
    return question, set(relevant_ids), child_chunks


def evaluate_dataset(path: Path = DATASET_PATH, top_k: int = 3) -> dict[str, Any]:
    if not 1 <= top_k <= 20:
        raise ValueError("top_k must be between 1 and 20")
    dataset, dataset_sha256 = _load_dataset(path)
    case_results: list[dict[str, Any]] = []
    totals = {
        strategy: {name: 0.0 for name in METRIC_NAMES}
        for strategy in RetrievalStrategy
    }

    for case in dataset["cases"]:
        if not isinstance(case, dict):
            raise ValueError("Each evaluation case must be a JSON object")
        question, relevant_ids, chunks = _load_case_chunks(case)
        strategy_results = []
        for strategy in RetrievalStrategy:
            retrieved = retrieve_chunks(question, chunks, strategy, top_k)
            retrieved_ids = [item.chunk.chunk_id for item in retrieved]
            metrics = ranking_metrics(retrieved_ids, relevant_ids, top_k)
            values = {
                name: round(getattr(metrics, name), 6)
                for name in METRIC_NAMES
            }
            for name, value in values.items():
                totals[strategy][name] += value
            strategy_results.append(
                {
                    "strategy": strategy.value,
                    "retrieved_chunk_ids": retrieved_ids,
                    **values,
                }
            )
        case_results.append(
            {
                "question": question,
                "relevant_chunk_ids": sorted(relevant_ids),
                "strategies": strategy_results,
            }
        )

    case_count = len(case_results)
    return {
        "dataset_id": dataset["dataset_id"],
        "dataset_sha256": dataset_sha256,
        "synthetic_only": True,
        "top_k": top_k,
        "case_count": case_count,
        "aggregate": {
            strategy.value: {
                name: round(value / case_count, 6)
                for name, value in totals[strategy].items()
            }
            for strategy in RetrievalStrategy
        },
        "cases": case_results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate local retrieval against the synthetic benchmark."
    )
    parser.add_argument("--top-k", type=int, default=3, choices=range(1, 21))
    args = parser.parse_args()
    print(json.dumps(evaluate_dataset(top_k=args.top_k), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
