"""Dossier Markdown → PDF 导出（reportlab + 中文字体）。

字体策略：优先系统常见中文字体（微软雅黑/Noto Sans SC），
都找不到则回退 reportlab 内置 CID 字体 STSong-Light（无需字体文件）。
"""
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

_FONT = None

FONT_CANDIDATES = [
    ("MSYH", r"C:\Windows\Fonts\msyh.ttc"),          # 微软雅黑（Windows）
    ("NotoSC", r"C:\Windows\Fonts\NotoSansSC-VF.ttf"),  # Noto Sans SC
    ("NotoSC", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    ("NotoSC", "/System/Library/Fonts/PingFang.ttc"),
]


def _register_font() -> str:
    global _FONT
    if _FONT:
        return _FONT
    for name, path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                _FONT = name
                return name
            except Exception:
                continue
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    _FONT = "STSong-Light"
    return _FONT


def _styles(font: str) -> dict:
    base = ParagraphStyle("base", fontName=font, fontSize=10, leading=15, wordWrap="CJK")
    return {
        "title": ParagraphStyle("title", parent=base, fontSize=18, leading=24, spaceAfter=8),
        "h2": ParagraphStyle("h2", parent=base, fontSize=13, leading=18,
                             spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#1a1a1a")),
        "body": ParagraphStyle("body", parent=base),
        "bullet": ParagraphStyle("bullet", parent=base, leftIndent=14, bulletIndent=4, spaceAfter=2),
        "note": ParagraphStyle("note", parent=base, fontSize=9,
                               textColor=colors.HexColor("#b45309")),
    }


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _parse_table(table_lines: list):
    header = [c.strip() for c in table_lines[0].strip().strip("|").split("|")]
    rows = []
    for line in table_lines[1:]:
        if all(ch in "-|: " for ch in line):   # 分隔线 |---|---|
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells:
            rows.append(cells)
    return header, rows


def render(markdown: str, output_path: str, title: str = "FTO 分析卷宗"):
    """把 Dossier Markdown 渲染成 PDF 文件。同步执行（调用方放线程池）。"""
    font = _register_font()
    st = _styles(font)
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=16 * mm, rightMargin=16 * mm,
        topMargin=14 * mm, bottomMargin=14 * mm,
        title=title,
    )
    story = []
    lines = markdown.split("\n")
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped:
            i += 1
            continue
        if stripped.startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1
            header, rows = _parse_table(table_lines)
            t = Table([header] + rows, repeatRows=1)
            t.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), font),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2f7")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(t)
            story.append(Spacer(1, 6))
            continue
        if stripped.startswith("# "):
            story.append(Paragraph(_esc(stripped[2:]), st["title"]))
        elif stripped.startswith("## "):
            story.append(Paragraph(_esc(stripped[3:]), st["h2"]))
        elif stripped.startswith("> "):
            story.append(Paragraph(_esc(stripped[2:]), st["note"]))
        elif stripped.startswith("- "):
            story.append(Paragraph("• " + _esc(stripped[2:]), st["bullet"]))
        else:
            story.append(Paragraph(_esc(stripped), st["body"]))
        i += 1
    doc.build(story)
    return output_path
