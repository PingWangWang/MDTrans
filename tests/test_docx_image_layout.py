"""DOCX 图片排版回归测试。"""

from pathlib import Path

import pytest
from docx import Document
from docx.shared import Pt
from PIL import Image

from mdtrans.export_services.services.svc_md_to_docx import (
    IMAGE_MAX_HEIGHT_RATIO,
    _apply_formatting,
    _get_image_limits,
)


def _create_a4_document():
    """创建使用项目样例页边距的 A4 文档。"""
    doc = Document()
    section = doc.sections[0]
    section.page_width = Pt(595.3)
    section.page_height = Pt(841.9)
    section.left_margin = Pt(90)
    section.right_margin = Pt(90)
    section.top_margin = Pt(72)
    section.bottom_margin = Pt(72)
    return doc


def _create_test_image(path: Path) -> None:
    """生成用于验证尺寸缩放的本地 PNG 图片。"""
    Image.new("RGB", (100, 100), "white").save(path)


def _get_image_paragraph(doc):
    """返回文档中包含图片的段落。"""
    return next(
        paragraph
        for paragraph in doc.paragraphs
        if paragraph._element.xpath(".//w:drawing")
    )


def test_tall_image_reserves_space_for_following_text(tmp_path):
    """纵向超大图片应缩小并与其后正文保持同页。"""
    image_path = tmp_path / "tall.png"
    _create_test_image(image_path)

    doc = _create_a4_document()
    image_paragraph = doc.add_paragraph()
    image_paragraph.add_run().add_picture(str(image_path), width=Pt(420), height=Pt(2100))
    doc.add_paragraph("图片后的正文。")

    output_path = tmp_path / "tall.docx"
    doc.save(output_path)
    _apply_formatting(output_path)

    formatted = Document(output_path)
    max_width, max_height = _get_image_limits(formatted)
    shape = formatted.inline_shapes[0]
    image_paragraph = _get_image_paragraph(formatted)

    assert max_width == pytest.approx(415.3, abs=0.2)
    assert max_height == pytest.approx(697.9 * IMAGE_MAX_HEIGHT_RATIO, abs=0.2)
    assert shape.height.pt <= max_height + 0.1
    assert shape.width.pt <= max_width + 0.1
    assert image_paragraph.paragraph_format.line_spacing == pytest.approx(1.0)
    assert image_paragraph.paragraph_format.keep_with_next is True

    display_extent = image_paragraph._element.xpath(".//wp:extent")[0]
    graphic_extent = image_paragraph._element.xpath(".//pic:spPr/a:xfrm/a:ext")[0]
    assert int(display_extent.get("cx")) == int(graphic_extent.get("cx"))
    assert int(display_extent.get("cy")) == int(graphic_extent.get("cy"))


def test_wide_image_is_limited_to_content_width(tmp_path):
    """横向超大图片应缩小到正文区宽度以内并保持宽高比。"""
    image_path = tmp_path / "wide.png"
    _create_test_image(image_path)

    doc = _create_a4_document()
    image_paragraph = doc.add_paragraph()
    image_paragraph.add_run().add_picture(str(image_path), width=Pt(900), height=Pt(450))
    doc.add_paragraph("图片后的正文。")

    output_path = tmp_path / "wide.docx"
    doc.save(output_path)
    _apply_formatting(output_path)

    formatted = Document(output_path)
    max_width, _ = _get_image_limits(formatted)
    shape = formatted.inline_shapes[0]

    assert shape.width.pt <= max_width + 0.1
    assert shape.width.pt / shape.height.pt == pytest.approx(2.0, rel=0.01)


def test_small_image_is_not_resized(tmp_path):
    """未超过限制的小图片应保持原始尺寸。"""
    image_path = tmp_path / "small.png"
    _create_test_image(image_path)

    doc = _create_a4_document()
    image_paragraph = doc.add_paragraph()
    image_paragraph.add_run().add_picture(str(image_path), width=Pt(200), height=Pt(120))

    output_path = tmp_path / "small.docx"
    doc.save(output_path)
    _apply_formatting(output_path)

    formatted = Document(output_path)
    shape = formatted.inline_shapes[0]

    assert shape.width.pt == pytest.approx(200.0, abs=0.1)
    assert shape.height.pt == pytest.approx(120.0, abs=0.1)
