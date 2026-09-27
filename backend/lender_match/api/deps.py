"""Dependencies shared by the routes."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from lender_match.db.session import session_scope


def get_session() -> Iterator[Session]:
    """A session per request. Commits on success, rolls back on error,
    and always closes.
    """
    with session_scope() as session:
        yield session


# Function scope commits before the response is sent, so background
# tasks and the client both see the committed rows.
SessionDep = Annotated[Session, Depends(get_session, scope="function")]
