"""MDTrans - 配置持久化管理器。

从 MarkitDownGUI 迁移，扩展为双模式配置支持。
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _get_config_dir() -> Path:
    """获取配置存储目录。

    优先级：
    1. PyInstaller 打包时：%APPDATA%\\MDTrans
    2. 开发模式：项目根目录
    """
    if getattr(sys, "frozen", False):
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            return Path(appdata) / "MDTrans"
    return Path(__file__).resolve().parent.parent.parent.parent  # src/ 上级


CONFIG_FILE = _get_config_dir() / "config.json"


# 默认配置
DEFAULT_CONFIG: dict = {
    "theme": "light",
    "import": {
        "last_output_dir": "",
        "image_mode": "file",
    },
    "export": {
        "last_output_dir": "",
        "last_format": "docx",
        "use_template": False,
        "template_path": "",
        "convert_mermaid": True,
        "save_mermaid_images": False,
    },
    "window": {
        "width": 750,
        "height": 560,
    },
}


def load_config() -> dict:
    """从 JSON 文件加载配置，缺失字段以默认值填充。"""
    config = dict(DEFAULT_CONFIG)
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, encoding="utf-8") as f:
                saved = json.load(f)
            _deep_merge(config, saved)
    except Exception:
        pass
    return config


def save_config(config: dict) -> None:
    """保存配置到 JSON 文件。"""
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def _deep_merge(base: dict, override: dict) -> None:
    """递归合并 dict，override 中的值覆盖 base。"""
    for key, val in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(val, dict):
            _deep_merge(base[key], val)
        else:
            base[key] = val
