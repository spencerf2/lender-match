from uuid import UUID

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from lender_match.api.deps import SessionDep
from lender_match.api.errors import found
from lender_match.domain.policy import Lender, LenderDraft
from lender_match.enums import LenderStatus
from lender_match.repositories.lenders import LenderRepository
from lender_match.services.policies import PolicyProblems, check_policy

router = APIRouter(prefix="/lenders", tags=["lenders"])


class PolicyCheck(BaseModel):
    problems: list[str]


def _has_match_results() -> HTTPException:
    # Result rows point at program rows, so replacing or deleting a
    # policy fails the foreign keys once a run has stored results.
    return HTTPException(
        status_code=409,
        detail="This lender has match results. Archive it instead of editing or deleting it.",
    )


@router.get("")
def list_lenders(
    session: SessionDep, status: LenderStatus | None = None
) -> list[Lender]:
    return LenderRepository(session).list(status)


@router.post("/check")
def check_lender_policy(draft: LenderDraft, session: SessionDep) -> PolicyCheck:
    try:
        check_policy(draft, session)
    except PolicyProblems as exc:
        return PolicyCheck(problems=exc.problems)
    return PolicyCheck(problems=[])


@router.get("/{lender_id}")
def get_lender(lender_id: UUID, session: SessionDep) -> Lender:
    return found(
        LenderRepository(session).get(lender_id), f"no lender with id {lender_id}"
    )


@router.post("", status_code=201)
def create_lender(draft: LenderDraft, session: SessionDep) -> Lender:
    check_policy(draft, session)
    return LenderRepository(session).add(draft, LenderStatus.active)


@router.put("/{lender_id}")
def replace_lender(lender_id: UUID, draft: LenderDraft, session: SessionDep) -> Lender:
    check_policy(draft, session)
    try:
        return LenderRepository(session).replace(lender_id, draft)
    except IntegrityError:
        raise _has_match_results() from None


@router.delete("/{lender_id}", status_code=204)
def delete_lender(lender_id: UUID, session: SessionDep) -> Response:
    try:
        LenderRepository(session).delete(lender_id)
    except IntegrityError:
        raise _has_match_results() from None
    return Response(status_code=204)
