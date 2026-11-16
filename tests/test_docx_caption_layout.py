"""DOCX 图注和表注排版回归测试。"""

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from PIL import Image

from mdtrans.export_services.services.svc_md_to_docx import convert_md_to_docx


def test_docx_pandoc_captions_are_centered_and_ordered(tmp_path):
    """标准图注和表注应居中，并分别位于图片下方和表格上方。"""
    image_path = tmp_path / "sample.png"
    Image.new("RGB", (320, 180), "white").save(image_path)

    md_text = f"""# 图注与表注测试

![图 2-1 图片名称]({image_path.as_posix()})

| 序号 | 名称 |
|---|---|
| 1 | 项目一 |

: 表 2-1 表格名称
"""
    output_path = tmp_path / "captions.docx"

    convert_md_to_docx(md_text, output_path, convert_mermaid=False)

    doc = Document(output_path)
    image_paragraph = next(p for p in doc.paragraphs if p.style.name == "Image Paragraph")
    image_caption = next(p for p in doc.paragraphs if p.style.name == "Image Caption")
    table_caption = next(p for p in doc.paragraphs if p.style.name == "Table Caption")

    assert image_paragraph.paragraph_format.keep_with_next is True
    assert image_caption.paragraph_format.alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert image_caption.paragraph_format.left_indent.pt == 0
    assert image_caption.paragraph_format.first_line_indent.pt == 0
    assert image_caption.paragraph_format.keep_with_next is False

    assert table_caption.paragraph_format.alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert table_caption.paragraph_format.left_indent.pt == 0
    assert table_caption.paragraph_format.first_line_indent.pt == 0
    assert table_caption.paragraph_format.keep_with_next is True

    body_elements = list(doc.element.body.iterchildren())
    image_index = next(
        index
        for index, element in enumerate(body_elements)
        if any(node.tag.endswith("drawing") for node in element.iter())
    )
    image_caption_index = next(
        index
        for index, element in enumerate(body_elements)
        if element.tag == qn("w:p") and "图 2-1 图片名称" in "".join(element.itertext())
    )
    table_caption_index = next(
        index
        for index, element in enumerate(body_elements)
        if element.tag == qn("w:p") and "表 2-1 表格名称" in "".join(element.itertext())
    )
    table_index = next(
        index for index, element in enumerate(body_elements) if element.tag == qn("w:tbl")
    )

    assert image_caption_index == image_index + 1
    assert table_caption_index + 1 == table_index
