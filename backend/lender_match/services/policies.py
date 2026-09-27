"""Checks a lender policy before it is saved."""

from sqlalchemy.orm import Session

from lender_match.domain.criterion_check import check_lender
from lender_match.domain.fields import application_fields
from lender_match.domain.policy import LenderDraft
from lender_match.repositories.judgment_questions import JudgmentQuestionRepository


class PolicyProblems(Exception):
    """A lender's criteria do not fit the application fields."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("\n".join(problems))
        self.problems = problems


def check_policy(draft: LenderDraft, session: Session) -> None:
    """Check every criterion against the application fields, judgment
    fields included. Raises PolicyProblems listing what is wrong.
    """
    questions = JudgmentQuestionRepository(session).list()
    problems = check_lender(draft, application_fields(questions))
    if problems:
        raise PolicyProblems(problems)
