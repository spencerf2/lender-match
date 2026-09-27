"""Builds the FastAPI app."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lender_match.api.errors import add_error_handlers
from lender_match.api.routes import (
    applications,
    fields,
    judgment_questions,
    lenders,
    runs,
)
from lender_match.config import get_config


def create_app() -> FastAPI:
    # Read the settings now so a bad one stops startup.
    get_config()
    app = FastAPI(title="Lender Match")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    add_error_handlers(app)
    for module in (applications, runs, lenders, judgment_questions, fields):
        app.include_router(module.router)
    return app


app = create_app()
