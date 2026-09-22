"""Tests for stock lookup and portfolio analysis."""

from __future__ import annotations

import pandas as pd
import pytest

from src.analysis import TickerNotFoundError, find_stock, portfolio_summary, rank_stocks


@pytest.fixture
def sample_data() -> pd.DataFrame:
    """Create a small cleaned portfolio for analysis tests."""
    return pd.DataFrame(
        {
            "ticker": ["PETR4", "VALE3", "ITUB4"],
            "nome": ["PETROBRAS", "VALE", "ITAUUNIBANCO"],
            "tipo": ["PN N2", "ON NM", "PN N1"],
            "quantidade_teorica": [4_000, 2_000, 5_000],
            "participacao_percentual": [8.3, 11.0, 8.4],
            "data_referencia": pd.to_datetime(["2026-09-21"] * 3),
        }
    )


def test_find_stock_is_case_insensitive(sample_data: pd.DataFrame) -> None:
    """Ticker lookup should ignore case and spaces."""
    assert find_stock(sample_data, " petr4 ")["nome"] == "PETROBRAS"


def test_find_stock_reports_missing_ticker(sample_data: pd.DataFrame) -> None:
    """An absent ticker should produce a domain-specific error."""
    with pytest.raises(TickerNotFoundError, match="não faz parte"):
        find_stock(sample_data, "XXXX3")


def test_summary_and_ranking(sample_data: pd.DataFrame) -> None:
    """Summary and ranking should use numeric columns correctly."""
    summary = portfolio_summary(sample_data)
    ranking = rank_stocks(sample_data, "participacao_percentual", limit=2)

    assert summary["total_ativos"] == 3
    assert summary["maior_participacao"]["ticker"] == "VALE3"
    assert summary["maior_quantidade_teorica"]["ticker"] == "ITUB4"
    assert ranking["ticker"].tolist() == ["VALE3", "ITUB4"]

