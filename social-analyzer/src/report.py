"""Monta o PDF final do relatório de diagnóstico de redes sociais."""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from . import charts
from .history import follower_series, get_previous_snapshot
from .metrics import Metrics, compare_to_previous
from .scraper import ProfileData

NAVY = colors.HexColor("#0f172a")
BLUE = colors.HexColor("#2563eb")
GREEN = colors.HexColor("#16a34a")
RED = colors.HexColor("#dc2626")
MUTED = colors.HexColor("#6b7280")
LIGHT_BG = colors.HexColor("#f3f4f6")

PLATFORM_LABEL = {"instagram": "Instagram", "tiktok": "TikTok"}


def esc(text: str) -> str:
    return escape(text or "")


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    styles = {
        "CoverTitle": ParagraphStyle("CoverTitle", parent=base["Title"], fontSize=26, textColor=NAVY, spaceAfter=6, alignment=1),
        "CoverSubtitle": ParagraphStyle("CoverSubtitle", parent=base["Normal"], fontSize=14, textColor=MUTED, alignment=1, spaceAfter=4),
        "CoverMeta": ParagraphStyle("CoverMeta", parent=base["Normal"], fontSize=11, textColor=colors.black, alignment=1, spaceAfter=2),
        "H1": ParagraphStyle("H1", parent=base["Heading1"], fontSize=16, textColor=NAVY, spaceBefore=14, spaceAfter=8),
        "H2": ParagraphStyle("H2", parent=base["Heading2"], fontSize=12.5, textColor=BLUE, spaceBefore=10, spaceAfter=6),
        "Body": ParagraphStyle("Body", parent=base["Normal"], fontSize=10, leading=14, textColor=colors.black),
        "Muted": ParagraphStyle("Muted", parent=base["Normal"], fontSize=9, leading=12, textColor=MUTED),
        "StatValue": ParagraphStyle("StatValue", parent=base["Normal"], fontSize=18, leading=20, textColor=NAVY, fontName="Helvetica-Bold"),
        "StatLabel": ParagraphStyle("StatLabel", parent=base["Normal"], fontSize=8.5, leading=11, textColor=MUTED),
        "StatDelta": ParagraphStyle("StatDelta", parent=base["Normal"], fontSize=8.5, leading=11, textColor=GREEN),
        "ProText": ParagraphStyle("ProText", parent=base["Normal"], fontSize=9.5, leading=13, textColor=colors.black, leftIndent=4),
        "ConText": ParagraphStyle("ConText", parent=base["Normal"], fontSize=9.5, leading=13, textColor=colors.black, leftIndent=4),
        "TableHeader": ParagraphStyle("TableHeader", parent=base["Normal"], fontSize=9.5, leading=12, textColor=colors.white, fontName="Helvetica-Bold"),
    }
    return styles


def _footer(canvas, doc, agency_name: str):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(2 * cm, 1.2 * cm, agency_name)
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Página {doc.page}")
    canvas.restoreState()


def _stat_cell(value: str, label: str, delta: str | None, styles: dict) -> list:
    rows = [Paragraph(value, styles["StatValue"]), Paragraph(label, styles["StatLabel"])]
    if delta:
        rows.append(Paragraph(delta, styles["StatDelta"]))
    return rows


