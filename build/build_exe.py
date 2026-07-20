"""MDTrans - PyInstaller 打包脚本。

用法:
    python build/build_exe.py

构建为单文件 exe，输出到 dist/ 目录。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# 确保 src/ 在 sys.path 中
_project_root = Path(__file__).resolve().parent.parent
_src = _project_root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))


def main() -> None:
    """执行 PyInstaller 打包。"""
    # 读取版本号
    try:
        from mdtrans.__about__ import __version__ as VERSION
    except Exception:
        VERSION = "1.0.0"

    # 导入 PyInstaller
    try:
        import PyInstaller.__main__
    except ImportError:
        print("请先安装 PyInstaller: pip install pyinstaller")
        sys.exit(1)

    # ── 收集 hidden imports ────────────────────────────────────────────────
    hidden_imports = [
        # GUI
        "mdtrans",
        "mdtrans.main",
        "mdtrans.app.navigator",
        "mdtrans.app.interface",
        # GUI 共享组件
        "mdtrans.gui._theme_manager",
        "mdtrans.gui._gui_helpers",
        "mdtrans.gui._dialogs",
        "mdtrans.gui._config",
        "mdtrans.gui._version",
        # 导出
        "mdtrans.export_ui.app",
        "mdtrans.export_ui.conversion",
        "mdtrans.export_services",
        "mdtrans.export_services.services.svc_md_to_docx",
        "mdtrans.export_services.services.svc_md_to_pdf",
        "mdtrans.export_services.services.svc_md_to_html",
        "mdtrans.export_services.services.svc_md_to_image",
        "mdtrans.export_services.utils.file_utils",
        "mdtrans.export_services.utils.image_utils",
        "mdtrans.export_services.utils.logger_utils",
        "mdtrans.export_services.utils.markdown_utils",
        "mdtrans.export_services.utils.mermaid_utils",
        "mdtrans.export_services.utils.mimetype_utils",
        "mdtrans.export_services.utils.pandoc_utils",
        "mdtrans.export_services.utils.param_utils",
        "mdtrans.export_services.utils.table_utils",
        "mdtrans.export_services.utils.text_utils",
        # 导入
        "mdtrans.import_ui.app",
        # Playwright（系统浏览器截图）
        "playwright",
        "playwright.sync_api",
    ]

    # ── 构建命令行参数 ────────────────────────────────────────────────────
    build_dir = _project_root / "build" / "pyinstaller"
    dist_dir = _project_root / "dist"

    args = [
        "--onefile",
        "--noconfirm",
        "--clean",
        "--windowed",
        f"--name=MDTrans_v{VERSION}",
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        f"--specpath={build_dir}",
        # 图标
        f"--icon={_project_root / 'res' / 'icon.ico'}",
        # Python 路径
        f"--paths={_src}",
    ]

    # 添加 hidden imports
    for mod in hidden_imports:
        args.append(f"--hidden-import={mod}")

    # ── 收集 reportlab 条码模块（xhtml2pdf 运行时动态导入） ───────────────
    args.append("--collect-submodules=reportlab.graphics.barcode")
    args.append("--collect-submodules=reportlab.pdfbase")
    # ── 收集 playwright 子模块（系统浏览器截图） ──────────────────────────
    args.append("--collect-submodules=playwright._impl")

    # ── 排除无关重型包 ──────────────────────────────────────────────────
    # 这些包不在项目依赖中，但 PyInstaller 会因 hook 扫描而误扫，拖慢打包
    exclude_modules = [
        # ML 框架
        "torch", "torchvision", "torchaudio", "torch.distributed",
        "tensorflow", "tensorboard",
        "transformers", "tokenizers", "sentencepiece",
        # CV
        "cv2", "opencv_python",
        # 数据分析（pandas 虽大但实际使用，保留）
        "pyarrow", "scipy", "scikit_learn", "sklearn",
        # 绘图
        "matplotlib", "seaborn", "plotly",
        # 其他无关
        "gi",  # GObject Introspection (Linux only)
        "nvidia", "cupy",  # GPU 相关
        "PIL.SpiderImagePlugin",  # 非必要 PIL 插件
        # Playwright 浏览器下载驱动（使用系统浏览器，不下载）
        "playwright._impl._driver",
        "playwright._impl._driver_server",
    ]
    for mod in exclude_modules:
        args.append(f"--exclude-module={mod}")

    # ── 添加数据文件 ────────────────────────────────────────────────────
    # 图标
    args.append(f"--add-data={_project_root / 'res' / 'icon.ico'}{os.pathsep}res/")

    # magika 模型文件（markitdown 传递依赖，运行时必须）
    try:
        import magika
        _magika_dir = Path(magika.__file__).parent
        # 模型目录（含 model.onnx ~3MB）
        args.append(
            f"--add-data={_magika_dir / 'models'}{os.pathsep}magika/models"
        )
        # 配置目录（含 content_types_kb.min.json）
        args.append(
            f"--add-data={_magika_dir / 'config'}{os.pathsep}magika/config"
        )
    except ImportError:
        print("警告：未找到 magika 包，导入转换功能可能异常")

    # DOCX 模板文件
    _template_dir = _project_root / "src" / "mdtrans" / "export_services" / "assets" / "template"
    if _template_dir.exists():
        args.append(
            f"--add-data={_template_dir}{os.pathsep}mdtrans/export_services/assets/template"
        )

    # ── 入口文件 ────────────────────────────────────────────────────────
    entry = _src / "mdtrans" / "__main__.py"
    args.append(str(entry))

    # ── 执行打包 ────────────────────────────────────────────────────────
    print(f"MDTrans v{VERSION} 开始打包...")
    print(f"Python: {sys.executable}")
    print(f"入口: {entry}")
    print(f"输出: {dist_dir / f'MDTrans_v{VERSION}.exe'}")
    print("-" * 60)

    PyInstaller.__main__.run(args)

    print("-" * 60)
    print(f"打包完成！输出文件: {dist_dir / f'MDTrans_v{VERSION}.exe'}")


if __name__ == "__main__":
    main()
