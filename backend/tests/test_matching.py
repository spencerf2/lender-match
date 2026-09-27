from datetime import date
from decimal import Decimal
from typing import Any

from lender_match.domain.application import (
    ApplicationDraft,
    BusinessCreditDraft,
    BusinessDraft,
    GuarantorDraft,
    LoanRequestDraft,
)
from lender_match.domain.fields import application_fields
from lender_match.domain.matching import (
    choose_best_program,
    evaluate_criterion,
    evaluate_lender,
    evaluate_program,
    fit_score,
    judgment_keys_needed,
    rank_lenders,
    resolve_judgment,
)
from lender_match.domain.policy import (
    CriterionDraft,
    JudgmentQuestionDraft,
    LenderDraft,
    ProgramDraft,
    RateBand,
)
from lender_match.domain.results import (
    CriterionResult,
    JudgmentAnswer,
    LenderResult,
    ProgramResult,
)
from lender_match.enums import CriterionOperator, JudgmentOutputType

AS_OF = date(2026, 9, 27)
LOAN_AMOUNT = Decimal(50000)

ESSENTIAL_USE = JudgmentQuestionDraft(
    key="judgment.essential_use",
    question="Is this equipment essential to running the business?",
    output_type=JudgmentOutputType.yes_no,
    yes_threshold=Decimal("0.7"),
)
MEDICAL_CATEGORY = JudgmentQuestionDraft(
    key="judgment.medical_category",
    question="What kind of medical practice is this?",
    output_type=JudgmentOutputType.choice,
    options=["general", "aesthetic", "dental"],
)
FIELDS = application_fields([ESSENTIAL_USE, MEDICAL_CATEGORY])


def _field_values(**overrides: Any) -> dict[str, Any]:
    """Built-in field values for a typical applicant, with overrides
    by field key (dots written as double underscores).
    """
    application = ApplicationDraft(
        business=BusinessDraft(
            industry="trucking",
            state="TX",
            founded_date=date(2020, 1, 1),
            annual_revenue=Decimal(500000),
        ),
        guarantors=[GuarantorDraft(fico=600)],
        business_credit=BusinessCreditDraft(paynet_score=650),
        loan_request=LoanRequestDraft(
            amount=LOAN_AMOUNT,
            term_months=36,
            equipment_type="class_8_truck",
            equipment_year=2022,
        ),
    )
    values: dict[str, Any] = application.built_in_field_values(as_of=AS_OF)
    for key, value in overrides.items():
        values[key.replace("__", ".")] = value
    return values


def _hard(field: str, operator: CriterionOperator, value: Any = None):
    return CriterionDraft(field=field, operator=operator, value=value, hard=True)


def _soft(
    field: str,
    operator: CriterionOperator,
    value: Any = None,
    weight: Decimal | None = None,
):
    return CriterionDraft(
        field=field, operator=operator, value=value, hard=False, weight=weight
    )


def _result(hard: bool, passed: bool | None) -> CriterionResult:
    return CriterionResult(
        field="guarantor.min_fico",
        operator=CriterionOperator.gte,
        value=700,
        hard=hard,
        weight=None if hard else Decimal("0.5"),
        actual_value=720,
        passed=passed,
        explanation="",
    )


def _explanation(criterion: CriterionDraft, **overrides: Any) -> str:
    result = evaluate_criterion(criterion, _field_values(**overrides), FIELDS)
    assert result.passed is False
    return result.explanation


GTE = CriterionOperator.gte
FICO_580 = _hard("guarantor.min_fico", GTE, 580)


def test_applicant_below_the_fico_floor_fails_that_criterion_with_the_reason():
    criterion = _hard("guarantor.min_fico", GTE, 700)

    result = evaluate_criterion(criterion, _field_values(), FIELDS)

    assert result.passed is False
    assert result.actual_value == 600
    assert result.field == "guarantor.min_fico"
    assert result.operator is GTE
    assert result.value == 700
    assert result.hard is True
    assert result.explanation == (
        "Minimum FICO across guarantors must be at least 700. Applicant has 600."
    )


