#!/usr/bin/env python3
"""Render the reviewed PandaFlow API Markdown source as a submission PDF."""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

DOCUMENT_VERSION = "2026-09-14"


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "docs" / "PandaFlow-API接口文档.md"
DEFAULT_OUTPUT = ROOT / "output" / "pdf" / "PandaFlow-API接口文档.pdf"
FONT_PATH = Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf")
FONT_NAME = "PandaFlowUnicode"
NAVY = colors.HexColor("#14324A")
GREEN = colors.HexColor("#12805C")
PALE_GREEN = colors.HexColor("#EAF7F1")
PALE_BLUE = colors.HexColor("#EDF4F8")
MUTED = colors.HexColor("#526574")
LINE = colors.HexColor("#C9D6DE")


def register_fonts() -> None:
    if not FONT_PATH.is_file():
        raise FileNotFoundError(f"Required CJK font is unavailable: {FONT_PATH}")
    pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH)))


def rich_text(value: str) -> str:
    """Convert the small inline Markdown subset used by the source."""

    escaped = html.escape(value.strip())
    escaped = re.sub(
        r"\[([^]]+)]\((https?://[^)]+)\)",
        r'<link href="\2" color="#12805C"><u>\1</u></link>',
        escaped,
    )
    escaped = re.sub(
        r"`([^`]+)`",
        rf'<font name="{FONT_NAME}" color="#0A6647">\1</font>',
        escaped,
    )
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)
    return escaped


def styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "CoverTitle", parent=base["Title"], fontName=FONT_NAME,
            fontSize=29, leading=36, textColor=NAVY, alignment=TA_LEFT,
            spaceAfter=12,
        ),
        "cover_subtitle": ParagraphStyle(
            "CoverSubtitle", parent=base["Normal"], fontName=FONT_NAME,
            fontSize=13, leading=20, textColor=MUTED, spaceAfter=12,
        ),
        "h1": ParagraphStyle(
            "Heading1CN", parent=base["Heading1"], fontName=FONT_NAME,
            fontSize=17, leading=23, textColor=NAVY, spaceBefore=13,
            spaceAfter=7, keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "Heading2CN", parent=base["Heading2"], fontName=FONT_NAME,
            fontSize=13.5, leading=19, textColor=GREEN, spaceBefore=11,
            spaceAfter=5, keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "Heading3CN", parent=base["Heading3"], fontName=FONT_NAME,
            fontSize=11, leading=16, textColor=NAVY, spaceBefore=8,
            spaceAfter=4, keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "BodyCN", parent=base["BodyText"], fontName=FONT_NAME,
            fontSize=8.7, leading=14.2, textColor=colors.HexColor("#20313D"),
            spaceAfter=6, wordWrap="CJK",
        ),
        "quote": ParagraphStyle(
            "QuoteCN", parent=base["BodyText"], fontName=FONT_NAME,
            fontSize=8.5, leading=14, leftIndent=10, rightIndent=8,
            borderColor=GREEN, borderWidth=0, borderPadding=7,
            backColor=PALE_GREEN, textColor=NAVY, spaceAfter=8,
            wordWrap="CJK",
        ),
        "bullet": ParagraphStyle(
            "BulletCN", parent=base["BodyText"], fontName=FONT_NAME,
            fontSize=8.6, leading=14, leftIndent=14, firstLineIndent=-8,
            bulletIndent=3, textColor=colors.HexColor("#20313D"),
            spaceAfter=3, wordWrap="CJK",
        ),
        "table": ParagraphStyle(
            "TableCN", parent=base["BodyText"], fontName=FONT_NAME,
            fontSize=7.2, leading=10.5, textColor=colors.HexColor("#20313D"),
            wordWrap="CJK",
        ),
        "table_head": ParagraphStyle(
            "TableHeadCN", parent=base["BodyText"], fontName=FONT_NAME,
            fontSize=7.4, leading=10.8, textColor=colors.white,
            wordWrap="CJK",
        ),
        "code": ParagraphStyle(
            "CodeCN", parent=base["Code"], fontName=FONT_NAME,
            fontSize=6.8, leading=9.6, leftIndent=0, rightIndent=0,
            borderPadding=7, backColor=colors.HexColor("#F3F6F8"),
            textColor=colors.HexColor("#21313C"), spaceBefore=2,
            spaceAfter=8,
        ),
        "footer": ParagraphStyle(
            "Footer", parent=base["Normal"], fontName=FONT_NAME,
            fontSize=7.2, textColor=MUTED, alignment=TA_CENTER,
        ),
    }


def parse_table(lines: list[str], style_map: dict[str, ParagraphStyle]) -> Table:
    rows = []
    for row_index, line in enumerate(lines):
        if row_index == 1:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        style_name = "table_head" if row_index == 0 else "table"
        rows.append([Paragraph(rich_text(cell), style_map[style_name]) for cell in cells])

    count = len(rows[0])
    available = A4[0] - 36 * mm
    if count == 2:
        widths = [available * 0.27, available * 0.73]
    elif count == 3:
        widths = [available * 0.22, available * 0.25, available * 0.53]
    elif count == 4:
        widths = [available * 0.19, available * 0.18, available * 0.15, available * 0.48]
    else:
        widths = [available / count] * count

    table = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE_BLUE]),
    ]))
    return table


