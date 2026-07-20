"""验证版本号一致性：__about__.py 与 pyproject.toml 必须匹配。"""
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


def test_version_consistency():
    """__about__.py 是版本号单源真理，pyproject.toml 必须与之一致。"""
    root = Path(__file__).resolve().parent.parent

    # 从 __about__.py 读取
    about_path = root / "src" / "mdtrans" / "__about__.py"
    about_content = about_path.read_text(encoding="utf-8")
    about_match = re.search(r'__version__\s*=\s*"([^"]+)"', about_content)
    assert about_match, "无法从 __about__.py 读取 __version__"
    about_ver = about_match.group(1)

    # 从 pyproject.toml 读取
    pyproject_path = root / "pyproject.toml"
    pyproject_content = pyproject_path.read_text(encoding="utf-8")
    pyproject_match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject_content, re.MULTILINE)
    assert pyproject_match, "无法从 pyproject.toml 读取 version"
    pyproject_ver = pyproject_match.group(1)

    assert about_ver == pyproject_ver, (
        f"版本号不一致\n"
        f"  __about__.py:  {about_ver}\n"
        f"  pyproject.toml: {pyproject_ver}\n"
        f"  请运行: python scripts/sync_version.py"
    )
