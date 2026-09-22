"""Cleaning and standardization functions for all collected market data."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

ASSET_COLUMNS = [
    "ticker",
    "name",
    "asset_type",
    "subtype",
    "price",
    "change_percent",
    "open",
    "high",
    "low",
    "volume",
    "composition_percent",
    "theoretical_quantity",
    "source",
    "updated_at",
]
INDICATOR_COLUMNS = [
    "indicator",
    "description",
    "value",
    "unit",
    "source",
    "updated_at",
]
B3_SOURCE_COLUMNS = {"cod", "asset", "type", "theoricalQty", "part"}
INDEX_CLASSIFICATION = {
    "IBOV": ("Ação", "B3 - Carteira do Ibovespa"),
    "IFIX": ("FII", "B3 - Carteira do IFIX"),
}


def parse_brazilian_number(value: Any) -> float | None:
    """Convert a Brazilian-formatted numeric value to a float."""
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    normalized = text.replace(".", "").replace(",", ".")
    try:
        return float(normalized)
    except ValueError as exc:
        raise ValueError(f"Valor numérico brasileiro inválido: {value!r}") from exc


def parse_decimal(value: Any) -> float | None:
    """Convert a JSON decimal value to float while preserving missing data."""
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError as exc:
        raise ValueError(f"Valor decimal inválido: {value!r}") from exc


def parse_b3_date(value: Any) -> pd.Timestamp:
    """Parse B3's DD/MM/YY reference date."""
    try:
        parsed = datetime.strptime(str(value).strip(), "%d/%m/%y")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Data de referência B3 inválida: {value!r}") from exc
    return pd.Timestamp(parsed)


def parse_bcb_date(value: Any) -> pd.Timestamp:
    """Parse Banco Central's DD/MM/YYYY observation date."""
    try:
        parsed = datetime.strptime(str(value).strip(), "%d/%m/%Y")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Data do Banco Central inválida: {value!r}") from exc
    return pd.Timestamp(parsed)


def parse_unix_timestamp(value: Any) -> pd.Timestamp | pd.NaT:
    """Parse Unix timestamps expressed in seconds, milliseconds, or finer units."""
    if value is None or pd.isna(value):
        return pd.NaT
    try:
        numeric_value = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Timestamp inválido: {value!r}") from exc

    absolute_value = abs(numeric_value)
    if absolute_value >= 10**17:
        unit = "ns"
    elif absolute_value >= 10**14:
        unit = "us"
    elif absolute_value >= 10**11:
        unit = "ms"
    else:
        unit = "s"
    return (
        pd.to_datetime(numeric_value, unit=unit, utc=True)
        .tz_convert("America/Sao_Paulo")
        .tz_localize(None)
    )


def classify_b3_index(index_code: str) -> tuple[str, str]:
    """Classify B3 records by their source index, not by ticker suffix."""
    normalized_index = index_code.strip().upper()
    try:
        return INDEX_CLASSIFICATION[normalized_index]
    except KeyError as exc:
        raise ValueError(f"Índice B3 não reconhecido: {index_code!r}.") from exc


def empty_asset_dataframe() -> pd.DataFrame:
    """Return an empty DataFrame with the common asset schema."""
    return _standardize_asset_types(pd.DataFrame(columns=ASSET_COLUMNS))


def _standardize_asset_types(data: pd.DataFrame) -> pd.DataFrame:
    """Apply consistent pandas dtypes to an asset DataFrame."""
    frame = data.reindex(columns=ASSET_COLUMNS).copy()
    for column in ("ticker", "name", "asset_type", "subtype", "source"):
        frame[column] = frame[column].astype("string")
    for column in (
        "price",
        "change_percent",
        "open",
        "high",
        "low",
        "volume",
        "composition_percent",
    ):
        frame[column] = pd.to_numeric(frame[column], errors="coerce").astype("Float64")
    frame["theoretical_quantity"] = pd.to_numeric(
        frame["theoretical_quantity"], errors="coerce"
    ).astype("Int64")
    frame["updated_at"] = pd.to_datetime(frame["updated_at"], errors="coerce")
    return frame


def build_b3_assets(raw_data: dict[str, Any], index_code: str) -> pd.DataFrame:
    """Build standardized stock or FII records from a B3 portfolio response."""
    asset_type, source = classify_b3_index(index_code)
    results = raw_data.get("results")
    header = raw_data.get("header")
    if not isinstance(results, list):
        raise ValueError("A resposta da B3 não contém uma lista de ativos.")
    if not isinstance(header, dict) or "date" not in header:
        raise ValueError("A resposta da B3 não contém a data da carteira.")
    if not results:
        return empty_asset_dataframe()

    source_frame = pd.DataFrame(results)
    missing = B3_SOURCE_COLUMNS.difference(source_frame.columns)
    if missing:
        raise ValueError(
            "A estrutura dos ativos B3 mudou. Campos ausentes: "
            f"{', '.join(sorted(missing))}."
        )

    reference_date = parse_b3_date(header["date"])
    records = []
    for item in results:
        ticker = str(item["cod"]).strip().upper()
        if not ticker:
            raise ValueError("A B3 retornou um registro sem ticker.")
        records.append(
            {
                "ticker": ticker,
                "name": str(item["asset"]).strip(),
                "asset_type": asset_type,
                "subtype": " ".join(str(item["type"]).split()),
                "price": None,
                "change_percent": None,
                "open": None,
                "high": None,
                "low": None,
                "volume": None,
                "composition_percent": parse_brazilian_number(item["part"]),
                "theoretical_quantity": parse_brazilian_number(item["theoricalQty"]),
                "source": source,
                "updated_at": reference_date,
            }
        )

    frame = _standardize_asset_types(pd.DataFrame(records))
    if frame["ticker"].duplicated().any():
        duplicates = ", ".join(frame.loc[frame["ticker"].duplicated(), "ticker"])
        raise ValueError(f"A B3 retornou tickers duplicados: {duplicates}.")
    return frame.sort_values("ticker", ignore_index=True)


