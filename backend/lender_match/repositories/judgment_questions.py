from sqlalchemy import select
from sqlalchemy.orm import Session

from lender_match import db
from lender_match.domain.policy import JudgmentQuestion, JudgmentQuestionDraft


class JudgmentQuestionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_by_key(self, draft: JudgmentQuestionDraft) -> JudgmentQuestion:
        row = self._session.scalar(
            select(db.JudgmentQuestion).where(db.JudgmentQuestion.key == draft.key)
        )
        if row is None:
            row = db.JudgmentQuestion(key=draft.key)
            self._session.add(row)
        row.question = draft.question
        row.output_type = draft.output_type
        row.options = draft.options
        row.yes_threshold = draft.yes_threshold
        self._session.flush()
        return JudgmentQuestion.model_validate(row)

    def list(self) -> list[JudgmentQuestion]:
        rows = self._session.scalars(
            select(db.JudgmentQuestion).order_by(db.JudgmentQuestion.key)
        )
        return [JudgmentQuestion.model_validate(row) for row in rows]
