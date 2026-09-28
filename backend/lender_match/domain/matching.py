"""Evaluates an application's field values against lender policies."""

from collections.abc import Mapping, Sequence
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from lender_match.domain.fields import (
    ApplicationFields,
    FieldDefinition,
    FieldFormat,
    FieldSource,
)
from lender_match.domain.policy import (
    CriterionDraft,
    JudgmentQuestionDraft,
    LenderDraft,
    ProgramDraft,
)
from lender_match.domain.results import (
    CriterionResult,
    JudgmentAnswer,
    LenderResult,
    ProgramResult,
)
from lender_match.domain.values import to_decimal
from lender_match.enums import CriterionOperator, JudgmentOutputType

_JUDGMENT_PREFIX = "judgment."
_PROBABILITY_SUFFIX = "_probability"


def _plain(number: Decimal) -> str:
    if number == number.to_integral_value():
        return str(int(number))
    return format(number.normalize(), "f")


def _format_value(value: Any, definition: FieldDefinition) -> str:
    """Print one value the way its field's format asks."""
    match definition.format:
        case FieldFormat.money:
            amount = to_decimal(value)
            if amount == amount.to_integral_value():
                return f"${int(amount):,}"
            return f"${amount:,.2f}"
        case FieldFormat.percent:
            return f"{_plain(to_decimal(value) * 100)}%"
        case FieldFormat.years:
            years = to_decimal(value).quantize(Decimal("0.1"), ROUND_HALF_UP)
            return f"{_plain(years)} years"
        case FieldFormat.number:
            return _plain(to_decimal(value))
        case FieldFormat.text:
            return str(value)


def _yes_no(value: Any) -> str:
    return "yes" if value is True else "no"


def _absent_text(definition: FieldDefinition) -> str:
    if definition.absent_text is not None:
        return definition.absent_text
    return f"No {definition.label.lower()} on record."


def _compare(
    criterion: CriterionDraft,
    actual: Any,
    definition: FieldDefinition,
) -> tuple[bool, str]:
    """Apply the operator to a present value. Returns whether it passed
    and the explanation.
    """
    label = definition.label
    value: Any = criterion.value
    op = CriterionOperator
    match criterion.operator:
        case op.gte:
            passed = to_decimal(actual) >= to_decimal(value)
            rule = f"must be at least {_format_value(value, definition)}"
        case op.lte:
            passed = to_decimal(actual) <= to_decimal(value)
            rule = f"must be at most {_format_value(value, definition)}"
        case op.between:
            low, high = value
            passed = to_decimal(low) <= to_decimal(actual) <= to_decimal(high)
            rule = (
                f"must be between {_format_value(low, definition)} "
                f"and {_format_value(high, definition)}"
            )
        case op.in_:
            passed = str(actual) in value
            return passed, (
                f"{label} must be one of: {', '.join(value)}. Applicant: {actual}."
            )
        case op.not_in:
            passed = str(actual) not in value
            return passed, (
                f"{label} must not be one of: {', '.join(value)}. Applicant: {actual}."
            )
        case op.is_true:
            return actual is True, f"{label} is required. Applicant: {_yes_no(actual)}."
        case op.is_false:
            return (
                actual is False,
                f"{label} is not allowed. Applicant: {_yes_no(actual)}.",
            )
        case op.is_null:
            passed = False
            rule = "must be absent"
        case op.count_at_least:
            raise ValueError("count_at_least is not evaluated")
    return passed, (
        f"{label} {rule}. Applicant has {_format_value(actual, definition)}."
    )


def evaluate_criterion(
    criterion: CriterionDraft,
    field_values: Mapping[str, Any],
    fields: ApplicationFields,
) -> CriterionResult:
    """Check one criterion against the field values."""
    definition = fields.get(criterion.field)
    actual = field_values.get(criterion.field)
    passed: bool | None
    if criterion.operator is CriterionOperator.count_at_least:
        passed = None
        explanation = (
            f"{definition.label}: not evaluated. count_at_least is not supported yet"
        )
    elif (
        definition.source is FieldSource.judgment
        and criterion.field not in field_values
    ):
        passed = None
        explanation = f"{definition.label}: not evaluated. no answer yet"
    elif actual is None:
        if definition.null_passes or criterion.operator is CriterionOperator.is_null:
            passed = True
            explanation = _absent_text(definition)
        else:
            passed = False
            explanation = f"{definition.label} not provided."
    else:
        passed, explanation = _compare(criterion, actual, definition)
    return CriterionResult(
        field=criterion.field,
        operator=criterion.operator,
        value=criterion.value,
        hard=criterion.hard,
        weight=criterion.weight,
        actual_value=actual,
        passed=passed,
        explanation=explanation,
    )