def markdown_story(source: str, style_map: dict[str, ParagraphStyle]) -> list:
    lines = source.splitlines()
    story: list = []
    index = 0
    first_heading_consumed = False
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            index += 1
            continue

        if stripped.startswith("```"):
            code_lines: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(lines[index].rstrip())
                index += 1
            story.append(Preformatted("\n".join(code_lines), style_map["code"], maxLineLength=105))
            index += 1
            continue

        if stripped.startswith("|") and index + 1 < len(lines) and re.match(r"^\|[\s|:\-]+\|$", lines[index + 1].strip()):
            table_lines = [line, lines[index + 1]]
            index += 2
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index])
                index += 1
            story.extend([parse_table(table_lines, style_map), Spacer(1, 7)])
            continue

        if stripped.startswith("# ") and not first_heading_consumed:
            first_heading_consumed = True
            index += 1
            continue

        heading = re.match(r"^(#{1,3})\s+(.+)$", stripped)
        if heading:
            story.append(Paragraph(rich_text(heading.group(2)), style_map[f"h{len(heading.group(1))}"]))
            index += 1
            continue

        if stripped.startswith("> "):
            story.append(Paragraph(rich_text(stripped[2:]), style_map["quote"]))
            index += 1
            continue

        bullet = re.match(r"^[-*]\s+(.+)$", stripped)
        numbered = re.match(r"^(\d+)\.\s+(.+)$", stripped)
        if bullet or numbered:
            text = bullet.group(1) if bullet else numbered.group(2)
            marker = "•" if bullet else f"{numbered.group(1)}."
            story.append(Paragraph(f"{marker} {rich_text(text)}", style_map["bullet"]))
            index += 1
            continue

        paragraph_lines = [stripped]
        index += 1
        while index < len(lines):
            candidate = lines[index].strip()
            if not candidate or candidate.startswith(("#", "```", "> ", "|", "- ")) or re.match(r"^\d+\.\s+", candidate):
                break
            paragraph_lines.append(candidate)
            index += 1
        story.append(Paragraph(rich_text(" ".join(paragraph_lines)), style_map["body"]))

    return story


def decorate_page(canvas: Canvas, doc: SimpleDocTemplate) -> None:
    canvas.saveState()
    width, height = A4
    canvas.setFillColor(NAVY)
    canvas.rect(0, height - 8 * mm, width, 8 * mm, fill=1, stroke=0)
    canvas.setStrokeColor(LINE)
    canvas.line(18 * mm, 14 * mm, width - 18 * mm, 14 * mm)
    canvas.setFont(FONT_NAME, 7.2)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 9 * mm, f"PandaFlow API · v1 · {DOCUMENT_VERSION}")
    canvas.drawRightString(width - 18 * mm, 9 * mm, f"{doc.page}")
    canvas.restoreState()


def build_pdf(source_path: Path, output_path: Path) -> None:
    register_fonts()
    style_map = styles()
    source = source_path.read_text(encoding="utf-8")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_path), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=17 * mm, bottomMargin=19 * mm,
        title="PandaFlow API 接口文档",
        author="PandaFlow",
        subject="六个独立 Skill、总控 API 与 WorkHub 字段映射",
    )
    story = [
        Spacer(1, 34 * mm),
        Paragraph("PandaFlow", style_map["cover_title"]),
        Paragraph("API 接口文档", style_map["cover_title"]),
        Spacer(1, 8 * mm),
        Table(
            [[Paragraph("六个独立 Skill", style_map["cover_subtitle"]),
              Paragraph("固定游客故事线总控", style_map["cover_subtitle"])],
             [Paragraph("WorkHub 字段映射", style_map["cover_subtitle"]),
              Paragraph("错误与安全降级", style_map["cover_subtitle"])]],
            colWidths=[78 * mm, 78 * mm],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), PALE_GREEN),
                ("BOX", (0, 0), (-1, -1), 0.7, GREEN),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, LINE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]),
        ),
        Spacer(1, 15 * mm),
        Paragraph(f"版本 {DOCUMENT_VERSION} · API v1 · 应用 0.1.0", style_map["cover_subtitle"]),
        Paragraph(
            "参赛原型交付件｜公网 HTTPS 已验证｜WorkHub 真实联调待完成",
            style_map["quote"],
        ),
        PageBreak(),
    ]
    story.extend(markdown_story(source, style_map))
    doc.build(story, onFirstPage=decorate_page, onLaterPages=decorate_page)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build_pdf(args.source.resolve(), args.output.resolve())
    print(args.output.resolve())


if __name__ == "__main__":
    main()
