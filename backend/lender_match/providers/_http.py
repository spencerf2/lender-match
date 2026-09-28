import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)


def post_json(
    client: httpx.Client, url: str, body: dict[str, Any], model: str
) -> tuple[Any, int] | None:
    """POST body and return the JSON reply and latency in ms, or None
    when the call fails. Retries once on a network error, timeout, 429
    or 5xx. Logs failures instead of raising.
    """
    start = time.perf_counter()
    logger.info("decision call started", extra={"model": model, "url": url})
    status: int | str = "error"
    for attempt in (1, 2):
        try:
            response = client.post(url, json=body)
        except (httpx.TransportError, httpx.TimeoutException) as exc:
            status = type(exc).__name__
            if attempt == 1:
                continue
            break
        status = response.status_code
        if (status == 429 or status >= 500) and attempt == 1:
            continue
        if status != 200:
            break
        duration_ms = int((time.perf_counter() - start) * 1000)
        try:
            data = response.json()
        except ValueError:
            status = "malformed body"
            break
        if not isinstance(data, dict) or "error" in data:
            status = "error body"
            break
        logger.info(
            "decision call completed",
            extra={"model": model, "duration_ms": duration_ms, "status": status},
        )
        return data, duration_ms
    duration_ms = int((time.perf_counter() - start) * 1000)
    logger.error(
        "decision call failed",
        extra={"model": model, "duration_ms": duration_ms, "status": status},
    )
    return None


def log_bad_reply(model: str, reason: str) -> None:
    logger.error(
        "decision reply could not be read",
        extra={"model": model, "duration_ms": None, "status": reason},
    )
