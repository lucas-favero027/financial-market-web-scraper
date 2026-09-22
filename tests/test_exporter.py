"""Tests for CSV and Excel output from standardized DataFrames."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

import src.exporter as exporter
from src.data_processing import ASSET_COLUMNS, build_indicator_dataframe


def test_export_market_data_creates_all_expected_files(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """CSV and XLSX exports should be readable and keep typed numeric cells."""
    monkeypatch.setattr(exporter, "PROCESSED_DIR", tmp_path)
    stock = pd.DataFrame(
        [
            {
                "ticker": "PETR4",
                "name": "PETROBRAS",
                "asset_type": "Ação",
                "composition_percent": 8.232,
                "theoretical_quantity": 4_410_957_710,
                "updated_at": pd.Timestamp("2026-09-21"),
            }
        ]
    ).reindex(columns=ASSET_COLUMNS)
    empty = stock.iloc[0:0].copy()
    indicators = build_indicator_dataframe({"results": []})

    paths = exporter.export_market_data(
        stock,
        empty,
        empty,
        indicators,
        stock,
    )

    assert set(paths) == {
        "stocks",
        "fiis",
        "crypto",
        "economic_indicators",
        "market_data",
        "excel",
    }
    assert all(path.exists() for path in paths.values())
    assert pd.read_csv(paths["stocks"])["ticker"].tolist() == ["PETR4"]

    workbook = load_workbook(paths["excel"], data_only=True)
    assert workbook.sheetnames == [
        "Market Data",
        "Stocks",
        "FIIs",
        "Crypto",
        "Indicators",
    ]
    assert workbook["Stocks"].freeze_panes == "A2"
