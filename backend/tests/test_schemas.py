from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas import ComparisonRequest, QuestionRequest, RetrievalStrategy


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
