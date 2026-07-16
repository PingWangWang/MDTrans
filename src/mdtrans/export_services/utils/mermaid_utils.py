#!/usr/bin/env python3
"""
Mermaid 图表转图片工具模块

提供将 Mermaid 代码转换为 PNG/SVG 图片的功能,使用 mermaid.ink 在线服务。
支持超时重试机制,可在 DOCX/PPTX 等转换服务中复用。
"""

import base64
import re
import time
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import requests

from ..utils import get_logger

logger = get_logger(__name__)

# mermaid.ink API 配置
MERMAID_INK_API = "https://mermaid.ink/img/"
DEFAULT_TIMEOUT = 30  # 默认超时时间（秒），增加到 30 秒以应对大图片
MAX_RETRIES = 5  # 最大重试次数，增加到 5 次提高成功率
RETRY_DELAY = 3  # 重试间隔（秒），增加到 3 秒避免频繁请求


def encode_mermaid_code(code: str) -> str:
    """
    将 Mermaid 代码编码为 mermaid.ink 所需的格式
    
    Args:
        code: Mermaid 图表代码
        
    Returns:
        编码后的字符串
    """
    # 移除首尾空白
    code = code.strip()
    
    # 将代码转为 base64
    code_bytes = code.encode('utf-8')
    encoded = base64.urlsafe_b64encode(code_bytes).decode('utf-8')
    
    return encoded


def extract_mermaid_blocks(md_text: str) -> list[tuple[str, int, int]]:
    """
    从 Markdown 文本中提取所有 Mermaid 代码块
    
    Args:
        md_text: Markdown 文本
        
    Returns:
        列表，每个元素为 (mermaid_code, start_pos, end_pos)
    """
    pattern = r'```mermaid\s*\n(.*?)\n\s*```'
    matches = []
    
    for match in re.finditer(pattern, md_text, re.DOTALL | re.IGNORECASE):
        code = match.group(1).strip()
        if code:
            matches.append((code, match.start(), match.end()))
    
    logger.info(f"找到 {len(matches)} 个 Mermaid 代码块")
    return matches


def convert_mermaid_to_image(
    mermaid_code: str,
    output_path: Path,
    image_format: str = "png",
    timeout: int = DEFAULT_TIMEOUT,
    max_retries: int = MAX_RETRIES,
    retry_delay: int = RETRY_DELAY,
    scale: int = 3,  # 缩放比例，默认 3 倍以提高清晰度
    theme: str = "default",  # 主题：default, dark, forest, neutral
) -> Optional[Path]:
    """
    将 Mermaid 代码转换为图片文件
    
    Args:
        mermaid_code: Mermaid 图表代码
        output_path: 输出图片路径
        image_format: 图片格式 ('png' 或 'svg')
        timeout: 请求超时时间（秒）
        max_retries: 最大重试次数
        retry_delay: 重试间隔（秒）
        scale: 图片缩放比例 (1-5)，值越大越清晰但文件越大，默认 3
        theme: 主题风格 (default, dark, forest, neutral)
        
    Returns:
        成功返回输出路径，失败返回 None
    """
    # 在 mermaid 代码前添加配置，设置更大的渲染尺寸
    config_block = f"""%%{{init: {{'theme': '{theme}', 'themeVariables': {{'fontSize': '20px', 'nodeBorder': '#333', 'lineColor': '#666'}}, 'flowchart': {{'htmlLabels': true, 'curve': 'basis', 'padding': 20, 'nodeSpacing': 50, 'rankSpacing': 80}}}} }}%%\n"""
    enhanced_code = config_block + mermaid_code
    
    encoded_code = encode_mermaid_code(enhanced_code)
    
    # 构建 URL
    # mermaid.ink 的基础格式: https://mermaid.ink/img/{encoded_code}
    url = f"{MERMAID_INK_API}{encoded_code}"
    
    logger.info(f"正在转换 Mermaid 图表到: {output_path.name} (缩放: {scale}x)")
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"尝试 {attempt}/{max_retries}: 请求 mermaid.ink 服务...")
            
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            
            # 保存图片
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"✓ Mermaid 图表转换成功: {output_path.name}")
            return output_path
            
        except requests.exceptions.Timeout:
            logger.warning(f"⚠ 请求超时 (尝试 {attempt}/{max_retries})")
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"⚠ 连接错误 (尝试 {attempt}/{max_retries}): {e}")
        except requests.exceptions.HTTPError as e:
            logger.error(f"✗ HTTP 错误 (尝试 {attempt}/{max_retries}): {e}")
            # HTTP 错误通常不需要重试
            break
        except Exception as e:
            logger.warning(f"⚠ 未知错误 (尝试 {attempt}/{max_retries}): {e}")
        
        # 如果不是最后一次尝试，等待后重试
        if attempt < max_retries:
            logger.info(f"等待 {retry_delay} 秒后重试...")
            time.sleep(retry_delay)
    
    logger.error(f"✗ Mermaid 图表转换失败（已重试 {max_retries} 次）")
    return None


