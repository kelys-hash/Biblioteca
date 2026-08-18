"""Cálculo de métricas de engajamento e geração de prós/contras a partir de
um ProfileData coletado (ver scraper.py)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from .scraper import Platform, ProfileData, Post

# Benchmarks aproximados de mercado (uso apenas como heurística de diagnóstico,
# não são valores absolutos de nenhum estudo específico).
ENGAGEMENT_BENCHMARKS = {
    "instagram": {"baixo": 1.0, "bom": 3.5},
    "tiktok": {"baixo": 3.0, "bom": 6.0},
}
POSTING_FREQ_BENCHMARKS = {"baixo": 2.0, "bom": 5.0}  # posts por semana


@dataclass
class Metrics:
    avg_likes: float
    avg_comments: float
    avg_views: float | None
    engagement_rate: float  # em %
    posting_frequency: float  # posts por semana
    best_post: Post | None
    worst_post: Post | None
    posts_analyzed: int


def compute_metrics(profile: ProfileData) -> Metrics:
    posts = profile.posts
    n = len(posts)

    if n == 0:
        return Metrics(
            avg_likes=0.0,
            avg_comments=0.0,
            avg_views=None,
            engagement_rate=0.0,
            posting_frequency=0.0,
            best_post=None,
            worst_post=None,
            posts_analyzed=0,
        )

    avg_likes = sum(p.likes for p in posts) / n
    avg_comments = sum(p.comments for p in posts) / n
    views = [p.views for p in posts if p.views is not None]
    avg_views = (sum(views) / len(views)) if views else None

    engagement_rate = 0.0
    if profile.followers > 0:
        engagement_rate = ((avg_likes + avg_comments) / profile.followers) * 100

    timestamps = [p.timestamp for p in posts if p.timestamp is not None]
    posting_frequency = 0.0
    if len(timestamps) >= 2:
        span_days = (max(timestamps) - min(timestamps)).total_seconds() / 86400
        if span_days > 0:
            posting_frequency = (n - 1) / (span_days / 7)

    ranked = sorted(posts, key=lambda p: p.engagements)
    worst_post, best_post = ranked[0], ranked[-1]

    return Metrics(
        avg_likes=avg_likes,
        avg_comments=avg_comments,
        avg_views=avg_views,
        engagement_rate=engagement_rate,
        posting_frequency=posting_frequency,
        best_post=best_post,
        worst_post=worst_post,
        posts_analyzed=n,
    )


def generate_pros_cons(profile: ProfileData, metrics: Metrics) -> list[tuple[str, str]]:
    """Retorna lista de (tipo, texto) com tipo em {"pro", "con"}."""
    items: list[tuple[str, str]] = []
    bands = ENGAGEMENT_BENCHMARKS[profile.platform]

    if metrics.posts_analyzed == 0:
        items.append(("con", "Não foi possível analisar posts recentes (perfil sem publicações públicas)."))
        return items

    if metrics.engagement_rate >= bands["bom"]:
        items.append((
            "pro",
            f"Taxa de engajamento de {metrics.engagement_rate:.1f}% está acima da média do mercado "
            f"({bands['bom']:.1f}%+), indicando audiência ativa e conectada ao conteúdo.",
        ))
    elif metrics.engagement_rate <= bands["baixo"]:
        items.append((
            "con",
            f"Taxa de engajamento de {metrics.engagement_rate:.1f}% está abaixo da média do mercado "
            f"(referência: {bands['baixo']:.1f}%), sugerindo baixa conexão com a audiência atual.",
        ))
    else:
        items.append((
            "pro",
            f"Taxa de engajamento de {metrics.engagement_rate:.1f}% está na média do mercado, com espaço "
            "claro para evolução.",
        ))

    if metrics.posting_frequency >= POSTING_FREQ_BENCHMARKS["bom"]:
        items.append((
            "pro",
            f"Frequência de publicação alta (~{metrics.posting_frequency:.1f} posts/semana), mantendo o "
            "perfil constantemente ativo.",
        ))
    elif metrics.posting_frequency <= POSTING_FREQ_BENCHMARKS["baixo"]:
        items.append((
            "con",
            f"Frequência de publicação baixa (~{metrics.posting_frequency:.1f} posts/semana), o que reduz "
            "o alcance orgânico e a chance de viralização.",
        ))
    else:
        items.append((
            "pro",
            f"Frequência de publicação razoável (~{metrics.posting_frequency:.1f} posts/semana).",
        ))

    if profile.verified:
        items.append(("pro", "Perfil verificado, o que aumenta a credibilidade junto à audiência."))

    if not profile.bio or len(profile.bio.strip()) < 10:
        items.append(("con", "Biografia curta ou vazia — perde a chance de comunicar proposta de valor e call-to-action."))

    if metrics.avg_views is not None and profile.followers > 0:
        view_ratio = metrics.avg_views / profile.followers
        if view_ratio >= 1.0:
            items.append((
                "pro",
                "Vídeos alcançam, em média, mais visualizações do que o total de seguidores — sinal de "
                "boa distribuição para além da base atual (alcance orgânico/algorítmico forte).",
            ))
        elif view_ratio < 0.3:
            items.append((
                "con",
                "Visualizações médias dos vídeos ficam bem abaixo do número de seguidores, indicando baixo "
                "alcance mesmo entre quem já segue o perfil.",
            ))

    if profile.followers > 0 and profile.following > 0:
        ratio = profile.followers / profile.following
        if ratio < 1:
            items.append((
                "con",
                "Perfil segue mais contas do que é seguido, o que pode transmitir menor autoridade no nicho.",
            ))

    return items


def compare_to_previous(current: dict, previous: dict | None) -> dict | None:
    """Compara snapshot atual com o anterior salvo em history.py. Retorna deltas ou None."""
    if previous is None:
        return None

    follower_delta = current["followers"] - previous["followers"]
    follower_growth_pct = (
        (follower_delta / previous["followers"] * 100) if previous["followers"] > 0 else 0.0
    )
    engagement_delta = current["engagement_rate"] - previous["engagement_rate"]

    return {
        "previous_date": previous["snapshot_date"],
        "follower_delta": follower_delta,
        "follower_growth_pct": follower_growth_pct,
        "engagement_delta": engagement_delta,
    }
