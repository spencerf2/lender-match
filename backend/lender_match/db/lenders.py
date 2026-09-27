from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Numeric, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lender_match.db.base import BaseTable
from lender_match.enums import CriterionOperator, LenderStatus, PolicyNoteKind

if TYPE_CHECKING:
    from lender_match.db.runs import CriterionResult, MatchResult, ProgramResult


class Lender(BaseTable):
    """A lender and its credit policy."""

    __tablename__ = "lenders"

    name: Mapped[str] = mapped_column(Text, unique=True)
    source_effective_date: Mapped[date | None]
    status: Mapped[LenderStatus] = mapped_column(
        Enum(
            LenderStatus,
            name="lender_status",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda e: [m.value for m in e],
        ),
        default=LenderStatus.draft,
    )

    contacts: Mapped[list["LenderContact"]] = relationship(
        back_populates="lender", cascade="all, delete-orphan", passive_deletes=True
    )
    programs: Mapped[list["Program"]] = relationship(
        back_populates="lender", cascade="all, delete-orphan", passive_deletes=True
    )
    policy_notes: Mapped[list["PolicyNote"]] = relationship(
        back_populates="lender", cascade="all, delete-orphan", passive_deletes=True
    )
    documents: Mapped[list["LenderDocument"]] = relationship(
        back_populates="lender", cascade="all, delete-orphan", passive_deletes=True
    )
    match_results: Mapped[list["MatchResult"]] = relationship(back_populates="lender")


class LenderContact(BaseTable):
    """A person or functional inbox at a lender. Contacts are people we
    email.
    """

    __tablename__ = "lender_contacts"

    lender_id: Mapped[UUID] = mapped_column(
        ForeignKey("lenders.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text)

    lender: Mapped["Lender"] = relationship(back_populates="contacts")


class Program(BaseTable):
    """A program within a lender's policy."""

    __tablename__ = "programs"
    __table_args__ = (UniqueConstraint("lender_id", "name"),)

    lender_id: Mapped[UUID] = mapped_column(
        ForeignKey("lenders.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(Text)
    rank: Mapped[int | None]
    app_only_max_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    notes: Mapped[str | None] = mapped_column(Text)

    lender: Mapped["Lender"] = relationship(back_populates="programs")
    criteria: Mapped[list["Criterion"]] = relationship(
        back_populates="program", cascade="all, delete-orphan", passive_deletes=True
    )
    rate_bands: Mapped[list["RateBand"]] = relationship(
        back_populates="program", cascade="all, delete-orphan", passive_deletes=True
    )
    policy_notes: Mapped[list["PolicyNote"]] = relationship(
        back_populates="program", cascade="all, delete-orphan", passive_deletes=True
    )
    program_results: Mapped[list["ProgramResult"]] = relationship(
        back_populates="program"
    )


class Criterion(BaseTable):
    """One rule a program applies to one application field."""

    __tablename__ = "criteria"

    program_id: Mapped[UUID] = mapped_column(
        ForeignKey("programs.id", ondelete="CASCADE"), index=True
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
    # Null for operators that take no value, such as is_true.
    value: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    hard: Mapped[bool] = mapped_column(default=False)
    # Soft criteria only.
    weight: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    source_quote: Mapped[str | None] = mapped_column(Text)
    quote_verified: Mapped[bool] = mapped_column(default=False)
    position: Mapped[int]

    program: Mapped["Program"] = relationship(back_populates="criteria")
    criterion_results: Mapped[list["CriterionResult"]] = relationship(
        back_populates="criterion", passive_deletes=True
    )


class RateBand(BaseTable):
    """A rate a program offers for an amount range, optionally by credit
    grade.
    """

    __tablename__ = "rate_bands"

    program_id: Mapped[UUID] = mapped_column(
        ForeignKey("programs.id", ondelete="CASCADE"), index=True
    )
    credit_grade: Mapped[str | None] = mapped_column(Text)
    min_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    max_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    rate_pct: Mapped[Decimal] = mapped_column(Numeric(6, 3))

    program: Mapped["Program"] = relationship(back_populates="rate_bands")


class PolicyNote(BaseTable):
    """A policy line that no criterion evaluates. Policy notes never
    affect the score.
    """

    __tablename__ = "policy_notes"

    lender_id: Mapped[UUID] = mapped_column(
        ForeignKey("lenders.id", ondelete="CASCADE"), index=True
    )
    program_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("programs.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[PolicyNoteKind] = mapped_column(
        Enum(
            PolicyNoteKind,
            name="policy_note_kind",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda e: [m.value for m in e],
        )
    )
    text: Mapped[str] = mapped_column(Text)

    lender: Mapped["Lender"] = relationship(back_populates="policy_notes")
    program: Mapped["Program | None"] = relationship(back_populates="policy_notes")


class LenderDocument(BaseTable):
    """A lender's policy PDF and its OCR output."""

    __tablename__ = "lender_documents"

    lender_id: Mapped[UUID] = mapped_column(
        ForeignKey("lenders.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(Text)
    pdf_path: Mapped[str] = mapped_column(Text)
    markdown: Mapped[str] = mapped_column(Text)
    page_count: Mapped[int]
    ocr_report: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    trace_id: Mapped[str | None] = mapped_column(Text)

    lender: Mapped["Lender"] = relationship(back_populates="documents")
