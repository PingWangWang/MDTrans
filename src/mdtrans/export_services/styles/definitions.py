"""
统一样式定义

定义 `StyleDefinition` 数据类，以及 MDTrans 支持的全部 14 种段落样式。
每种样式的视觉属性与 DOCX 的 `STYLE_CONFIGS` 完全对应，供所有格式共用。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# 样式定义数据类
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StyleDefinition:
    """段落样式定义 —— 跨格式的唯一样式源。

    每个实例描述一种段落样式的全部视觉属性。
    各格式适配器从此数据类生成对应的样式代码（python-docx / CSS 等）。

    Attributes:
        name: 样式名称，如 "Heading 1"
        style_keywords: Pandoc 输出中的样式名匹配关键字
        font_name: 中文字体名称
        font_name_latin: 西文字体名称
        font_size_pt: 字号（磅）
        bold: 是否加粗
        italic: 是否斜体
        color_hex: 字体颜色十六进制（如 "#000000"）
        first_line_indent_pt: 首行缩进（磅）
        left_indent_pt: 左缩进（磅）
        line_spacing: 行距倍数
        space_before_pt: 段前间距（磅）
        space_after_pt: 段后间距（磅）
        background_color_hex: 背景色十六进制（如 "#000000"），None 表示无背景
        alignment: 对齐方式 ("left", "center", "right")
        is_list: 是否为列表项
        is_custom_list: 是否为自定义列表项
        is_table: 是否为表格内文本
        is_image: 是否为图片段落
        is_code: 是否为代码块
        is_toc: 是否为目录项
    """

    name: str
    style_keywords: tuple[str, ...] = ()
    font_name: str = "宋体"
    font_name_latin: str = "Times New Roman"
    font_size_pt: float = 12.0
    bold: bool = False
    italic: bool = False
    color_hex: str = "#000000"
    first_line_indent_pt: float = 0.0
    left_indent_pt: float = 0.0
    line_spacing: float = 1.3
    space_before_pt: float = 0.0
    space_after_pt: float = 0.0
    background_color_hex: Optional[str] = None
    alignment: str = "left"
    is_list: bool = False
    is_custom_list: bool = False
    is_table: bool = False
    is_image: bool = False
    is_code: bool = False
    is_toc: bool = False


# ---------------------------------------------------------------------------
# 预定义样式实例
# ---------------------------------------------------------------------------

HEADING_1 = StyleDefinition(
    name="Heading 1",
    style_keywords=("Heading 1",),
    font_name="宋体",
    font_name_latin="Times New Roman",
    font_size_pt=20.0,
    bold=True,
    color_hex="#000000",
    line_spacing=1.3,
    space_before_pt=3.0,
    space_after_pt=3.0,
)

HEADING_2 = StyleDefinition(
    name="Heading 2",
    style_keywords=("Heading 2",),
    font_name="宋体",
    font_name_latin="Times New Roman",
    font_size_pt=18.0,
    bold=True,
    color_hex="#000000",
    line_spacing=1.3,
    space_before_pt=3.0,
    space_after_pt=3.0,
)

HEADING_3 = StyleDefinition(
    name="Heading 3",
    style_keywords=("Heading 3",),
    font_name="宋体",
    font_name_latin="Times New Roman",
    font_size_pt=16.0,
    bold=True,
    color_hex="#000000",
    line_spacing=1.3,
    space_before_pt=3.0,
    space_after_pt=3.0,
)

HEADING_4 = StyleDefinition(
    name="Heading 4",
    style_keywords=("Heading 4",),
    font_name="宋体",
    font_name_latin="Times New Roman",
    font_size_pt=14.0,
    bold=True,
    color_hex="#000000",
    line_spacing=1.3,
    space_before_pt=3.0,
    space_after_pt=3.0,
)

HEADING_5 = StyleDefinition(
    name="Heading 5",
    style_keywords=("Heading 5",),
    font_name="宋体",
    font_name_latin="Times New Roman",
    font_size_pt=12.0,
    bold=True,
    color_hex="#000000",
    line_spacing=1.3,
    space_before_pt=3.0,
    space_after_pt=3.0,
)

HEADING_6 = StyleDefinition(
    name="Heading 6",
    style_keywords=("Heading 6",),
    font_name="宋体",
    font_name_latin="Times New Roman",
    font_size_pt=12.0,
    bold=True,
    color_hex="#000000",
    line_spacing=1.3,
    space_before_pt=3.0,
    space_after_pt=3.0,
)

NORMAL = StyleDefinition(
    name="Normal",
    style_keywords=("Normal",),
    font_name="宋体",
    font_name_latin="Times New Roman",
    font_size_pt=12.0,
    color_hex="#000000",
    first_line_indent_pt=24.0,
    line_spacing=1.3,
)

LIST_PARAGRAPH = StyleDefinition(
    name="List Paragraph",
    style_keywords=("List Paragraph", "List"),
    font_name="宋体",
    font_name_latin="Times New Roman",
    font_size_pt=12.0,
    color_hex="#000000",
    line_spacing=1.3,
    is_list=True,
)

CUSTOM_LIST = StyleDefinition(
    name="Custom List",
    font_name="宋体",
    font_name_latin="Times New Roman",
    font_size_pt=12.0,
    color_hex="#000000",
    first_line_indent_pt=24.0,
    line_spacing=1.3,
    is_custom_list=True,
)

TABLE_TEXT = StyleDefinition(
    name="Table Text",
    font_name="宋体",
    font_name_latin="Times New Roman",
    font_size_pt=12.0,
    color_hex="#000000",
    line_spacing=1.0,
    alignment="center",
    is_table=True,
)

IMAGE_PARAGRAPH = StyleDefinition(
    name="Image Paragraph",
    font_name="宋体",
    font_name_latin="Times New Roman",
    font_size_pt=12.0,
    color_hex="#000000",
    line_spacing=1.3,
    alignment="center",
    is_image=True,
)

CODE_BLOCK = StyleDefinition(
    name="Code Block",
    font_name="宋体",
    font_name_latin="Times New Roman",
    font_size_pt=10.5,  # 五号字
    italic=True,
    color_hex="#FFFFFF",
    left_indent_pt=24.0,  # 左缩进 2 字符
    line_spacing=1.0,
    background_color_hex="#000000",  # 黑色背景
    is_code=True,
)

TOC_1 = StyleDefinition(
    name="Table of Contents 1",
    style_keywords=("Table of Contents 1", "TOC 1"),
    font_name="宋体",
    font_name_latin="Times New Roman",
    font_size_pt=12.0,
    color_hex="#000000",
    line_spacing=1.0,
    is_toc=True,
)

TOC_2 = StyleDefinition(
    name="Table of Contents 2",
    style_keywords=("Table of Contents 2", "TOC 2"),
    font_name="宋体",
    font_name_latin="Times New Roman",
    font_size_pt=12.0,
    color_hex="#000000",
    line_spacing=1.0,
    is_toc=True,
)

TOC_3 = StyleDefinition(
    name="Table of Contents 3",
    style_keywords=("Table of Contents 3", "TOC 3"),
    font_name="宋体",
    font_name_latin="Times New Roman",
    font_size_pt=12.0,
    color_hex="#000000",
    line_spacing=1.0,
    is_toc=True,
)

# ---------------------------------------------------------------------------
# 聚合导出
# ---------------------------------------------------------------------------

ALL_STYLES: list[StyleDefinition] = [
    HEADING_1,
    HEADING_2,
    HEADING_3,
    HEADING_4,
    HEADING_5,
    HEADING_6,
    NORMAL,
    LIST_PARAGRAPH,
    CUSTOM_LIST,
    TABLE_TEXT,
    IMAGE_PARAGRAPH,
    CODE_BLOCK,
    TOC_1,
    TOC_2,
    TOC_3,
]

STYLE_BY_NAME: dict[str, StyleDefinition] = {s.name: s for s in ALL_STYLES}

# Pandoc / 语法高亮可能产生的代码样式关键字（用于 DOCX 代码块检测）
CODE_STYLE_KEYWORDS: tuple[str, ...] = (
    "Preformatted",
    "Code",
    "Source Code",
    "NormalTok",
    "Verbatim",
    "KeywordTok",
    "StringTok",
    "CommentTok",
    "FunctionTok",
    "VariableTok",
    "DataTypeTok",
    "DecValTok",
    "BaseNTok",
    "FloatTok",
    "ConstantTok",
    "CharTok",
    "SpecialCharTok",
    "ImportTok",
    "DocumentationTok",
    "AnnotationTok",
    "OtherTok",
    "ControlFlowTok",
    "OperatorTok",
    "BuiltInTok",
    "ExtensionTok",
    "PreprocessorTok",
    "AttributeTok",
    "RegionMarkerTok",
    "InformationTok",
    "WarningTok",
    "AlertTok",
    "ErrorTok",
)
