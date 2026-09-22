"""Load reproducible demo data and recent local collection snapshots."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
SAMPLE_SNAPSHOT = PROJECT_ROOT / "data" / "samples" / "market_sample.json"


class SnapshotError(ValueError):
    """Raised when a saved market snapshot is absent or structurally invalid."""


def load_snapshot(path: Path) -> dict[str, Any]:
    """Read and validate one raw snapshot produced by the application."""
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SnapshotError(f"Snapshot não encontrado: {path}.") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise SnapshotError(f"Não foi possível ler o snapshot {path}: {exc}.") from exc

    if not isinstance(content, dict):
        raise SnapshotError("O snapshot deve conter um objeto JSON.")
    sources = content.get("sources")
    errors = content.get("errors", {})
    collected_at_text = content.get("collected_at")
    if not isinstance(sources, dict):
        raise SnapshotError("O snapshot não contém o objeto 'sources'.")
    if not isinstance(errors, dict):
        raise SnapshotError("O campo 'errors' do snapshot é inválido.")
    try:
        collected_at = datetime.fromisoformat(str(collected_at_text))
    except (TypeError, ValueError) as exc:
        raise SnapshotError("A data de coleta do snapshot é inválida.") from exc

    return {
        "path": path,
        "collected_at": collected_at,
        "sources": sources,
        "errors": {str(key): str(value) for key, value in errors.items()},
    }


def find_recent_snapshot(
    max_age_minutes: int,
    *,
    raw_dir: Path = RAW_DIR,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    """Return the newest valid snapshot inside the configured cache window."""
    if max_age_minutes <= 0:
        raise ValueError("O tempo de cache deve ser maior que zero.")

    reference_time = now or datetime.now()
    maximum_age = timedelta(minutes=max_age_minutes)
    candidates = sorted(raw_dir.glob("market_snapshot_*.json"), reverse=True)
    for path in candidates:
        try:
            snapshot = load_snapshot(path)
        except SnapshotError:
            continue
        age = reference_time - snapshot["collected_at"]
        if timedelta(0) <= age <= maximum_age:
            return snapshot
    return None
