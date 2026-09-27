from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from lender_match import db
from lender_match.domain.application import Application, ApplicationDraft
from lender_match.enums import ApplicationStatus

_LOAD_FORM = (
    selectinload(db.Application.business),
    selectinload(db.Application.guarantors),
    selectinload(db.Application.business_credit),
    selectinload(db.Application.trade_lines),
    selectinload(db.Application.loan_request),
)


def _write_form(row: db.Application, draft: ApplicationDraft) -> None:
    """Build the application's child rows from the draft."""
    row.submitted_by = draft.submitted_by
    row.business = db.Business(**draft.business.model_dump())
    row.guarantors = [db.Guarantor(**g.model_dump()) for g in draft.guarantors]
    row.business_credit = db.BusinessCredit(**draft.business_credit.model_dump())
    row.trade_lines = [db.TradeLine(**t.model_dump()) for t in draft.trade_lines]
    row.loan_request = db.LoanRequest(**draft.loan_request.model_dump())


class ApplicationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, draft: ApplicationDraft, status: ApplicationStatus) -> Application:
        row = db.Application(status=status)
        _write_form(row, draft)
        self._session.add(row)
        self._session.flush()
        return Application.model_validate(row)

    def get(self, application_id: UUID) -> Application | None:
        row = self._session.get(db.Application, application_id, options=_LOAD_FORM)
        return Application.model_validate(row) if row is not None else None

    def update(self, application_id: UUID, draft: ApplicationDraft) -> Application:
        row = self._get_row(application_id)
        row.business = None
        row.guarantors.clear()
        row.business_credit = None
        row.trade_lines.clear()
        row.loan_request = None
        # Delete the old rows before inserting the new ones, or the
        # unique application_id on the one-per-application tables
        # rejects the insert.
        self._session.flush()
        _write_form(row, draft)
        self._session.flush()
        return Application.model_validate(row)

    def delete(self, application_id: UUID) -> None:
        self._session.delete(self._get_row(application_id))
        self._session.flush()

    def list(self) -> list[Application]:
        query = (
            select(db.Application)
            .options(*_LOAD_FORM)
            .order_by(db.Application.created_at.desc())
        )
        return [Application.model_validate(row) for row in self._session.scalars(query)]

    def _get_row(self, application_id: UUID) -> db.Application:
        row = self._session.get(db.Application, application_id, options=_LOAD_FORM)
        if row is None:
            raise LookupError(f"no application with id {application_id}")
        return row
