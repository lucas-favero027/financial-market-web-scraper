"""PowerShell-friendly terminal presentation functions."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

SEPARATOR = "=" * 92


def _is_missing(value: object) -> bool:
    """Return whether a scalar value is missing."""
    return value is None or bool(pd.isna(value))


def format_number_br(value: object, decimal_places: int = 2) -> str:
    """Format a numeric value with Brazilian separators."""
    if _is_missing(value):
        return "indisponível"
    formatted = f"{float(value):,.{decimal_places}f}"
    return formatted.replace(",", "_").replace(".", ",").replace("_", ".")


def format_currency(value: object) -> str:
    """Format a BRL monetary value or indicate missing data."""
    return f"R$ {format_number_br(value, 2)}" if not _is_missing(value) else "—"


def format_percent(value: object, *, table: bool = False) -> str:
    """Format a percentage, preserving unavailable values."""
    if _is_missing(value):
        return "—" if table else "indisponível"
    number = float(value)
    sign = "+" if number > 0 else ""
    return f"{sign}{format_number_br(number, 2)}%"


def _shorten(value: object, width: int) -> str:
    """Truncate text without breaking the table width."""
    text = str(value)
    return text if len(text) <= width else f"{text[: width - 1]}…"


def print_header(collected_at: datetime) -> None:
    """Print the application title and collection timestamp."""
    print(SEPARATOR)
    print("FINANCIAL MARKET WEB SCRAPER")
    print(SEPARATOR)
    print(f"Dados coletados em: {collected_at:%d/%m/%Y %H:%M:%S}")


def print_data_origin(origin: str, snapshot_date: datetime | None = None) -> None:
    """Identify whether this execution used the internet, cache, or demo data."""
    date_text = (
        f" | coleta original: {snapshot_date:%d/%m/%Y %H:%M:%S}"
        if snapshot_date is not None and origin != "Internet"
        else ""
    )
    print(f"Origem dos dados: {origin}{date_text}")


def print_market_summary(summary: dict[str, int]) -> None:
    """Print counts for every supported category."""
    print("\nRESUMO DO MERCADO\n")
    print(f"Ações encontradas:               {summary['stocks']}")
    print(f"Fundos Imobiliários encontrados: {summary['fiis']}")
    print(f"Criptomoedas encontradas:        {summary['crypto']}")
    print(f"Total de ativos:                 {summary['total']}")


def print_indicators(indicators: pd.DataFrame) -> None:
    """Print SELIC and CDI separately from tradable assets."""
    print("\nINDICADORES ECONÔMICOS\n")
    indexed = indicators.set_index("indicator") if not indicators.empty else None
    for name in ("SELIC", "CDI"):
        if indexed is None or name not in indexed.index:
            print(f"{name}: indisponível")
            continue
        row = indexed.loc[name]
        if _is_missing(row["value"]):
            print(f"{name}: indisponível")
            continue
        date_text = (
            f" (referência: {row['updated_at']:%d/%m/%Y})"
            if not _is_missing(row["updated_at"])
            else ""
        )
        print(f"{name}: {format_number_br(row['value'], 2)}% a.a.{date_text}")


def print_assets_table(
    data: pd.DataFrame,
    page: int,
    total_pages: int,
    total_items: int,
    page_size: int,
) -> None:
    """Print one fixed-width page of assets."""
    print("\nATIVOS DISPONÍVEIS\n")
    if data.empty:
        print("Nenhum ativo encontrado para o filtro selecionado.")
        return

    header = (
        f"{'Ticker':<10} {'Categoria':<14} {'Nome':<27} "
        f"{'Preço':>15} {'Variação':>11} {'Part. índice':>12}"
    )
    print(header)
    print("-" * len(header))
    for _, row in data.iterrows():
        price = format_currency(row["price"])
        change = format_percent(row["change_percent"], table=True)
        composition = (
            f"{format_number_br(row['composition_percent'], 3)}%"
            if not _is_missing(row["composition_percent"])
            else "—"
        )
        print(
            f"{_shorten(row['ticker'], 10):<10} "
            f"{_shorten(row['asset_type'], 14):<14} "
            f"{_shorten(row['name'], 27):<27} "
            f"{price:>15} {change:>11} {composition:>12}"
        )
    first_item = (page - 1) * page_size + 1
    last_item = first_item + len(data) - 1
    print(
        f"\nPágina {page} de {total_pages} | "
        f"Exibindo {first_item}-{last_item} de {total_items} ativos"
    )


def print_asset_details(asset: pd.Series) -> None:
    """Print only fields that are available for the selected asset."""
    print(f"\n{SEPARATOR}")
    print(f"{asset['ticker']} — {asset['name']}")
    print(SEPARATOR)
    print(f"Tipo: {asset['asset_type']}")
    if not _is_missing(asset["subtype"]):
        print(f"Subtipo: {asset['subtype']}")
    if not _is_missing(asset["price"]):
        print(f"Preço atual: {format_currency(asset['price'])}")
    if not _is_missing(asset["change_percent"]):
        print(f"Variação no período: {format_percent(asset['change_percent'])}")
    if not _is_missing(asset["open"]):
        print(f"Abertura: {format_currency(asset['open'])}")
    if not _is_missing(asset["high"]):
        print(f"Máxima: {format_currency(asset['high'])}")
    if not _is_missing(asset["low"]):
        print(f"Mínima: {format_currency(asset['low'])}")
    if not _is_missing(asset["volume"]):
        print(f"Volume: {format_number_br(asset['volume'], 8)}")
    if not _is_missing(asset["composition_percent"]):
        print(
            "Participação no índice: "
            f"{format_number_br(asset['composition_percent'], 3)}%"
        )
    if not _is_missing(asset["theoretical_quantity"]):
        print(
            "Quantidade teórica: "
            f"{format_number_br(asset['theoretical_quantity'], 0)}"
        )
    if not _is_missing(asset["updated_at"]):
        updated = asset["updated_at"]
        date_format = (
            "%d/%m/%Y"
            if updated.time() == datetime.min.time()
            else "%d/%m/%Y %H:%M:%S"
        )
        print(f"Última atualização: {updated:{date_format}}")
    print(f"Fonte: {asset['source']}")
    print(SEPARATOR)


def print_ranking(data: pd.DataFrame, title: str, column: str) -> None:
    """Print one ranking with formatting appropriate to its metric."""
    print(f"\n{title.upper()}\n")
    if data.empty:
        print("Não há dados disponíveis para este ranking.")
        return

    labels = {
        "composition_percent": "Participação",
        "change_percent": "Variação",
        "volume": "Volume",
    }
    print(f"{'#':<4} {'Ticker':<10} {'Nome':<35} {labels[column]:>20}")
    print("-" * 72)
    for position, (_, row) in enumerate(data.iterrows(), start=1):
        if column == "change_percent":
            value = format_percent(row[column], table=True)
        elif column == "composition_percent":
            value = f"{format_number_br(row[column], 3)}%"
        else:
            value = format_number_br(row[column], 4)
        print(
            f"{position:<4} {_shorten(row['ticker'], 10):<10} "
            f"{_shorten(row['name'], 35):<35} {value:>20}"
        )


def print_asset_comparison(data: pd.DataFrame) -> None:
    """Compare heterogeneous assets without fabricating unavailable fields."""
    print("\nCOMPARAÇÃO DE ATIVOS\n")
    header = (
        f"{'Ticker':<10} {'Categoria':<14} {'Preço':>16} "
        f"{'Variação':>11} {'Part. índice':>14} {'Volume':>18}"
    )
    print(header)
    print("-" * len(header))
    for _, row in data.iterrows():
        composition = (
            f"{format_number_br(row['composition_percent'], 3)}%"
            if not _is_missing(row["composition_percent"])
            else "—"
        )
        volume = (
            format_number_br(row["volume"], 4)
            if not _is_missing(row["volume"])
            else "—"
        )
        print(
            f"{_shorten(row['ticker'], 10):<10} "
            f"{_shorten(row['asset_type'], 14):<14} "
            f"{format_currency(row['price']):>16} "
            f"{format_percent(row['change_percent'], table=True):>11} "
            f"{composition:>14} {volume:>18}"
        )


def print_source_warnings(errors: dict[str, str]) -> None:
    """Print non-fatal source failures without hiding unavailable data."""
    if not errors:
        return
    print("\nAVISOS DE FONTES\n")
    for source, message in errors.items():
        print(f"- {source}: {message}")


def print_exported_files(paths: dict[str, Path]) -> None:
    """Print the files produced by the export step."""
    print("\nARQUIVOS GERADOS\n")
    for label, path in paths.items():
        print(f"{label}: {path}")