def _stats_grid(profile: ProfileData, metrics: Metrics, deltas: dict | None, styles: dict) -> Table:
    def fmt_delta(value: float, suffix: str = "", pct: bool = False) -> str | None:
        if deltas is None:
            return None
        sign = "+" if value >= 0 else ""
        return f"{sign}{value:.1f}{suffix}" if pct else f"{sign}{value:.0f}{suffix}"

    follower_delta = fmt_delta(deltas["follower_delta"], "") if deltas else None
    engagement_delta = fmt_delta(deltas["engagement_delta"], " p.p.", pct=True) if deltas else None

    cells = [
        _stat_cell(f"{profile.followers:,}".replace(",", "."), "Seguidores", follower_delta, styles),
        _stat_cell(f"{metrics.engagement_rate:.1f}%", "Taxa de engajamento", engagement_delta, styles),
        _stat_cell(f"{metrics.posting_frequency:.1f}/sem", "Frequência de posts", None, styles),
        _stat_cell(f"{metrics.avg_likes:,.0f}".replace(",", "."), "Média de curtidas", None, styles),
        _stat_cell(f"{metrics.avg_comments:,.0f}".replace(",", "."), "Média de comentários", None, styles),
        _stat_cell(
            f"{metrics.avg_views:,.0f}".replace(",", ".") if metrics.avg_views is not None else "—",
            "Média de visualizações",
            None,
            styles,
        ),
    ]

    table = Table([cells], colWidths=[(A4[0] - 4 * cm) / 6] * 6)
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
        ("BOX", (0, 0), (-1, -1), 0, colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LINEAFTER", (0, 0), (-2, 0), 0.5, colors.white),
    ]))
    return table


def _post_row(post, styles) -> list:
    caption = post.caption[:110] + ("…" if len(post.caption) > 110 else "")
    views = f"{post.views:,.0f}".replace(",", ".") if post.views is not None else "—"
    return [
        Paragraph(esc(caption) or "<i>(sem legenda)</i>", styles["Body"]),
        Paragraph(f"{post.likes:,}".replace(",", "."), styles["Body"]),
        Paragraph(f"{post.comments:,}".replace(",", "."), styles["Body"]),
        Paragraph(views, styles["Body"]),
    ]


