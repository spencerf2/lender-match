"""Classes that describe a loan application as the form collects it,
with the values derived from it next to the data they come from.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import (
    Field,
    computed_field,
    field_validator,
    model_validator,
)

from lender_match.domain.base import DomainModel
from lender_match.domain.fields import EQUIPMENT_TYPES, INDUSTRIES, US_STATES
from lender_match.domain.values import years_between
from lender_match.enums import ApplicationStatus


class BusinessDraft(DomainModel):
    """The business applying."""

    legal_name: str | None = None
    industry: str | None = None
    state: str | None = None
    founded_date: date | None = None
    annual_revenue: Decimal | None = Field(default=None, ge=0)
    description: str | None = None

    @field_validator("industry")
    @classmethod
    def _check_industry(cls, value: str | None) -> str | None:
        if value is not None and value not in INDUSTRIES:
            raise ValueError(f"unknown industry: {value}")
        return value

    @field_validator("state")
    @classmethod
    def _check_state(cls, value: str | None) -> str | None:
        if value is not None and value not in US_STATES:
            raise ValueError(f"unknown state: {value}")
        return value


class GuarantorDraft(DomainModel):
    """A person guaranteeing the loan."""

    name: str | None = None
    ownership_pct: Decimal | None = Field(default=None, ge=0, le=100)
    fico: int | None = Field(default=None, ge=300, le=850)
    is_homeowner: bool = False
    is_us_citizen: bool = False
    bankruptcy_discharge_date: date | None = None
    has_judgments: bool = False
    has_foreclosures: bool = False
    has_repossessions: bool = False


class BusinessCreditDraft(DomainModel):
    """The business's credit scores."""

    paynet_score: int | None = Field(default=None, ge=0, le=1000)


class TradeLineDraft(DomainModel):
    """One account on a credit report."""

    creditor: str | None = None
    amount: Decimal | None = Field(default=None, ge=0)
    opened_on: date | None = None
    closed_on: date | None = None
    status: str | None = None

    @model_validator(mode="after")
    def _check_dates(self) -> "TradeLineDraft":
        if (
            self.opened_on is not None
            and self.closed_on is not None
            and self.closed_on < self.opened_on
        ):
            raise ValueError("closed_on must not be before opened_on")
        return self


class LoanRequestDraft(DomainModel):
    """The equipment and amount being financed."""

    amount: Decimal | None = Field(default=None, gt=0)
    term_months: int | None = Field(default=None, gt=0)
    down_payment_amount: Decimal = Field(default=Decimal(0), ge=0)
    equipment_type: str | None = None
    equipment_description: str | None = None
    equipment_year: int | None = None
    equipment_mileage: int | None = Field(default=None, ge=0)
    is_private_party_sale: bool = False

    @field_validator("equipment_type")
    @classmethod
    def _check_equipment_type(cls, value: str | None) -> str | None:
        if value is not None and value not in EQUIPMENT_TYPES:
            raise ValueError(f"unknown equipment type: {value}")
        return value

    @field_validator("equipment_year")
    @classmethod
    def _check_equipment_year(cls, value: int | None) -> int | None:
        # Next year's models go on sale during the current year.
        latest = datetime.now(UTC).year + 1
        if value is not None and not 1900 <= value <= latest:
            raise ValueError(f"equipment_year must be 1900 to {latest}")
        return value


