"""Histórico de métricas por cliente, para permitir comparação mês a mês (ou
quinzena a quinzena) nos relatórios de acompanhamento."""

from __future__ import annotations

import json
from pathlib import Path

from .metrics import Metrics
from .scraper import Platform, ProfileData

HISTORY_DIR = Path(__file__).resolve().parent.parent / "data" / "history"


def _history_path(platform: Platform, handle: str) -> Path:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    safe_handle = handle.lower().replace("/", "_")
    return HISTORY_DIR / f"{platform}_{safe_handle}.json"


def load_history(platform: Platform, handle: str) -> list[dict]:
    path = _history_path(platform, handle)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_previous_snapshot(platform: Platform, handle: str) -> dict | None:
    history = load_history(platform, handle)
    return history[-1] if history else None


def build_snapshot(profile: ProfileData, metrics: Metrics) -> dict:
    return {
        "snapshot_date": profile.fetched_at.isoformat(),
        "followers": profile.followers,
        "following": profile.following,
        "posts_count": profile.posts_count,
        "avg_likes": metrics.avg_likes,
        "avg_comments": metrics.avg_comments,
        "avg_views": metrics.avg_views,
        "engagement_rate": metrics.engagement_rate,
        "posting_frequency": metrics.posting_frequency,
    }


def save_snapshot(platform: Platform, handle: str, snapshot: dict) -> None:
    path = _history_path(platform, handle)
    history = load_history(platform, handle)
    history.append(snapshot)
    with path.open("w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def follower_series(platform: Platform, handle: str) -> list[tuple[str, int]]:
    """Retorna [(data, seguidores), ...] de todo o histórico salvo, para gráfico de evolução."""
    history = load_history(platform, handle)
    return [(h["snapshot_date"], h["followers"]) for h in history]