def test_a_failed_hard_criterion_makes_the_program_ineligible():
    program = ProgramDraft(
        name="Tier 1",
        criteria=[
            _hard("guarantor.min_fico", GTE, 700),
            _soft("business_credit.paynet", GTE, 600),
        ],
    )

    result = evaluate_program(program, _field_values(), FIELDS, LOAN_AMOUNT)

    assert result.eligible is False
    assert result.hard_failures == 1
    assert result.fit_score == 33


def test_a_failed_soft_criterion_only_lowers_the_fit_score():
    program = ProgramDraft(
        name="Tier 1",
        criteria=[FICO_580, _soft("business_credit.paynet", GTE, 700)],
    )

    result = evaluate_program(program, _field_values(), FIELDS, LOAN_AMOUNT)

    assert result.eligible is True
    assert result.hard_failures == 0
    assert result.fit_score == 67


def test_fit_score_is_the_share_of_criterion_weight_that_passed():
    all_hard_one_soft = [_result(True, True)] * 6 + [
        _result(False, True),
        _result(False, False),
    ]
    one_hard_failed_both_soft = (
        [_result(True, True)] * 5 + [_result(True, False)] + [_result(False, True)] * 2
    )
    with_one_not_evaluated = [*all_hard_one_soft, _result(True, None)]

    assert fit_score(all_hard_one_soft) == 93
    assert fit_score(one_hard_failed_both_soft) == 86
    assert fit_score(with_one_not_evaluated) == 93


def test_a_missing_paynet_score_fails_a_paynet_criterion_as_not_provided():
    criterion = _hard("business_credit.paynet", GTE, 650)

    result = evaluate_criterion(
        criterion, _field_values(business_credit__paynet=None), FIELDS
    )

    assert result.passed is False
    assert result.actual_value is None
    assert result.explanation == "PayNet score not provided."


def test_no_bankruptcy_on_record_passes_a_bankruptcy_lookback():
    criterion = _hard("guarantor.years_since_bankruptcy", GTE, 4)
    values = _field_values()
    assert values["guarantor.years_since_bankruptcy"] is None

    result = evaluate_criterion(criterion, values, FIELDS)

    assert result.passed is True
    assert result.explanation == ("No bankruptcy on record.")


def test_an_excluded_state_fails_with_the_states_named():
    criterion = _hard("business.state", CriterionOperator.not_in, ["CA", "NV"])

    result = evaluate_criterion(criterion, _field_values(business__state="NV"), FIELDS)

    assert result.passed is False
    assert result.explanation == "State must not be one of: CA, NV. Applicant: NV."


def _band(low: str, high: str, rate: str) -> RateBand:
    return RateBand(
        min_amount=Decimal(low), max_amount=Decimal(high), rate_pct=Decimal(rate)
    )


def test_between_two_eligible_programs_with_equal_fit_the_lower_rate_wins():
    # Alpha's cheapest band does not cover the loan amount, so its
    # rate for this loan is 8.0, above Cheaper's 7.0. The later
    # tiebreaks both favor Alpha: rank 1 beats rank 2, and "Alpha"
    # sorts before "Cheaper" alphabetically. So only the rate
    # comparison can pick Cheaper, which proves rate is checked first.
    cheaper = ProgramDraft(
        name="Cheaper",
        rank=2,
        criteria=[FICO_580],
        rates=[_band("0", "100000", "7.0")],
    )
    pricier = ProgramDraft(
        name="Alpha",
        rank=1,
        criteria=[FICO_580],
        rates=[_band("0", "25000", "6.0"), _band("25000.01", "100000", "8.0")],
    )
    values = _field_values()
    results = [
        evaluate_program(program, values, FIELDS, LOAN_AMOUNT)
        for program in (pricier, cheaper)
    ]

    best = choose_best_program(results)

    assert best is not None
    assert best.program_name == "Cheaper"
    assert best.estimated_rate_pct == Decimal("7.0")
    assert results[0].estimated_rate_pct == Decimal("8.0")


