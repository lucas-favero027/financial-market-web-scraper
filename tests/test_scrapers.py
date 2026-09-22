"""Unit tests for the three HTTP source modules."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from src.scrapers.b3 import fetch_index_portfolio
from src.scrapers.common import ScraperError
from src.scrapers.crypto import fetch_crypto_market
from src.scrapers.economic_indicators import fetch_economic_indicators


class FakeResponse:
    """Minimal successful requests response."""

    def __init__(self, payload: Any) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        """Simulate a successful status code."""

    def json(self) -> Any:
        """Return the predefined payload."""
        return self.payload


class FakeSession:
    """Return responses in order and record request options."""

    def __init__(self, payloads: list[Any]) -> None:
        self.payloads = list(payloads)
        self.calls: list[dict[str, Any]] = []

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        """Record one GET and return the next payload."""
        self.calls.append({"url": url, **kwargs})
        return FakeResponse(self.payloads.pop(0))


def test_b3_scraper_combines_paginated_results() -> None:
    """All pages from an index portfolio should be combined."""
    session = FakeSession(
        [
            {
                "page": {"totalPages": 2},
                "header": {"date": "21/09/26"},
                "results": [{"cod": "PETR4"}],
            },
            {
                "page": {"totalPages": 2},
                "header": {"date": "21/09/26"},
                "results": [{"cod": "VALE3"}],
            },
        ]
    )

    result = fetch_index_portfolio("IBOV", session=session)

    assert [item["cod"] for item in result["results"]] == ["PETR4", "VALE3"]
    assert result["page"]["totalRecords"] == 2
    assert len(session.calls) == 2
    assert all(call["timeout"] == 15 for call in session.calls)


def test_b3_scraper_rejects_invalid_response() -> None:
    """A structural source change should produce a clear scraper error."""
    session = FakeSession([{"unexpected": []}])

    with pytest.raises(ScraperError, match="Campos ausentes"):
        fetch_index_portfolio("IFIX", session=session)


def test_crypto_scraper_requests_metadata_and_tickers() -> None:
    """Crypto collection should use public metadata and ticker endpoints."""
    symbols = {
        "symbol": ["BTC-BRL"],
        "description": ["Bitcoin"],
        "base-currency": ["BTC"],
        "currency": ["BRL"],
        "type": ["CRYPTO"],
    }
    tickers = [{"pair": "BTC-BRL", "last": "100.00"}]
    session = FakeSession([symbols, tickers])

    result = fetch_crypto_market(session=session, assets=("BTC",))

    assert result["symbols"]["description"] == ["Bitcoin"]
    assert result["tickers"][0]["pair"] == "BTC-BRL"
    assert len(session.calls) == 2
    assert session.calls[0]["params"]["symbols"] == "BTC-BRL"


def test_economic_scraper_limits_data_to_reference_date() -> None:
    """SGS requests must not select observations after the reference date."""
    session = FakeSession(
        [
            [{"data": "21/09/2026", "valor": "13.75"}],
            [{"data": "18/09/2026", "valor": "13.65"}],
        ]
    )

    result = fetch_economic_indicators(
        session=session,
        reference_date=date(2026, 9, 21),
    )

    assert [item["indicator"] for item in result["results"]] == ["SELIC", "CDI"]
    assert all(
        call["params"]["dataFinal"] == "21/09/2026" for call in session.calls
    )

