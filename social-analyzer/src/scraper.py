"""Coleta dados públicos de perfis do Instagram e TikTok via Apify e normaliza
para um schema comum consumido pelo restante do pipeline (metrics/report)."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from apify_client import ApifyClient

IG_ACTOR_ID = "apify/instagram-profile-scraper"
TIKTOK_ACTOR_ID = "clockworks/tiktok-profile-scraper"

Platform = Literal["instagram", "tiktok"]


class ScraperError(RuntimeError):
    """Erro ao coletar ou interpretar dados de uma rede social."""


@dataclass
class Post:
    url: str
    caption: str
    timestamp: datetime | None
    likes: int
    comments: int
    views: int | None
    post_type: str = ""

    @property
    def engagements(self) -> int:
        return self.likes + self.comments


@dataclass
class ProfileData:
    platform: Platform
    handle: str
    full_name: str
    bio: str
    verified: bool
    followers: int
    following: int
    posts_count: int
    profile_pic_url: str
    fetched_at: datetime
    posts: list[Post] = field(default_factory=list)


def clean_handle(platform: Platform, raw: str) -> str:
    """Aceita @usuario, usuario ou URL completa e devolve só o username."""
    raw = raw.strip()
    raw = re.sub(r"^https?://(www\.)?(instagram\.com|tiktok\.com)/", "", raw, flags=re.I)
    raw = raw.strip("/")
    if platform == "tiktok" and raw.startswith("@"):
        raw = raw[1:]
    if platform == "instagram" and raw.startswith("@"):
        raw = raw[1:]
    # remove query string / sub-paths remanescentes (ex: usuario/reels)
    raw = raw.split("?")[0].split("/")[0]
    return raw


def _get_apify_client(token: str | None = None) -> ApifyClient:
    token = token or os.environ.get("APIFY_API_TOKEN") or os.environ.get("APIFY_TOKEN")
    if not token:
        raise ScraperError(
            "Token da Apify não encontrado. Defina a variável de ambiente "
            "APIFY_API_TOKEN (obtenha em https://console.apify.com/account/integrations) "
            "ou passe --apify-token."
        )
    return ApifyClient(token)


def _parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def fetch_instagram_profile(username: str, posts_limit: int, token: str | None = None) -> ProfileData:
    username = clean_handle("instagram", username)
    client = _get_apify_client(token)

    run = client.actor(IG_ACTOR_ID).call(run_input={"usernames": [username]})
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())

    if not items:
        raise ScraperError(f"Nenhum dado retornado para o Instagram @{username}. Verifique o @ informado.")

    profile = items[0]
    if profile.get("error") or "followersCount" not in profile:
        raise ScraperError(
            f"Não foi possível coletar @{username} no Instagram "
            f"(perfil privado, inexistente ou bloqueado): {profile.get('error', 'sem detalhes')}"
        )

    raw_posts = (profile.get("latestPosts") or [])[:posts_limit]
    posts = [
        Post(
            url=p.get("url", ""),
            caption=(p.get("caption") or "").strip(),
            timestamp=_parse_iso(p.get("timestamp")),
            likes=int(p.get("likesCount") or 0),
            comments=int(p.get("commentsCount") or 0),
            views=p.get("videoViewCount"),
            post_type=p.get("type", ""),
        )
        for p in raw_posts
    ]

    return ProfileData(
        platform="instagram",
        handle=profile.get("username", username),
        full_name=profile.get("fullName") or "",
        bio=profile.get("biography") or "",
        verified=bool(profile.get("verified")),
        followers=int(profile.get("followersCount") or 0),
        following=int(profile.get("followsCount") or 0),
        posts_count=int(profile.get("postsCount") or 0),
        profile_pic_url=profile.get("profilePicUrlHD") or profile.get("profilePicUrl") or "",
        fetched_at=datetime.now(timezone.utc),
        posts=posts,
    )


def fetch_tiktok_profile(username: str, posts_limit: int, token: str | None = None) -> ProfileData:
    username = clean_handle("tiktok", username)
    client = _get_apify_client(token)

    run = client.actor(TIKTOK_ACTOR_ID).call(
        run_input={
            "profiles": [username],
            "resultsPerPage": posts_limit,
            "profileSorting": "latest",
            "profileScrapeSections": ["videos"],
            "excludePinnedPosts": False,
        }
    )
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())

    if not items:
        raise ScraperError(f"Nenhum dado retornado para o TikTok @{username}. Verifique o usuário informado.")

    author = items[0].get("authorMeta") or {}
    if not author:
        raise ScraperError(f"Não foi possível coletar @{username} no TikTok (perfil privado ou inexistente).")

    posts = [
        Post(
            url=item.get("webVideoUrl", ""),
            caption=(item.get("text") or "").strip(),
            timestamp=_parse_iso(item.get("createTimeISO") or item.get("createTime")),
            likes=int(item.get("diggCount") or 0),
            comments=int(item.get("commentCount") or 0),
            views=item.get("playCount"),
            post_type="video",
        )
        for item in items[:posts_limit]
        if not item.get("isAd")
    ]

    return ProfileData(
        platform="tiktok",
        handle=author.get("name", username),
        full_name=author.get("nickName") or "",
        bio=author.get("signature") or "",
        verified=bool(author.get("verified")),
        followers=int(author.get("fans") or 0),
        following=int(author.get("following") or 0),
        posts_count=int(author.get("video") or 0),
        profile_pic_url=author.get("avatar") or "",
        fetched_at=datetime.now(timezone.utc),
        posts=posts,
    )


def fetch_profile(platform: Platform, handle: str, posts_limit: int, token: str | None = None) -> ProfileData:
    if platform == "instagram":
        return fetch_instagram_profile(handle, posts_limit, token)
    if platform == "tiktok":
        return fetch_tiktok_profile(handle, posts_limit, token)
    raise ValueError(f"Plataforma desconhecida: {platform}")