def test_rank_breaks_a_tie_when_fit_and_rate_are_equal():
    rates = [_band("0", "100000", "7.0")]
    first_by_name = ProgramDraft(name="Alpha", rank=2, criteria=[FICO_580], rates=rates)
    first_by_rank = ProgramDraft(name="Bravo", rank=1, criteria=[FICO_580], rates=rates)
    values = _field_values()
    results = [
        evaluate_program(program, values, FIELDS, LOAN_AMOUNT)
        for program in (first_by_name, first_by_rank)
    ]

    best = choose_best_program(results)

    assert best is not None
    assert best.program_name == "Bravo"


def test_when_no_program_is_eligible_the_fewest_hard_failures_is_chosen_and_its_failures_are_the_reasons():
    # The applicant has FICO 600, PayNet 650, revenue 500,000.
    # "Two hard failures" fails both hard criteria. Its soft criterion
    # passes and carries weight 3, so 3 of the 5 total weight passed:
    # fit 60.
    two_failures = ProgramDraft(
        name="Two hard failures",
        criteria=[
            _hard("guarantor.min_fico", GTE, 720),
            _hard("business_credit.paynet", GTE, 700),
            _soft("business.annual_revenue", GTE, 100000, weight=Decimal(3)),
        ],
    )
    # "One hard failure" fails one hard criterion and passes the other,
    # so 1 of 2 total weight passed: fit 50. It has the lower fit score
    # but the fewer hard failures, so it is chosen, and its one failure
    # is the rejection reason.
    one_failure = ProgramDraft(
        name="One hard failure",
        criteria=[
            _hard("guarantor.min_fico", GTE, 700),
            _hard("business_credit.paynet", GTE, 600),
        ],
    )
    lender = LenderDraft(name="Stearns", programs=[two_failures, one_failure])

    result = evaluate_lender(lender, _field_values(), FIELDS, LOAN_AMOUNT)

    assert result.eligible is False
    assert result.best_program is not None
    assert result.best_program.program_name == "One hard failure"
    assert result.fit_score == 50
    assert result.rejection_reasons == [
        "Minimum FICO across guarantors must be at least 700. Applicant has 600."
    ]
    assert [p.program_name for p in result.programs] == [
        "Two hard failures",
        "One hard failure",
    ]
    assert result.position is None


def _lender_result(name: str, eligible: bool, fit: int) -> LenderResult:
    program = ProgramResult(
        program_name="Only",
        rank=None,
        eligible=eligible,
        fit_score=fit,
        hard_failures=0 if eligible else 1,
        criteria=[],
        estimated_rate_pct=Decimal("7.0"),
    )
    return LenderResult(
        lender_name=name,
        eligible=eligible,
        best_program=program,
        fit_score=fit,
        rejection_reasons=[] if eligible else ["reason"],
        programs=[program],
        position=None,
    )


def test_eligible_lenders_rank_above_ineligible_ones_regardless_of_fit_score():
    results = [
        _lender_result("Alpha", eligible=True, fit=60),
        _lender_result("Bravo", eligible=False, fit=95),
        _lender_result("Charlie", eligible=True, fit=80),
        _lender_result("Delta", eligible=False, fit=40),
    ]

    ranked = rank_lenders(results)

    assert [r.lender_name for r in ranked] == ["Charlie", "Alpha", "Bravo", "Delta"]
    assert [r.position for r in ranked] == [1, 2, 3, 4]


