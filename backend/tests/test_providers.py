import json
from decimal import Decimal
from typing import Any

import httpx
import pytest
from pydantic import ValidationError

from lender_match.config import Settings
from lender_match.domain.policy import JudgmentQuestionDraft
from lender_match.enums import JudgmentOutputType
from lender_match.providers import JevDecisionProvider, OpenRouterDecisionProvider
from lender_match.services.providers import decision_provider

ESSENTIAL_USE = JudgmentQuestionDraft(
    key="judgment.essential_use",
    question="Is this equipment essential to the day-to-day operation of this business?",
    output_type=JudgmentOutputType.yes_no,
)
EQUIPMENT_USE = JudgmentQuestionDraft(
    key="judgment.equipment_use",
    question="How is the equipment used?",
    output_type=JudgmentOutputType.choice,
    options=["business", "personal", "mixed"],
)
CONTEXT = {"business": {"industry": "manufacturing"}, "equipment": {"type": "cnc"}}


def _chat_reply(content: str) -> httpx.MockTransport:
    body = {
        "model": "anthropic/claude-sonnet-5",
        "choices": [{"message": {"content": content}}],
    }
    return httpx.MockTransport(lambda request: httpx.Response(200, json=body))


def _openrouter(transport: httpx.BaseTransport) -> OpenRouterDecisionProvider:
    return OpenRouterDecisionProvider(
        model="anthropic/claude-sonnet-5", api_key="test", transport=transport
    )


def test_a_yes_no_reply_becomes_a_yes_and_no_distribution():
    reply = json.dumps({"probability_yes": 0.82, "reason": "Runs daily."})
    answer = _openrouter(_chat_reply(reply)).answer(ESSENTIAL_USE, CONTEXT)

    assert answer is not None
    assert answer.distribution == {"yes": Decimal("0.82"), "no": Decimal("0.18")}
    assert answer.confidence is None


def test_a_choice_reply_is_normalized_so_its_probabilities_sum_to_one():
    reply = json.dumps(
        {
            "probabilities": {"business": 2, "personal": 1, "mixed": 1},
            "reason": "Mostly business.",
        }
    )
    answer = _openrouter(_chat_reply(reply)).answer(EQUIPMENT_USE, CONTEXT)

    assert answer is not None
    assert answer.distribution == {
        "business": Decimal("0.5"),
        "personal": Decimal("0.25"),
        "mixed": Decimal("0.25"),
    }


def test_a_reply_that_is_not_json_yields_no_answer_instead_of_an_error():
    answer = _openrouter(_chat_reply("I think yes.")).answer(ESSENTIAL_USE, CONTEXT)

    assert answer is None


def test_a_network_error_is_retried_once_and_then_yields_no_answer():
    attempts: list[Any] = []

    def fail(request: httpx.Request) -> httpx.Response:
        attempts.append(request)
        raise httpx.ConnectError("down", request=request)

    answer = _openrouter(httpx.MockTransport(fail)).answer(ESSENTIAL_USE, CONTEXT)

    assert answer is None
    assert len(attempts) == 2


def test_the_jev_adapter_maps_a_noul_reply_to_a_yes_no_distribution():
    # Shape observed from OpenRouter's /systemone on 2026-09-27.
    body = {
        "model": "typesafe/jev-1.13-20260917",
        "answers": {"q": {"type": "noul", "noul": 0.92}},
        "usage": {"input_tokens": 387, "output_tokens": 54},
    }
    provider = JevDecisionProvider(
        api_key="test",
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=body)),
    )

    answer = provider.answer(ESSENTIAL_USE, CONTEXT)

    assert answer is not None
    assert answer.distribution == {"yes": Decimal("0.92"), "no": Decimal("0.08")}
    assert answer.confidence is None
    assert answer.call is not None
    assert answer.call.model == "typesafe/jev-1.13-20260917"


def test_a_real_provider_is_refused_when_no_key_is_configured():
    config = Settings(
        database_url="postgresql://unused",
        decision_provider="openrouter",
        openrouter_api_key=None,
    )

    with pytest.raises(ValueError, match="OPENROUTER_API_KEY is not set"):
        decision_provider(config)


def test_config_rejects_an_unknown_decision_provider():
    with pytest.raises(ValidationError):
        Settings(database_url="postgresql://unused", decision_provider="magic")  # pyright: ignore[reportArgumentType]
