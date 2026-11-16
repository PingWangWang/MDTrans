"""Mermaid 图注转换回归测试。"""

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from PIL import Image

from mdtrans.export_services.utils import mermaid_utils
from mdtrans.export_services.services.svc_md_to_docx import convert_md_to_docx


def test_mermaid_caption_becomes_image_alt_text(tmp_path, monkeypatch):
    """Mermaid图名应写入图片替代文本，并移除重复的可见图名段落。"""

    def fake_convert_mermaid_to_image(mermaid_code, output_path, **_kwargs):
        Image.new("RGB", (320, 180), "white").save(output_path)
        return output_path

    monkeypatch.setattr(
        mermaid_utils, "convert_mermaid_to_image", fake_convert_mermaid_to_image
    )

    md_text = """# 测试

```mermaid
flowchart TB
    accTitle: 图2-1：项目整体业务流程图
    A --> B
```

图2-1：项目整体业务流程图

后续正文。

```mermaid
flowchart LR
    C --> D
```

图2-2：系统模块依赖关系图

结束。
"""

    modified_text, images, stats, failed = mermaid_utils.replace_mermaid_with_images(
        md_text, tmp_path
    )

    assert stats == {"total": 2, "success": 2, "failed": 0}
    assert failed == []
    assert len(images) == 2
    assert "![图2-1：项目整体业务流程图](mermaid_1_flowchart.png)" in modified_text
    assert "![图2-2：系统模块依赖关系图](mermaid_2_flowchart.png)" in modified_text
    assert modified_text.count("图2-1：项目整体业务流程图") == 1
    assert modified_text.count("图2-2：系统模块依赖关系图") == 1
    assert "后续正文。" in modified_text
    assert "结束。" in modified_text


def test_mermaid_caption_is_centered_in_docx(tmp_path, monkeypatch):
    """Mermaid图名应通过Image Caption样式在DOCX中居中。"""

    def fake_convert_mermaid_to_image(mermaid_code, output_path, **_kwargs):
        Image.new("RGB", (320, 180), "white").save(output_path)
        return output_path

    monkeypatch.setattr(
        mermaid_utils, "convert_mermaid_to_image", fake_convert_mermaid_to_image
    )

    md_text = """# 测试

```mermaid
flowchart TB
    accTitle: 图2-1：项目整体业务流程图
    A --> B
```

图2-1：项目整体业务流程图
"""
    output_path = tmp_path / "mermaid_caption.docx"

    convert_md_to_docx(md_text, output_path, convert_mermaid=True)

    doc = Document(output_path)
    image_caption = next(p for p in doc.paragraphs if p.style.name == "Image Caption")
    assert image_caption.text == "图2-1：项目整体业务流程图"
    assert image_caption.paragraph_format.alignment == WD_ALIGN_PARAGRAPH.CENTER


def test_docx_conversion_returns_mermaid_failure_stats(tmp_path, monkeypatch):
    """DOCX 服务应返回失败统计，并保留失败代码供调用层反馈。"""
    monkeypatch.setattr(
        mermaid_utils,
        "convert_mermaid_to_image",
        lambda *_args, **_kwargs: None,
    )

    md_text = """# 测试

```mermaid
flowchart LR
    A --> B
```
"""
    output_path = tmp_path / "failed_mermaid.docx"

    stats = convert_md_to_docx(md_text, output_path, convert_mermaid=True)

    assert stats == {"total": 1, "success": 0, "failed": 1}
    assert output_path.exists()
    assert (tmp_path / "failed_mermaid_failed_mermaid_codes.md").exists()
