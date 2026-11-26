from enum import StrEnum


class AnalysisIntent(StrEnum):
    QUESTION = "question"
    COMPARISON = "comparison"
    CLAIM = "claim"


def route_analysis_intent(question: str) -> AnalysisIntent:
    """Route an analysis request using deterministic insurance-domain signals."""
    normalized = question.lower()
    comparison_terms = (
        "compare",
        "comparison",
        "difference",
        "versus",
        " vs ",
    )
    claim_terms = (
        "claim",
        "loss",
        "damage",
        "incident",
        "completeness",
    )
    if any(term in normalized for term in comparison_terms):
        return AnalysisIntent.COMPARISON
    if any(term in normalized for term in claim_terms):
        return AnalysisIntent.CLAIM
    return AnalysisIntent.QUESTION
