from pathlib import Path

import pytest

from app.evaluation import metrics
from app.evaluation.__main__ import evaluate_dataset


def test_ranking_metrics_use_k_as_precision_denominator() -> None:
    result = metrics.ranking_metrics(
        ["relevant", "other"],
        {"relevant"},
        5,
    )

    assert result.precision_at_k == 0.2
    assert result.recall_at_k == 1.0
    assert result.mrr_at_k == 1.0
    assert result.ndcg_at_k == 1.0


def test_synthetic_benchmark_is_reproducible_and_reports_all_strategies() -> None:
    first = evaluate_dataset()
    second = evaluate_dataset()

    assert first == second
    assert first["synthetic_only"] is True
    assert first["case_count"] == 4
    assert first["top_k"] == 3
    assert set(first["aggregate"]) == {"semantic", "bm25", "hybrid"}
    assert all(
        set(metrics) == {
            "precision_at_k",
            "recall_at_k",
            "mrr_at_k",
            "ndcg_at_k",
        }
        for metrics in first["aggregate"].values()
    )


def test_evaluation_rejects_relevant_ids_not_in_case_corpus(tmp_path: Path) -> None:
    invalid_dataset = tmp_path / "invalid.json"
    invalid_dataset.write_text(
        """
        {
          "dataset_id": "synthetic-invalid",
          "synthetic_only": true,
          "cases": [{
            "question": "What is covered?",
            "relevant_chunk_ids": ["missing"],
            "chunks": [{"chunk_id": "present", "text": "Synthetic text."}]
          }]
        }
        """,
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="absent from its corpus"):
        evaluate_dataset(invalid_dataset)
