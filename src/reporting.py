"""Generate a lightweight HTML report and PNG charts from processed data."""

from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path

import pandas as pd
from matplotlib.figure import Figure

from src.analysis import build_named_ranking, data_quality_summary, market_summary

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = PROJECT_ROOT / "data" / "processed" / "report"

COLORS = {
    "blue": "#2563eb",
    "cyan": "#0891b2",
    "green": "#16a34a",
    "red": "#dc2626",
    "slate": "#334155",
}


def _save_horizontal_chart(
    data: pd.DataFrame,
    *,
    value_column: str,
    title: str,
    x_label: str,
    path: Path,
    color: str,
) -> None:
    """Save a compact horizontal ranking chart."""
    ordered = data.sort_values(value_column, ascending=True)
    figure = Figure(figsize=(9, 5.2), layout="constrained")
    axis = figure.subplots()
    axis.barh(ordered["ticker"], ordered[value_column], color=color)
    axis.set_title(title, fontsize=15, fontweight="bold", pad=14)
    axis.set_xlabel(x_label)
    axis.grid(axis="x", linestyle="--", alpha=0.25)
    axis.spines[["top", "right", "left"]].set_visible(False)
    figure.savefig(path, dpi=150, facecolor="white")


def _save_crypto_change_chart(data: pd.DataFrame, path: Path) -> None:
    """Save crypto change bars colored by positive or negative direction."""
    ordered = data.sort_values("change_percent", ascending=True)
    colors = [
        COLORS["green"] if value >= 0 else COLORS["red"]
        for value in ordered["change_percent"]
    ]
    figure = Figure(figsize=(9, 5.2), layout="constrained")
    axis = figure.subplots()
    axis.barh(ordered["ticker"], ordered["change_percent"], color=colors)
    axis.axvline(0, color=COLORS["slate"], linewidth=0.8)
    axis.set_title("Variação das criptomoedas", fontsize=15, fontweight="bold", pad=14)
    axis.set_xlabel("Variação calculada a partir de last e open (%)")
    axis.grid(axis="x", linestyle="--", alpha=0.25)
    axis.spines[["top", "right", "left"]].set_visible(False)
    figure.savefig(path, dpi=150, facecolor="white")


def _format_indicator_table(indicators: pd.DataFrame) -> str:
    """Return an HTML table while keeping unavailable observations explicit."""
    formatted = indicators.copy()
    formatted["value"] = formatted["value"].map(
        lambda value: "indisponível" if pd.isna(value) else f"{float(value):.2f}% a.a."
    )
    formatted["updated_at"] = formatted["updated_at"].map(
        lambda value: "indisponível" if pd.isna(value) else value.strftime("%d/%m/%Y")
    )
    formatted = formatted.rename(
        columns={
            "indicator": "Indicador",
            "description": "Descrição",
            "value": "Valor",
            "updated_at": "Referência",
            "source": "Fonte",
        }
    )
    return formatted[
        ["Indicador", "Descrição", "Valor", "Referência", "Fonte"]
    ].to_html(index=False, classes="data-table", border=0)


def _format_quality_table(data: pd.DataFrame) -> str:
    """Format coverage percentages for the report's quality section."""
    labels = {
        "asset_type": "Categoria",
        "records": "Registros",
        "price": "Preço",
        "change_percent": "Variação",
        "volume": "Volume",
        "composition_percent": "Participação",
        "updated_at": "Atualização",
    }
    selected = data[list(labels)].rename(columns=labels)
    for column in ("Preço", "Variação", "Volume", "Participação", "Atualização"):
        selected[column] = selected[column].map(lambda value: f"{value:.1f}%")
    return selected.to_html(index=False, classes="data-table", border=0)


