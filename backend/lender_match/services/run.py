"""Runs the matcher over one application, step by step."""

import logging
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from lender_match.config import get_config
from lender_match.db.session import session_scope
from lender_match.domain.decisions import DecisionProvider, FakeDecisionProvider
from lender_match.domain.fields import ApplicationFields, application_fields
from lender_match.domain.matching import (
    evaluate_lender,
    judgment_keys_needed,
    rank_lenders,
    resolve_judgment,
)
from lender_match.domain.policy import Lender
from lender_match.domain.results import JudgmentAnswer, LenderResult
from lender_match.enums import LenderStatus, MatchRunStatus
from lender_match.repositories.applications import ApplicationRepository
from lender_match.repositories.judgment_questions import JudgmentQuestionRepository
from lender_match.repositories.lenders import LenderRepository
from lender_match.repositories.runs import MatchRunRepository

logger = logging.getLogger(__name__)


def execute_run(run_id: UUID) -> None:
    """Take a queued run to completed, incomplete, or failed. Errors are
    stored on the run instead of raised, because this runs as a
    background task where nobody would see them.
    """
    try:
        with session_scope() as session:
            _execute(session, run_id)
    except Exception as exc:  # noqa: BLE001
        try:
            with session_scope() as session:
                MatchRunRepository(session).set_status(
                    run_id, MatchRunStatus.failed, str(exc)
                )
        except Exception:
            logger.exception("could not mark match run %s failed", run_id)


def _execute(session: Session, run_id: UUID) -> None:
    runs = MatchRunRepository(session)

    def advance(status: MatchRunStatus, error: str | None = None) -> None:
        runs.set_status(run_id, status, error)
        # Commit each step so a client polling the run sees it.
        session.commit()

    advance(MatchRunStatus.validating)
    run = runs.get(run_id)
    if run is None:
        raise LookupError(f"no match run with id {run_id}")
    application = ApplicationRepository(session).get(run.application_id)
    if application is None:
        raise LookupError(f"no application with id {run.application_id}")
    questions = JudgmentQuestionRepository(session).list()
    fields = application_fields(questions)
    field_values = application.built_in_field_values(as_of=datetime.now(UTC).date())
    missing = [
        fields.get(key).label
        for key in fields.required_keys()
        if field_values.get(key) is None
    ]
    if missing:
        advance(MatchRunStatus.incomplete, "\n".join(missing))
        return

    advance(MatchRunStatus.deriving)
    runs.set_field_values(run_id, field_values)

    advance(MatchRunStatus.matching)
    lenders = LenderRepository(session).list(LenderStatus.active)
    loan_amount = application.loan_request.amount
    results = _evaluate_all(lenders, field_values, fields, loan_amount)
    # Ask only the judgment questions that could still change an
    # outcome, then evaluate again with the answers.
    needed = set[str]().union(
        *(
            judgment_keys_needed(lender.programs, result.programs)
            for lender, result in zip(lenders, results, strict=True)
        )
    )
    questions_by_key = {question.key: question for question in questions}
    provider = _decision_provider()
    context = application.model_dump(mode="json")
    answers: dict[str, JudgmentAnswer] = {}
    for key in sorted(needed):
        answer = provider.answer(questions_by_key[key], context)
        if answer is not None:
            answers[key] = answer
    if answers:
        for key, answer in answers.items():
            field_values.update(resolve_judgment(questions_by_key[key], answer))
        runs.set_field_values(run_id, field_values)
        results = _evaluate_all(lenders, field_values, fields, loan_amount)

    advance(MatchRunStatus.ranking)
    runs.save_results(
        run_id,
        rank_lenders(results),
        lender_ids={lender.name: lender.id for lender in lenders},
        program_ids={
            (lender.name, program.name): program.id
            for lender in lenders
            for program in lender.programs
        },
    )
    advance(MatchRunStatus.completed)


def _evaluate_all(
    lenders: Sequence[Lender],
    field_values: Mapping[str, Any],
    fields: ApplicationFields,
    loan_amount: Decimal | None,
) -> list[LenderResult]:
    return [
        evaluate_lender(lender, field_values, fields, loan_amount) for lender in lenders
    ]


def _decision_provider() -> DecisionProvider:
    match get_config().decision_provider:
        case "fake":
            return FakeDecisionProvider({})
        case other:
            raise ValueError(f"decision_provider {other!r} is not implemented")
