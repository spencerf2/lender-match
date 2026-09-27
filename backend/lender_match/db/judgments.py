from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lender_match.db.base import BaseTable
from lender_match.enums import JudgmentOutputType

if TYPE_CHECKING:
    from lender_match.db.runs import MatchRun


class JudgmentQuestion(BaseTable):
    """A question a model answers about the application, defining one
    catalog field.
    """

    __tablename__ = "judgment_questions"

    key: Mapped[str] = mapped_column(Text, unique=True)
    question: Mapped[str] = mapped_column(Text)
    output_type: Mapped[JudgmentOutputType] = mapped_column(
        Enum(
            JudgmentOutputType,
            name="judgment_output_type",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda e: [m.value for m in e],
        )
    )
    options: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    yes_threshold: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))

    results: Mapped[list["JudgmentResult"]] = relationship(
        back_populates="judgment_question"
    )


class JudgmentResult(BaseTable):
    """One answer to a judgment question, kept so a match result stays
    explainable from our own database.
    """

    __tablename__ = "judgment_results"

    judgment_question_id: Mapped[UUID] = mapped_column(
        ForeignKey("judgment_questions.id"), index=True
    )
    # Null for question previews, which run outside a match run.
    match_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("match_runs.id", ondelete="SET NULL"), index=True
    )
    provider: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(Text)
    distribution: Mapped[dict[str, Any]] = mapped_column(JSONB)
    # Jev's confidence, if the API reports it separately from
    # probability.
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    threshold_used: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    resolved_value: Mapped[Any] = mapped_column(JSONB)
    raw_request: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    raw_response: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    latency_ms: Mapped[int | None]
    trace_id: Mapped[str | None] = mapped_column(Text)

    judgment_question: Mapped["JudgmentQuestion"] = relationship(
        back_populates="results"
    )
    match_run: Mapped["MatchRun | None"] = relationship(
        back_populates="judgment_results"
    )
