"""Scraper for the IBOV and IFIX daily portfolios published by B3."""

from __future__ import annotations

import base64
import json
from typing import Any

import requests

from src.scrapers.common import DEFAULT_TIMEOUT, ScraperError, request_json

BASE_URL = (
    "https://sistemaswebb3-listados.b3.com.br/"
    "indexProxy/indexCall/GetPortfolioDay/"
)
PAGE_URL = (
    "https://sistemaswebb3-listados.b3.com.br/"
    "indexPage/day/{index_code}?language=pt-br"
)
PAGE_SIZE = 120
SUPPORTED_INDEXES = {"IBOV", "IFIX"}


def _encode_payload(payload: dict[str, Any]) -> str:
    """Encode a request payload in the format used by B3's web page."""
    compact_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return base64.b64encode(compact_json.encode("utf-8")).decode("ascii")


def _validate_response(data: Any, index_code: str) -> dict[str, Any]:
    """Validate the minimum B3 response structure used by the project."""
    if not isinstance(data, dict):
        raise ScraperError(f"A B3 retornou um formato inesperado para {index_code}.")

    required_keys = {"page", "header", "results"}
    missing_keys = required_keys.difference(data)
    if missing_keys:
        missing = ", ".join(sorted(missing_keys))
        raise ScraperError(
            f"A estrutura da B3 para {index_code} mudou. Campos ausentes: {missing}."
        )
    if not isinstance(data["page"], dict) or not isinstance(data["header"], dict):
        raise ScraperError(f"Os metadados da B3 para {index_code} são inválidos.")
    if not isinstance(data["results"], list):
        raise ScraperError(f"Os resultados da B3 para {index_code} não são uma lista.")
    return data


def _request_page(
    session: requests.Session,
    index_code: str,
    page_number: int,
    timeout: int | float,
) -> dict[str, Any]:
    """Download one page of a B3 index portfolio."""
    payload = {
        "language": "pt-br",
        "pageNumber": page_number,
        "pageSize": PAGE_SIZE,
        "index": index_code,
        "segment": "1",
    }
    data = request_json(
        session,
        f"{BASE_URL}{_encode_payload(payload)}",
        source_name=f"B3 ({index_code})",
        timeout=timeout,
        referer=PAGE_URL.format(index_code=index_code),
    )
    return _validate_response(data, index_code)


def fetch_index_portfolio(
    index_code: str,
    timeout: int | float = DEFAULT_TIMEOUT,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    """Fetch every page of an IBOV or IFIX portfolio."""
    normalized_index = index_code.strip().upper()
    if normalized_index not in SUPPORTED_INDEXES:
        raise ValueError(f"Índice B3 não suportado: {index_code!r}.")

    http_session = session or requests.Session()
    should_close_session = session is None
    try:
        first_page = _request_page(
            http_session,
            normalized_index,
            page_number=1,
            timeout=timeout,
        )
        total_pages = int(first_page["page"].get("totalPages", 1))
        all_results = list(first_page["results"])

        for page_number in range(2, total_pages + 1):
            page = _request_page(
                http_session,
                normalized_index,
                page_number,
                timeout,
            )
            all_results.extend(page["results"])

        first_page["results"] = all_results
        first_page["page"]["pageNumber"] = 1
        first_page["page"]["totalPages"] = total_pages
        first_page["page"]["totalRecords"] = len(all_results)
        first_page["indexCode"] = normalized_index
        return first_page
    finally:
        if should_close_session:
            http_session.close()


def fetch_stocks(
    timeout: int | float = DEFAULT_TIMEOUT,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    """Fetch the current Ibovespa portfolio."""
    return fetch_index_portfolio("IBOV", timeout=timeout, session=session)


def fetch_fiis(
    timeout: int | float = DEFAULT_TIMEOUT,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    """Fetch the current IFIX portfolio."""
    return fetch_index_portfolio("IFIX", timeout=timeout, session=session)

