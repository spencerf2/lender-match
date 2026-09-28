"""Picks the decision provider the config names."""

from lender_match.config import Settings, get_config
from lender_match.domain.decisions import DecisionProvider, FakeDecisionProvider
from lender_match.providers import JevDecisionProvider, OpenRouterDecisionProvider


def decision_provider(config: Settings | None = None) -> DecisionProvider:
    config = config or get_config()
    if config.decision_provider == "fake":
        return FakeDecisionProvider({})
    key = config.openrouter_api_key
    if not key:
        raise ValueError("OPENROUTER_API_KEY is not set")
    if config.decision_provider == "openrouter":
        return OpenRouterDecisionProvider(model=config.decision_model, api_key=key)
    return JevDecisionProvider(api_key=key, model=config.jev_model)
