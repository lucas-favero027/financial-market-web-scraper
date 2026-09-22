"""Scraper for public BRL cryptocurrency market data from Mercado Bitcoin."""

from __future__ import annotations

from typing import Any

import requests

from src.scrapers.common import DEFAULT_TIMEOUT, ScraperError, request_json

SYMBOLS_URL = "https://api.mercadobitcoin.net/api/v4/symbols"
TICKERS_URL = "https://api.mercadobitcoin.net/api/v4/tickers"
CRYPTO_ASSETS = (
    "BTC", "ETH", "SOL", "USDT", "USDC", "XRP", "ADA", "DOGE", "AVAX",
    "LINK", "LTC", "BCH", "DOT", "UNI", "AAVE", "SUI", "TRX", "NEAR",
    "ATOM", "PAXG",
)


def _validate_symbols(data: Any) -> dict[str, Any]:
    """Validate the parallel arrays returned by the symbols endpoint."""
    if not isinstance(data, dict):
        raise ScraperError("O Mercado Bitcoin retornou símbolos em formato inválido.")
    required = {"symbol", "description", "base-currency", "currency", "type"}
    missing = required.difference(data)
    if missing:
        raise ScraperError(
            "A estrutura de símbolos do Mercado Bitcoin mudou. "
            f"Campos ausentes: {', '.join(sorted(missing))}."
        )
    if any(not isinstance(data[key], list) for key in required):
        raise ScraperError("As listas de símbolos do Mercado Bitcoin são inválidas.")
    lengths = {len(data[key]) for key in required}
    if len(lengths) != 1:
        raise ScraperError("As listas de símbolos têm tamanhos diferentes.")
    return data


def _validate_tickers(data: Any) -> list[dict[str, Any]]:
    """Validate the ticker list returned by Mercado Bitcoin."""
    if not isinstance(data, list):
        raise ScraperError("O Mercado Bitcoin retornou cotações em formato inválido.")
    if any(not isinstance(item, dict) or "pair" not in item for item in data):
        raise ScraperError("Uma cotação do Mercado Bitcoin possui estrutura inválida.")
    return data


def fetch_crypto_market(
    timeout: int | float = DEFAULT_TIMEOUT,
    session: requests.Session | None = None,
    assets: tuple[str, ...] = CRYPTO_ASSETS,
) -> dict[str, Any]:
    """Fetch metadata and ticker data for selected BRL crypto pairs."""
    normalized_assets = tuple(dict.fromkeys(asset.strip().upper() for asset in assets))
    if not normalized_assets or any(not asset for asset in normalized_assets):
        raise ValueError("Informe ao menos uma criptomoeda válida.")

    pairs = ",".join(f"{asset}-BRL" for asset in normalized_assets)
    http_session = session or requests.Session()
    should_close_session = session is None
    try:
        symbols = request_json(
            http_session,
            SYMBOLS_URL,
            source_name="Mercado Bitcoin (símbolos)",
            timeout=timeout,
            params={"symbols": pairs},
        )
        tickers = request_json(
            http_session,
            TICKERS_URL,
            source_name="Mercado Bitcoin (cotações)",
            timeout=timeout,
            params={"symbols": pairs},
        )
        return {
            "symbols": _validate_symbols(symbols),
            "tickers": _validate_tickers(tickers),
        }
    finally:
        if should_close_session:
            http_session.close()

