from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from lender_match import db
from lender_match.domain.results import JudgmentResultRecord
from lender_match.repositories.json_values import to_json_safe


class JudgmentResultRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self,
        run_id: UUID | None,
        question_id: UUID,
        provider: str,
        model: str,
        distribution: dict[str, Decimal],
        confidence: Decimal | None,
        threshold_used: Decimal | None,
        resolved_value: Any,
        raw_request: Any | None,
        raw_response: Any | None,
        latency_ms: int | None,
    ) -> None:
        self._session.add(
            db.JudgmentResult(
                match_run_id=run_id,
                judgment_question_id=question_id,
                provider=provider,
                model=model,
                distribution=to_json_safe(distribution),
                confidence=confidence,
                threshold_used=threshold_used,
                resolved_value=to_json_safe(resolved_value),
                raw_request=to_json_safe(raw_request),
                raw_response=to_json_safe(raw_response),
                latency_ms=latency_ms,
            )
        )
        self._session.flush()

    def list_for_run(self, run_id: UUID) -> list[JudgmentResultRecord]:
        rows = self._session.scalars(
            select(db.JudgmentResult)
            .where(db.JudgmentResult.match_run_id == run_id)
            .options(selectinload(db.JudgmentResult.judgment_question))
            .order_by(db.JudgmentResult.created_at)
        )
        return [
            JudgmentResultRecord(
                id=row.id,
                match_run_id=row.match_run_id,
                judgment_question_id=row.judgment_question_id,
                question_key=row.judgment_question.key,
                provider=row.provider,
                model=row.model,
                distribution=row.distribution,
                confidence=row.confidence,
                threshold_used=row.threshold_used,
                resolved_value=row.resolved_value,
                raw_request=row.raw_request,
                raw_response=row.raw_response,
                latency_ms=row.latency_ms,
            )
            for row in rows
        ]
