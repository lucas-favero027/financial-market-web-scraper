"""Shared HTTP helpers used by the data-source modules."""

from __future__ import annotations

from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_TIMEOUT = 15
USER_AGENT = "financial-market-web-scraper/1.1 (educational Python project)"


class ScraperError(RuntimeError):
    """Raised when a public data source cannot be downloaded or validated."""


def create_retry_session(total_retries: int = 2) -> requests.Session:
    """Create a session that retries transient, idempotent HTTP failures.

    Retries are intentionally limited and apply only to GET requests with
    common temporary status codes. Permanent client errors are not retried.
    """
    if total_retries < 0:
        raise ValueError("O número de tentativas não pode ser negativo.")

    retry_policy = Retry(
        total=total_retries,
        connect=total_retries,
        read=total_retries,
        status=total_retries,
        allowed_methods=frozenset({"GET"}),
        status_forcelist=(429, 500, 502, 503, 504),
        backoff_factor=0.5,
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_policy)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def request_json(
    session: requests.Session,
    url: str,
    *,
    source_name: str,
    timeout: int | float = DEFAULT_TIMEOUT,
    params: dict[str, Any] | None = None,
    referer: str | None = None,
) -> Any:
    """Request JSON with consistent headers, timeout, and error messages."""
    if timeout <= 0:
        raise ValueError("O timeout deve ser maior que zero.")

    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if referer:
        headers["Referer"] = referer

    try:
        response = session.get(
            url,
            params=params,
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()
    except requests.Timeout as exc:
        raise ScraperError(
            f"A requisição a {source_name} excedeu {timeout} segundos."
        ) from exc
    except requests.RequestException as exc:
        raise ScraperError(f"Não foi possível acessar {source_name}: {exc}") from exc
    except ValueError as exc:
        raise ScraperError(f"{source_name} não retornou um JSON válido.") from exc
