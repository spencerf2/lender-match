from pathlib import Path

import pytest
from pydantic import TypeAdapter

from lender_match.domain.criterion_check import check_lender
from lender_match.domain.fields import ApplicationFields, application_fields
from lender_match.domain.policy import JudgmentQuestionDraft, LenderDraft

SEEDS = Path(__file__).resolve().parents[1] / "seeds"
LENDER_FILES = sorted((SEEDS / "lenders").glob("*.json"))


def _judgment_questions() -> list[JudgmentQuestionDraft]:
    text = (SEEDS / "judgment_questions.json").read_text()
    return TypeAdapter(list[JudgmentQuestionDraft]).validate_json(text)


@pytest.fixture(scope="module")
def fields() -> ApplicationFields:
    return application_fields(_judgment_questions())


def test_judgment_question_seeds_parse() -> None:
    _judgment_questions()


@pytest.mark.parametrize(
    "path",
    LENDER_FILES
    or [pytest.param(None, marks=pytest.mark.skip(reason="no seed files yet"))],
    ids=lambda path: path.name if path else "none",
)
def test_every_seed_file_is_a_valid_lender_policy(
    path: Path, fields: ApplicationFields
) -> None:
    lender = LenderDraft.model_validate_json(path.read_text())
    problems = check_lender(lender, fields)
    assert not problems, "\n".join(problems)
