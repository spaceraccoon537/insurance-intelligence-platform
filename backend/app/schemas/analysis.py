from enum import StrEnum
from uuid import UUID

from pydantic import Field

from app.schemas.common import ContractModel, SourceCitation


class FindingSeverity(StrEnum):
    NOTE = "note"
    POTENTIAL_ISSUE = "potential_issue"
    MISSING_INFORMATION = "missing_information"


class ComparisonRequest(ContractModel):
    document_ids: list[UUID] = Field(min_length=2, max_length=10)
    focus_areas: list[str] = Field(default_factory=list, max_length=20)


class ComparisonValue(ContractModel):
    document_id: UUID
    value: str
    citations: list[SourceCitation]


class ComparisonDimension(ContractModel):
    name: str
    values: list[ComparisonValue]


class ComparisonResponse(ContractModel):
    request_id: UUID
    dimensions: list[ComparisonDimension]
    summary: str


class ClaimAnalysisRequest(ContractModel):
    policy_document_id: UUID
    claim_document_ids: list[UUID] = Field(min_length=1, max_length=20)


class Finding(ContractModel):
    severity: FindingSeverity
    title: str
    explanation: str
    citations: list[SourceCitation]


class ClaimAnalysisResponse(ContractModel):
    request_id: UUID
    findings: list[Finding]
    potentially_missing_document_types: list[str]
    disclaimer: str
