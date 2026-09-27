from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lender_match.db.base import BaseTable
from lender_match.enums import ApplicationStatus

if TYPE_CHECKING:
    from lender_match.db.runs import MatchRun


class Application(BaseTable):
    """One broker application. Every application-side table is filled
    from its one form.
    """

    __tablename__ = "applications"

    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(
            ApplicationStatus,
            name="application_status",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda e: [m.value for m in e],
        ),
        default=ApplicationStatus.draft,
    )
    submitted_by: Mapped[str | None] = mapped_column(Text)

    business: Mapped["Business | None"] = relationship(
        back_populates="application", cascade="all, delete-orphan", passive_deletes=True
    )
    guarantors: Mapped[list["Guarantor"]] = relationship(
        back_populates="application", cascade="all, delete-orphan", passive_deletes=True
    )
    business_credit: Mapped["BusinessCredit | None"] = relationship(
        back_populates="application", cascade="all, delete-orphan", passive_deletes=True
    )
    trade_lines: Mapped[list["TradeLine"]] = relationship(
        back_populates="application", cascade="all, delete-orphan", passive_deletes=True
    )
    loan_request: Mapped["LoanRequest | None"] = relationship(
        back_populates="application", cascade="all, delete-orphan", passive_deletes=True
    )
    match_runs: Mapped[list["MatchRun"]] = relationship(
        back_populates="application", cascade="all, delete-orphan", passive_deletes=True
    )


class Business(BaseTable):
    """The business applying. One per application."""

    __tablename__ = "businesses"

    application_id: Mapped[UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True, unique=True
    )
    legal_name: Mapped[str | None] = mapped_column(Text)
    industry: Mapped[str | None] = mapped_column(String)
    state: Mapped[str | None] = mapped_column(String(2))
    founded_date: Mapped[date | None]
    annual_revenue: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    description: Mapped[str | None] = mapped_column(Text)

    application: Mapped["Application"] = relationship(back_populates="business")


class Guarantor(BaseTable):
    """A person guaranteeing the loan. Many per application."""

    __tablename__ = "guarantors"

    application_id: Mapped[UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str | None] = mapped_column(Text)
    ownership_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    fico: Mapped[int | None]
    is_homeowner: Mapped[bool] = mapped_column(default=False)
    is_us_citizen: Mapped[bool] = mapped_column(default=False)
    bankruptcy_discharge_date: Mapped[date | None]
    has_judgments: Mapped[bool] = mapped_column(default=False)
    has_foreclosures: Mapped[bool] = mapped_column(default=False)
    has_repossessions: Mapped[bool] = mapped_column(default=False)

    application: Mapped["Application"] = relationship(back_populates="guarantors")


class BusinessCredit(BaseTable):
    """The business's credit scores. One per application."""

    __tablename__ = "business_credit"

    application_id: Mapped[UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True, unique=True
    )
    paynet_score: Mapped[int | None]

    application: Mapped["Application"] = relationship(back_populates="business_credit")


class TradeLine(BaseTable):
    """One account on a credit report. Many per application."""

    __tablename__ = "trade_lines"

    application_id: Mapped[UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    creditor: Mapped[str | None] = mapped_column(Text)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    opened_on: Mapped[date | None]
    closed_on: Mapped[date | None]
    status: Mapped[str | None] = mapped_column(String)

    application: Mapped["Application"] = relationship(back_populates="trade_lines")


class LoanRequest(BaseTable):
    """The equipment and amount being financed. One per application."""

    __tablename__ = "loan_requests"

    application_id: Mapped[UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True, unique=True
    )
    amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    term_months: Mapped[int | None]
    down_payment_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    equipment_type: Mapped[str | None] = mapped_column(String)
    equipment_description: Mapped[str | None] = mapped_column(Text)
    equipment_year: Mapped[int | None]
    equipment_mileage: Mapped[int | None]
    is_private_party_sale: Mapped[bool] = mapped_column(default=False)

    application: Mapped["Application"] = relationship(back_populates="loan_request")