def test_judgment_questions_are_needed_only_for_programs_that_passed_their_deterministic_hard_criteria():
    passing = ProgramDraft(
        name="Tier 1",
        criteria=[
            FICO_580,
            _hard("judgment.essential_use", CriterionOperator.is_true),
        ],
    )
    failing = ProgramDraft(
        name="Medical",
        criteria=[
            _hard("guarantor.min_fico", GTE, 700),
            _hard(
                "judgment.medical_category",
                CriterionOperator.not_in,
                ["aesthetic"],
            ),
        ],
    )
    programs = [passing, failing]
    values = _field_values()
    results = [
        evaluate_program(program, values, FIELDS, LOAN_AMOUNT) for program in programs
    ]

    assert judgment_keys_needed(programs, results) == {"judgment.essential_use"}


def test_a_judgment_criterion_with_no_answer_yet_is_not_evaluated():
    judgment = _hard("judgment.essential_use", CriterionOperator.is_true)
    program = ProgramDraft(name="Tier 1", criteria=[FICO_580, judgment])
    values = _field_values()

    criterion_result = evaluate_criterion(judgment, values, FIELDS)
    program_result = evaluate_program(program, values, FIELDS, LOAN_AMOUNT)

    assert criterion_result.passed is None
    assert criterion_result.actual_value is None
    assert program_result.eligible is True
    assert program_result.hard_failures == 0
    assert program_result.fit_score == 100


def test_a_yes_no_answer_resolves_with_the_questions_threshold():
    below = JudgmentAnswer(
        distribution={"yes": Decimal("0.65"), "no": Decimal("0.35")},
        confidence=None,
    )
    above = JudgmentAnswer(
        distribution={"yes": Decimal("0.75"), "no": Decimal("0.25")},
        confidence=None,
    )

    assert resolve_judgment(ESSENTIAL_USE, below) == {
        "judgment.essential_use": False,
        "judgment.essential_use_probability": Decimal("0.65"),
    }
    assert resolve_judgment(ESSENTIAL_USE, above) == {
        "judgment.essential_use": True,
        "judgment.essential_use_probability": Decimal("0.75"),
    }


def test_a_choice_answer_resolves_to_the_most_likely_option():
    answer = JudgmentAnswer(
        distribution={
            "general": Decimal("0.2"),
            "aesthetic": Decimal("0.5"),
            "dental": Decimal("0.3"),
        },
        confidence=Decimal("0.9"),
    )

    assert resolve_judgment(MEDICAL_CATEGORY, answer) == {
        "judgment.medical_category": "aesthetic"
    }


def test_count_at_least_is_reported_as_not_evaluated():
    trade_lines = _hard(
        "business_credit.trade_lines",
        CriterionOperator.count_at_least,
        {"count": 2, "min_amount": 10000, "active_within_months": 24},
    )
    program = ProgramDraft(name="Tier 1", criteria=[FICO_580, trade_lines])
    values = _field_values()

    criterion_result = evaluate_criterion(trade_lines, values, FIELDS)
    program_result = evaluate_program(program, values, FIELDS, LOAN_AMOUNT)

    assert criterion_result.passed is None
    assert program_result.eligible is True
    assert program_result.fit_score == 100


def test_explanations_print_money_and_percent_in_their_format():
    revenue = _hard("business.annual_revenue", GTE, Decimal(75000))
    ratio = _hard("business_credit.comparable_credit_ratio", GTE, Decimal("0.7"))
    amount = _hard(
        "loan.amount",
        CriterionOperator.between,
        [Decimal(10000), Decimal(500000)],
    )

    assert _explanation(revenue, business__annual_revenue=Decimal(50000)) == (
        "Annual revenue must be at least $75,000. Applicant has $50,000."
    )
    assert _explanation(
        ratio, business_credit__comparable_credit_ratio=Decimal("0.5")
    ) == (
        "Largest prior loan as a share of the requested amount must be at "
        "least 70%. Applicant has 50%."
    )
    assert _explanation(amount, loan__amount=Decimal(5000)) == (
        "Requested amount must be between $10,000 and $500,000. Applicant has $5,000."
    )
