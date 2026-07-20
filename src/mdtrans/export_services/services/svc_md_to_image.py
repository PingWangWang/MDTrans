#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown 转图片转换服务

基于 Playwright 控制系统已安装的浏览器（Edge / Chrome）
将 Markdown 渲染为 HTML，然后截取全页截图，
再通过 Pillow 切分为指定张数的图片。

使用流程（在 GUI 线程外调用）::

    from mdtrans.export_services.services.svc_md_to_image import convert_md_to_image

    convert_md_to_image(md_text, "output", "/path/to/dir", ImageOptions(...))
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PIL import Image as PILImage

from ..utils.image_utils import (
    FORMAT_EXTENSIONS,
    encode_image,
    estimate_image_size,
    normalize_format_name,
    open_image_from_bytes,
    split_image_evenly,
)
from ..utils.markdown_utils import get_md_text
from ..utils import get_logger

logger = get_logger(__name__)


@dataclass
class ImageOptions:
    """Markdown → 图片 转换选项。

    Attributes:
        image_format: 输出图片格式（小写），如 ``"png"``、``"jpeg"``、``"webp"``。
        quality: 压缩质量 1–100（仅 JPEG/WebP 有效；PNG/BMP/TIFF 忽略）。
        page_count: 输出图片张数（均匀切分），默认 1（单张长图）。
        image_width: 渲染宽度（像素），默认 1200。
        background_color: 页面背景色，默认 ``"white"``。
        padding: 内容边距（像素），默认 40。
        convert_mermaid: 是否渲染 Mermaid 图表，默认 True。
        dpi: 输出 DPI，默认 96。
    """
    image_format: str = "png"
    quality: int = 100
    page_count: int = 1
    image_width: int = 1200
    background_color: str = "white"
    padding: int = 40
    convert_mermaid: bool = True
    dpi: int = 96


def _build_html(
    md_text: str,
    options: ImageOptions,
    log_callback: Callable[[str], None] | None = None,
) -> str:
    """将 Markdown 文本转换为带完整 CSS 样式的 HTML 页面。

    复用 pandoc 将 MD → HTML，再注入 ``generate_full_stylesheet()`` 生成的
    与 DOCX 风格一致的 CSS 样式表。

    Args:
        md_text: 预处理后的 Markdown 文本。
        options: 图片转换选项（用于边距、背景色等）。
        log_callback: 可选的日志回调。

    Returns:
        完整的 HTML 字符串，含 <!DOCTYPE> 声明，可直接用浏览器渲染。

    Raises:
        ImportError: pypandoc 未安装。
        ValueError: Markdown 内容为空或处理失败。
    """
    from pypandoc import convert_text  # noqa: PLC0415
    from ..styles.css_adapter import generate_full_stylesheet  # noqa: PLC0415

    processed_md = get_md_text(md_text, is_strip_wrapper=False)
    if log_callback:
        log_callback("  · 调用 pandoc 将 Markdown 转换为 HTML...")

    html_body = convert_text(processed_md, format="markdown", to="html")
    full_css = generate_full_stylesheet()

    # 覆盖 body 边距和背景色
    body_margin = f"{options.padding}px"
    bg_color = options.background_color
    body_override = (
        f"body {{ margin: {body_margin}; background-color: {bg_color}; }}\n"
    )
    # 图片段落额外留空
    img_style = (
        ".image-paragraph img { max-width: 100%; height: auto; }\n"
    )

    full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width={options.image_width}">
