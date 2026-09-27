from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Response

from lender_match.api.deps import SessionDep
from lender_match.api.errors import found
from lender_match.domain.application import Application, ApplicationDraft
from lender_match.domain.results import MatchRunRecord
from lender_match.enums import ApplicationStatus
from lender_match.repositories.applications import ApplicationRepository
from lender_match.repositories.runs import MatchRunRepository
from lender_match.services.run import execute_run

router = APIRouter(prefix="/applications", tags=["applications"])


def _check_exists(session: SessionDep, application_id: UUID) -> None:
    found(
        ApplicationRepository(session).get(application_id),
        f"no application with id {application_id}",
    )


@router.post("", status_code=201)
def create_application(draft: ApplicationDraft, session: SessionDep) -> Application:
    return ApplicationRepository(session).add(draft, ApplicationStatus.submitted)


@router.get("")
def list_applications(session: SessionDep) -> list[Application]:
    return ApplicationRepository(session).list()


@router.get("/{application_id}")
def get_application(application_id: UUID, session: SessionDep) -> Application:
    return found(
        ApplicationRepository(session).get(application_id),
        f"no application with id {application_id}",
    )


@router.put("/{application_id}")
def update_application(
    application_id: UUID, draft: ApplicationDraft, session: SessionDep
) -> Application:
    return ApplicationRepository(session).update(application_id, draft)


@router.delete("/{application_id}", status_code=204)
def delete_application(application_id: UUID, session: SessionDep) -> Response:
    ApplicationRepository(session).delete(application_id)
    return Response(status_code=204)


@router.post("/{application_id}/runs", status_code=202)
def start_run(
    application_id: UUID, session: SessionDep, background_tasks: BackgroundTasks
) -> MatchRunRecord:
    _check_exists(session, application_id)
    run = MatchRunRepository(session).create(application_id)
    background_tasks.add_task(execute_run, run.id)
    return run


@router.get("/{application_id}/runs")
def list_runs(application_id: UUID, session: SessionDep) -> list[MatchRunRecord]:
    _check_exists(session, application_id)
    return MatchRunRepository(session).list_for_application(application_id)
