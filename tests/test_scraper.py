"""Tests for the HTTP layer."""

from __future__ import annotations

import base64
import json
from typing import Any

from src.scraper import fetch_ibovespa_portfolio


class FakeResponse:
    """Minimal requests.Response substitute used by unit tests."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        """Simulate a successful HTTP response."""

    def json(self) -> dict[str, Any]:
        """Return the prepared JSON payload."""
        return self.payload


class FakeSession:
    """Record requests and return predefined pages."""

    def __init__(self, pages: list[dict[str, Any]]) -> None:
        self.pages = pages
        self.requested_pages: list[int] = []

    def get(self, url: str, **_: Any) -> FakeResponse:
        """Decode the B3 payload and return the requested fake page."""
        encoded = url.rsplit("/", 1)[-1]
        payload = json.loads(base64.b64decode(encoded).decode("utf-8"))
        page_number = payload["pageNumber"]
        self.requested_pages.append(page_number)
        return FakeResponse(self.pages[page_number - 1])


def test_fetches_and_combines_all_pages() -> None:
    """The scraper should combine paginated results."""
    pages = [
        {
            "page": {"totalPages": 2, "totalRecords": 2},
            "header": {"date": "21/09/26"},
            "results": [{"cod": "PETR4"}],
        },
        {
            "page": {"totalPages": 2, "totalRecords": 2},
            "header": {"date": "21/09/26"},
            "results": [{"cod": "VALE3"}],
        },
    ]
    session = FakeSession(pages)

    result = fetch_ibovespa_portfolio(session=session)

    assert session.requested_pages == [1, 2]
    assert [item["cod"] for item in result["results"]] == ["PETR4", "VALE3"]
    assert result["page"]["totalRecords"] == 2

