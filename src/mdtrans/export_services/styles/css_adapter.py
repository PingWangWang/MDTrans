"""
CSS 样式适配器

将 `StyleDefinition` 转换为 CSS 规则字符串。
生成的 CSS 可供 HTML 直接引用，也可注入到 xhtml2pdf 的 HTML 中。

使用方式：
    from ..styles.css_adapter import generate_full_stylesheet
    css = generate_full_stylesheet()
    # 注入到 HTML <head> 中
"""

from __future__ import annotations

from .definitions import StyleDefinition, ALL_STYLES


def _style_def_to_css_rules(
    style_def: StyleDefinition,
    xhtml2pdf_compatible: bool = False,
) -> list[str]:
    """将单个 StyleDefinition 转换为 CSS 规则列表。

    Args:
        style_def: 样式定义
        xhtml2pdf_compatible: 若为 True，生成的 CSS 仅包含 xhtml2pdf 支持的属性

    Returns:
        一个或多个 CSS 规则字符串（含选择器和声明块）。
    """
    rules: list[str] = []

    # ---- 选择器 ----
    selectors = _get_selectors(style_def)
    if not selectors:
        return rules

    # ---- 声明块 ----
    declarations: list[str] = []

    # 字体族（xhtml2pdf 使用首个可用字体，故将中文字体放首位以确保中文渲染）
    cn_font = "SimSun" if style_def.font_name == "宋体" else style_def.font_name
    font_family_parts = [f'"{cn_font}"', f'"{style_def.font_name_latin}"', "serif"]
    declarations.append(f"font-family: {', '.join(font_family_parts)};")

    # 字号
    declarations.append(f"font-size: {style_def.font_size_pt}pt;")

    # 字重
    declarations.append(f"font-weight: {'bold' if style_def.bold else 'normal'};")

    # 字体样式
    if style_def.italic:
        declarations.append("font-style: italic;")

    # 颜色
    declarations.append(f"color: {style_def.color_hex};")

    # 背景色
    if style_def.background_color_hex:
        declarations.append(f"background-color: {style_def.background_color_hex};")
        declarations.append(f"padding: 2pt 4pt;")

    # 首行缩进
    if style_def.first_line_indent_pt:
        declarations.append(f"text-indent: {style_def.first_line_indent_pt}pt;")

    # 左缩进（margin-left 或 padding-left）
    if style_def.left_indent_pt:
        declarations.append(f"margin-left: {style_def.left_indent_pt}pt;")

    # 行距
    declarations.append(f"line-height: {style_def.line_spacing};")

    # 段前/段后间距
    if style_def.space_before_pt:
        declarations.append(f"margin-top: {style_def.space_before_pt}pt;")
    if style_def.space_after_pt:
        declarations.append(f"margin-bottom: {style_def.space_after_pt}pt;")

    # 对齐
    if style_def.alignment and style_def.alignment != "left":
        declarations.append(f"text-align: {style_def.alignment};")

    # 图片段落
    if style_def.is_image:
        declarations.append("text-align: center;")

    # 代码块额外修饰（xhtml2pdf 兼容版本去掉不支持的属性）
    if style_def.is_code:
        if xhtml2pdf_compatible:
            declarations.append("white-space: pre;")
            declarations.append("word-wrap: break-word;")
        else:
            declarations.append("white-space: pre-wrap;")
            declarations.append("overflow-x: auto;")
            declarations.append("border-radius: 2pt;")

    # 表格内文本
    if style_def.is_table:
        declarations.append("vertical-align: middle;")

    # 组装规则
    selector_str = ", ".join(selectors)
    block = f"{selector_str} {{\n    " + "\n    ".join(declarations) + "\n}"
    rules.append(block)

    return rules


def _get_selectors(style_def: StyleDefinition) -> list[str]:
    """获取样式定义对应的 CSS 选择器列表。

    根据样式类型返回合适的 HTML 标签 / class 选择器。
    """
    name = style_def.name
    selectors: list[str] = []

    if name == "Normal":
        selectors.append("body")
        selectors.append("p")
    elif name.startswith("Heading "):
        try:
            level = int(name.split()[-1])
            selectors.append(f"h{level}")
        except (ValueError, IndexError):
            selectors.append(f".{name.replace(' ', '-')}")
    elif name == "Code Block":
        selectors.append("pre")
        selectors.append("code")
        selectors.append("pre code")
    elif name == "Table Text":
        selectors.append("td")
        selectors.append("th")
    elif name == "Image Paragraph":
        selectors.append(".image-paragraph")
        selectors.append("p img")
    elif name == "List Paragraph":
        selectors.append("li")
    elif name.startswith("Table of Contents"):
        try:
            level = int(name.split()[-1])
            selectors.append(f".toc-{level}")
        except (ValueError, IndexError):
            selectors.append(".toc")
    else:
        # 回退：用 class 选择器
        css_class = name.lower().replace(" ", "-")
        selectors.append(f".{css_class}")

    return selectors


