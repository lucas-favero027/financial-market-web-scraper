"""Tests for DataFrame construction and data cleaning."""

from __future__ import annotations

from src.data_processing import build_dataframe, parse_brazilian_number


def test_parse_brazilian_number() -> None:
    """Brazilian thousands and decimal separators should be normalized."""
    assert parse_brazilian_number("4.043.349.180") == 4_043_349_180
    assert parse_brazilian_number("2,393") == 2.393


def test_build_dataframe_cleans_source_fields() -> None:
    """The DataFrame should contain typed, normalized fields."""
    raw_data = {
        "header": {"date": "21/09/26"},
        "results": [
            {
                "cod": " petr4 ",
                "asset": " PETROBRAS ",
                "type": "PN      N2",
                "theoricalQty": "4.043.349.180",
                "part": "8,307",
            }
        ],
    }

    data = build_dataframe(raw_data)

    assert data.loc[0, "ticker"] == "PETR4"
    assert data.loc[0, "tipo"] == "PN N2"
    assert data.loc[0, "quantidade_teorica"] == 4_043_349_180
    assert data.loc[0, "participacao_percentual"] == 8.307
    assert data.loc[0, "data_referencia"].strftime("%Y-%m-%d") == "2026-09-21"

