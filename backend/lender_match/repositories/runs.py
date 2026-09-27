from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from lender_match import db
from lender_match.domain.results import (
    CriterionResult,
    LenderResult,
    MatchRunRecord,
    ProgramResult,
)
from lender_match.enums import MatchRunStatus
from lender_match.repositories.json_values import to_json_safe
from lender_match.repositories.lenders import program_sort_key

_FINISHED = (
    MatchRunStatus.completed,
    MatchRunStatus.failed,
    MatchRunStatus.incomplete,
)


def _criterion_row(result: CriterionResult) -> db.CriterionResult:
    return db.CriterionResult(
        criterion_id=None,
        field=result.field,
        operator=result.operator,
        value=to_json_safe(result.value),
        hard=result.hard,
        weight=result.weight,
        actual_value=to_json_safe(result.actual_value),
        passed=result.passed,
        explanation=result.explanation,
    )


def _to_program_result(
    row: db.ProgramResult, match_result: db.MatchResult
) -> ProgramResult:
    # Only the lender's rate is stored, and it is the best program's.
    is_best = row.program_id == match_result.best_program_id
    return ProgramResult(
        program_name=row.program.name,
        rank=row.program.rank,
        eligible=row.eligible,
        fit_score=row.fit_score,
        hard_failures=row.hard_failures,
        criteria=[CriterionResult.model_validate(c) for c in row.criterion_results],
        estimated_rate_pct=match_result.estimated_rate_pct if is_best else None,
    )


def _to_lender_result(row: db.MatchResult) -> LenderResult:
    program_rows = sorted(
        row.program_results, key=lambda r: program_sort_key(r.program)
    )
    programs = [_to_program_result(r, row) for r in program_rows]
    best = next(
        (
            program
            for program, program_row in zip(programs, program_rows, strict=True)
            if program_row.program_id == row.best_program_id
        ),
        None,
    )
    # Rejection reasons have no column of their own. They are rebuilt
    # from the stored criterion results: the explanations of the best
    # program's failed hard criteria.
    rejection_reasons = (
        []
        if best is None or row.eligible
        else [c.explanation for c in best.criteria if c.hard and c.passed is False]
    )
    return LenderResult(
        lender_name=row.lender.name,
        eligible=row.eligible,
        best_program=best,
        fit_score=row.fit_score,
        rejection_reasons=rejection_reasons,
        programs=programs,
        position=row.position,
    )


class MatchRunRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, application_id: UUID) -> MatchRunRecord:
        row = db.MatchRun(application_id=application_id, status=MatchRunStatus.queued)
        self._session.add(row)
        self._session.flush()
        return MatchRunRecord.model_validate(row)

    def set_status(
        self, run_id: UUID, status: MatchRunStatus, error: str | None = None
    ) -> None:
        row = self._get_row(run_id)
        now = datetime.now(UTC)
        if row.status is MatchRunStatus.queued and status is not MatchRunStatus.queued:
            row.started_at = now
        if status in _FINISHED:
            row.finished_at = now
        row.status = status
        row.error = error
        self._session.flush()

    def set_field_values(self, run_id: UUID, values: Mapping[str, Any]) -> None:
        self._get_row(run_id).field_values = to_json_safe(dict(values))
        self._session.flush()

    def save_results(
        self,
        run_id: UUID,
        results: Sequence[LenderResult],
        lender_ids: Mapping[str, UUID],
        program_ids: Mapping[tuple[str, str], UUID],
    ) -> None:
        for result in results:
            lender = result.lender_name
            best = result.best_program
            self._session.add(
                db.MatchResult(
                    match_run_id=run_id,
                    lender_id=lender_ids[lender],
                    eligible=result.eligible,
                    best_program_id=(
                        program_ids[(lender, best.program_name)] if best else None
                    ),
                    fit_score=result.fit_score,
                    position=result.position,
                    estimated_rate_pct=best.estimated_rate_pct if best else None,
                    program_results=[
                        db.ProgramResult(
                            program_id=program_ids[(lender, program.program_name)],
                            eligible=program.eligible,
                            fit_score=program.fit_score,
                            hard_failures=program.hard_failures,
                            criterion_results=[
                                _criterion_row(c) for c in program.criteria
                            ],
                        )
                        for program in result.programs
                    ],
                )
            )
        self._session.flush()

    def get(self, run_id: UUID) -> MatchRunRecord | None:
        row = self._session.get(db.MatchRun, run_id)
        return MatchRunRecord.model_validate(row) if row is not None else None

    def list_for_application(self, application_id: UUID) -> list[MatchRunRecord]:
        rows = self._session.scalars(
            select(db.MatchRun)
            .where(db.MatchRun.application_id == application_id)
            .order_by(db.MatchRun.created_at.desc())
        )
        return [MatchRunRecord.model_validate(row) for row in rows]

    def get_results(self, run_id: UUID) -> list[LenderResult]:
        program_results = selectinload(db.MatchResult.program_results)
        rows = self._session.scalars(
            select(db.MatchResult)
            .where(db.MatchResult.match_run_id == run_id)
            .options(
                selectinload(db.MatchResult.lender),
                program_results.selectinload(db.ProgramResult.program),
                program_results.selectinload(db.ProgramResult.criterion_results),
            )
            .order_by(db.MatchResult.position.asc().nulls_last())
        )
        return [_to_lender_result(row) for row in rows]

    def _get_row(self, run_id: UUID) -> db.MatchRun:
        row = self._session.get(db.MatchRun, run_id)
        if row is None:
            raise LookupError(f"no match run with id {run_id}")
        return row