def _crypto_metadata(symbols: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Transform the symbols endpoint's parallel arrays into a lookup."""
    metadata: dict[str, dict[str, str]] = {}
    for index, pair in enumerate(symbols["symbol"]):
        metadata[str(pair)] = {
            "name": str(symbols["description"][index]),
            "ticker": str(symbols["base-currency"][index]),
            "quote_currency": str(symbols["currency"][index]),
            "source_type": str(symbols["type"][index]),
        }
    return metadata


def build_crypto_assets(raw_data: dict[str, Any]) -> pd.DataFrame:
    """Build standardized crypto records from Mercado Bitcoin responses."""
    symbols = raw_data.get("symbols")
    tickers = raw_data.get("tickers")
    if not isinstance(symbols, dict) or not isinstance(tickers, list):
        raise ValueError("Os dados brutos de criptomoedas estão incompletos.")
    metadata = _crypto_metadata(symbols)
    records = []

    for item in tickers:
        pair = str(item.get("pair", "")).strip().upper()
        if pair not in metadata:
            raise ValueError(f"Metadados ausentes para o par {pair!r}.")
        pair_metadata = metadata[pair]
        price = parse_decimal(item.get("last"))
        opening = parse_decimal(item.get("open"))
        change_percent = None
        if price is not None and opening not in (None, 0):
            change_percent = (price / opening - 1) * 100

        records.append(
            {
                "ticker": pair_metadata["ticker"],
                "name": pair_metadata["name"],
                "asset_type": "Criptomoeda",
                "subtype": f"Par {pair_metadata['quote_currency']}",
                "price": price,
                "change_percent": change_percent,
                "open": opening,
                "high": parse_decimal(item.get("high")),
                "low": parse_decimal(item.get("low")),
                "volume": parse_decimal(item.get("vol")),
                "composition_percent": None,
                "theoretical_quantity": None,
                "source": "Mercado Bitcoin - API pública v4",
                "updated_at": parse_unix_timestamp(item.get("date")),
            }
        )

    return _standardize_asset_types(pd.DataFrame(records)).sort_values(
        "ticker", ignore_index=True
    )


def build_indicator_dataframe(raw_data: dict[str, Any]) -> pd.DataFrame:
    """Build SELIC and CDI rows, retaining missing indicators as unavailable."""
    raw_results = raw_data.get("results", [])
    if not isinstance(raw_results, list):
        raise ValueError("Os indicadores econômicos não estão em uma lista.")
    by_name = {
        str(item.get("indicator", "")).upper(): item
        for item in raw_results
        if isinstance(item, dict)
    }
    records = []
    descriptions = {
        "SELIC": "Meta Selic definida pelo Copom",
        "CDI": "CDI acumulada no mês anualizada, base 252",
    }
    for indicator in ("SELIC", "CDI"):
        item = by_name.get(indicator)
        records.append(
            {
                "indicator": indicator,
                "description": (
                    item.get("description") if item else descriptions[indicator]
                ),
                "value": parse_decimal(item.get("value")) if item else None,
                "unit": item.get("unit") if item else "% a.a.",
                "source": item.get("source") if item else "Banco Central do Brasil",
                "updated_at": parse_bcb_date(item.get("date")) if item else pd.NaT,
            }
        )

    frame = pd.DataFrame(records, columns=INDICATOR_COLUMNS)
    for column in ("indicator", "description", "unit", "source"):
        frame[column] = frame[column].astype("string")
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce").astype("Float64")
    frame["updated_at"] = pd.to_datetime(frame["updated_at"], errors="coerce")
    return frame


def combine_assets(*frames: pd.DataFrame) -> pd.DataFrame:
    """Combine asset categories while preserving the common schema."""
    valid_frames = [frame.reindex(columns=ASSET_COLUMNS) for frame in frames]
    if not valid_frames:
        return empty_asset_dataframe()
    combined = pd.concat(valid_frames, ignore_index=True)
    return _standardize_asset_types(combined).sort_values(
        ["asset_type", "ticker"], ignore_index=True
    )


def build_dataframe(raw_data: dict[str, Any]) -> pd.DataFrame:
    """Backward-compatible alias for the original Ibovespa transformation."""
    return build_b3_assets(raw_data, "IBOV")
