"""Loads the seed files into the database."""

from dataclasses import dataclass

from pydantic import TypeAdapter
from sqlalchemy.orm import Session

from lender_match.domain.criterion_check import check_lender
from lender_match.domain.fields import application_fields
from lender_match.domain.policy import JudgmentQuestionDraft, LenderDraft
from lender_match.enums import LenderStatus
from lender_match.paths import SEEDS_DIR
from lender_match.repositories.judgment_questions import JudgmentQuestionRepository
from lender_match.repositories.lenders import LenderRepository


@dataclass(frozen=True)
class SeedSummary:
    judgment_questions: int
    lenders: int


def seed(session: Session) -> SeedSummary:
    """Write the seed judgment questions and lenders. Existing rows with
    the same key or name are overwritten, so running it again is safe.
    """
    questions = JudgmentQuestionRepository(session)
    text = (SEEDS_DIR / "judgment_questions.json").read_text()
    drafts = TypeAdapter(list[JudgmentQuestionDraft]).validate_json(text)
    for draft in drafts:
        questions.upsert_by_key(draft)
    fields = application_fields(questions.list())

    lenders = LenderRepository(session)
    paths = sorted((SEEDS_DIR / "lenders").glob("*.json"))
    for path in paths:
        lender = LenderDraft.model_validate_json(path.read_text())
        problems = check_lender(lender, fields)
        if problems:
            raise ValueError("\n".join([f"{path.name}:", *problems]))
        existing = lenders.get_by_name(lender.name)
        if existing is None:
            lenders.add(lender, LenderStatus.active)
        else:
            lenders.replace(existing.id, lender)
    return SeedSummary(judgment_questions=len(drafts), lenders=len(paths))
