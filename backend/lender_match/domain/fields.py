"""The application fields: every field a criterion can test, with its
type.

A field's value comes from the application form, from arithmetic over
form fields, or from Jev answering a judgment question. Criteria may
only reference application fields. Form and derived fields are
built-in fields, defined here in code. Judgment fields are built from
judgment question rows at run time by `application_fields`.
"""

from collections.abc import Iterable
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from lender_match.domain.policy import JudgmentQuestionDraft
from lender_match.enums import CriterionOperator, JudgmentOutputType


class FieldType(StrEnum):
    integer = "integer"
    decimal = "decimal"
    boolean = "boolean"
    enum = "enum"
    probability = "probability"
    trade_lines = "trade_lines"


class FieldSource(StrEnum):
    form = "form"
    derived = "derived"
    judgment = "judgment"


class FieldFormat(StrEnum):
    """How a value prints in explanation text."""

    number = "number"
    money = "money"
    percent = "percent"
    years = "years"
    text = "text"


_OPERATORS_BY_TYPE: dict[FieldType, tuple[CriterionOperator, ...]] = {
    FieldType.integer: (
        CriterionOperator.gte,
        CriterionOperator.lte,
        CriterionOperator.between,
    ),
    FieldType.decimal: (
        CriterionOperator.gte,
        CriterionOperator.lte,
        CriterionOperator.between,
    ),
    FieldType.probability: (CriterionOperator.gte, CriterionOperator.lte),
    FieldType.boolean: (CriterionOperator.is_true, CriterionOperator.is_false),
    FieldType.enum: (CriterionOperator.in_, CriterionOperator.not_in),
    FieldType.trade_lines: (CriterionOperator.count_at_least,),
}


class FieldDefinition(BaseModel):
    """One field a criterion can test."""

    model_config = ConfigDict(frozen=True)

    key: str = Field(pattern=r"^[a-z_]+\.[a-z_]+$")
    label: str
    type: FieldType
    source: FieldSource
    nullable: bool = False
    required: bool = False
    # A null value passes every comparison. For fields where having no
    # value is the good outcome, such as years since bankruptcy when
    # there was none.
    null_passes: bool = False
    values: tuple[str, ...] | None = None
    format: FieldFormat = FieldFormat.number

    @model_validator(mode="after")
    def _check_consistency(self) -> "FieldDefinition":
        if self.type is FieldType.enum and not self.values:
            raise ValueError(f"{self.key}: enum fields need values")
        if self.type is not FieldType.enum and self.values is not None:
            raise ValueError(f"{self.key}: only enum fields take values")
        if self.null_passes and not self.nullable:
            raise ValueError(f"{self.key}: null_passes needs nullable")
        return self

    @property
    def allowed_operators(self) -> tuple[CriterionOperator, ...]:
        operators = _OPERATORS_BY_TYPE[self.type]
        if self.nullable:
            return (*operators, CriterionOperator.is_null)
        return operators


US_STATES: tuple[str, ...] = (
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI", "ID", "IL",
    "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE",
    "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD",
    "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
)  # fmt: skip

INDUSTRIES: tuple[str, ...] = (
    "trucking",
    "logging",
    "construction",
    "manufacturing",
    "medical",
    "automotive_repair",
    "landscaping",
    "commercial_cleaning",
    "waste_management",
    "restaurant",
    "agriculture",
    "oil_and_gas",
    "cannabis",
    "gambling",
    "adult_entertainment",
    "firearms",
    "real_estate",
    "money_services",
    "beauty_salon",
    "tattoo_piercing",
    "car_wash",
    "religious_or_nonprofit",
    "hazmat",
    "other",
)

EQUIPMENT_TYPES: tuple[str, ...] = (
    "class_8_truck",
    "class_8_trailer",
    "reefer_trailer",
    "dump_truck",
    "medium_duty_truck",
    "light_duty_truck",
    "vocational_truck",
    "construction_equipment",
    "forklift",
    "machine_tool",
    "industrial_machinery",
    "medical_equipment",
    "automotive_repair_equipment",
    "restaurant_equipment",
    "office_equipment",
    "janitorial_equipment",
    "lawn_and_turf_equipment",
    "farm_equipment",
    "audio_visual_equipment",
    "electric_vehicle",
    "aircraft",
    "boat",
    "atm",
    "kiosk",
    "furniture",
    "signage",
    "tanning_bed",
    "software",
    "leasehold_improvements",
    "other",
)


