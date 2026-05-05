"""Analytics: PDF (ReportLab) + HTML dashboard (Chart.js) + CSV export."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from modules.utils import PALETTE, get_logger, load_config, safe

log = get_logger("casa_ludic.analytics")

OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


class Analytics:
    def __init__(self, db: Any) -> None:
        self.db = db
        self.cfg = load_config()
        self.env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    @safe(default=None, log_name="casa_ludic.analytics")
    def generate_pdf_report(self, path: Path | None = None) -> Path | None:
        path = Path(path) if path else OUTPUTS_DIR / f"relatorio_{datetime.now():%Y%m%d_%H%M%S}.pdf"
        path.parent.mkdir(parents=True, exist_ok=True)

        kpis = self.db.kpis()
        ig = self.db.latest_instagram_metrics()

        doc = SimpleDocTemplate(str(path), pagesize=A4,
                                topMargin=2 * cm, bottomMargin=2 * cm,
                                leftMargin=2 * cm, rightMargin=2 * cm)
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "title", parent=styles["Heading1"], fontName="Helvetica-Bold",
            fontSize=18, textColor=colors.HexColor(PALETTE["secondary"]),
        )
        h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontName="Helvetica-Bold",
                            fontSize=14, textColor=colors.HexColor(PALETTE["primary"]))
        body = ParagraphStyle("body", parent=styles["BodyText"], fontName="Helvetica", fontSize=11)
        footer = ParagraphStyle("footer", parent=styles["BodyText"], fontName="Helvetica", fontSize=9,
                                textColor=colors.grey)

        story: list[Any] = []
        story.append(Paragraph("Casa Ludic - Relatório Executivo", title_style))
        story.append(Paragraph(f"Rio das Ostras/RJ | Gerado em {datetime.now():%d/%m/%Y %H:%M}", body))
        story.append(Spacer(1, 0.6 * cm))

        story.append(Paragraph("Indicadores Chave", h2))
        kpi_table = Table([
            ["Total de leads", str(kpis.get("total_leads", 0))],
            ["Mensagens enviadas", str(kpis.get("total_outreach", 0))],
        ], colWidths=[8 * cm, 6 * cm])
        kpi_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor(PALETTE["primary"])),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 12),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(kpi_table)
        story.append(Spacer(1, 0.6 * cm))

        story.append(Paragraph("Distribuição por Prioridade", h2))
        story.append(self._dict_table(kpis.get("by_priority", {})))
        story.append(Spacer(1, 0.4 * cm))

        story.append(Paragraph("Distribuição por Estágio", h2))
        story.append(self._dict_table(kpis.get("by_stage", {})))
        story.append(Spacer(1, 0.4 * cm))

        story.append(Paragraph("Distribuição por Serviço", h2))
        story.append(self._dict_table(kpis.get("by_service", {})))
        story.append(Spacer(1, 0.6 * cm))

        if ig:
            story.append(Paragraph("Instagram - última coleta", h2))
            ig_table = Table([
                ["Data", str(ig.get("date", "-"))],
                ["Seguidores", str(ig.get("followers", 0))],
                ["Posts", str(ig.get("posts", 0))],
                ["Engagement (%)", str(ig.get("engagement", 0))],
                ["Fonte", str(ig.get("source", "-"))],
            ], colWidths=[6 * cm, 8 * cm])
            ig_table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 11),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ]))
            story.append(ig_table)
            story.append(Spacer(1, 0.6 * cm))

        story.append(Paragraph(
            f"Gerado em {datetime.now().isoformat(timespec='seconds')} - Casa Ludic CRM v1.0",
            footer,
        ))

        doc.build(story)
        log.info("PDF gerado: %s", path)
        return path

    def _dict_table(self, data: dict[str, Any]) -> Table:
        if not data:
            data = {"(sem dados)": 0}
        rows = [[str(k), str(v)] for k, v in data.items()]
        t = Table(rows, colWidths=[8 * cm, 6 * cm])
        t.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 11),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f3f3fa")),
        ]))
        return t

    @safe(default=None, log_name="casa_ludic.analytics")
    def generate_html_dashboard(self, path: Path | None = None) -> Path | None:
        path = Path(path) if path else OUTPUTS_DIR / "dashboard.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        kpis = self.db.kpis()
        template = self.env.get_template("dashboard.html")
        rendered = template.render(
            clinic=self.cfg.get("clinic", {"name": "Casa Ludic", "city": "Rio das Ostras/RJ"}),
            palette=PALETTE,
            kpis=kpis,
            instagram=self.db.latest_instagram_metrics(),
            priority_json=json.dumps(kpis.get("by_priority", {}), ensure_ascii=False),
            stage_json=json.dumps(kpis.get("by_stage", {}), ensure_ascii=False),
            service_json=json.dumps(kpis.get("by_service", {}), ensure_ascii=False),
            timeline_json=json.dumps(kpis.get("timeline_30d", []), ensure_ascii=False),
            generated_at=datetime.now().isoformat(timespec="seconds"),
        )
        path.write_text(rendered, encoding="utf-8")
        log.info("Dashboard HTML gerado: %s", path)
        return path

    @safe(default=None, log_name="casa_ludic.analytics")
    def export_csv(self, path: Path | None = None) -> Path | None:
        path = Path(path) if path else OUTPUTS_DIR / f"leads_{datetime.now():%Y%m%d_%H%M%S}.csv"
        if self.db.export_csv(path):
            return path
        return None

    @safe(default=False, log_name="casa_ludic.analytics")
    def daily_report(self) -> bool:
        """Scheduler job 6: PDF + HTML."""
        pdf = self.generate_pdf_report()
        html = self.generate_html_dashboard()
        return bool(pdf and html)
