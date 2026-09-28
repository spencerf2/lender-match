from collections.abc import Mapping
from decimal import Decimal
from typing import Any

import httpx

from lender_match.domain.policy import JudgmentQuestionDraft
from lender_match.domain.results import JudgmentAnswer, ProviderCall
from lender_match.enums import JudgmentOutputType
from lender_match.providers._http import log_bad_reply, post_json

_PLACES = Decimal("0.0001")


class JevDecisionProvider:
    """Answers judgment questions with TypeSafe's Jev through
    OpenRouter's System One endpoint.
    """

    name = "jev"

    def __init__(
        self,
        api_key: str,
        model: str = "typesafe/jev-1.13",
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
        if yes_no:
            jev_question: dict[str, Any] = {
                "type": "noul",
                "instructions": question.question,
            }
        else:
            jev_question = {
                "type": "choice",
                "instructions": question.question,
                "criteria": {option: None for option in question.options or []},
            }
        body = {
            "state": dict(context),
            "model": self.model,
            "questions": {"q": jev_question},
        }
        reply = post_json(self._client, f"{self._base_url}/systemone", body, self.model)
        if reply is None:
            return None
        data, latency_ms = reply
        try:
            answer = data["answers"]["q"]
            if yes_no:
                p = Decimal(str(answer["noul"])).quantize(_PLACES)
                if not 0 <= p <= 1:
                    raise ValueError(p)
                distribution = {"yes": p, "no": Decimal(1) - p}
                confidence = None
            else:
                distribution = {
                    k: Decimal(str(v)).quantize(_PLACES)
                    for k, v in answer["probabilities"].items()
                }
                confidence = Decimal(str(answer["confidence"])).quantize(_PLACES)
        except (KeyError, TypeError, AttributeError, ArithmeticError, ValueError):
            log_bad_reply(self.model, "unreadable reply")
            return None
        model = data.get("model") or self.model
        return JudgmentAnswer(
            distribution=distribution,
            confidence=confidence,
            call=ProviderCall(
                provider=self.name,
                model=model,
                request=body,
                response=data,
                latency_ms=latency_ms,
            ),
        )
