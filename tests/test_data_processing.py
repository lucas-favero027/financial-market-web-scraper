"""Tests for normalization, classification, and missing values."""

from __future__ import annotations

import pandas as pd
import pytest

from src.data_processing import (
    build_b3_assets,
    build_crypto_assets,
    build_indicator_dataframe,
    classify_b3_index,
    parse_brazilian_number,
    parse_decimal,
)


def test_numeric_conversions() -> None:
    """Brazilian percentages and JSON money values should remain numeric."""
    assert parse_brazilian_number("4.410.957.710") == 4_410_957_710
    assert parse_brazilian_number("8,232") == 8.232
    assert parse_decimal("443028.50000000") == 443_028.5
    assert parse_decimal(None) is None


def test_classification_uses_source_index() -> None:
    """IBOV and IFIX should classify assets without ticker suffix heuristics."""
    assert classify_b3_index("ibov")[0] == "Ação"
    assert classify_b3_index("IFIX")[0] == "FII"
    with pytest.raises(ValueError, match="não reconhecido"):
        classify_b3_index("UNKNOWN")


def test_b3_assets_keep_unavailable_prices_missing() -> None:
    """B3 portfolio fields should be populated without inventing prices."""
    raw_data = {
        "header": {"date": "21/09/26"},
        "results": [
            {
                "cod": "PETR4",
                "asset": "PETROBRAS",
                "type": "PN      N2",
                "theoricalQty": "4.410.957.710",
                "part": "8,232",
            }
        ],
    }

    data = build_b3_assets(raw_data, "IBOV")

    assert data.loc[0, "asset_type"] == "Ação"
    assert data.loc[0, "subtype"] == "PN N2"
    assert data.loc[0, "composition_percent"] == 8.232
    assert pd.isna(data.loc[0, "price"])
    assert pd.isna(data.loc[0, "change_percent"])


def test_crypto_change_is_calculated_from_real_source_fields() -> None:
    """Daily change should use last and open only when both exist."""
    raw_data = {
        "symbols": {
            "symbol": ["BTC-BRL", "ETH-BRL"],
            "description": ["Bitcoin", "Ethereum"],
            "base-currency": ["BTC", "ETH"],
            "currency": ["BRL", "BRL"],
            "type": ["CRYPTO", "CRYPTO"],
        },
        "tickers": [
            {
                "pair": "BTC-BRL",
                "last": "110.00",
                "open": "100.00",
                "high": "115.00",
                "low": "95.00",
                "vol": "2.5",
                "date": 1_790_036_012,
            },
            {
                "pair": "ETH-BRL",
                "last": "20.00",
                "open": None,
                "high": None,
                "low": None,
                "vol": None,
                "date": None,
            },
        ],
    }

    data = build_crypto_assets(raw_data).set_index("ticker")

    assert data.loc["BTC", "change_percent"] == pytest.approx(10.0)
    assert data.loc["BTC", "price"] == 110.0
    assert pd.isna(data.loc["ETH", "change_percent"])
    assert pd.isna(data.loc["ETH", "volume"])


def test_missing_indicator_is_unavailable_not_zero() -> None:
    """A missing CDI observation should stay null rather than becoming zero."""
    raw_data = {
        "results": [
            {
                "indicator": "SELIC",
                "description": "Meta Selic definida pelo Copom",
                "value": "13.75",
                "date": "21/09/2026",
                "unit": "% a.a.",
                "source": "BCB",
            }
        ]
    }

    indicators = build_indicator_dataframe(raw_data).set_index("indicator")

    assert indicators.loc["SELIC", "value"] == 13.75
    assert pd.isna(indicators.loc["CDI", "value"])


def test_invalid_b3_structure_is_rejected() -> None:
    """Processing should fail explicitly when expected fields disappear."""
    with pytest.raises(ValueError, match="Campos ausentes"):
        build_b3_assets(
            {"header": {"date": "21/09/26"}, "results": [{"cod": "PETR4"}]},
            "IBOV",
        )

