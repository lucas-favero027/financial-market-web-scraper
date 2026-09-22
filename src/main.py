"""Command-line entry point for the stock web scraper."""

from __future__ import annotations

import argparse
import json
import sys
from copy import copy
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.analysis import TickerNotFoundError, find_stock, portfolio_summary
from src.data_processing import build_dataframe
from src.scraper import ScraperError, fetch_ibovespa_portfolio

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def parse_arguments() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(
        description="Coleta e analisa a carteira atual do Ibovespa publicada pela B3."
    )
    parser.add_argument(
        "--ticker",
        help="Ticker a consultar, por exemplo PETR4. Se omitido, será solicitado.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15,
        help="Timeout da requisição HTTP em segundos (padrão: 15).",
    )
    return parser.parse_args()


def save_raw_data(raw_data: dict[str, Any]) -> Path:
    """Save the unchanged JSON response for traceability."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = RAW_DIR / f"ibov_carteira_bruta_{timestamp}.json"
    output_path.write_text(
        json.dumps(raw_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return output_path


def export_processed_data(data: pd.DataFrame) -> tuple[Path, Path]:
    """Export the cleaned data to CSV and Excel."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    reference_date = data["data_referencia"].iloc[0].strftime("%Y%m%d")
    csv_path = PROCESSED_DIR / f"ibov_carteira_tratada_{reference_date}.csv"
    xlsx_path = PROCESSED_DIR / f"ibov_carteira_tratada_{reference_date}.xlsx"

    data.to_csv(csv_path, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        data.to_excel(writer, index=False, sheet_name="Carteira Ibovespa")
        worksheet = writer.sheets["Carteira Ibovespa"]
        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = worksheet.dimensions
        widths = {"A": 12, "B": 22, "C": 16, "D": 22, "E": 24, "F": 18}
        for column, width in widths.items():
            worksheet.column_dimensions[column].width = width
        for cell in worksheet[1]:
            header_font = copy(cell.font)
            header_font.bold = True
            cell.font = header_font
        for row in range(2, worksheet.max_row + 1):
            worksheet[f"D{row}"].number_format = "#,##0"
            worksheet[f"E{row}"].number_format = "0.000"
            worksheet[f"F{row}"].number_format = "dd/mm/yyyy"

    return csv_path, xlsx_path


def format_number_br(value: int | float, decimal_places: int = 0) -> str:
    """Format a number for terminal display using Brazilian separators."""
    formatted = f"{value:,.{decimal_places}f}"
    return formatted.replace(",", "_").replace(".", ",").replace("_", ".")


def print_portfolio_summary(data: pd.DataFrame) -> None:
    """Print the main portfolio highlights."""
    summary = portfolio_summary(data)
    top_part = summary["maior_participacao"]
    low_part = summary["menor_participacao"]
    top_quantity = summary["maior_quantidade_teorica"]

    print("\nResumo da carteira")
    print(f"Data de referência: {summary['data_referencia']:%d/%m/%Y}")
    print(f"Quantidade de ativos: {summary['total_ativos']}")
    print(
        "Maior participação: "
        f"{top_part['ticker']} "
        f"({format_number_br(top_part['participacao_percentual'], 3)}%)"
    )
    print(
        "Menor participação: "
        f"{low_part['ticker']} "
        f"({format_number_br(low_part['participacao_percentual'], 3)}%)"
    )
    print(
        "Maior quantidade teórica: "
        f"{top_quantity['ticker']} "
        f"({format_number_br(top_quantity['quantidade_teorica'])})"
    )


def print_stock(stock: pd.Series) -> None:
    """Print one stock in a readable terminal format."""
    print("\nAção encontrada")
    print(f"Ticker: {stock['ticker']}")
    print(f"Nome: {stock['nome']}")
    print(f"Tipo: {stock['tipo']}")
    print(
        "Quantidade teórica: "
        f"{format_number_br(stock['quantidade_teorica'])}"
    )
    print(
        "Participação no Ibovespa: "
        f"{format_number_br(stock['participacao_percentual'], 3)}%"
    )
    print(f"Data de referência: {stock['data_referencia']:%d/%m/%Y}")


def run(ticker: str | None, timeout: float) -> int:
    """Execute the complete collection, cleaning, analysis, and export flow."""
    print("Coletando a carteira do Ibovespa na B3...")
    raw_data = fetch_ibovespa_portfolio(timeout=timeout)
    raw_path = save_raw_data(raw_data)

    print("Tratando os dados com pandas...")
    data = build_dataframe(raw_data)
    csv_path, xlsx_path = export_processed_data(data)

    print_portfolio_summary(data)
    selected_ticker = ticker or input("\nDigite um ticker para consultar: ").strip()
    stock = find_stock(data, selected_ticker)
    print_stock(stock)

    print("\nArquivos gerados")
    print(f"JSON bruto: {raw_path}")
    print(f"CSV tratado: {csv_path}")
    print(f"Excel tratado: {xlsx_path}")
    return 0


def main() -> int:
    """Run the CLI and translate expected failures into clear messages."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    args = parse_arguments()
    try:
        return run(args.ticker, args.timeout)
    except (ScraperError, TickerNotFoundError, ValueError) as exc:
        print(f"\nErro: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nExecução cancelada pelo usuário.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
