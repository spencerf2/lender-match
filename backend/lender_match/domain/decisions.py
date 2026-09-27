"""The interface every judgment question answer goes through."""

from collections.abc import Mapping
from typing import Any, Protocol

from lender_match.domain.policy import JudgmentQuestionDraft
from lender_match.domain.results import JudgmentAnswer


class DecisionProvider(Protocol):
    """Answers judgment questions about an application."""

    def answer(
        self,
        question: JudgmentQuestionDraft,
        context: Mapping[str, Any],
    ) -> JudgmentAnswer: ...


class FakeDecisionProvider:
    """Returns fixed answers by question key, for tests."""

    def __init__(self, answers: dict[str, JudgmentAnswer]) -> None:
        self._answers = answers

    def answer(
        self,
        question: JudgmentQuestionDraft,
        context: Mapping[str, Any],
    ) -> JudgmentAnswer:
        return self._answers[question.key]