class ApplicationDraft(DomainModel):
    """One broker application, possibly with blanks."""

    submitted_by: str | None = None
    business: BusinessDraft = Field(default_factory=BusinessDraft)
    guarantors: list[GuarantorDraft] = Field(default_factory=list)
    business_credit: BusinessCreditDraft = Field(default_factory=BusinessCreditDraft)
    trade_lines: list[TradeLineDraft] = Field(default_factory=list)
    loan_request: LoanRequestDraft = Field(default_factory=LoanRequestDraft)

    @field_validator("business", "business_credit", "loan_request", mode="before")
    @classmethod
    def _missing_row_is_empty(cls, value: object) -> object:
        return {} if value is None else value

    @computed_field
    @property
    def min_fico(self) -> int | None:
        ficos = [g.fico for g in self.guarantors if g.fico is not None]
        return min(ficos, default=None)

    @computed_field
    @property
    def is_homeowner(self) -> bool:
        return bool(self.guarantors) and all(g.is_homeowner for g in self.guarantors)

    @computed_field
    @property
    def is_us_citizen(self) -> bool:
        return bool(self.guarantors) and all(g.is_us_citizen for g in self.guarantors)

    @computed_field
    @property
    def has_judgments(self) -> bool:
        return any(g.has_judgments for g in self.guarantors)

    @computed_field
    @property
    def has_foreclosures(self) -> bool:
        return any(g.has_foreclosures for g in self.guarantors)

    @computed_field
    @property
    def has_repossessions(self) -> bool:
        return any(g.has_repossessions for g in self.guarantors)

    @computed_field
    @property
    def comparable_credit_ratio(self) -> Decimal | None:
        amount = self.loan_request.amount
        trade_amounts = [t.amount for t in self.trade_lines if t.amount is not None]
        if not trade_amounts or amount is None:
            return None
        return (max(trade_amounts) / amount).quantize(Decimal("0.0001"))

    @computed_field
    @property
    def down_payment_pct(self) -> Decimal | None:
        amount = self.loan_request.amount
        if amount is None:
            return None
        down = self.loan_request.down_payment_amount
        return (down / amount).quantize(Decimal("0.0001"))

    def years_since_bankruptcy(self, as_of: date) -> Decimal | None:
        """Years since the most recent discharge across guarantors.
        Returns None when no guarantor has one.
        """
        years = [
            years_between(g.bankruptcy_discharge_date, as_of)
            for g in self.guarantors
            if g.bankruptcy_discharge_date is not None
        ]
        return min(years, default=None)

    def years_in_business(self, as_of: date) -> Decimal | None:
        """Years since the business was founded. Returns None when the
        founding date is blank.
        """
        founded = self.business.founded_date
        if founded is None:
            return None
        return years_between(founded, as_of)

    def equipment_age_years(self, as_of: date) -> int | None:
        """Equipment age in whole years, never below zero. Returns None
        when the model year is blank.
        """
        year = self.loan_request.equipment_year
        if year is None:
            return None
        return max(as_of.year - year, 0)

    def built_in_field_values(self, as_of: date) -> dict[str, object]:
        """Every built-in application field's value, by field key."""
        return {
            "guarantor.min_fico": self.min_fico,
            "guarantor.is_homeowner": self.is_homeowner,
            "guarantor.is_us_citizen": self.is_us_citizen,
            "guarantor.has_judgments": self.has_judgments,
            "guarantor.has_foreclosures": self.has_foreclosures,
            "guarantor.has_repossessions": self.has_repossessions,
            "guarantor.years_since_bankruptcy": self.years_since_bankruptcy(as_of),
            "business_credit.paynet": self.business_credit.paynet_score,
            "business_credit.comparable_credit_ratio": self.comparable_credit_ratio,
            "business_credit.trade_lines": self.trade_lines,
            "business.years_in_business": self.years_in_business(as_of),
            "business.state": self.business.state,
            "business.industry": self.business.industry,
            "business.annual_revenue": self.business.annual_revenue,
            "loan.amount": self.loan_request.amount,
            "loan.term_months": self.loan_request.term_months,
            "loan.down_payment_pct": self.down_payment_pct,
            "equipment.type": self.loan_request.equipment_type,
            "equipment.age_years": self.equipment_age_years(as_of),
            "equipment.mileage": self.loan_request.equipment_mileage,
            "equipment.is_private_party_sale": (
                self.loan_request.is_private_party_sale
            ),
        }


class Application(ApplicationDraft):
    id: UUID
    status: ApplicationStatus
    created_at: datetime
    updated_at: datetime
