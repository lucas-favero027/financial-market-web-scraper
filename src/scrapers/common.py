"""Shared HTTP helpers used by the data-source modules."""

from __future__ import annotations

from typing import Any

import requests

DEFAULT_TIMEOUT = 15
USER_AGENT = "financial-market-web-scraper/1.0 (educational Python project)"


class ScraperError(RuntimeError):
    """Raised when a public data source cannot be downloaded or validated."""


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

