"""Checks a lender's criteria against the application fields. This is
not a validator on the policy classes because judgment fields come from
database rows, so the full set of fields is only known at run time.
"""

from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from lender_match.domain.fields import (
    ApplicationFields,
    FieldDefinition,
    FieldType,
    UnknownField,
)
from lender_match.domain.policy import CountAtLeast, CriterionDraft, LenderDraft
from lender_match.domain.values import is_integer, is_number, is_probability
from lender_match.enums import CriterionOperator

_NO_VALUE_OPERATORS = (
    CriterionOperator.is_true,
    CriterionOperator.is_false,
    CriterionOperator.is_null,
)


_NUMBER_CHECKS: dict[FieldType, tuple[Callable[[Any], bool], str]] = {
    FieldType.integer: (is_integer, "a whole number"),
    FieldType.decimal: (is_number, "a number"),
    FieldType.probability: (is_probability, "a number from 0 to 1"),
}


def _value_problem(
    definition: FieldDefinition,
    operator: CriterionOperator,
    value: Any,
) -> str | None:
    """Describe what is wrong with the value for this field. Returns
    None when the value fits.
    """
    if operator in _NO_VALUE_OPERATORS:
        return None if value is None else "this operator takes no value"
    if definition.type is FieldType.enum:
        allowed = definition.values or ()
        unknown = [v for v in value if v not in allowed]
        if unknown:
            return f"unknown values: {', '.join(unknown)}"
        return None
    if definition.type is FieldType.trade_lines:
        try:
            CountAtLeast.model_validate(value)
        except ValidationError:
            return "value is not a valid count_at_least"
        return None
    check, description = _NUMBER_CHECKS[definition.type]
    if operator is CriterionOperator.between:
        if not all(check(v) for v in value):
            return f"both values must be {description}"
        return None
    if not check(value):
        return f"value must be {description}"
    return None


def check_criterion(criterion: CriterionDraft, fields: ApplicationFields) -> list[str]:
    """List what is wrong with the criterion, as plain sentences.
    Returns an empty list when it is fine.
    """
    key = criterion.field
    try:
        definition = fields.get(key)
    except UnknownField:
        return [f"{key}: not an application field"]
    operator = criterion.operator
    if operator not in definition.allowed_operators:
        article = "an" if definition.type[0] in "aeiou" else "a"
        return [
            (
                f"{key}: operator {operator.value} is not allowed for "
                f"{article} {definition.type} field"
            )
        ]
    problem = _value_problem(definition, operator, criterion.value)
    return [f"{key}: {problem}"] if problem else []


def check_lender(lender: LenderDraft, fields: ApplicationFields) -> list[str]:
    """Check every criterion of every program. Each problem starts with
    the program name.
    """
    return [
        f"{program.name}: {problem}"
        for program in lender.programs
        for criterion in program.criteria
        for problem in check_criterion(criterion, fields)
    ]
