from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from lender_match import db
from lender_match.domain.policy import (
    Criterion,
    Lender,
    LenderContact,
    LenderDraft,
    PolicyNote,
    Program,
    RateBand,
)
from lender_match.enums import LenderStatus
from lender_match.repositories.json_values import to_json_safe

_LOAD_POLICY = (
    selectinload(db.Lender.contacts),
    selectinload(db.Lender.programs).selectinload(db.Program.criteria),
    selectinload(db.Lender.programs).selectinload(db.Program.rate_bands),
    selectinload(db.Lender.policy_notes).selectinload(db.PolicyNote.program),
)


def program_sort_key(program: db.Program) -> tuple[bool, int, str]:
    """Ranked programs first, then by name."""
    return (program.rank is None, program.rank or 0, program.name)


def _to_program(row: db.Program) -> Program:
    return Program.model_validate(
        {
            "id": row.id,
            "name": row.name,
            "rank": row.rank,
            "app_only_max_amount": row.app_only_max_amount,
            "notes": row.notes,
            "criteria": [
                Criterion.model_validate(c)
                for c in sorted(row.criteria, key=lambda c: c.position)
            ],
            "rates": [RateBand.model_validate(b) for b in row.rate_bands],
        }
    )


def _to_lender(row: db.Lender) -> Lender:
    # Three names differ between the row and the domain: policy_notes
    # versus notes, rate_bands versus rates, and a note's program is a
    # row here but a name in the domain. So build a dict rather than
    # validating the row directly.
    return Lender.model_validate(
        {
            "id": row.id,
            "name": row.name,
            "source_effective_date": row.source_effective_date,
            "status": row.status,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "contacts": [LenderContact.model_validate(c) for c in row.contacts],
            "programs": [
                _to_program(p) for p in sorted(row.programs, key=program_sort_key)
            ],
            "notes": [
                PolicyNote(
                    kind=n.kind,
                    text=n.text,
                    program=n.program.name if n.program is not None else None,
                )
                for n in row.policy_notes
            ],
        }
    )


def _write_policy(row: db.Lender, draft: LenderDraft) -> None:
    """Build the lender's contacts, programs, and notes."""
    row.contacts = [db.LenderContact(**c.model_dump()) for c in draft.contacts]
    programs = {
        p.name: db.Program(
            name=p.name,
            rank=p.rank,
            app_only_max_amount=p.app_only_max_amount,
            notes=p.notes,
            criteria=[
                db.Criterion(
                    field=c.field,
                    operator=c.operator,
                    value=to_json_safe(c.value),
                    hard=c.hard,
                    weight=c.weight,
                    source_quote=c.source_quote,
                    position=c.position,
                )
                for c in p.criteria
            ],
            rate_bands=[db.RateBand(**b.model_dump()) for b in p.rates],
        )
        for p in draft.programs
    }
    row.programs = list(programs.values())
    row.policy_notes = [
        db.PolicyNote(
            kind=n.kind,
            text=n.text,
            program=programs[n.program] if n.program is not None else None,
        )
        for n in draft.notes
    ]


class LenderRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, draft: LenderDraft, status: LenderStatus) -> Lender:
        row = db.Lender(
            name=draft.name,
            source_effective_date=draft.source_effective_date,
            status=status,
        )
        _write_policy(row, draft)
        self._session.add(row)
        self._session.flush()
        return _to_lender(row)

    def get(self, lender_id: UUID) -> Lender | None:
        row = self._session.get(db.Lender, lender_id, options=_LOAD_POLICY)
        return _to_lender(row) if row is not None else None

    def get_by_name(self, name: str) -> Lender | None:
        row = self._session.scalar(
            select(db.Lender).where(db.Lender.name == name).options(*_LOAD_POLICY)
        )
        return _to_lender(row) if row is not None else None

    def replace(self, lender_id: UUID, draft: LenderDraft) -> Lender:
        row = self._get_row(lender_id)
        row.name = draft.name
        row.source_effective_date = draft.source_effective_date
        row.contacts.clear()
        row.programs.clear()
        row.policy_notes.clear()
        # Delete the old rows before inserting the new ones, or the
        # unique (lender_id, name) on programs rejects the insert.
        self._session.flush()
        _write_policy(row, draft)
        self._session.flush()
        return _to_lender(row)

    def delete(self, lender_id: UUID) -> None:
        self._session.delete(self._get_row(lender_id))
        self._session.flush()

    def list(self, status: LenderStatus | None = None) -> list[Lender]:
        query = select(db.Lender).options(*_LOAD_POLICY).order_by(db.Lender.name)
        if status is not None:
            query = query.where(db.Lender.status == status)
        return [_to_lender(row) for row in self._session.scalars(query)]

    def _get_row(self, lender_id: UUID) -> db.Lender:
        row = self._session.get(db.Lender, lender_id, options=_LOAD_POLICY)
        if row is None:
            raise LookupError(f"no lender with id {lender_id}")
        return row
