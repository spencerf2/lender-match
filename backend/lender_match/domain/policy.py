"""Classes that describe a lender's policy. Drafts are what extraction
produces and seed files hold; stored classes add ids.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import ConfigDict, Field, model_validator

from lender_match.domain.base import DomainModel
from lender_match.domain.values import is_number
from lender_match.enums import (
    CriterionOperator,
    JudgmentOutputType,
    LenderStatus,
    PolicyNoteKind,
)


class CountAtLeast(DomainModel):
    """The value of a `count_at_least` criterion on trade lines.

    Passes when at least `count` trade lines have an amount of
    `min_amount` or more and were active within `active_within_months`.
    """

    model_config = ConfigDict(frozen=True)

    count: int = Field(ge=1)
    min_amount: Decimal = Field(ge=0)
    active_within_months: int = Field(ge=1)


class CriterionDraft(DomainModel):
    """One rule a program applies to one application field."""

    field: str
    operator: CriterionOperator
    value: Any | None = None
    hard: bool
    weight: Decimal | None = None
    source_quote: str | None = None
    position: int = 0

    @model_validator(mode="after")
    def _check_value_and_weight(self) -> "CriterionDraft":
        self._check_value()
        if self.hard:
            if self.weight is not None:
                raise ValueError(f"{self.field}: hard criteria take no weight")
        elif self.weight is None:
            self.weight = Decimal("0.5")
        elif self.weight <= 0:
            raise ValueError(f"{self.field}: weight must be above zero")
        return self

    def _check_value(self) -> None:
        op = CriterionOperator
        value = self.value
        match self.operator:
            case op.gte | op.lte:
                if not is_number(value):
                    raise ValueError(f"{self.field}: value must be a number")
            case op.between:
                if not (
                    isinstance(value, list)
                    and len(value) == 2
                    and all(is_number(v) for v in value)
                ):
                    raise ValueError(
                        f"{self.field}: value must be a list of two numbers"
                    )
                if value[0] > value[1]:
                    raise ValueError(
                        f"{self.field}: first number must not exceed second"
                    )
            case op.in_ | op.not_in:
                if not (
                    isinstance(value, list)
                    and value
                    and all(isinstance(v, str) for v in value)
                ):
                    raise ValueError(
                        f"{self.field}: value must be a non-empty list of strings"
                    )
            case op.is_true | op.is_false | op.is_null:
                if value is not None:
                    raise ValueError(f"{self.field}: value must be empty")
            case op.count_at_least:
                CountAtLeast.model_validate(value)


class RateBand(DomainModel):
    """The rate a program charges for one amount range, optionally
    limited to one credit grade. No max_amount means the band has no
    upper bound.
    """

    credit_grade: str | None = None
    min_amount: Decimal = Field(ge=0)
    max_amount: Decimal | None = Field(default=None, ge=0)
    rate_pct: Decimal = Field(ge=0)

    @model_validator(mode="after")
    def _check_range(self) -> "RateBand":
        if self.max_amount is not None and self.min_amount > self.max_amount:
            raise ValueError("min_amount must not exceed max_amount")
        return self


class ProgramDraft(DomainModel):
    """One program a lender offers, with its criteria and rates."""

    name: str = Field(min_length=1)
    rank: int | None = Field(default=None, ge=1)
    app_only_max_amount: Decimal | None = Field(default=None, ge=0)
    notes: str | None = None
    criteria: list[CriterionDraft] = Field(default_factory=list)
    rates: list[RateBand] = Field(default_factory=list)


class LenderContact(DomainModel):
    """A person or team to contact at a lender."""

    name: str | None = None
    title: str | None = None
    email: str | None = None
    phone: str | None = None
    role: str

    @model_validator(mode="after")
    def _check_reachable(self) -> "LenderContact":
        if self.name is None and self.email is None and self.phone is None:
            raise ValueError("a contact needs a name, email, or phone")
        return self


class PolicyNote(DomainModel):
    """Policy text that is not a criterion."""

    kind: PolicyNoteKind
    text: str = Field(min_length=1)
    # A program name within the lender, or None for the whole lender.
    program: str | None = None


class LenderDraft(DomainModel):
    """A lender's full policy."""

    name: str = Field(min_length=1)
    source_effective_date: date | None = None
    contacts: list[LenderContact] = Field(default_factory=list)
    programs: list[ProgramDraft] = Field(min_length=1)
    notes: list[PolicyNote] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_program_names(self) -> "LenderDraft":
        names = [program.name for program in self.programs]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            raise ValueError(f"duplicate program names: {duplicates}")
        for note in self.notes:
            if note.program is not None and note.program not in names:
                raise ValueError(f"note names unknown program: {note.program}")
        return self


class JudgmentQuestionDraft(DomainModel):
    """A question a model answers about an application. It defines the
    judgment fields named by its key.
    """

    key: str = Field(pattern=r"^judgment\.[a-z_]+$")
    question: str = Field(min_length=1)
    output_type: JudgmentOutputType
    options: list[str] | None = None
    yes_threshold: Decimal | None = None

    @model_validator(mode="after")
    def _check_output_type(self) -> "JudgmentQuestionDraft":
        if self.output_type is JudgmentOutputType.yes_no:
            if self.options is not None:
                raise ValueError(f"{self.key}: yes_no questions take no options")
            if self.yes_threshold is None:
                self.yes_threshold = Decimal("0.5")
            if not 0 < self.yes_threshold < 1:
                raise ValueError(f"{self.key}: yes_threshold must be between 0 and 1")
        else:
            if self.options is None or len(set(self.options)) < 2:
                raise ValueError(
                    f"{self.key}: choice questions need two distinct options"
                )
            if self.yes_threshold is not None:
                raise ValueError(f"{self.key}: choice questions take no yes_threshold")
        return self


class Criterion(CriterionDraft):
    id: UUID


class Program(ProgramDraft):
    id: UUID
    criteria: list[Criterion] = Field(default_factory=list)  # pyright: ignore[reportIncompatibleVariableOverride]


class Lender(LenderDraft):
    id: UUID
    status: LenderStatus
    created_at: datetime
    updated_at: datetime
    programs: list[Program] = Field(min_length=1)  # pyright: ignore[reportIncompatibleVariableOverride]


class JudgmentQuestion(JudgmentQuestionDraft):
    id: UUID