def _estimated_rate(
    program: ProgramDraft, loan_amount: Decimal | None
) -> Decimal | None:
    if loan_amount is None:
        return None
    covering = [
        band.rate_pct
        for band in program.rates
        if band.min_amount <= loan_amount
        and (band.max_amount is None or loan_amount <= band.max_amount)
    ]
    return min(covering, default=None)


def evaluate_program(
    program: ProgramDraft,
    field_values: Mapping[str, Any],
    fields: ApplicationFields,
    loan_amount: Decimal | None,
) -> ProgramResult:
    """Check every criterion of one program and score it."""
    results = [
        evaluate_criterion(criterion, field_values, fields)
        for criterion in program.criteria
    ]
    hard_failures = sum(1 for r in results if r.hard and r.passed is False)
    return ProgramResult(
        program_name=program.name,
        rank=program.rank,
        eligible=hard_failures == 0,
        fit_score=fit_score(results),
        hard_failures=hard_failures,
        criteria=results,
        estimated_rate_pct=_estimated_rate(program, loan_amount),
    )


def fit_score(results: Sequence[CriterionResult]) -> int:
    """Share of criterion weight that passed, from 0 to 100."""
    total = Decimal(0)
    passed = Decimal(0)
    for result in results:
        if result.passed is None:
            continue
        weight = Decimal(1) if result.hard else result.weight or Decimal(0)
        total += weight
        if result.passed:
            passed += weight
    if total == 0:
        return 100
    return int((100 * passed / total).quantize(Decimal(1), ROUND_HALF_UP))


def judgment_keys_needed(
    programs: Sequence[ProgramDraft],
    results: Sequence[ProgramResult],
) -> set[str]:
    """Judgment field keys referenced by programs whose evaluated hard
    criteria all passed.
    """
    return {
        criterion.field.removesuffix(_PROBABILITY_SUFFIX)
        for program, result in zip(programs, results, strict=True)
        if result.eligible
        for criterion in program.criteria
        if criterion.field.startswith(_JUDGMENT_PREFIX)
    }


def resolve_judgment(
    question: JudgmentQuestionDraft,
    answer: JudgmentAnswer,
) -> dict[str, Any]:
    """The field values one judgment answer produces."""
    if question.output_type is JudgmentOutputType.yes_no:
        probability = answer.distribution["yes"]
        threshold = question.yes_threshold or Decimal("0.5")
        return {
            question.key: probability >= threshold,
            f"{question.key}{_PROBABILITY_SUFFIX}": probability,
        }
    distribution = answer.distribution
    return {question.key: max(distribution, key=lambda k: distribution[k])}


def _last_when_none(value: Decimal | int | None) -> tuple[bool, Decimal | int]:
    return (value is None, value if value is not None else 0)


def choose_best_program(
    results: Sequence[ProgramResult],
) -> ProgramResult | None:
    """Pick the program that represents the lender."""
    eligible = [r for r in results if r.eligible]
    if eligible:
        return min(
            eligible,
            key=lambda r: (
                -r.fit_score,
                _last_when_none(r.estimated_rate_pct),
                _last_when_none(r.rank),
                r.program_name,
            ),
        )
    return min(
        results,
        key=lambda r: (
            r.hard_failures,
            -r.fit_score,
            _last_when_none(r.rank),
            r.program_name,
        ),
        default=None,
    )


def evaluate_lender(
    lender: LenderDraft,
    field_values: Mapping[str, Any],
    fields: ApplicationFields,
    loan_amount: Decimal | None,
) -> LenderResult:
    """Evaluate every program of one lender and pick the best."""
    programs = [
        evaluate_program(program, field_values, fields, loan_amount)
        for program in lender.programs
    ]
    best = choose_best_program(programs)
    eligible = best is not None and best.eligible
    rejection_reasons = (
        []
        if best is None or eligible
        else [c.explanation for c in best.criteria if c.hard and c.passed is False]
    )
    return LenderResult(
        lender_name=lender.name,
        eligible=eligible,
        best_program=best,
        fit_score=best.fit_score if best is not None else 0,
        rejection_reasons=rejection_reasons,
        programs=programs,
        position=None,
    )


def _lender_rate(result: LenderResult) -> Decimal | None:
    if result.best_program is None:
        return None
    return result.best_program.estimated_rate_pct


def rank_lenders(results: Sequence[LenderResult]) -> list[LenderResult]:
    """Order lender results and set their positions from 1."""
    eligible = sorted(
        (r for r in results if r.eligible),
        key=lambda r: (
            -r.fit_score,
            _last_when_none(_lender_rate(r)),
            r.lender_name,
        ),
    )
    ineligible = sorted(
        (r for r in results if not r.eligible),
        key=lambda r: (-r.fit_score, r.lender_name),
    )
    return [
        result.model_copy(update={"position": position})
        for position, result in enumerate([*eligible, *ineligible], start=1)
    ]
