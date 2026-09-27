from fastapi import APIRouter

from lender_match.api.deps import SessionDep
from lender_match.domain.fields import FieldDefinition, application_fields
from lender_match.repositories.judgment_questions import JudgmentQuestionRepository

router = APIRouter(prefix="/application-fields", tags=["application fields"])


@router.get("")
def list_application_fields(session: SessionDep) -> list[FieldDefinition]:
    questions = JudgmentQuestionRepository(session).list()
    return list(application_fields(questions).definitions())
