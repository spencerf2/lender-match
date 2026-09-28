"""Classes that hold the outcome of matching one application against
lender policies.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from lender_match.domain.base import DomainModel
from lender_match.enums import CriterionOperator, MatchRunStatus


class CriterionResult(DomainModel):
    """How the application fared against one criterion."""

    field: str
    operator: CriterionOperator
    value: Any | None
    hard: bool
    weight: Decimal | None
    actual_value: Any | None
    # None when the criterion could not be evaluated: a judgment field
    # with no answer yet, or an operator nothing evaluates yet.
    passed: bool | None
    explanation: str


class ProgramResult(DomainModel):
    """How the application fared against one program."""

    program_name: str
    rank: int | None
    eligible: bool
    fit_score: int
    hard_failures: int
    criteria: list[CriterionResult]
    estimated_rate_pct: Decimal | None


class LenderResult(DomainModel):
    """How the application fared against one lender."""

    lender_name: str
    eligible: bool
    # The best eligible program, or the program with the fewest hard
    # failures when none is eligible.
    best_program: ProgramResult | None
    fit_score: int
    # Explanations of best_program's failed hard criteria when the
    # lender is ineligible.
    rejection_reasons: list[str]
    programs: list[ProgramResult]
    position: int | None


class ProviderCall(DomainModel):
    """The call a decision provider made to get an answer."""

    provider: str
    model: str
    request: Any | None = None
    response: Any | None = None
    latency_ms: int | None = None


class JudgmentAnswer(DomainModel):
    """A model's answer to one judgment question."""

    distribution: dict[str, Decimal]
    confidence: Decimal | None
    call: ProviderCall | None = None


class JudgmentResultRecord(DomainModel):
    """One stored answer to a judgment question."""

    id: UUID
    match_run_id: UUID | None
    judgment_question_id: UUID
    question_key: str
    provider: str
    model: str
    distribution: dict[str, Any]
    confidence: Decimal | None
    threshold_used: Decimal | None
    resolved_value: Any
    raw_request: Any | None
    raw_response: Any | None
    latency_ms: int | None


class MatchRunRecord(DomainModel):
    """One run of the matcher over an application."""

    id: UUID
    application_id: UUID
    status: MatchRunStatus
    field_values: dict[str, Any] | None
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime
