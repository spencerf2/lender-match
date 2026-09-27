from enum import StrEnum


class LenderStatus(StrEnum):
    """Review state of a lender's policy. Draft means extracted and not
    yet reviewed.
    """

    draft = "draft"
    active = "active"
    archived = "archived"


class ApplicationStatus(StrEnum):
    """Whether a broker has submitted an application."""

    draft = "draft"
    submitted = "submitted"


class MatchRunStatus(StrEnum):
    """The step a match run is on, or how it ended."""

    queued = "queued"
    validating = "validating"
    deriving = "deriving"
    matching = "matching"
    ranking = "ranking"
    completed = "completed"
    failed = "failed"
    incomplete = "incomplete"


class CriterionOperator(StrEnum):
    """How a criterion compares a field value to its value."""

    gte = "gte"
    lte = "lte"
    between = "between"
    in_ = "in"
    not_in = "not_in"
    is_true = "is_true"
    is_false = "is_false"
    is_null = "is_null"
    count_at_least = "count_at_least"


class PolicyNoteKind(StrEnum):
    """Why a policy note is not a criterion."""

    unmapped = "unmapped"
    informational = "informational"


class JudgmentOutputType(StrEnum):
    """The shape of a judgment question's answer. Choice also covers
    ordered options.
    """

    yes_no = "yes_no"
    choice = "choice"