def generate_market_report(
    market_data: pd.DataFrame,
    indicators: pd.DataFrame,
    *,
    generated_at: datetime,
    data_origin: str,
    output_dir: Path = REPORT_DIR,
) -> dict[str, Path]:
    """Create charts and an HTML dashboard from the current processed data."""
    output_dir.mkdir(parents=True, exist_ok=True)
    chart_paths: dict[str, Path] = {}

    chart_specs = (
        (
            "ibov",
            "composition_percent",
            "Maiores participações no Ibovespa",
            "Participação no índice (%)",
            "ibov-composition.png",
            COLORS["blue"],
        ),
        (
            "fiis",
            "composition_percent",
            "Maiores participações no IFIX",
            "Participação no índice (%)",
            "ifix-composition.png",
            COLORS["cyan"],
        ),
        (
            "crypto-volume",
            "volume",
            "Maiores volumes de criptomoedas",
            "Volume informado pela fonte",
            "crypto-volume.png",
            COLORS["slate"],
        ),
    )
    for ranking_name, column, title, x_label, filename, color in chart_specs:
        _, _, ranking = build_named_ranking(market_data, ranking_name, limit=10)
        if ranking.empty:
            continue
        chart_path = output_dir / filename
        _save_horizontal_chart(
            ranking,
            value_column=column,
            title=title,
            x_label=x_label,
            path=chart_path,
            color=color,
        )
        chart_paths[ranking_name] = chart_path

    crypto = market_data.loc[
        (market_data["asset_type"] == "Criptomoeda")
        & market_data["change_percent"].notna()
    ].nlargest(10, "volume")
    if not crypto.empty:
        change_path = output_dir / "crypto-change.png"
        _save_crypto_change_chart(crypto, change_path)
        chart_paths["crypto-change"] = change_path

    summary = market_summary(market_data)
    quality_html = _format_quality_table(data_quality_summary(market_data))
    indicators_html = _format_indicator_table(indicators)
    chart_cards = "\n".join(
        f'<article class="chart-card"><img src="{escape(path.name)}" '
        f'alt="Gráfico {escape(name)}"></article>'
        for name, path in chart_paths.items()
    )
    html = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Financial Market Web Scraper — Relatório</title>
  <style>
    :root {{ color-scheme: light; --navy:#0f172a; --slate:#475569; --line:#e2e8f0; --blue:#2563eb; }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; font:16px/1.5 system-ui,sans-serif; background:#f8fafc; color:var(--navy); }}
    main {{ width:min(1180px,92vw); margin:42px auto 64px; }}
    header {{ background:linear-gradient(135deg,#0f172a,#1e3a8a); color:white; padding:34px; border-radius:18px; }}
    h1 {{ margin:0 0 8px; font-size:clamp(28px,4vw,46px); }}
    h2 {{ margin-top:42px; }}
    .meta {{ color:#bfdbfe; margin:4px 0; }}
    .cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:16px; margin-top:24px; }}
    .card,.chart-card,.table-wrap {{ background:white; border:1px solid var(--line); border-radius:14px; padding:20px; box-shadow:0 8px 24px #0f172a0d; }}
    .card strong {{ display:block; color:var(--blue); font-size:30px; }}
    .charts {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(390px,1fr)); gap:18px; }}
    .chart-card img {{ width:100%; height:auto; display:block; }}
    .table-wrap {{ overflow-x:auto; }}
    .data-table {{ width:100%; border-collapse:collapse; }}
    .data-table th,.data-table td {{ padding:11px 12px; border-bottom:1px solid var(--line); text-align:left; white-space:nowrap; }}
    .data-table th {{ background:#eff6ff; }}
    footer {{ color:var(--slate); margin-top:36px; font-size:14px; }}
  </style>
</head>
<body>
<main>
  <header>
    <h1>Financial Market Web Scraper</h1>
    <p class="meta">Relatório gerado em {generated_at:%d/%m/%Y %H:%M:%S}</p>
    <p class="meta">Origem dos dados: {escape(data_origin)}</p>
  </header>
  <section class="cards">
    <article class="card"><span>Ações</span><strong>{summary['stocks']}</strong></article>
    <article class="card"><span>FIIs</span><strong>{summary['fiis']}</strong></article>
    <article class="card"><span>Criptomoedas</span><strong>{summary['crypto']}</strong></article>
    <article class="card"><span>Total de ativos</span><strong>{summary['total']}</strong></article>
  </section>
  <h2>Indicadores econômicos</h2>
  <div class="table-wrap">{indicators_html}</div>
  <h2>Análises visuais</h2>
  <section class="charts">{chart_cards or '<p>Não há dados suficientes para gerar gráficos.</p>'}</section>
  <h2>Qualidade e disponibilidade dos dados</h2>
  <p>A cobertura representa a proporção de registros em que cada campo foi fornecido pela fonte.</p>
  <div class="table-wrap">{quality_html}</div>
  <footer>Dados informativos. Este relatório não constitui recomendação de investimento.</footer>
</main>
</body>
</html>
"""
    report_path = output_dir / "index.html"
    report_path.write_text(html, encoding="utf-8")
    return {"html_report": report_path, **{f"chart_{key}": value for key, value in chart_paths.items()}}