# A derived field is a parameter-free fact about the application. A
# lender's numbers belong in the criterion value, never in a field. When
# a rule needs more than one number, give the operator a structured
# value, as `count_at_least` does, instead of adding a field per lender.
BUILT_IN_FIELDS: tuple[FieldDefinition, ...] = (
    # Guarantors. Several guarantors combine by the rule in the label.
    FieldDefinition(
        key="guarantor.min_fico",
        label="Minimum FICO across guarantors",
        type=FieldType.integer,
        source=FieldSource.derived,
        required=True,
    ),
    FieldDefinition(
        key="guarantor.is_homeowner",
        label="Every guarantor is a homeowner",
        type=FieldType.boolean,
        source=FieldSource.derived,
    ),
    FieldDefinition(
        key="guarantor.is_us_citizen",
        label="Every guarantor is a US citizen",
        type=FieldType.boolean,
        source=FieldSource.derived,
    ),
    FieldDefinition(
        key="guarantor.has_judgments",
        label="Any guarantor has a judgment on record",
        type=FieldType.boolean,
        source=FieldSource.derived,
    ),
    FieldDefinition(
        key="guarantor.has_foreclosures",
        label="Any guarantor has a foreclosure on record",
        type=FieldType.boolean,
        source=FieldSource.derived,
    ),
    FieldDefinition(
        key="guarantor.has_repossessions",
        label="Any guarantor has a repossession on record",
        type=FieldType.boolean,
        source=FieldSource.derived,
    ),
    FieldDefinition(
        key="guarantor.years_since_bankruptcy",
        label="Years since the most recent bankruptcy discharge",
        type=FieldType.decimal,
        source=FieldSource.derived,
        nullable=True,
        null_passes=True,
        format=FieldFormat.years,
    ),
    # Business credit
    FieldDefinition(
        key="business_credit.paynet",
        label="PayNet score",
        type=FieldType.integer,
        source=FieldSource.form,
        nullable=True,
    ),
    FieldDefinition(
        key="business_credit.comparable_credit_ratio",
        label="Largest prior loan as a share of the requested amount",
        type=FieldType.decimal,
        source=FieldSource.derived,
        nullable=True,
        format=FieldFormat.percent,
    ),
    FieldDefinition(
        key="business_credit.trade_lines",
        label="Trade lines",
        type=FieldType.trade_lines,
        source=FieldSource.form,
        format=FieldFormat.text,
    ),
    # Business
    FieldDefinition(
        key="business.years_in_business",
        label="Years in business",
        type=FieldType.decimal,
        source=FieldSource.derived,
        nullable=True,
        format=FieldFormat.years,
    ),
    FieldDefinition(
        key="business.state",
        label="State",
        type=FieldType.enum,
        source=FieldSource.form,
        required=True,
        values=US_STATES,
        format=FieldFormat.text,
    ),
    FieldDefinition(
        key="business.industry",
        label="Industry",
        type=FieldType.enum,
        source=FieldSource.form,
        required=True,
        values=INDUSTRIES,
        format=FieldFormat.text,
    ),
    FieldDefinition(
        key="business.annual_revenue",
        label="Annual revenue",
        type=FieldType.decimal,
        source=FieldSource.form,
        nullable=True,
        format=FieldFormat.money,
    ),
    # Loan request
    FieldDefinition(
        key="loan.amount",
        label="Requested amount",
        type=FieldType.decimal,
        source=FieldSource.form,
        required=True,
        format=FieldFormat.money,
    ),
    FieldDefinition(
        key="loan.term_months",
        label="Term in months",
        type=FieldType.integer,
        source=FieldSource.form,
        required=True,
    ),
    FieldDefinition(
        key="loan.down_payment_pct",
        label="Down payment as a share of the requested amount",
        type=FieldType.decimal,
        source=FieldSource.derived,
        format=FieldFormat.percent,
    ),
    # Equipment
    FieldDefinition(
        key="equipment.type",
        label="Equipment type",
        type=FieldType.enum,
        source=FieldSource.form,
        required=True,
        values=EQUIPMENT_TYPES,
        format=FieldFormat.text,
    ),
    FieldDefinition(
        key="equipment.age_years",
        label="Equipment age",
        type=FieldType.integer,
        source=FieldSource.derived,
        nullable=True,
        format=FieldFormat.years,
    ),
    FieldDefinition(
        key="equipment.mileage",
        label="Mileage",
        type=FieldType.integer,
        source=FieldSource.form,
        nullable=True,
    ),
    FieldDefinition(
        key="equipment.is_private_party_sale",
        label="Private party sale",
        type=FieldType.boolean,
        source=FieldSource.form,
    ),
)


def judgment_field_definitions(
    question: JudgmentQuestionDraft,
) -> tuple[FieldDefinition, ...]:
    """The application fields one judgment question defines.

    A yes_no question defines two: the bool, and the probability under
    `<key>_probability`. A choice question defines one enum field over
    its options.
    """
    label = question.key.split(".", 1)[1].replace("_", " ")
    if question.output_type is JudgmentOutputType.yes_no:
        return (
            FieldDefinition(
                key=question.key,
                label=label,
                type=FieldType.boolean,
                source=FieldSource.judgment,
            ),
            FieldDefinition(
                key=f"{question.key}_probability",
                label=f"{label} probability",
                type=FieldType.probability,
                source=FieldSource.judgment,
                format=FieldFormat.percent,
            ),
        )
    return (
        FieldDefinition(
            key=question.key,
            label=label,
            type=FieldType.enum,
            source=FieldSource.judgment,
            values=tuple(question.options or ()),
            format=FieldFormat.text,
        ),
    )


class UnknownField(KeyError):
    """A criterion referenced a field not in the application fields."""


class ApplicationFields:
    """Every field the system knows about an application, by key."""

    def __init__(self, definitions: Iterable[FieldDefinition]) -> None:
        self._definitions: dict[str, FieldDefinition] = {}
        for definition in definitions:
            if definition.key in self._definitions:
                raise ValueError(f"duplicate application field: {definition.key}")
            self._definitions[definition.key] = definition

    def get(self, key: str) -> FieldDefinition:
        try:
            return self._definitions[key]
        except KeyError:
            raise UnknownField(key) from None

    def __contains__(self, key: str) -> bool:
        return key in self._definitions

    def definitions(self) -> tuple[FieldDefinition, ...]:
        return tuple(self._definitions.values())

    def required_keys(self) -> tuple[str, ...]:
        return tuple(
            definition.key
            for definition in self._definitions.values()
            if definition.required
        )


def application_fields(
    judgment_questions: Iterable[JudgmentQuestionDraft] = (),
) -> ApplicationFields:
    """Built-in fields plus those the judgment questions define."""
    definitions = list(BUILT_IN_FIELDS)
    for question in judgment_questions:
        definitions.extend(judgment_field_definitions(question))
    return ApplicationFields(definitions)
