"""HTTP client for the public B3 Ibovespa portfolio endpoint."""

from __future__ import annotations

import base64
import json
from typing import Any

import requests

BASE_URL = (
    "https://sistemaswebb3-listados.b3.com.br/"
    "indexProxy/indexCall/GetPortfolioDay/"
)
PAGE_URL = (
    "https://sistemaswebb3-listados.b3.com.br/"
    "indexPage/day/IBOV?language=pt-br"
)
DEFAULT_TIMEOUT = 15
PAGE_SIZE = 120


class ScraperError(RuntimeError):
    """Raised when B3 data cannot be downloaded or validated."""


def _encode_payload(payload: dict[str, Any]) -> str:
    """Encode the request payload in the format expected by the B3 page."""
    compact_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return base64.b64encode(compact_json.encode("utf-8")).decode("ascii")


def _validate_response(data: Any) -> dict[str, Any]:
    """Validate the minimum response structure used by the application."""
    if not isinstance(data, dict):
        raise ScraperError("A B3 retornou um conteúdo em formato inesperado.")

    required_keys = {"page", "header", "results"}
    missing_keys = required_keys.difference(data)
    if missing_keys:
        missing = ", ".join(sorted(missing_keys))
        raise ScraperError(
            f"A estrutura retornada pela B3 mudou. Campos ausentes: {missing}."
        )

    if not isinstance(data["results"], list):
        raise ScraperError("O campo 'results' da B3 não contém uma lista.")

    return data


def _request_page(
    session: requests.Session,
    page_number: int,
    timeout: int | float,
) -> dict[str, Any]:
    """Download one page of the current Ibovespa portfolio."""
    payload = {
        "language": "pt-br",
        "pageNumber": page_number,
        "pageSize": PAGE_SIZE,
        "index": "IBOV",
        "segment": "1",
    }
    url = f"{BASE_URL}{_encode_payload(payload)}"
    headers = {
        "Accept": "application/json",
        "Referer": PAGE_URL,
        "User-Agent": "stock-web-scraper/1.0 (educational Python project)",
    }

    try:
        response = session.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return _validate_response(response.json())
    except requests.Timeout as exc:
        raise ScraperError(
            f"A requisição à B3 excedeu o limite de {timeout} segundos."
        ) from exc
    except requests.RequestException as exc:
        raise ScraperError(f"Não foi possível acessar a B3: {exc}") from exc
    except ValueError as exc:
        raise ScraperError("A resposta da B3 não contém um JSON válido.") from exc


def fetch_ibovespa_portfolio(
    timeout: int | float = DEFAULT_TIMEOUT,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    """Fetch every page of the current Ibovespa portfolio from B3.

    A session can be injected to make the HTTP layer easy to test without
    accessing the internet.
    """
    if timeout <= 0:
        raise ValueError("O timeout deve ser maior que zero.")

    http_session = session or requests.Session()
    should_close_session = session is None

    try:
        first_page = _request_page(http_session, page_number=1, timeout=timeout)
        page_info = first_page["page"]
        total_pages = int(page_info.get("totalPages", 1))
        all_results = list(first_page["results"])

        for page_number in range(2, total_pages + 1):
            page = _request_page(http_session, page_number, timeout)
            all_results.extend(page["results"])

        first_page["results"] = all_results
        first_page["page"]["pageNumber"] = 1
        first_page["page"]["totalPages"] = total_pages
        first_page["page"]["totalRecords"] = len(all_results)
        return first_page
    finally:
        if should_close_session:
            http_session.close()

