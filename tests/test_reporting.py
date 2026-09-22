"""Tests for the generated HTML report and visual artifacts."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from src.data_processing import ASSET_COLUMNS, build_indicator_dataframe
from src.reporting import generate_market_report


def test_report_creates_html_and_available_charts(tmp_path: Path) -> None:
    """The report should remain useful even with a small mixed dataset."""
    rows = [
        {
            "ticker": "PETR4",
            "name": "PETROBRAS",
            "asset_type": "Ação",
            "composition_percent": 8.2,
            "updated_at": "2026-09-21",
        },
        {
            "ticker": "BTC",
            "name": "Bitcoin",
            "asset_type": "Criptomoeda",
            "price": 100.0,
            "change_percent": 2.0,
            "volume": 50.0,
            "updated_at": "2026-09-21",
        },
    ]
    market_data = pd.DataFrame(rows).reindex(columns=ASSET_COLUMNS)
    indicators = build_indicator_dataframe({"results": []})

    paths = generate_market_report(
        market_data,
        indicators,
        generated_at=datetime(2026, 9, 22, 12, 0),
        data_origin="Teste",
        output_dir=tmp_path,
    )

    html = paths["html_report"].read_text(encoding="utf-8")
    assert "Financial Market Web Scraper" in html
    assert "Origem dos dados: Teste" in html
    assert paths["chart_ibov"].exists()
    assert paths["chart_crypto-volume"].exists()
