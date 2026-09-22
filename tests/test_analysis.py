"""Tests for ticker search, category counts, filters, and pagination."""

from __future__ import annotations

import pandas as pd
import pytest

from src.analysis import (
    TickerNotFoundError,
    build_named_ranking,
    compare_assets,
    filter_assets,
    find_asset,
    market_summary,
    paginate_assets,
)
from src.data_processing import ASSET_COLUMNS


@pytest.fixture
def sample_data() -> pd.DataFrame:
    """Create standardized rows for the three asset categories."""
    rows = [
        {"ticker": "PETR4", "name": "PETROBRAS", "asset_type": "Ação"},
        {"ticker": "HGLG11", "name": "FII HGLG", "asset_type": "FII"},
        {"ticker": "BTC", "name": "Bitcoin", "asset_type": "Criptomoeda"},
    ]
    return pd.DataFrame(rows).reindex(columns=ASSET_COLUMNS)


def test_find_asset_is_case_insensitive(sample_data: pd.DataFrame) -> None:
    """Ticker lookup should ignore case and spaces."""
    assert find_asset(sample_data, " petr4 ")["name"] == "PETROBRAS"


def test_find_asset_reports_missing_ticker(sample_data: pd.DataFrame) -> None:
    """An unknown ticker should produce a clear domain error."""
    with pytest.raises(TickerNotFoundError, match="não foi encontrado"):
        find_asset(sample_data, "XXXX3")


def test_summary_always_contains_all_categories(sample_data: pd.DataFrame) -> None:
    """Category counts should include explicit zeros."""
    stock_only = sample_data.loc[sample_data["asset_type"] == "Ação"]

    summary = market_summary(stock_only)

    assert summary == {"stocks": 1, "fiis": 0, "crypto": 0, "total": 1}


def test_filter_and_paginate_assets(sample_data: pd.DataFrame) -> None:
    """CLI filters and pages should return predictable subsets."""
    crypto = filter_assets(sample_data, "crypto")
    page, total_pages, total_items = paginate_assets(sample_data, 1, 5)

    assert crypto["ticker"].tolist() == ["BTC"]
    assert page["ticker"].tolist() == ["PETR4", "HGLG11", "BTC"]
    assert (total_pages, total_items) == (1, 3)


def test_invalid_page_is_rejected(sample_data: pd.DataFrame) -> None:
    """Invalid pagination input should not silently return an empty page."""
    with pytest.raises(ValueError, match="não existe"):
        paginate_assets(sample_data, page=2, page_size=5)


def test_named_ranking_filters_category_and_metric(sample_data: pd.DataFrame) -> None:
    """A named ranking should not mix unrelated asset categories."""
    sample_data.loc[sample_data["ticker"] == "PETR4", "composition_percent"] = 8.2
    title, column, ranking = build_named_ranking(sample_data, "ibov", limit=5)

    assert title == "Maiores participações no Ibovespa"
    assert column == "composition_percent"
    assert ranking["ticker"].tolist() == ["PETR4"]


def test_compare_assets_preserves_order_and_accepts_commas(
    sample_data: pd.DataFrame,
) -> None:
    """Comparison input should be convenient for both shell syntaxes."""
    compared = compare_assets(sample_data, ["btc,PETR4", "BTC"])

    assert compared["ticker"].tolist() == ["BTC", "PETR4"]


def test_compare_assets_requires_two_distinct_tickers(
    sample_data: pd.DataFrame,
) -> None:
    """A single asset is a lookup, not a comparison."""
    with pytest.raises(ValueError, match="pelo menos dois"):
        compare_assets(sample_data, ["PETR4", "petr4"])
