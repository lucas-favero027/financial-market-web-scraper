"""Scraper for SELIC and CDI series from Banco Central do Brasil."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import requests

from src.scrapers.common import DEFAULT_TIMEOUT, ScraperError, request_json

SERIES_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{series_code}/dados"
SERIES = {
    "SELIC": {"series_code": 432, "description": "Meta Selic definida pelo Copom"},
    "CDI": {
        "series_code": 4389,
        "description": "CDI acumulada no mês anualizada, base 252",
    },
}


def _validate_series(data: Any, indicator: str) -> list[dict[str, Any]]:
    """Validate one BCB time-series response."""
    if not isinstance(data, list) or not data:
        raise ScraperError(f"O Banco Central não retornou dados para {indicator}.")
    if any(
        not isinstance(item, dict) or not {"data", "valor"}.issubset(item)
        for item in data
    ):
        raise ScraperError(f"A estrutura da série {indicator} é inválida.")
    return data


def fetch_economic_indicators(
    timeout: int | float = DEFAULT_TIMEOUT,
    session: requests.Session | None = None,
    reference_date: date | None = None,
    lookback_days: int = 45,
) -> dict[str, Any]:
    """Fetch the latest SELIC and CDI observations available up to today.

    The explicit end date prevents future observations already registered in
    an SGS series from being displayed before they become effective.
    """
    if lookback_days <= 0:
        raise ValueError("A janela de consulta deve ser maior que zero.")

    end_date = reference_date or date.today()
    start_date = end_date - timedelta(days=lookback_days)
    params = {
        "formato": "json",
        "dataInicial": start_date.strftime("%d/%m/%Y"),
        "dataFinal": end_date.strftime("%d/%m/%Y"),
    }
    http_session = session or requests.Session()
    should_close_session = session is None
    results: list[dict[str, Any]] = []
    errors: dict[str, str] = {}

    try:
        for indicator, metadata in SERIES.items():
            try:
                data = request_json(
                    http_session,
                    SERIES_URL.format(series_code=metadata["series_code"]),
                    source_name=f"Banco Central ({indicator})",
                    timeout=timeout,
                    params=params,
                )
                latest = _validate_series(data, indicator)[-1]
                results.append(
                    {
                        "indicator": indicator,
                        "description": metadata["description"],
                        "value": latest["valor"],
                        "date": latest["data"],
                        "unit": "% a.a.",
                        "source": f"Banco Central do Brasil - SGS {metadata['series_code']}",
                    }
                )
            except ScraperError as exc:
                errors[indicator] = str(exc)
        return {"results": results, "errors": errors}
    finally:
        if should_close_session:
            http_session.close()
