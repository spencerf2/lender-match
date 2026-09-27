"""The command line for the common operations."""

import argparse
import json

from lender_match import seeding
from lender_match.db.session import session_scope
from lender_match.domain.policy import JudgmentQuestionDraft, LenderDraft
from lender_match.paths import SEEDS_DIR


def schema(args: argparse.Namespace) -> None:
    """Write the JSON Schemas for seed files to seeds/schema/."""
    schema_dir = SEEDS_DIR / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    for file_name, model in (
        ("lender-draft.json", LenderDraft),
        ("judgment-question-draft.json", JudgmentQuestionDraft),
    ):
        path = schema_dir / file_name
        path.write_text(json.dumps(model.model_json_schema(), indent=2) + "\n")
        print(path)


def seed(args: argparse.Namespace) -> None:
    """Load the seed judgment questions and lenders."""
    with session_scope() as session:
        summary = seeding.seed(session)
    print(f"judgment questions: {summary.judgment_questions}")
    print(f"lenders: {summary.lenders}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="lender_match")
    subparsers = parser.add_subparsers(required=True)
    subparsers.add_parser(
        "schema", help="write the JSON Schemas for seed files"
    ).set_defaults(handler=schema)
    subparsers.add_parser(
        "seed", help="load the seed files into the database"
    ).set_defaults(handler=seed)
    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
