from fastapi import APIRouter

from lender_match.api.deps import SessionDep
from lender_match.domain.policy import JudgmentQuestion, JudgmentQuestionDraft
from lender_match.repositories.judgment_questions import JudgmentQuestionRepository

router = APIRouter(prefix="/judgment-questions", tags=["judgment questions"])


@router.get("")
def list_judgment_questions(session: SessionDep) -> list[JudgmentQuestion]:
    return JudgmentQuestionRepository(session).list()


@router.post("")
def upsert_judgment_question(
    draft: JudgmentQuestionDraft, session: SessionDep
) -> JudgmentQuestion:
    return JudgmentQuestionRepository(session).upsert_by_key(draft)
