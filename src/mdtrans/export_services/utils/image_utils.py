#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片处理工具函数

提供格式编码、均匀切分、文件大小预估等功能，
供 ``svc_md_to_image`` 转换服务使用。
"""

from __future__ import annotations

import io
from typing import Sequence

from PIL import Image

# ── 格式常量 ─────────────────────────────────────────────────────────────────

# 支持导出的图片格式（小写）
SUPPORTED_FORMATS: frozenset[str] = frozenset({"png", "jpeg", "webp", "bmp", "tiff"})

# 有损压缩格式（quality 参数有效）
LOSSY_FORMATS: frozenset[str] = frozenset({"jpeg", "webp"})

# 无损格式
LOSSLESS_FORMATS: frozenset[str] = frozenset({"png", "bmp", "tiff"})

# 格式默认扩展名
FORMAT_EXTENSIONS: dict[str, str] = {
    "png": ".png",
    "jpeg": ".jpg",
    "webp": ".webp",
    "bmp": ".bmp",
    "tiff": ".tiff",
}


def encode_image(
    image: Image.Image,
    image_format: str,
    quality: int | None = None,
) -> bytes:
    """将 PIL Image 编码为指定格式的字节流。

    Args:
        image: PIL Image 对象（RGB 或 RGBA）。
        image_format: 目标格式（小写），如 ``"png"``、``"jpeg"``、``"webp"``。
        quality: 压缩质量 1–100。对 JPEG/WebP 有意义；PNG/BMP/TIFF 忽略此参数。

    Returns:
        编码后的图片字节流。

    Raises:
        ValueError: 不支持的图片格式。
    """
    fmt = image_format.lower()
    if fmt not in SUPPORTED_FORMATS:
        raise ValueError(f"不支持的图片格式: {image_format}，可选: {', '.join(sorted(SUPPORTED_FORMATS))}")

    # JPEG 不支持 RGBA，需要转 RGB
    if fmt == "jpeg" and image.mode == "RGBA":
        image = image.convert("RGB")

    save_kwargs: dict = {"format": fmt.upper()}
    if fmt in LOSSY_FORMATS and quality is not None:
        save_kwargs["quality"] = max(1, min(100, quality))

    buf = io.BytesIO()
    image.save(buf, **save_kwargs)
    return buf.getvalue()


def split_image_evenly(image: Image.Image, n_pages: int) -> list[Image.Image]:
    """将 PIL Image 在垂直方向上均匀切分为 N 张子图。

    Args:
        image: 输入 PIL Image（建议为 RGB/RGBA 模式）。
        n_pages: 切分份数（>= 1）。若为 1，返回原始图片的副本列表。

    Returns:
        N 张子图列表，每个子图高度 ≈ 原始高度 / N。

    Raises:
        ValueError: n_pages 小于 1。
    """
    if n_pages < 1:
        raise ValueError(f"页数必须 >= 1，收到: {n_pages}")

    if n_pages == 1:
        return [image.copy()]

    width, total_height = image.size
    page_height = total_height // n_pages
    images: list[Image.Image] = []

    for i in range(n_pages):
        top = i * page_height
        # 最后一张包含剩余像素，避免整除截断丢掉内容
        bottom = total_height if i == n_pages - 1 else (i + 1) * page_height
        box = (0, top, width, bottom)
        images.append(image.crop(box))

    return images


def _pixel_count_to_bytes(
    pixels: int,
    image_format: str,
    quality: int | None,
) -> int:
    """基于像素数和格式参数估算图片字节数。

    估算基于典型压缩率参考值，不保证精确：
      - PNG: 约 0.5–2.0 bytes/px（取决于内容复杂度）
      - JPEG: quality 1 → 0.05, quality 100 → 0.55 bytes/px
      - WebP: 比 JPEG 约小 25–35%
      - BMP: 每像素 3 字节（RGB）或 4 字节（RGBA）
      - TIFF: 约 1.0–2.5 bytes/px

    Args:
        pixels: 总像素数（宽 × 高）。
        image_format: 目标格式（小写）。
        quality: 压缩质量 1–100（仅 JPEG/WebP 有效）。

    Returns:
        估算的字节数。
    """
    fmt = image_format.lower()

    if fmt == "png":
        # PNG 无损，假设中等复杂度 ~1.0 bytes/px
        bpp = 1.0
    elif fmt == "jpeg":
        # JPEG 线性插值：quality=1 → 0.05, quality=50 → 0.25, quality=100 → 0.55
        q = min(100, max(1, quality if quality is not None else 85))
        bpp = 0.05 + (q / 100) * 0.50
    elif fmt == "webp":
        q = min(100, max(1, quality if quality is not None else 85))
        # WebP 比 JPEG 约小 30%
        bpp = (0.05 + (q / 100) * 0.50) * 0.70
    elif fmt == "bmp":
        bpp = 3.0
    elif fmt == "tiff":
        bpp = 1.5
    else:
        bpp = 1.0

    return int(pixels * bpp)


def estimate_image_size(
    md_text: str,
    image_format: str,
    quality: int | None = None,
    image_width: int = 1200,
    dpi: int = 96,
    page_count: int = 1,
) -> tuple[str, str]:
    """估算转换后单张图片的文件大小。

    基于 Markdown 文本长度估算渲染后的像素数，
    再按格式和压缩参数推算字节数。

    Args:
        md_text: Markdown 文本。
        image_format: 目标图片格式。
        quality: 压缩质量 1–100。
        image_width: 图片宽度（像素）。
        dpi: 输出 DPI。
        page_count: 目标图片张数。
        page_count: 目标图片张数。

    Returns:
        ``(per_page_str, total_str)`` 元组，
        如 ``("120 KB", "360 KB")``。
    """
    # 估算总行数
    char_count = len(md_text)
    estimated_lines = max(1, char_count // 60)  # 每行约 60 字符

    # 估算总体高度（像素）
    line_height_px = 22.0 * (dpi / 96.0)  # 行高约 22px @96dpi
    estimated_total_height = int(estimated_lines * line_height_px)

    # 每张图的高度
    per_page_height = estimated_total_height // page_count

    # 像素数
    pixels_per_page = image_width * per_page_height

    # 估算字节
    bytes_per_page = _pixel_count_to_bytes(pixels_per_page, image_format, quality)
    bytes_total = bytes_per_page * page_count

    def _human_size(b: int) -> str:
        """将字节数转换为人类可读的字符串（B/KB/MB）。"""
        if b < 1024:
            return f"{b} B"
        elif b < 1024 * 1024:
            return f"{b // 1024} KB"
        else:
            return f"{b / 1024 / 1024:.1f} MB"

    return _human_size(bytes_per_page), _human_size(bytes_total)


def open_image_from_bytes(data: bytes) -> Image.Image:
    """从字节流打开 PIL Image。

    Args:
        data: 图片字节流。

    Returns:
        PIL Image 对象（转换为 RGB 模式）。
    """
    image = Image.open(io.BytesIO(data))
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGB")
    return image


def normalize_format_name(name: str) -> str:
    """标准化图片格式名为小写键名。

    Args:
        name: 用户输入的格式名，如 ``"JPEG"``、``"PNG"``、``"WebP"``。

    Returns:
        小写标准化名称，如 ``"jpeg"``、``"png"``、``"webp"``。
    """
    lower = name.lower().strip()
    # JPEG 和 JPG 统一
    if lower == "jpg":
        return "jpeg"
    # TIFF 和 TIF 统一
    if lower == "tif":
        return "tiff"
    return lower
