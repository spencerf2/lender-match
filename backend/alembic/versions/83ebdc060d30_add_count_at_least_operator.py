"""add count_at_least operator

Revision ID: 83ebdc060d30
Revises: 9ea4d0c60cf3
Create Date: 2026-09-27 16:20:58.719347

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "83ebdc060d30"
down_revision: str | Sequence[str] | None = "9ea4d0c60cf3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("criteria", "criterion_results")
CONSTRAINT = "ck_{table}_criterion_operator"
OLD_OPERATORS = (
    "gte",
    "lte",
    "between",
    "in",
    "not_in",
    "is_true",
    "is_false",
    "is_null",
)
NEW_OPERATORS = (*OLD_OPERATORS, "count_at_least")


def _operator_check(operators: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{operator}'" for operator in operators)
    return f"operator IN ({quoted})"


def upgrade() -> None:
    """Allow the count_at_least operator."""
    for table in TABLES:
        # op.f marks the name as final, so the naming convention is not
        # applied a second time.
        name = op.f(CONSTRAINT.format(table=table))
        op.drop_constraint(name, table, type_="check")
        op.create_check_constraint(name, table, _operator_check(NEW_OPERATORS))


def downgrade() -> None:
    """Disallow count_at_least. Fails if any row uses it."""
    for table in TABLES:
        name = op.f(CONSTRAINT.format(table=table))
        op.drop_constraint(name, table, type_="check")
        op.create_check_constraint(name, table, _operator_check(OLD_OPERATORS))
