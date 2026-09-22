"""Analysis functions for the cleaned Ibovespa portfolio."""

from __future__ import annotations

from difflib import get_close_matches
from typing import Any

import pandas as pd


class TickerNotFoundError(LookupError):
    """Raised when a ticker is not present in the collected portfolio."""


def find_stock(data: pd.DataFrame, ticker: str) -> pd.Series:
    """Return the row for a ticker, ignoring case and surrounding spaces."""
    normalized_ticker = ticker.strip().upper()
    if not normalized_ticker:
        raise TickerNotFoundError("Informe um ticker não vazio.")

    matches = data.loc[data["ticker"] == normalized_ticker]
    if not matches.empty:
        return matches.iloc[0]

    available = data["ticker"].dropna().astype(str).tolist()
    suggestions = get_close_matches(normalized_ticker, available, n=3, cutoff=0.5)
    hint = f" Tickers parecidos: {', '.join(suggestions)}." if suggestions else ""
    raise TickerNotFoundError(
        f"O ticker {normalized_ticker} não faz parte da carteira atual do Ibovespa."
        f"{hint}"
    )


def rank_stocks(
    data: pd.DataFrame,
    column: str,
    limit: int = 5,
    ascending: bool = False,
) -> pd.DataFrame:
    """Rank stocks by one numeric column and return the most useful fields."""
    allowed_columns = {"participacao_percentual", "quantidade_teorica"}
    if column not in allowed_columns:
        raise ValueError(f"Indicador não permitido para ranking: {column}.")
    if limit <= 0:
        raise ValueError("O limite do ranking deve ser maior que zero.")

    columns = ["ticker", "nome", column]
    return (
        data.dropna(subset=[column])
        .sort_values(column, ascending=ascending)
        .head(limit)[columns]
        .reset_index(drop=True)
    )


def portfolio_summary(data: pd.DataFrame) -> dict[str, Any]:
    """Calculate a small summary of the collected portfolio."""
    if data.empty:
        raise ValueError("Não há dados para analisar.")

    highest_participation = data.loc[data["participacao_percentual"].idxmax()]
    lowest_participation = data.loc[data["participacao_percentual"].idxmin()]
    highest_quantity = data.loc[data["quantidade_teorica"].idxmax()]

    return {
        "total_ativos": len(data),
        "data_referencia": data["data_referencia"].iloc[0],
        "maior_participacao": highest_participation,
        "menor_participacao": lowest_participation,
        "maior_quantidade_teorica": highest_quantity,
    }