def replace_mermaid_with_images(
    md_text: str,
    temp_dir: Path,
    image_format: str = "png",  # 使用 PNG 格式
    timeout: int = DEFAULT_TIMEOUT,
    max_retries: int = MAX_RETRIES,
    retry_delay: int = RETRY_DELAY,
    scale: int = 3,  # 缩放比例（仅 PNG 需要，SVG 不需要）
    theme: str = "default",  # 主题风格
) -> tuple[str, list[Path], dict, list[dict]]:
    """
    将 Markdown 中的 Mermaid 代码块替换为图片引用
    
    Args:
        md_text: 原始 Markdown 文本
        temp_dir: 临时目录，用于存放生成的图片
        image_format: 图片格式 ('png' 或 'svg')
        timeout: 请求超时时间（秒）
        max_retries: 最大重试次数
        retry_delay: 重试间隔（秒）
        scale: 图片缩放比例 (1-5)，值越大越清晰，默认 3
        theme: 主题风格 (default, dark, forest, neutral)
        
    Returns:
        (修改后的 Markdown 文本, 生成的图片路径列表, 统计信息字典, 失败的代码列表)
        统计信息字典包含: {'total': 总数, 'success': 成功数, 'failed': 失败数}
        失败的代码列表包含: [{'index': 序号, 'code': 代码, 'filename': 文件名}, ...]
    """
    mermaid_blocks = extract_mermaid_blocks(md_text)
    
    if not mermaid_blocks:
        logger.info("未发现 Mermaid 代码块，跳过转换")
        return md_text, [], {'total': 0, 'success': 0, 'failed': 0}, []
    
    # 确保临时目录存在
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    modified_text = md_text
    generated_images = []
    offset = 0  # 用于跟踪文本偏移量
    success_count = 0
    failed_count = 0
    failed_codes = []  # 保存转换失败的 Mermaid 代码
    
    for idx, (code, start, end) in enumerate(mermaid_blocks, 1):
        logger.info(f"处理第 {idx}/{len(mermaid_blocks)} 个 Mermaid 图表...")
        
        # 生成图片文件名，包含图表类型信息
        # 尝试从代码中提取图表类型（graph, flowchart, sequenceDiagram 等）
        chart_type = "diagram"  # 默认类型
        first_line = code.strip().split('\n')[0].strip().lower()
        if 'graph' in first_line or 'flowchart' in first_line:
            chart_type = "flowchart"
        elif 'sequencediagram' in first_line:
            chart_type = "sequence"
        elif 'classdiagram' in first_line:
            chart_type = "class"
        elif 'statediagram' in first_line:
            chart_type = "state"
        elif 'erdiagram' in first_line:
            chart_type = "er"
        elif 'gantt' in first_line:
            chart_type = "gantt"
        elif 'pie' in first_line:
            chart_type = "pie"
        elif 'gitgraph' in first_line:
            chart_type = "git"
        elif 'mindmap' in first_line:
            chart_type = "mindmap"
        
        img_filename = f"mermaid_{idx}_{chart_type}.{image_format}"
        img_path = temp_dir / img_filename
        
        # 转换 Mermaid 为图片
        result_path = convert_mermaid_to_image(
            code,
            img_path,
            image_format=image_format,
            timeout=timeout,
            max_retries=max_retries,
            retry_delay=retry_delay,
            scale=scale,
            theme=theme,
        )
        
        if result_path and result_path.exists():
            generated_images.append(result_path)
            success_count += 1
                    
            # 构建图片引用（Markdown 格式）- 使用空替代文本避免显示额外文字
            img_ref = f"![]({img_filename})"
                    
            # 替换原文本中的代码块
            adjusted_start = start + offset
            adjusted_end = end + offset
            modified_text = modified_text[:adjusted_start] + img_ref + modified_text[adjusted_end:]
                    
            # 更新偏移量
            offset += len(img_ref) - (adjusted_end - adjusted_start)
                    
            logger.info(f"✓ 已替换第 {idx} 个 Mermaid 图表为图片")
        else:
            failed_count += 1
            # 保存失败的代码
            failed_codes.append({
                'index': idx,
                'code': code,
                'filename': img_filename
            })
            logger.error(f"✗ 第 {idx} 个 Mermaid 图表转换失败，保留原始代码")
    
    stats = {
        'total': len(mermaid_blocks),
        'success': success_count,
        'failed': failed_count
    }
    
    logger.info(f"完成：共转换 {success_count}/{len(mermaid_blocks)} 个 Mermaid 图表")
    return modified_text, generated_images, stats, failed_codes


def cleanup_temp_images(image_paths: list[Path]) -> None:
    """
    清理临时生成的图片文件
    
    Args:
        image_paths: 图片路径列表
    """
    for img_path in image_paths:
        try:
            if img_path.exists():
                img_path.unlink()
                logger.debug(f"已删除临时文件: {img_path.name}")
        except Exception as e:
            logger.warning(f"无法删除临时文件 {img_path.name}: {e}")