def style_def_to_css(style_def: StyleDefinition) -> str:
    """将单个 StyleDefinition 转换为完整的 CSS 规则字符串。"""
    rules = _style_def_to_css_rules(style_def)
    return "\n\n".join(rules)


def style_def_to_xhtml2pdf_css(style_def: StyleDefinition) -> str:
    """将单个 StyleDefinition 转换为 xhtml2pdf 兼容的 CSS 规则字符串。

    与 ``style_def_to_css`` 的区别：
    - 不输出 ``overflow-x``、``border-radius`` 等 xhtml2pdf 不支持的属性
    - 代码块使用 ``word-wrap: break-word`` 替代 ``overflow-x: auto``
    """
    rules = _style_def_to_css_rules(style_def, xhtml2pdf_compatible=True)
    return "\n\n".join(rules)


# ---------------------------------------------------------------------------
# 完整样式表生成
# ---------------------------------------------------------------------------

# 表格通用样式（独立于 StyleDefinition，适用于所有含表格的文档）
_TABLE_BASE_CSS = """
table {
    border-collapse: collapse;
    width: 100%;
    table-layout: fixed;
    margin: 0;
    padding: 0;
}
table, th, td {
    border: 1px solid #000000;
}
th, td {
    padding: 4pt 6pt;
    vertical-align: middle;
    word-wrap: break-word;
    overflow-wrap: break-word;
    word-break: break-all;
    -pdf-word-wrap: CJK;
}
"""

# 页面基础样式
_PAGE_BASE_CSS = """
body {
    margin: 72pt 72pt;
    font-family: "SimSun", "Times New Roman", serif;
    font-size: 12pt;
    line-height: 1.3;
    color: #000000;
}
"""

# 页面基础样式（xhtml2pdf 增强版：添加 @page 规则和图片约束）
_XHTML2PDF_PAGE_BASE_CSS = """
@page {
    size: A4;
    margin: 2.54cm;
}
body {
    font-family: "SimSun", "Times New Roman", serif;
    font-size: 12pt;
    line-height: 1.3;
    color: #000000;
    -pdf-word-wrap: CJK;
}
img {
    max-width: 100%;
    height: auto;
}
h1, h2, h3, h4, h5, h6 {
    page-break-after: avoid;
}
pre, code {
    page-break-inside: avoid;
}
table {
    page-break-inside: avoid;
}
"""


def generate_full_stylesheet() -> str:
    """生成完整的 CSS 样式表，包含所有预定义样式。

    Returns:
        完整的 CSS 字符串，可直接嵌入 HTML <style> 标签。
    """
    parts: list[str] = []

    # 页面基础样式
    parts.append(_PAGE_BASE_CSS)

    # 逐样式生成 CSS
    for style_def in ALL_STYLES:
        css = style_def_to_css(style_def)
        if css.strip():
            parts.append(css)

    # 表格样式
    parts.append(_TABLE_BASE_CSS)

    # 图片段落样式辅助
    parts.append("""
.image-paragraph {
    text-align: center;
    margin: 12pt 0;
}
""")

    return "\n\n".join(parts)


def generate_xhtml2pdf_stylesheet() -> str:
    """生成兼容 xhtml2pdf 的 CSS 样式表。

    与 ``generate_full_stylesheet`` 的区别：
    - 使用 ``@page`` 规则控制页面尺寸和边距
    - 添加 ``max-width: 100%`` 约束图片不超出页面
    - 添加 ``page-break-after/inside`` 防止标题/代码/表格被不合理截断
    - 代码块不使用 ``overflow-x`` 和 ``border-radius``

    Returns:
        完整的 CSS 字符串，可直接嵌入 xhtml2pdf 的 HTML <style> 标签。
    """
    parts: list[str] = []

    # 页面基础样式（含 @page 和图片约束）
    parts.append(_XHTML2PDF_PAGE_BASE_CSS)

    # 逐样式生成 xhtml2pdf 兼容 CSS
    for style_def in ALL_STYLES:
        css = style_def_to_xhtml2pdf_css(style_def)
        if css.strip():
            parts.append(css)

    # 表格样式
    parts.append(_TABLE_BASE_CSS)

    # 图片段落样式辅助
    parts.append("""
.image-paragraph {
    text-align: center;
    margin: 12pt 0;
}
""")

    return "\n\n".join(parts)
