import json
from collections.abc import Mapping
from decimal import Decimal
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from lender_match.domain.policy import JudgmentQuestionDraft
from lender_match.domain.results import JudgmentAnswer, ProviderCall
from lender_match.enums import JudgmentOutputType
from lender_match.providers._http import log_bad_reply, post_json

_PLACES = Decimal("0.0001")
_SYSTEM = "Reply with JSON only, matching the given schema. No other text."


class _YesNoReply(BaseModel):
    probability_yes: float
    reason: str


class _ChoiceReply(BaseModel):
    probabilities: dict[str, float]
    reason: str


class OpenRouterDecisionProvider:
    """Answers judgment questions with a chat model on OpenRouter."""

    name = "openrouter"

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        timeout_seconds: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.model = model
        self._base_url = base_url
        self._client = httpx.Client(
            timeout=timeout_seconds,
            headers={"Authorization": f"Bearer {api_key}"},
            transport=transport,
        )

    def answer(
        self,
        question: JudgmentQuestionDraft,
        context: Mapping[str, Any],
    ) -> JudgmentAnswer | None:
        yes_no = question.output_type is JudgmentOutputType.yes_no
        options = question.options or []
        if yes_no:
            ask = "Give the probability that the answer is yes, from 0 to 1"
            properties: dict[str, Any] = {"probability_yes": {"type": "number"}}
        else:
            ask = f"Give a probability for each option ({', '.join(options)})"
            properties = {
                "probabilities": {
                    "type": "object",
                    "properties": {o: {"type": "number"} for o in options},
                    "required": options,
                    "additionalProperties": False,
                }
            }
        properties["reason"] = {"type": "string"}
        schema = {
            "type": "object",
            "properties": properties,
            "required": list(properties),
            "additionalProperties": False,
        }
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": _SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"Application:\n{json.dumps(context, default=str)}\n\n"
                        f"Question: {question.question}\n"
                        f"{ask}, and a one-sentence reason."
                    ),
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "answer", "strict": True, "schema": schema},
            },
        }
        reply = post_json(
            self._client, f"{self._base_url}/chat/completions", body, self.model
        )
        if reply is None:
            return None
        data, latency_ms = reply
        try:
            content = data["choices"][0]["message"]["content"].strip()
            content = content.removeprefix("```json").removeprefix("```")
            parsed = json.loads(content.removesuffix("```"))
            if yes_no:
                distribution = _yes_no(_YesNoReply.model_validate(parsed))
            else:
                distribution = _choice(_ChoiceReply.model_validate(parsed), options)
        except (
            KeyError,
            IndexError,
            TypeError,
            AttributeError,
            ValueError,
            ValidationError,
        ):
            log_bad_reply(self.model, "unreadable reply")
            return None
        if distribution is None:
            log_bad_reply(self.model, "invalid probabilities")
            return None
        return JudgmentAnswer(
            distribution=distribution,
            confidence=None,
            call=ProviderCall(
                provider=self.name,
                model=self.model,
                request=body,
                response=data,
                latency_ms=latency_ms,
            ),
        )


def _yes_no(reply: _YesNoReply) -> dict[str, Decimal]:
    p = Decimal(str(min(max(reply.probability_yes, 0.0), 1.0))).quantize(_PLACES)
    return {"yes": p, "no": Decimal(1) - p}


def _choice(reply: _ChoiceReply, options: list[str]) -> dict[str, Decimal] | None:
    values = [reply.probabilities.get(o) for o in options]
    if any(v is None or v < 0 for v in values):
        return None
    total = sum(v for v in values if v is not None)
    if total == 0:
        return None
    return {
        o: Decimal(str(v / total)).quantize(_PLACES)
        for o, v in zip(options, values, strict=True)
        if v is not None
    }
