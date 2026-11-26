from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas import (
    ComparisonRequest,
    FindingSeverity,
    QuestionRequest,
    RetrievalEvaluationRequest,
    RetrievalStrategy,
)


def test_question_defaults_to_hybrid_and_no_document_filter() -> None:
    request = QuestionRequest(question="What does the policy exclude?")

    assert request.retrieval_strategy is RetrievalStrategy.HYBRID
    assert request.document_ids == []


def test_question_rejects_empty_question() -> None:
    with pytest.raises(ValidationError):
        QuestionRequest(question=" ")


def test_comparison_requires_at_least_two_documents() -> None:
    with pytest.raises(ValidationError):
        ComparisonRequest(document_ids=[uuid4()])


def test_finding_severities_are_stable() -> None:
    assert FindingSeverity.MISSING_INFORMATION == "missing_information"
    assert FindingSeverity.POTENTIAL_ISSUE == "potential_issue"


def test_retrieval_evaluation_defaults_to_all_strategies() -> None:
    request = RetrievalEvaluationRequest(question="What flood damage is excluded?")

    assert set(request.strategies) == set(RetrievalStrategy)
