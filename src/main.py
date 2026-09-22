"""Command-line entry point for the financial market web scraper."""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from typing import Any

import requests

from src.analysis import (
    TickerNotFoundError,
    filter_assets,
    find_asset,
    market_summary,
    paginate_assets,
)
from src.data_processing import (
    build_b3_assets,
    build_crypto_assets,
    build_indicator_dataframe,
    combine_assets,
    empty_asset_dataframe,
)
from src.display import (
    print_asset_details,
    print_assets_table,
    print_exported_files,
    print_header,
    print_indicators,
    print_market_summary,
    print_source_warnings,
)
from src.exporter import export_market_data, save_raw_snapshot
from src.scrapers.b3 import fetch_fiis, fetch_stocks
from src.scrapers.common import ScraperError
from src.scrapers.crypto import fetch_crypto_market
from src.scrapers.economic_indicators import fetch_economic_indicators


def parse_arguments() -> argparse.Namespace:
    """Parse CLI filters, pagination, ticker, and HTTP timeout."""
    parser = argparse.ArgumentParser(
        description=(
            "Coleta ações, FIIs, criptomoedas, SELIC e CDI de fontes públicas."
        )
    )
    parser.add_argument(
        "--ticker",
        help="Ticker a consultar, por exemplo PETR4, HGLG11 ou BTC.",
    )
    parser.add_argument(
        "--type",
        dest="asset_type",
        choices=("all", "stocks", "fii", "crypto"),
        default="all",
        help="Categoria exibida na tabela (padrão: all).",
    )
    parser.add_argument(
        "--page",
        type=int,
        default=1,
        help="Página da listagem (padrão: 1).",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=20,
        help="Itens por página, entre 5 e 100 (padrão: 20).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15,
        help="Timeout de cada requisição HTTP em segundos (padrão: 15).",
    )
    return parser.parse_args()


def collect_market_data(
    timeout: int | float,
    reference_date: date | None = None,
) -> dict[str, Any]:
    """Collect and process each source independently.

    A source failure produces an empty category and a warning instead of
    hiding the other categories.
    """
    if timeout <= 0:
        raise ValueError("O timeout deve ser maior que zero.")

    stocks = empty_asset_dataframe()
    fiis = empty_asset_dataframe()
    crypto = empty_asset_dataframe()
    raw_payloads: dict[str, Any] = {}
    errors: dict[str, str] = {}

    with requests.Session() as session:
        try:
            raw_payloads["stocks_b3_ibov"] = fetch_stocks(
                timeout=timeout, session=session
            )
            stocks = build_b3_assets(raw_payloads["stocks_b3_ibov"], "IBOV")
        except (ScraperError, ValueError) as exc:
            errors["Ações - B3"] = str(exc)

        try:
            raw_payloads["fiis_b3_ifix"] = fetch_fiis(
                timeout=timeout, session=session
            )
            fiis = build_b3_assets(raw_payloads["fiis_b3_ifix"], "IFIX")
        except (ScraperError, ValueError) as exc:
            errors["FIIs - B3"] = str(exc)

        try:
            raw_payloads["crypto_mercado_bitcoin"] = fetch_crypto_market(
                timeout=timeout, session=session
            )
            crypto = build_crypto_assets(raw_payloads["crypto_mercado_bitcoin"])
        except (ScraperError, ValueError) as exc:
            errors["Criptomoedas - Mercado Bitcoin"] = str(exc)

        try:
            raw_payloads["economic_indicators_bcb"] = fetch_economic_indicators(
                timeout=timeout,
                session=session,
                reference_date=reference_date,
            )
            errors.update(raw_payloads["economic_indicators_bcb"].get("errors", {}))
            indicators = build_indicator_dataframe(
                raw_payloads["economic_indicators_bcb"]
            )
        except (ScraperError, ValueError) as exc:
            errors["Indicadores - Banco Central"] = str(exc)
            indicators = build_indicator_dataframe({"results": []})

    market_data = combine_assets(stocks, fiis, crypto)
    return {
        "stocks": stocks,
        "fiis": fiis,
        "crypto": crypto,
        "indicators": indicators,
        "market_data": market_data,
        "raw_payloads": raw_payloads,
        "errors": errors,
    }


def run(args: argparse.Namespace) -> int:
    """Execute collection, display, ticker lookup, and exports."""
    collected_at = datetime.now()
    print_header(collected_at)
    print("\nColetando dados de fontes públicas...")
    result = collect_market_data(args.timeout, reference_date=collected_at.date())

    raw_path = save_raw_snapshot(
        result["raw_payloads"], result["errors"], collected_at
    )
    exported_paths = export_market_data(
        result["stocks"],
        result["fiis"],
        result["crypto"],
        result["indicators"],
        result["market_data"],
    )
    all_paths = {"raw_snapshot": raw_path, **exported_paths}

    print_market_summary(market_summary(result["market_data"]))
    print_indicators(result["indicators"])
    print_source_warnings(result["errors"])

    filtered = filter_assets(result["market_data"], args.asset_type)
    page_data, total_pages, total_items = paginate_assets(
        filtered,
        page=args.page,
        page_size=args.page_size,
    )
    print_assets_table(
        page_data,
        page=args.page,
        total_pages=total_pages,
        total_items=total_items,
        page_size=args.page_size,
    )

    selected_ticker = args.ticker
    if selected_ticker is None:
        print("\nDigite um ticker para consultar (Enter para encerrar):")
        selected_ticker = input("> ").strip()
    if selected_ticker:
        print_asset_details(find_asset(result["market_data"], selected_ticker))

    print_exported_files(all_paths)
    return 0


def _configure_console_encoding() -> None:
    """Use UTF-8 so Portuguese text renders correctly in modern PowerShell."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")


def main() -> int:
    """Run the CLI and translate expected failures into clear messages."""
    _configure_console_encoding()
    args = parse_arguments()
    try:
        return run(args)
    except (TickerNotFoundError, ValueError) as exc:
        print(f"\nErro: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nExecução cancelada pelo usuário.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