<style>
{full_css}
{body_override}
{img_style}
</style>
</head>
<body>
{html_body}
</body>
</html>
"""
    return full_html


def _render_html_to_image(
    html: str,
    options: ImageOptions,
    log_callback: Callable[[str], None] | None = None,
) -> PILImage.Image:
    """使用 Playwright 将 HTML 渲染为全页截图。

    优先使用系统已安装的浏览器（Edge → Chrome），避免下载 Chromium。
    PyInstaller 打包环境下设置 ``PLAYWRIGHT_BROWSERS_PATH=0`` 阻止自动下载。

    Args:
        html: 完整的 HTML 页面字符串。
        options: 图片转换选项（视口宽度、DPI 等）。
        log_callback: 可选的日志回调。

    Returns:
        PIL Image 对象（RGB 模式），为完整文档的长截图。

    Raises:
        ImportError: ``playwright`` 包未安装。
        RuntimeError: 无法找到可用浏览器或渲染失败。
    """
    try:
        from playwright.sync_api import sync_playwright  # noqa: PLC0415
    except ImportError as e:
        if getattr(sys, "frozen", False):
            raise ImportError(
                "缺少 playwright 模块，打包时未包含。请重新打包并确保 playwright 已加入 hiddenimports。"
            ) from e
        raise ImportError(
            "缺少 playwright 依赖。请运行:\n"
            "  uv add playwright"
        ) from e

    # 打包环境下阻止 Playwright 自动下载 Chromium
    import os as _os
    if getattr(sys, "frozen", False):
        _os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "0")

    if log_callback:
        log_callback("  · 启动浏览器渲染引擎...")

    # ── 尝试按优先级连接系统已安装浏览器 ──────────────────────────────
    # Edge (Win10/11 内置) → Chrome → 无头 Chromium（仅开发环境）
    _channels_to_try: list[tuple[str, str] | str] = [
        ("msedge", "Microsoft Edge"),
        ("chrome", "Google Chrome"),
    ]
    # 非打包环境（开发模式）额外尝试无头 Chromium（用户可能手动安装过）
    if not getattr(sys, "frozen", False):
        _channels_to_try.append(("chromium", "Chromium"))  # type: ignore[arg-type]

    _last_error: Exception | None = None
    screenshot: bytes | None = None

    for channel, label in _channels_to_try:
        try:
            with sync_playwright() as p:
                launch_kwargs = {"headless": True}
                if channel in ("msedge", "chrome"):
                    launch_kwargs["channel"] = channel
                browser = p.chromium.launch(**launch_kwargs)
                context = browser.new_context(
                    viewport={"width": options.image_width, "height": 800},
                    device_scale_factor=options.dpi / 96.0,
                )
                page = context.new_page()
                page.set_content(html)
                page.wait_for_load_state("networkidle")

                if log_callback:
                    log_callback("  · 截取全页截图...")

                screenshot = page.screenshot(full_page=True)
                browser.close()
                if log_callback:
                    log_callback(f"  ✓ 使用 {label} 渲染完成")
                break
        except Exception as e:
            _last_error = e
            if log_callback:
                log_callback(f"  ⚠ {label} 不可用，尝试下一个...")
            continue

    if screenshot is None:
        raise RuntimeError(
            "未找到可用的浏览器（Chrome 或 Edge）。\n"
            "请安装 Microsoft Edge 或 Google Chrome 后重试。\n"
            f"详细信息: {_last_error}"
        )

    return open_image_from_bytes(screenshot)


def convert_md_to_image(
    md_text: str,
    output_stem: str,
    output_dir: str,
    options: ImageOptions,
    log_callback: Callable[[str], None] | None = None,
) -> list[Path]:
    """将 Markdown 文本转换为指定张数的图片文件。

    完整管线：Markdown → pandoc(HTML) → Playwright(系统浏览器截图) → Pillow(切分+编码)。
    优先使用系统已安装的 Edge/Chrome 浏览器，无需额外下载。

    Args:
        md_text: 原始 Markdown 文本。
        output_stem: 输出文件前缀名（不含路径和后缀），
            实际文件为 ``{output_stem}_p001{ext}``、``{output_stem}_p002{ext}`` 等。
        output_dir: 输出目录路径。
        options: 图片转换选项。
        log_callback: 可选的日志回调函数。

    Returns:
        已保存的图片文件路径列表，按页码顺序排列。

    Raises:
        ValueError: Markdown 内容为空或参数无效。
        ImportError: 缺少依赖（pypandoc、playwright）。
        RuntimeError: 渲染或保存过程失败。
    """
    if not md_text or not md_text.strip():
        raise ValueError("Markdown 内容为空，无法转换")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    ext = FORMAT_EXTENSIONS.get(normalize_format_name(options.image_format), ".png")
    fmt = normalize_format_name(options.image_format)

    if log_callback:
        log_callback(f"  源格式: Markdown → 图片 ({fmt.upper()})")
        log_callback(f"  图片设置: {options.image_width}px × {options.page_count}张, quality={options.quality}")

    # 1. Markdown → HTML
    html = _build_html(md_text, options, log_callback)

    # 2. HTML → 全页截图（Playwright）
    full_image = _render_html_to_image(html, options, log_callback)

    # 3. 均匀切分
    if log_callback:
        log_callback(f"  · 切分为 {options.page_count} 张图片...")

    pages = split_image_evenly(full_image, options.page_count)

    # 4. 编码并保存
    saved_paths: list[Path] = []
    total_width, total_height = full_image.size
    if log_callback:
        log_callback(f"  渲染尺寸: {total_width}×{total_height}px → {len(pages)} 页")

    for i, page in enumerate(pages, 1):
        data = encode_image(page, fmt, quality=options.quality)
        filename = f"{output_stem}_p{i:03d}{ext}"
        filepath = output_path / filename
        filepath.write_bytes(data)
        saved_paths.append(filepath)

        if log_callback:
            w, h = page.size
            kb = len(data) / 1024
            log_callback(f"  ✓ 第 {i} 页: {filename} ({w}×{h}px, {kb:.0f} KB)")

    if log_callback:
        log_callback(f"  ✓ 共生成 {len(saved_paths)} 张图片")

    return saved_paths


def estimate_preview_size(
    md_text: str,
    options: ImageOptions,
) -> tuple[str, str]:
    """预估转换后的图片大小（不实际渲染）。

    用于 GUI 下拉选择质量时实时更新显示。

    Args:
        md_text: Markdown 文本。
        options: 图片转换选项。

    Returns:
        ``(per_page, total)`` 元组，如 ``("120 KB", "360 KB")``。
    """
    return estimate_image_size(
        md_text=md_text,
        image_format=options.image_format,
        quality=options.quality,
        image_width=options.image_width,
        dpi=options.dpi,
        page_count=options.page_count,
    )
