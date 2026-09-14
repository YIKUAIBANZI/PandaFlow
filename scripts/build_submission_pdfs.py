#!/usr/bin/env python3
"""Render two reviewable submission drafts using the existing PDF typography."""
from pathlib import Path

from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak

from build_api_pdf import (
    A4, FONT_NAME, NAVY, MUTED, LINE,
    register_fonts, styles, markdown_story,
)

ROOT = Path(__file__).resolve().parents[1]
VERSION = "2026-09-14"
DOCUMENTS = (
    ("PandaFlow-行业应用方案书", "行业应用方案书", "场景 · 六 Skill · 验证 · 平台交付"),
    ("PandaFlow-公开资料蒸馏包", "公开资料蒸馏包", "资料汇总 · 逻辑转化 · 来源清单"),
)


def build_document(stem: str, title: str, subtitle: str) -> Path:
    register_fonts()
    style_map = styles()
    style_map["body"].fontSize = 10
    style_map["body"].leading = 17
    style_map["table"].fontSize = 8.2
    style_map["table"].leading = 12
    source = (ROOT / "docs" / f"{stem}.md").read_text(encoding="utf-8")
    target = ROOT / "output" / "pdf" / f"{stem}.pdf"
    target.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(target), pagesize=A4, rightMargin=18*mm, leftMargin=18*mm,
        topMargin=20*mm, bottomMargin=20*mm,
        title=f"熊猫守望 PandaFlow {title}", author="PandaFlow",
        subject=f"本地初稿，WorkHub 尚未联调。{subtitle}",
    )

    def decorate(canvas, document):
        width, height = A4
        canvas.saveState()
        canvas.setFillColor(NAVY)
        canvas.rect(0, height-8*mm, width, 8*mm, fill=1, stroke=0)
        canvas.setStrokeColor(LINE)
        canvas.line(18*mm, 14*mm, width-18*mm, 14*mm)
        canvas.setFont(FONT_NAME, 7.2)
        canvas.setFillColor(MUTED)
        canvas.drawString(18*mm, 9*mm, f"PandaFlow | {VERSION} | 本地初稿 · 平台待验")
        canvas.drawRightString(width-18*mm, 9*mm, str(document.page))
        canvas.restoreState()

    story = [Spacer(1, 33*mm), Paragraph("熊猫守望", style_map["cover_title"]),
             Paragraph("PandaFlow", style_map["cover_title"]), Spacer(1, 8*mm),
             Paragraph(title, style_map["cover_title"]),
             Paragraph(subtitle, style_map["cover_subtitle"]), Spacer(1, 18*mm),
             Paragraph("B 赛道 · SP-A 协同调度中枢", style_map["cover_subtitle"]),
             Paragraph(f"版本 {VERSION} · 参赛原型材料", style_map["cover_subtitle"]),
             Spacer(1, 8*mm),
             Paragraph("本地初稿｜未完成 WorkHub 联调、能力超市上架或正式提交", style_map["quote"]),
             Paragraph("使用公开资料与明确标记的合成数据；无园区合作、专家访谈或内部 SOP 声明。", style_map["body"]),
             PageBreak()]
    for index, section in enumerate(source.split("<!-- pagebreak -->")):
        if index:
            story.append(PageBreak())
        story.extend(markdown_story(section, style_map))
    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    return target


if __name__ == "__main__":
    for config in DOCUMENTS:
        print(build_document(*config))
