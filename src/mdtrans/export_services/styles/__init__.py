"""
统一样式抽象层

本模块提供跨格式的样式定义和适配器：
- `definitions`：StyleDefinition 数据类及所有预定义样式实例
- `docx_adapter`：将 StyleDefinition 转换为 python-docx 样式操作
- `css_adapter`：将 StyleDefinition 转换为 CSS 规则字符串

使用方式：
    from ..styles.definitions import HEADING_1, NORMAL
    from ..styles.docx_adapter import create_or_update_style, apply_para_formatting
    from ..styles.css_adapter import generate_full_stylesheet
"""

from .definitions import (
    StyleDefinition,
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
    ALL_STYLES,
    STYLE_BY_NAME,
)
from . import docx_adapter
from . import css_adapter

__all__ = [
    "StyleDefinition",
    "HEADING_1",
    "HEADING_2",
    "HEADING_3",
    "HEADING_4",
    "HEADING_5",
    "HEADING_6",
    "NORMAL",
    "LIST_PARAGRAPH",
    "CUSTOM_LIST",
    "TABLE_TEXT",
    "IMAGE_PARAGRAPH",
    "CODE_BLOCK",
    "TOC_1",
    "TOC_2",
    "TOC_3",
    "ALL_STYLES",
    "STYLE_BY_NAME",
    "docx_adapter",
    "css_adapter",
]
