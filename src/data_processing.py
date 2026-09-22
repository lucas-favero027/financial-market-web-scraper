"""Transformation and cleaning functions for B3 portfolio data."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

SOURCE_COLUMNS = {
    "cod": "ticker",
    "asset": "nome",
    "type": "tipo",
    "theoricalQty": "quantidade_teorica",
    "part": "participacao_percentual",
}


def parse_brazilian_number(value: Any) -> float | None:
    """Convert a Brazilian-formatted number to a Python float.

    Examples: ``"4.043.349.180"`` becomes ``4043349180.0`` and
    ``"2,393"`` becomes ``2.393``.
    """
    if value is None or pd.isna(value):
        return None

    text = str(value).strip()
    if not text:
        return None

    normalized = text.replace(".", "").replace(",", ".")
    try:
        return float(normalized)
    except ValueError as exc:
        raise ValueError(f"Valor numérico inválido recebido da B3: {value!r}") from exc


def _parse_reference_date(raw_date: Any) -> pd.Timestamp:
    """Parse the reference date provided in B3's DD/MM/YY format."""
    try:
        parsed = datetime.strptime(str(raw_date).strip(), "%d/%m/%y")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Data de referência inválida: {raw_date!r}") from exc
    return pd.Timestamp(parsed.date())


def build_dataframe(raw_data: dict[str, Any]) -> pd.DataFrame:
    """Build and clean a DataFrame from the raw B3 response."""
    results = raw_data.get("results")
    header = raw_data.get("header")

    if not isinstance(results, list) or not results:
        raise ValueError("A resposta não contém ações para processar.")
    if not isinstance(header, dict) or "date" not in header:
        raise ValueError("A resposta não contém a data de referência da carteira.")

    frame = pd.DataFrame(results)
    missing_columns = set(SOURCE_COLUMNS).difference(frame.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"A estrutura dos ativos mudou. Campos ausentes: {missing}.")

    frame = frame[list(SOURCE_COLUMNS)].rename(columns=SOURCE_COLUMNS)
    frame["ticker"] = frame["ticker"].astype("string").str.strip().str.upper()
    frame["nome"] = frame["nome"].astype("string").str.strip()
    frame["tipo"] = (
        frame["tipo"].astype("string").str.strip().str.replace(r"\s+", " ", regex=True)
    )
    frame["quantidade_teorica"] = (
        frame["quantidade_teorica"].map(parse_brazilian_number).astype("Int64")
    )
    frame["participacao_percentual"] = (
        frame["participacao_percentual"]
        .map(parse_brazilian_number)
        .astype("Float64")
    )
    frame["data_referencia"] = _parse_reference_date(header["date"])

    if frame["ticker"].isna().any() or (frame["ticker"] == "").any():
        raise ValueError("Existem registros sem ticker na resposta da B3.")
    if frame["ticker"].duplicated().any():
        duplicated = ", ".join(frame.loc[frame["ticker"].duplicated(), "ticker"])
        raise ValueError(f"Foram encontrados tickers duplicados: {duplicated}.")

    return frame.sort_values("ticker", ignore_index=True)

