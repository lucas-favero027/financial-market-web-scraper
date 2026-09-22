"""Search, filtering, pagination, and summary functions for market data."""

from __future__ import annotations

from difflib import get_close_matches
from typing import Any

import pandas as pd

TYPE_FILTERS = {
    "all": None,
    "stocks": "Ação",
    "fii": "FII",
    "crypto": "Criptomoeda",
}


class TickerNotFoundError(LookupError):
    """Raised when a ticker is not present in the collected market data."""


def find_asset(data: pd.DataFrame, ticker: str) -> pd.Series:
    """Return one asset by ticker, ignoring case and surrounding spaces."""
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
        f"O ticker {normalized_ticker} não foi encontrado nos dados coletados.{hint}"
    )


def filter_assets(data: pd.DataFrame, type_filter: str = "all") -> pd.DataFrame:
    """Filter the common asset table by a CLI category name."""
    normalized_filter = type_filter.strip().lower()
    if normalized_filter not in TYPE_FILTERS:
        raise ValueError(f"Filtro de categoria inválido: {type_filter!r}.")
    asset_type = TYPE_FILTERS[normalized_filter]
    if asset_type is None:
        return data.copy()
    return data.loc[data["asset_type"] == asset_type].copy()


def paginate_assets(
    data: pd.DataFrame,
    page: int = 1,
    page_size: int = 20,
) -> tuple[pd.DataFrame, int, int]:
    """Return one page plus total page and item counts."""
    if page <= 0:
        raise ValueError("A página deve ser maior que zero.")
    if not 5 <= page_size <= 100:
        raise ValueError("O tamanho da página deve ficar entre 5 e 100.")

    total_items = len(data)
    total_pages = max(1, (total_items + page_size - 1) // page_size)
    if page > total_pages:
        raise ValueError(
            f"A página {page} não existe. Última página disponível: {total_pages}."
        )
    start = (page - 1) * page_size
    return data.iloc[start : start + page_size].copy(), total_pages, total_items


def market_summary(data: pd.DataFrame) -> dict[str, int]:
    """Count every supported asset category, including empty categories."""
    counts = data["asset_type"].value_counts() if not data.empty else pd.Series()
    return {
        "stocks": int(counts.get("Ação", 0)),
        "fiis": int(counts.get("FII", 0)),
        "crypto": int(counts.get("Criptomoeda", 0)),
        "total": int(len(data)),
    }


def rank_assets(
    data: pd.DataFrame,
    column: str,
    limit: int = 5,
    ascending: bool = False,
) -> pd.DataFrame:
    """Rank assets by an available numeric field."""
    allowed = {
        "price", "change_percent", "volume", "composition_percent",
        "theoretical_quantity",
    }
    if column not in allowed:
        raise ValueError(f"Indicador não permitido para ranking: {column}.")
    if limit <= 0:
        raise ValueError("O limite do ranking deve ser maior que zero.")
    return (
        data.dropna(subset=[column])
        .sort_values(column, ascending=ascending)
        .head(limit)[["ticker", "name", "asset_type", column]]
        .reset_index(drop=True)
    )


def find_stock(data: pd.DataFrame, ticker: str) -> pd.Series:
    """Backward-compatible alias for the original ticker lookup."""
    return find_asset(data, ticker)


def portfolio_summary(data: pd.DataFrame) -> dict[str, Any]:
    """Return a compact summary compatible with the original project concept."""
    if data.empty:
        raise ValueError("Não há dados para analisar.")
    result: dict[str, Any] = {"total_ativos": len(data)}
    composition = data.dropna(subset=["composition_percent"])
    quantities = data.dropna(subset=["theoretical_quantity"])
    if not composition.empty:
        result["maior_participacao"] = composition.loc[
            composition["composition_percent"].idxmax()
        ]
        result["menor_participacao"] = composition.loc[
            composition["composition_percent"].idxmin()
        ]
    if not quantities.empty:
        result["maior_quantidade_teorica"] = quantities.loc[
            quantities["theoretical_quantity"].idxmax()
        ]
    return result
