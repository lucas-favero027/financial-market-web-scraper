"""Tests for monetary, percentage, and missing-value terminal formatting."""

from __future__ import annotations

import pandas as pd

from src.display import format_currency, format_number_br, format_percent


def test_brazilian_terminal_formatting() -> None:
    """Money and percentages should use Brazilian display separators."""
    assert format_currency(443028.5) == "R$ 443.028,50"
    assert format_percent(1.234) == "+1,23%"
    assert format_percent(-0.5) == "-0,50%"
    assert format_number_br(4_410_957_710, 0) == "4.410.957.710"


def test_missing_values_are_not_rendered_as_zero() -> None:
    """Unknown values should be explicit, never numeric zero."""
    assert format_currency(None) == "—"
    assert format_percent(pd.NA) == "indisponível"
    assert format_percent(pd.NA, table=True) == "—"
