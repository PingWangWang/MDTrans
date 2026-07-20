# MDTrans — 双向文档转换工具

> 在 20+ 种文档格式与 Markdown 之间自由转换，导入靠 MarkItDown，导出靠 Pandoc + 自定义样式管线。

![Python](https://img.shields.io/badge/Python-3.11+-blue) ![License](https://img.shields.io/badge/License-Apache--2.0-green) ![Version](https://img.shields.io/badge/Version-1.0.0-orange)

**适合谁用**：需要批量处理文档格式的开发者、写作/翻译工作者、需要将 Markdown 导出为排版工整的 Word/PDF 的团队协作场景。

---

## ✨ 项目亮点

- **导入（20+ 格式 → Markdown）** — 基于 Microsoft MarkItDown 引擎，覆盖 PDF、Office 文档、图片、音频、邮件、Notebook 等常见格式
- **导出（Markdown → DOCX / PDF / HTML）** — 内置中文排版样式管线，支持自定义 Word 模板、Mermaid 图表自动渲染
- **GUI 桌面应用** — 基于 tkinter + ttkbootstrap，支持亮/暗主题、拖拽导入、批量转换
- **支持二次开发** — 纯 Python 实现、模块清晰、可直接作为库调用转换服务

## 📦 安装

```bash
# 使用 uv（推荐）
uv sync

# 或使用 pip
pip install -e .
```

> 💡 **图片导出**：功能将使用系统已安装的 Microsoft Edge 或 Google Chrome 浏览器，无需额外下载。

可选扩展：

```bash
# 安装全部可选依赖（音频转写、YouTube 字幕、OCR、拖拽支持）
uv sync --extra all
```

> 最低要求：Python ≥ 3.11

## 🚀 快速开始

```bash
# 启动 GUI（推荐，自动使用虚拟环境）
uv run python run.py

# 或作为模块启动
uv run python -m mdtrans

# 或通过已安装的命令行入口
mdtrans
```

开启后你将看到两个 Tab 页面：

**📥 导入模式** — 拖拽或选择文件，一键转为 Markdown
**📤 导出模式** — 选择 Markdown 文件，导出为 DOCX / PDF / HTML

## 🧭 使用示例

### 导入：PDF → Markdown

1. 打开 MDTrans，切换到 **📥 To Markdown** 页
2. 点击"添加文件"或直接拖入 PDF 文件
3. 点击"开始转换"，在右侧查看 Markdown 预览
4. 点击"保存"导出为 `.md` 文件

### 导出：Markdown → DOCX（含 Mermaid 图表）

1. 切换到 **📤 To DOCX/PDF/HTML** 页
2. 添加 Markdown 文件（支持批量）
3. 选择输出格式为 **DOCX**
4. （可选）勾选"转换图表"，表格中的 Mermaid 代码块将被渲染为图片嵌入
5. 点击"开始导出"，自动应用中文排版样式

## 📁 项目结构

```
MDTrans/
├── src/
│   └── mdtrans/
│       ├── __init__.py          # 包入口
│       ├── __main__.py          # `python -m mdtrans` 入口
│       ├── main.py              # GUI 启动入口（Tkinter 根窗口初始化）
│       ├── app/
│       │   ├── interface.py     # 页面接口定义（IPage Protocol）
│       │   └── navigator.py     # Tab 切换导航器
│       ├── gui/
│       │   ├── _config.py       # 配置读写（JSON）
│       │   ├── _dialogs.py      # 对话框（关于、主题选择、覆盖确认）
│       │   ├── _gui_helpers.py  # GUI 工具函数
│       │   ├── _theme_manager.py# 主题管理器（亮/暗切换）
│       │   └── _version.py      # 版本号读取
│       ├── import_ui/
│       │   └── app.py           # 导入模式 GUI 页面
│       ├── export_ui/
│       │   ├── app.py           # 导出模式 GUI 页面
│       │   └── conversion.py    # 导出转换业务逻辑
│       ├── import_services/     # 导入引擎（基于 MarkItDown）
│       │   └── markitdown/
│       └── export_services/     # 导出引擎
│           ├── services/
│           │   ├── svc_md_to_docx.py     # Markdown → DOCX
│           │   ├── svc_md_to_pdf.py      # Markdown → PDF
│           │   ├── svc_md_to_html.py     # Markdown → HTML
│           │   ├── svc_md_to_html_text.py# Markdown → 纯文本 HTML
│           │   └── svc_md_to_codeblock.py# Markdown → 代码块提取
│           └── utils/
│               ├── markdown_utils.py     # Markdown 文本提取
│               ├── mermaid_utils.py      # Mermaid 图表渲染
│               ├── pandoc_utils.py       # Pandoc 转换封装
│               ├── table_utils.py        # 表格处理
│               └── file_utils.py         # 文件工具
├── tests/
│   ├── test_export/
│   ├── test_gui/
│   └── test_import/
├── build/
│   └── build_exe.py             # PyInstaller 打包脚本
├── res/
│   └── icon.ico                 # 应用图标
├── config.json                  # 用户配置持久化
├── pyproject.toml               # 项目元数据与依赖
└── run.py                       # 开发快速启动入口
```

## 📥 导入支持格式

| 类别 | 格式 |
|------|------|
| 文档 | PDF、DOCX、DOC（旧版）、RTF、EPUB |
| 办公 | PPTX、XLSX、XLS（旧版） |
| 网页 | HTML、HTM、RSS、XML |
| 数据 | CSV、JSON |
| 图片 | JPEG、PNG、GIF、BMP |
| 音频 | WAV、MP3（需安装 `audio` 扩展） |
| 邮件 | MSG（Outlook） |
| 代码 | ZIP 压缩包、Jupyter Notebook (ipynb) |

## 📤 导出支持格式

| 格式 | 说明 | 特色 |
|------|------|------|
| **DOCX** | Word 文档 | 中文排版样式、Mermaid 图表渲染 |
| **PDF** | PDF 文档 | 基于 xhtml2pdf 渲染 |
| **HTML** | HTML 网页 | 干净可发布的 HTML 输出 |

## 🛠️ 开发

```bash
# 安装开发依赖
uv sync --dev

# 运行测试
uv run pytest

# 代码检查
uv run ruff check src/

# 打包为单文件 exe
python build/build_exe.py
```

打包产物位于 `dist/MDTrans_v1.0.0.exe`，可直接分发给无需 Python 环境的 Windows 用户。

## ⚙️ 配置说明

配置文件 `config.json` 位于项目根目录，支持：

```json
{
  "theme": "light",              // 亮/暗主题
  "import": {
    "image_mode": "embed"        // 图片模式：embed/link
  },
  "export": {
    "last_format": "DOCX",       // 默认导出格式
    "convert_mermaid": true      // 是否渲染 Mermaid 图表
  },
  "window": {
    "width": 750,                // 窗口宽度
    "height": 560                // 窗口高度
  }
}
```

## ❓ 适用场景

- **写作与发布**：用 Markdown 写稿，导出为 DOCX 提交给排版或打印
- **文档归档**：将 PDF、Office 文件批量转换为 Markdown，便于版本管理和全文检索
- **知识库迁移**：将 HTML/EPUB 等电子书格式转为 Markdown，导入笔记软件
- **团队协作**：统一使用 Markdown 协作，最终导出为带有公司模板的 Word 文档
- **内容中台**：将 Markdown 作为源格式，一次编写多渠道发布（Word + PDF + HTML）

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

- Bug 报告 / 功能建议：请开 GitHub Issue
- 代码贡献：Fork → 创建分支 → 提交 PR
- 代码风格：使用 Ruff（`uv run ruff check src/`）

## 📝 许可证

Apache-2.0 — 详见 [LICENSE](LICENSE)

---

> **技术栈**：Python 3.11+ · tkinter + ttkbootstrap · MarkItDown · Pandoc · python-docx · xhtml2pdf · Pillow · PyInstaller
