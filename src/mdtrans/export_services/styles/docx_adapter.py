"""
DOCX 样式适配器

将 `StyleDefinition` 转换为 python-docx 样式操作。
封装了 WORD 文档的段落样式创建/更新、run 级格式化、字体设置等逻辑。
"""

from __future__ import annotations

import re
from typing import Optional

from docx import Document
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Pt, RGBColor

from .definitions import (
    StyleDefinition,
    NORMAL,
    CODE_STYLE_KEYWORDS,
    ALL_STYLES,
)

# ---------------------------------------------------------------------------
# 样式集合常量
# ---------------------------------------------------------------------------

# 必须保留的段落样式白名单
REQUIRED_PARAGRAPH_STYLES: set[str] = {
    "Normal",
    "Heading 1",
    "Heading 2",
    "Heading 3",
    "Heading 4",
    "Heading 5",
    "Heading 6",
    "Table Text",
    "List Paragraph",
    "Image Paragraph",
    "Custom List",
    "Code Block",
    "Source Code",
    "Preformatted Text",
    "Table of Contents 1",
    "Table of Contents 2",
    "Table of Contents 3",
}

# 必须保留的字符样式白名单
REQUIRED_CHARACTER_STYLES: set[str] = {
    "Default Paragraph Font",
    "Hyperlink",
    "Strong",
    "Emphasis",
}

# 匹配以数字/字母序号开头的段落（应取消首行缩进）
_NO_INDENT_PATTERN = re.compile(
    r"^\s*(\d+[.、）)）]|[（(]\d+[）)]|[一二三四五六七八九十百]+[、.]|[a-zA-Z][.)])"
)


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def _rgb_from_hex(hex_color: str) -> RGBColor:
    """将 "#RRGGBB" 格式转换为 RGBColor 对象。"""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return RGBColor(r, g, b)


def _is_emoji(char: str) -> bool:
    """判断字符是否为 emoji。"""
    code = ord(char)
    return (
        0x1F600 <= code <= 0x1F64F
        or 0x1F900 <= code <= 0x1F9FF
        or 0x1F300 <= code <= 0x1F5FF
        or 0x1F680 <= code <= 0x1F6FF
        or 0x2600 <= code <= 0x26FF
        or 0x2700 <= code <= 0x27BF
        or 0xFE00 <= code <= 0xFE0F
        or 0x1FA00 <= code <= 0x1FA6F
        or 0x1FA70 <= code <= 0x1FAFF
        or code == 0x200D
        or code == 0x20E3
        or 0x1F1E0 <= code <= 0x1F1FF
    )


def _contains_emoji(text: str) -> bool:
    """判断文本中是否包含 emoji 字符。"""
    return any(_is_emoji(char) for char in text)


def _needs_no_indent(paragraph) -> bool:
    """判断段落是否应取消首行缩进（以编号/字母序号开头时）。"""
    return bool(_NO_INDENT_PATTERN.match(paragraph.text))


def _has_num_pr(paragraph) -> bool:
    """判断段落是否包含 w:numPr（通常表示列表项）。"""
    pPr = paragraph._p.find(qn("w:pPr"))
    return pPr is not None and pPr.find(qn("w:numPr")) is not None


def _has_image(paragraph) -> bool:
    """判断段落中是否包含图片节点。"""
    for child in paragraph._element.iter():
        if child.tag.endswith("drawing") or child.tag.endswith("pic"):
            return True
    return False


def _is_toc_paragraph(paragraph) -> tuple[bool, int]:
    """判断段落是否为目录项，并返回目录级别（1/2/3）。"""
    style_name = paragraph.style.name if paragraph.style else ""
    for level in [1, 2, 3]:
        toc_style_name = f"Table of Contents {level}"
        toc_short_name = f"TOC {level}"
        if toc_style_name in style_name or toc_short_name in style_name:
            return True, level
    return False, 0


def _is_code_block(paragraph, style_defs: tuple[str, ...] = CODE_STYLE_KEYWORDS) -> bool:
    """判断段落是否为代码块。

    判定顺序：
    1) 样式名是否包含代码关键词（Pandoc 常见输出）；
    2) run 字体是否为等宽字体（Consolas/Courier/Monospace）。
    """
    style_name = paragraph.style.name if paragraph.style else ""
    for keyword in style_defs:
        if keyword in style_name:
            return True
    for run in paragraph.runs:
        font_name = run.font.name
        if font_name and ("Consolas" in font_name or "Courier" in font_name or "Monospace" in font_name):
            return True
    return False


# ---------------------------------------------------------------------------
# 字体设置
# ---------------------------------------------------------------------------


def set_run_fonts(
    rpr_elem,
    font_name: str,
    font_name_latin: Optional[str] = None,
    force_emoji_font: bool = False,
) -> None:
    """设置 run 的中西文字体，并移除主题字体覆盖。

    Args:
        rpr_elem: run 的 rPr 元素
        font_name: 中文字体名称
        font_name_latin: 西文字体名称（可选，默认与 font_name 相同）
        force_emoji_font: 是否强制使用 emoji 字体
    """
    rFonts = rpr_elem.get_or_add_rFonts()

    if force_emoji_font:
        emoji_font = "Segoe UI Emoji"
        rFonts.set(qn("w:ascii"), emoji_font)
        rFonts.set(qn("w:hAnsi"), emoji_font)
        rFonts.set(qn("w:eastAsia"), emoji_font)
        rFonts.set(qn("w:cs"), emoji_font)
    else:
        latin_font = font_name_latin if font_name_latin else font_name
        rFonts.set(qn("w:ascii"), latin_font)
        rFonts.set(qn("w:hAnsi"), latin_font)
        rFonts.set(qn("w:eastAsia"), font_name)
        rFonts.set(qn("w:cs"), font_name)

    for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:themeEastAsia", "w:cstheme"):
        rFonts.attrib.pop(qn(attr), None)


