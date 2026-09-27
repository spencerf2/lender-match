"""Database tables. Import this package so every table is registered
before use.
"""

from lender_match.db.applications import (
    Application,
    Business,
    BusinessCredit,
    Guarantor,
    LoanRequest,
    TradeLine,
)
from lender_match.db.base import Base, BaseTable
from lender_match.db.judgments import JudgmentQuestion, JudgmentResult
from lender_match.db.lenders import (
    Criterion,
    Lender,
    LenderContact,
    LenderDocument,
    PolicyNote,
    Program,
    RateBand,
)
from lender_match.db.runs import CriterionResult, MatchResult, MatchRun, ProgramResult

__all__ = [
    "Application",
    "Base",
    "BaseTable",
    "Business",
    "BusinessCredit",
    "Criterion",
    "CriterionResult",
    "Guarantor",
    "JudgmentQuestion",
    "JudgmentResult",
    "Lender",
    "LenderContact",
    "LenderDocument",
    "LoanRequest",
    "MatchResult",
    "MatchRun",
    "PolicyNote",
    "Program",
    "ProgramResult",
    "RateBand",
    "TradeLine",
]
