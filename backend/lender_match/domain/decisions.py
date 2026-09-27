"""The interface every judgment question answer goes through."""

from collections.abc import Mapping
from typing import Any, Protocol

from lender_match.domain.policy import JudgmentQuestionDraft
from lender_match.domain.results import JudgmentAnswer


class DecisionProvider(Protocol):
    """Answers judgment questions about an application. Returns None
    when it has no answer.
    """

    def answer(
        self,
        question: JudgmentQuestionDraft,
        context: Mapping[str, Any],
    ) -> JudgmentAnswer | None: ...


class FakeDecisionProvider:
    """Returns fixed answers by question key, and no answer for any
    other key.
    """

    def __init__(self, answers: dict[str, JudgmentAnswer]) -> None:
        self._answers = answers

    def answer(
        self,
        question: JudgmentQuestionDraft,
        context: Mapping[str, Any],
    ) -> JudgmentAnswer | None:
        return self._answers.get(question.key)