# ---------------------------------------------------------------------------
# 样式查找
# ---------------------------------------------------------------------------


def get_style_config(style_name: str) -> StyleDefinition:
    """根据段落样式名获取对应的 StyleDefinition。

    按 ALL_STYLES 顺序匹配 style_keywords。
    未命中时回退到 NORMAL。
    """
    for config in ALL_STYLES:
        if config.is_table:
            continue
        for keyword in config.style_keywords:
            if keyword in style_name:
                return config
    return NORMAL


# ---------------------------------------------------------------------------
# 段落格式化
# ---------------------------------------------------------------------------


def apply_para_formatting(paragraph, style_def: StyleDefinition, is_table: bool = False) -> None:
    """按 StyleDefinition 应用段落与 run 级格式。

    Args:
        paragraph: 待处理段落
        style_def: 样式定义
        is_table: 是否处于表格上下文（用于对齐与缩进策略）
    """
    pf = paragraph.paragraph_format
    pf.line_spacing = style_def.line_spacing
    pf.space_before = Pt(style_def.space_before_pt)
    pf.space_after = Pt(style_def.space_after_pt)

    # 代码块：尽量保持段内连续
    if style_def.is_code:
        pf.keep_together = True
        pf.keep_with_next = True

    # 自定义列表：显式设置缩进
    if style_def.is_custom_list:
        pf.left_indent = Pt(style_def.left_indent_pt)
        pf.first_line_indent = Pt(style_def.first_line_indent_pt)
    elif style_def.is_list:
        pf.left_indent = Pt(style_def.left_indent_pt)
        pf.first_line_indent = Pt(0)
    elif not _has_num_pr(paragraph):
        if style_def.first_line_indent_pt and not is_table and _needs_no_indent(paragraph):
            pf.first_line_indent = Pt(0)
        else:
            pf.first_line_indent = Pt(style_def.first_line_indent_pt)
            pf.left_indent = Pt(style_def.left_indent_pt)

    # 对齐方式
    if is_table and style_def.alignment != "left":
        _set_alignment(pf, style_def.alignment)
    if style_def.is_image:
        pf.alignment = 1  # Center

    # run 级格式化
    color_rgb = _rgb_from_hex(style_def.color_hex)
    for run in paragraph.runs:
        run.font.color.rgb = color_rgb
        run.font.name = style_def.font_name_latin
        run.font.size = Pt(style_def.font_size_pt)
        if style_def.bold:
            run.font.bold = True
        elif run.font.bold is not True:
            run.font.bold = False
        if style_def.italic:
            run.font.italic = True

        has_emoji = _contains_emoji(run.text)
        if style_def.is_code:
            set_run_fonts(
                run._element.get_or_add_rPr(),
                style_def.font_name_latin,
                force_emoji_font=has_emoji,
            )
        else:
            set_run_fonts(
                run._element.get_or_add_rPr(),
                style_def.font_name,
                style_def.font_name_latin,
                force_emoji_font=has_emoji,
            )


def _set_alignment(pf, alignment: str) -> None:
    """将字符串对齐方式转换为 python-docx 对齐值。"""
    mapping = {
        "left": 0,
        "center": 1,
        "right": 2,
        "justify": 3,
    }
    pf.alignment = mapping.get(alignment, 0)


# ---------------------------------------------------------------------------
# 样式创建/刷新
# ---------------------------------------------------------------------------


def create_or_update_style(doc: Document, style_def: StyleDefinition) -> None:
    """在 Document 中创建或刷新一个段落样式。

    Args:
        doc: python-docx Document 对象
        style_def: 要创建/刷新的样式定义
    """
    existing_names = {s.name for s in doc.styles}
    name = style_def.name

    if name in existing_names:
        style = doc.styles[name]
    else:
        style = doc.styles.add_style(name, 1)  # 1 = paragraph style

    style.font.name = style_def.font_name_latin
    style.font.size = Pt(style_def.font_size_pt)
    style.font.bold = style_def.bold
    style.font.color.rgb = _rgb_from_hex(style_def.color_hex)

    rPr = style.element.get_or_add_rPr()
    set_run_fonts(rPr, style_def.font_name, style_def.font_name_latin)

    # 移除主题色覆盖
    color_elem = rPr.find(qn("w:color"))
    if color_elem is not None:
        for attr in ("w:themeColor", "w:themeShade", "w:themeTint"):
            color_elem.attrib.pop(qn(attr), None)

    pf = style.paragraph_format
    pf.line_spacing = style_def.line_spacing
    pf.first_line_indent = Pt(style_def.first_line_indent_pt)
    if style_def.left_indent_pt:
        pf.left_indent = Pt(style_def.left_indent_pt)
    pf.space_before = Pt(style_def.space_before_pt)
    pf.space_after = Pt(style_def.space_after_pt)

    # 代码块背景色（段落底纹）
    if style_def.background_color_hex:
        pPr = style.element.get_or_add_pPr()
        shd = pPr.find(qn("w:shd"))
        if shd is None:
            shd_xml = f'<w:shd {nsdecls("w")} w:val="clear"/>'
            shd = parse_xml(shd_xml)
            pPr.append(shd)
        hex_fill = style_def.background_color_hex.lstrip("#")
        shd.set(qn("w:fill"), hex_fill)
