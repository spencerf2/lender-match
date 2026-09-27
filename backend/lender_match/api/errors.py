"""How errors become HTTP responses."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from lender_match.services.policies import PolicyProblems


def found[T](value: T | None, message: str) -> T:
    """Return the value, or answer 404 when it is None."""
    if value is None:
        raise HTTPException(status_code=404, detail=message)
    return value


def _not_found(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


def _policy_problems(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, PolicyProblems)
    return JSONResponse(status_code=422, content={"problems": exc.problems})


def add_error_handlers(app: FastAPI) -> None:
    # Repositories raise LookupError for a missing id.
    app.add_exception_handler(LookupError, _not_found)
    app.add_exception_handler(PolicyProblems, _policy_problems)
