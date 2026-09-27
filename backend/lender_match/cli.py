"""The command line for the common operations."""

import argparse
import json
from pathlib import Path

from lender_match.domain.policy import JudgmentQuestionDraft, LenderDraft

SEEDS_DIR = Path(__file__).resolve().parents[1] / "seeds"


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


def main() -> None:
    parser = argparse.ArgumentParser(prog="lender_match")
    subparsers = parser.add_subparsers(required=True)
    subparsers.add_parser(
        "schema", help="write the JSON Schemas for seed files"
    ).set_defaults(handler=schema)
    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
