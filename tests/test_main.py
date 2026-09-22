"""Integration tests for the CLI orchestration using bundled offline data."""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

import src.exporter as exporter
import src.main as main_module
from src.analysis import market_summary
from src.main import (
    collect_market_data,
    load_market_data,
    parse_arguments,
    process_market_payloads,
    run,
)
from src.snapshots import SAMPLE_SNAPSHOT, load_snapshot


def test_offline_cli_runs_analysis_and_exports(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    """The interview-safe mode should exercise the complete pipeline offline."""
    monkeypatch.setattr(exporter, "PROCESSED_DIR", tmp_path)
    args = argparse.Namespace(
        ticker="PETR4",
        asset_type="all",
        page=1,
        page_size=5,
        timeout=1.0,
        offline=True,
        cache_minutes=0,
        ranking="ibov",
        ranking_limit=3,
        compare=["PETR4", "BTC"],
        report=False,
    )

    exit_code = run(args)
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Snapshot de demonstração" in output
    assert "MAIORES PARTICIPAÇÕES NO IBOVESPA" in output
    assert "COMPARAÇÃO DE ATIVOS" in output
    assert "PETR4 — PETROBRAS" in output
    assert (tmp_path / "market_data.xlsx").exists()


def test_parse_arguments_accepts_new_analysis_options(monkeypatch) -> None:
    """CLI documentation and parsing should evolve together."""
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "program",
            "--offline",
            "--ranking",
            "crypto-change",
            "--ranking-limit",
            "5",
            "--compare",
            "BTC",
            "ETH",
            "--report",
        ],
    )

    args = parse_arguments()

    assert args.offline is True
    assert args.ranking == "crypto-change"
    assert args.ranking_limit == 5
    assert args.compare == ["BTC", "ETH"]
    assert args.report is True


def test_process_market_payloads_reports_every_missing_source() -> None:
    """A partial snapshot should preserve explicit unavailable categories."""
    result = process_market_payloads({})

    assert market_summary(result["market_data"])["total"] == 0
    assert set(result["errors"]) == {
        "Ações - B3",
        "FIIs - B3",
        "Criptomoedas - Mercado Bitcoin",
        "Indicadores - Banco Central",
    }


def test_load_market_data_uses_valid_cache(monkeypatch) -> None:
    """A configured fresh snapshot should bypass HTTP collection."""
    snapshot = load_snapshot(SAMPLE_SNAPSHOT)
    monkeypatch.setattr(
        main_module, "find_recent_snapshot", lambda *args, **kwargs: snapshot
    )
    args = argparse.Namespace(offline=False, cache_minutes=15, timeout=1.0)

    result = load_market_data(args, datetime(2026, 9, 22, 12, 0))

    assert result["data_origin"] == "Cache local"
    assert len(result["market_data"]) == 195


def test_collect_market_data_combines_successful_sources(monkeypatch) -> None:
    """The online orchestrator should process all independently fetched payloads."""
    snapshot = load_snapshot(SAMPLE_SNAPSHOT)
    sources = snapshot["sources"]

    class SessionContext:
        def __enter__(self):
            return object()

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(main_module, "create_retry_session", SessionContext)
    monkeypatch.setattr(
        main_module,
        "fetch_stocks",
        lambda **kwargs: sources["stocks_b3_ibov"],
    )
    monkeypatch.setattr(
        main_module,
        "fetch_fiis",
        lambda **kwargs: sources["fiis_b3_ifix"],
    )
    monkeypatch.setattr(
        main_module,
        "fetch_crypto_market",
        lambda **kwargs: sources["crypto_mercado_bitcoin"],
    )
    monkeypatch.setattr(
        main_module,
        "fetch_economic_indicators",
        lambda **kwargs: sources["economic_indicators_bcb"],
    )

    result = collect_market_data(1.0, reference_date=date(2026, 9, 21))

    assert market_summary(result["market_data"])["total"] == 195
    assert result["errors"] == {}


def test_main_translates_expected_errors(monkeypatch, capsys) -> None:
    """Expected domain errors should become a clear non-zero CLI result."""
    monkeypatch.setattr(main_module, "parse_arguments", lambda: argparse.Namespace())
    monkeypatch.setattr(
        main_module,
        "run",
        lambda args: (_ for _ in ()).throw(ValueError("falha controlada")),
    )

    assert main_module.main() == 1
    assert "falha controlada" in capsys.readouterr().err
