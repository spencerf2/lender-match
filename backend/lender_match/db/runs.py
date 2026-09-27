from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lender_match.db.base import BaseTable
from lender_match.enums import CriterionOperator, MatchRunStatus

if TYPE_CHECKING:
    from lender_match.db.applications import Application
    from lender_match.db.judgments import JudgmentResult
    from lender_match.db.lenders import Criterion, Lender, Program


class MatchRun(BaseTable):
    """One run of the matcher over an application."""

    __tablename__ = "match_runs"

    application_id: Mapped[UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[MatchRunStatus] = mapped_column(
        Enum(
            MatchRunStatus,
            name="match_run_status",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda e: [m.value for m in e],
        ),
        default=MatchRunStatus.queued,
    )
    hatchet_run_id: Mapped[str | None] = mapped_column(Text)
    # Null until derive step.
    field_values: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]
    trace_id: Mapped[str | None] = mapped_column(Text)

    application: Mapped["Application"] = relationship(back_populates="match_runs")
    match_results: Mapped[list["MatchResult"]] = relationship(
        back_populates="match_run", cascade="all, delete-orphan", passive_deletes=True
    )
    judgment_results: Mapped[list["JudgmentResult"]] = relationship(
        back_populates="match_run", passive_deletes=True
    )


class MatchResult(BaseTable):
    """One lender's result in a run. One per lender per run."""

    __tablename__ = "match_results"

    match_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("match_runs.id", ondelete="CASCADE"), index=True
    )
    lender_id: Mapped[UUID] = mapped_column(ForeignKey("lenders.id"), index=True)
    eligible: Mapped[bool] = mapped_column(default=False)
    best_program_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("programs.id", ondelete="SET NULL"), index=True
    )
    fit_score: Mapped[int]
    # Assigned in rank step.
    position: Mapped[int | None]
    estimated_rate_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))

    match_run: Mapped["MatchRun"] = relationship(back_populates="match_results")
    lender: Mapped["Lender"] = relationship(back_populates="match_results")
    best_program: Mapped["Program | None"] = relationship()
    program_results: Mapped[list["ProgramResult"]] = relationship(
        back_populates="match_result",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ProgramResult(BaseTable):
    """One program's result in a run. One per program per lender per
    run.
    """

    __tablename__ = "program_results"

    match_result_id: Mapped[UUID] = mapped_column(
        ForeignKey("match_results.id", ondelete="CASCADE"), index=True
    )
    program_id: Mapped[UUID] = mapped_column(ForeignKey("programs.id"), index=True)
    eligible: Mapped[bool] = mapped_column(default=False)
    fit_score: Mapped[int]
    hard_failures: Mapped[int]

    match_result: Mapped["MatchResult"] = relationship(back_populates="program_results")
    program: Mapped["Program"] = relationship(back_populates="program_results")
    criterion_results: Mapped[list["CriterionResult"]] = relationship(
        back_populates="program_result",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class CriterionResult(BaseTable):
    """One criterion's result in a run. Copies the criterion as it was,
    so old results stay explainable after a policy edit.
    """

    __tablename__ = "criterion_results"

    program_result_id: Mapped[UUID] = mapped_column(
        ForeignKey("program_results.id", ondelete="CASCADE"), index=True
    )
    # Nullable because criterion may be deleted later.
    criterion_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("criteria.id", ondelete="SET NULL"), index=True
    )
    field: Mapped[str] = mapped_column(Text)
    operator: Mapped[CriterionOperator] = mapped_column(
        Enum(
            CriterionOperator,
            name="criterion_operator",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda e: [m.value for m in e],
        )
    )
    value: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    hard: Mapped[bool] = mapped_column(default=False)
    weight: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    actual_value: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    passed: Mapped[bool | None]
    explanation: Mapped[str] = mapped_column(Text)

    program_result: Mapped["ProgramResult"] = relationship(
        back_populates="criterion_results"
    )
    criterion: Mapped["Criterion | None"] = relationship(
        back_populates="criterion_results"
    )
