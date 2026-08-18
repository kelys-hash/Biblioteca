"""Geração de gráficos (PNG) embutidos no relatório PDF."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path

from .scraper import Post

COLOR_LIKES = "#2563eb"
COLOR_COMMENTS = "#f59e0b"
COLOR_LINE = "#16a34a"
COLOR_TEXT = "#1f2937"
COLOR_MUTED = "#9ca3af"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "text.color": COLOR_TEXT,
    "axes.edgecolor": COLOR_MUTED,
    "axes.labelcolor": COLOR_TEXT,
    "xtick.color": COLOR_TEXT,
    "ytick.color": COLOR_TEXT,
})


def engagement_bar_chart(posts: list[Post], out_path: Path) -> Path | None:
    if not posts:
        return None

    ordered = sorted(
        [p for p in posts if p.timestamp is not None],
        key=lambda p: p.timestamp,
    ) or posts
    labels = [f"P{i + 1}" for i in range(len(ordered))]
    likes = [p.likes for p in ordered]
    comments = [p.comments for p in ordered]

    fig, ax = plt.subplots(figsize=(6.4, 3.0), dpi=150)
    x = range(len(ordered))
    ax.bar(x, likes, color=COLOR_LIKES, label="Curtidas", width=0.6)
    ax.bar(x, comments, bottom=likes, color=COLOR_COMMENTS, label="Comentários", width=0.6)

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("Engajamento")
    ax.set_title("Engajamento por publicação (mais recentes primeiro →)", fontsize=10, loc="left")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    totals = [l + c for l, c in zip(likes, comments)]
    ax.set_ylim(0, max(totals) * 1.28 if totals else 1)
    ax.legend(frameon=False, loc="upper right", fontsize=8, ncols=2)
    fig.tight_layout()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, transparent=False, facecolor="white")
    plt.close(fig)
    return out_path


def follower_growth_chart(series: list[tuple[str, int]], out_path: Path) -> Path | None:
    """series: [(iso_date, followers), ...] em ordem cronológica. Precisa de >= 2 pontos."""
    if len(series) < 2:
        return None

    from datetime import datetime

    dates = [datetime.fromisoformat(d) for d, _ in series]
    followers = [f for _, f in series]

    fig, ax = plt.subplots(figsize=(6.4, 2.6), dpi=150)
    ax.plot(dates, followers, color=COLOR_LINE, marker="o", linewidth=2)
    ax.fill_between(dates, followers, min(followers) * 0.98 if min(followers) > 0 else 0, color=COLOR_LINE, alpha=0.08)

    ax.set_ylabel("Seguidores")
    ax.set_title("Evolução de seguidores", fontsize=10, loc="left")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m/%y"))
    fig.autofmt_xdate(rotation=30)
    fig.tight_layout()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, transparent=False, facecolor="white")
    plt.close(fig)
    return out_path