def build_report(
    profile: ProfileData,
    metrics: Metrics,
    output_path: Path,
    client_name: str,
    agency_name: str = "Sua Agência de Marketing",
    current_snapshot: dict | None = None,
) -> Path:
    styles = _styles()
    tmp_dir = Path(tempfile.mkdtemp(prefix="social_report_"))
    platform_label = PLATFORM_LABEL[profile.platform]

    deltas = None
    if current_snapshot is not None:
        previous = get_previous_snapshot(profile.platform, profile.handle)
        deltas = compare_to_previous(current_snapshot, previous) if previous else None

    story = []

    # --- Capa ---
    story.append(Spacer(1, 5 * cm))
    story.append(Paragraph("Relatório de Diagnóstico de Redes Sociais", styles["CoverTitle"]))
    story.append(Paragraph(f"{platform_label} · @{profile.handle}", styles["CoverSubtitle"]))
    story.append(Spacer(1, 0.6 * cm))
    story.append(Paragraph(f"Cliente: {esc(client_name)}", styles["CoverMeta"]))
    story.append(Paragraph(f"Preparado por: {esc(agency_name)}", styles["CoverMeta"]))
    story.append(Paragraph(f"Data: {profile.fetched_at.strftime('%d/%m/%Y')}", styles["CoverMeta"]))
    story.append(PageBreak())

    # --- Resumo executivo ---
    story.append(Paragraph("Resumo executivo", styles["H1"]))
    if profile.bio:
        story.append(Paragraph(esc(profile.bio), styles["Muted"]))
        story.append(Spacer(1, 8))
    story.append(_stats_grid(profile, metrics, deltas, styles))
    if deltas:
        prev_date = datetime.fromisoformat(deltas["previous_date"]).strftime("%d/%m/%Y")
        story.append(Spacer(1, 6))
        story.append(Paragraph(
            f"Comparado à última análise em {prev_date}: "
            f"{'ganho' if deltas['follower_delta'] >= 0 else 'perda'} de "
            f"{abs(deltas['follower_delta']):,.0f} seguidores "
            f"({deltas['follower_growth_pct']:+.1f}%).".replace(",", "."),
            styles["Muted"],
        ))

    # --- Gráficos ---
    chart_path = charts.engagement_bar_chart(profile.posts, tmp_dir / "engagement.png")
    growth_series = follower_series(profile.platform, profile.handle)
    growth_path = charts.follower_growth_chart(growth_series, tmp_dir / "growth.png")

    if chart_path or growth_path:
        story.append(Paragraph("Desempenho recente", styles["H1"]))
    if chart_path:
        story.append(Image(str(chart_path), width=16 * cm, height=16 * cm * 3.0 / 6.4))
        story.append(Spacer(1, 6))
    if growth_path:
        story.append(Image(str(growth_path), width=16 * cm, height=16 * cm * 2.6 / 6.4))

    # --- Melhor e pior post ---
    if metrics.best_post is not None:
        story.append(Paragraph("Destaques de conteúdo", styles["H1"]))
        table_data = [[
            Paragraph("Legenda", styles["TableHeader"]),
            Paragraph("Curtidas", styles["TableHeader"]),
            Paragraph("Comentários", styles["TableHeader"]),
            Paragraph("Views", styles["TableHeader"]),
        ]]
        story.append(Paragraph("Melhor publicação", styles["H2"]))
        story.append(Table([table_data[0], _post_row(metrics.best_post, styles)], colWidths=[8 * cm, 2.5 * cm, 2.8 * cm, 2.7 * cm], style=_post_table_style()))
        if metrics.worst_post is not None and metrics.worst_post is not metrics.best_post:
            story.append(Spacer(1, 8))
            story.append(Paragraph("Publicação com menor desempenho", styles["H2"]))
            story.append(Table([table_data[0], _post_row(metrics.worst_post, styles)], colWidths=[8 * cm, 2.5 * cm, 2.8 * cm, 2.7 * cm], style=_post_table_style()))

    # --- Prós e contras ---
    from .metrics import generate_pros_cons
    pros_cons = generate_pros_cons(profile, metrics)
    if pros_cons:
        story.append(Paragraph("Pontos fortes e oportunidades de melhoria", styles["H1"]))
        for kind, text in pros_cons:
            symbol = "✓" if kind == "pro" else "✗"
            color_hex = "#16a34a" if kind == "pro" else "#dc2626"
            style_name = "ProText" if kind == "pro" else "ConText"
            row = Table(
                [[Paragraph(f'<font color="{color_hex}"><b>{symbol}</b></font>', styles["Body"]), Paragraph(esc(text), styles[style_name])]],
                colWidths=[0.7 * cm, 15.3 * cm],
            )
            row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
            story.append(row)

    # --- Proposta de acompanhamento ---
    story.append(PageBreak())
    story.append(Paragraph("Próximos passos", styles["H1"]))
    story.append(Paragraph(
        "Este diagnóstico é uma fotografia do momento atual do perfil. Métricas de redes sociais mudam "
        "constantemente — algoritmo, comportamento da audiência e concorrência evoluem toda semana. "
        "Recomendamos um acompanhamento contínuo para transformar estes dados em crescimento real:",
        styles["Body"],
    ))
    story.append(Spacer(1, 8))
    for bullet in [
        "Relatório de métricas mensal ou quinzenal, com comparação de evolução período a período;",
        "Identificação contínua dos formatos de conteúdo com melhor retorno;",
        "Recomendações práticas de ajuste de estratégia a cada ciclo;",
        "Acompanhamento de indicadores-chave (engajamento, alcance, crescimento de seguidores).",
    ]:
        story.append(Paragraph(f"•  {bullet}", styles["Body"]))
    story.append(Spacer(1, 14))
    story.append(Paragraph(
        f"Fale com {esc(agency_name)} para conhecer o plano de acompanhamento contínuo e transformar "
        "estes dados em uma estratégia de crescimento consistente.",
        styles["Muted"],
    ))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=f"Análise {platform_label} - {profile.handle}",
        author=agency_name,
    )
    doc.build(story, onFirstPage=lambda c, d: _footer(c, d, agency_name), onLaterPages=lambda c, d: _footer(c, d, agency_name))
    return output_path


def _post_table_style() -> TableStyle:
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ])
