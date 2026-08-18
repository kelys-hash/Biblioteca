#!/usr/bin/env python3
"""CLI: gera um relatório em PDF de diagnóstico de Instagram/TikTok para
prospecção de clientes (marketing / social media).

Exemplos:
    python cli.py --instagram nomedocliente --client "Loja da Ana"
    python cli.py --tiktok nomedocliente --client "Loja da Ana" --agency "Minha Agência"
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import history, report
from src.metrics import compute_metrics
from src.scraper import ScraperError, fetch_profile

DEFAULT_POSTS_LIMIT = 12
REPORTS_DIR = Path(__file__).resolve().parent / "reports"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera relatório de diagnóstico de Instagram/TikTok em PDF.")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--instagram", metavar="USUARIO", help="@usuario ou URL do perfil no Instagram")
    target.add_argument("--tiktok", metavar="USUARIO", help="@usuario ou URL do perfil no TikTok")

    parser.add_argument("--client", metavar="NOME", help="Nome do cliente exibido no relatório (padrão: nome do perfil)")
    parser.add_argument("--agency", metavar="NOME", default="Sua Agência de Marketing", help="Nome da sua agência/empresa, exibido no relatório")
    parser.add_argument("--posts-limit", type=int, default=DEFAULT_POSTS_LIMIT, help=f"Quantos posts recentes analisar (padrão: {DEFAULT_POSTS_LIMIT})")
    parser.add_argument("--output", metavar="ARQUIVO.pdf", help="Caminho do PDF de saída (padrão: reports/<plataforma>_<usuario>_<data>.pdf)")
    parser.add_argument("--apify-token", metavar="TOKEN", help="Token da API da Apify (ou defina APIFY_API_TOKEN no ambiente)")
    parser.add_argument("--no-save", action="store_true", help="Não salvar este resultado no histórico do cliente")

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    platform = "instagram" if args.instagram else "tiktok"
    handle_input = args.instagram or args.tiktok

    print(f"→ Coletando dados públicos de {platform} para '{handle_input}'... (isso pode levar até 1-2 min)")
    try:
        profile = fetch_profile(platform, handle_input, args.posts_limit, token=args.apify_token)
    except ScraperError as e:
        print(f"✗ Erro: {e}", file=sys.stderr)
        return 1

    print(f"✓ Perfil coletado: @{profile.handle} · {profile.followers:,} seguidores · {len(profile.posts)} posts analisados".replace(",", "."))

    metrics = compute_metrics(profile)
    snapshot = history.build_snapshot(profile, metrics)

    client_name = args.client or profile.full_name or f"@{profile.handle}"
    output_path = Path(args.output) if args.output else (
        REPORTS_DIR / f"{platform}_{profile.handle}_{datetime.now().strftime('%Y%m%d')}.pdf"
    )

    print("→ Gerando PDF...")
    # Importante: comparar com o histórico ANTES de salvar o snapshot atual.
    report.build_report(
        profile=profile,
        metrics=metrics,
        output_path=output_path,
        client_name=client_name,
        agency_name=args.agency,
        current_snapshot=snapshot,
    )

    if not args.no_save:
        history.save_snapshot(platform, profile.handle, snapshot)
        print("✓ Snapshot salvo no histórico (será usado para comparação na próxima análise).")

    print(f"✓ Relatório gerado em: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
