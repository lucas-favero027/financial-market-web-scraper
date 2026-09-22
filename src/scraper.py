"""Backward-compatible imports for the original B3 scraper module.

New code should import from :mod:`src.scrapers.b3`.
"""

from typing import Any

from src.scrapers.b3 import fetch_index_portfolio, fetch_stocks
from src.scrapers.common import ScraperError


def fetch_ibovespa_portfolio(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Keep the original public function name available."""
    return fetch_stocks(*args, **kwargs)


__all__ = ["ScraperError", "fetch_ibovespa_portfolio", "fetch_index_portfolio"]
