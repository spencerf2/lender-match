from uuid import UUID

from fastapi import APIRouter

from lender_match.api.deps import SessionDep
from lender_match.api.errors import found
from lender_match.domain.results import LenderResult, MatchRunRecord
from lender_match.repositories.runs import MatchRunRepository

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("/{run_id}")
def get_run(run_id: UUID, session: SessionDep) -> MatchRunRecord:
    return found(MatchRunRepository(session).get(run_id), f"no run with id {run_id}")


@router.get("/{run_id}/results")
def get_results(run_id: UUID, session: SessionDep) -> list[LenderResult]:
    runs = MatchRunRepository(session)
    found(runs.get(run_id), f"no run with id {run_id}")
    return runs.get_results(run_id)
