from collections.abc import Sequence, Set
from dataclasses import dataclass
from math import log2


@dataclass(frozen=True)
class RankingMetrics:
    precision_at_k: float
    recall_at_k: float
    mrr_at_k: float
    ndcg_at_k: float


def ranking_metrics(
    retrieved_ids: Sequence[str],
    relevant_ids: Set[str],
    k: int,
) -> RankingMetrics:
    """Compute binary-relevance ranking metrics using standard @k cutoffs."""
    ranked_ids = retrieved_ids[:k]
    relevant_hits = sum(chunk_id in relevant_ids for chunk_id in ranked_ids)
    reciprocal_rank = next(
        (
            1.0 / rank
            for rank, chunk_id in enumerate(ranked_ids, start=1)
            if chunk_id in relevant_ids
        ),
        0.0,
    )
    dcg = sum(
        1.0 / log2(rank + 1)
        for rank, chunk_id in enumerate(ranked_ids, start=1)
        if chunk_id in relevant_ids
    )
    ideal_relevant_count = min(len(relevant_ids), k)
    ideal_dcg = sum(
        1.0 / log2(rank + 1)
        for rank in range(1, ideal_relevant_count + 1)
    )

    return RankingMetrics(
        precision_at_k=relevant_hits / k,
        recall_at_k=relevant_hits / len(relevant_ids),
        mrr_at_k=reciprocal_rank,
        ndcg_at_k=dcg / ideal_dcg if ideal_dcg else 0.0,
    )
