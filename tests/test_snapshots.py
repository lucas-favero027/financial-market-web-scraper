"""Tests for reproducible snapshots and the optional local cache."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.snapshots import SnapshotError, find_recent_snapshot, load_snapshot


def _write_snapshot(path: Path, collected_at: datetime) -> None:
    """Create a minimal structurally valid snapshot for one test."""
    content = {
        "collected_at": collected_at.isoformat(),
        "sources": {},
        "errors": {},
    }
    path.write_text(json.dumps(content), encoding="utf-8")


def test_load_snapshot_validates_required_fields(tmp_path: Path) -> None:
    """A malformed file should fail before the processing pipeline starts."""
    path = tmp_path / "invalid.json"
    path.write_text('{"collected_at": "invalid"}', encoding="utf-8")

    with pytest.raises(SnapshotError, match="sources"):
        load_snapshot(path)


def test_recent_snapshot_is_used_inside_cache_window(tmp_path: Path) -> None:
    """The cache should return the newest valid collection within its TTL."""
    now = datetime(2026, 9, 22, 12, 0)
    recent_path = tmp_path / "market_snapshot_20260922_115500.json"
    old_path = tmp_path / "market_snapshot_20260922_100000.json"
    _write_snapshot(recent_path, now - timedelta(minutes=5))
    _write_snapshot(old_path, now - timedelta(hours=2))

    snapshot = find_recent_snapshot(15, raw_dir=tmp_path, now=now)

    assert snapshot is not None
    assert snapshot["path"] == recent_path


def test_expired_cache_returns_none(tmp_path: Path) -> None:
    """An expired snapshot must not silently replace an online collection."""
    now = datetime(2026, 9, 22, 12, 0)
    _write_snapshot(
        tmp_path / "market_snapshot_20260922_100000.json",
        now - timedelta(hours=2),
    )

    assert find_recent_snapshot(15, raw_dir=tmp_path, now=now) is None
