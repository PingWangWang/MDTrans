---
name: bump-version
description: 修改代码后自动递增版本号补丁位（patch+1），同步更新所有引用处
---

# Bump Version — 代码修改后自动递增版本号

## 概述

修改代码后，调用此 skill 自动将版本号的补丁号（patch）+1。
版本号单源真理在 `src/mdtrans/__about__.py`，所有引用处自动同步。

## 执行步骤

### 步骤 1：读取当前版本号

```python
from pathlib import Path
import re

about_file = Path("src/mdtrans/__about__.py")
content = about_file.read_text(encoding="utf-8")
match = re.search(r'__version__\s*=\s*"([^"]+)"', content)
current = match.group(1)
print(f"当前版本: {current}")
```

### 步骤 2：解析并递增补丁号

```python
parts = current.split(".")
parts[-1] = str(int(parts[-1]) + 1)
new_version = ".".join(parts)
new_info = tuple(int(x) for x in parts)
print(f"新版本: {new_version}")
```

### 步骤 3：更新 `__about__.py`

替换两处：
- `__version__ = "{current}"` → `__version__ = "{new_version}"`
- `__version_info__ = ({current_tuple})` → `__version_info__ = ({new_info})`

### 步骤 4：更新 `_version.py` 中的回退值

`src/mdtrans/gui/_version.py` L30:
```python
return "{current}"  →  return "{new_version}"
```

### 步骤 5：同步 `pyproject.toml`

```bash
python scripts/sync_version.py
```

### 步骤 6：验证

确认三处版本号一致：
- `__about__.py` — 单源真理
- `_version.py` — 回退值
- `pyproject.toml` — 包配置

输出：
```
版本号: X.Y.Z → X.Y.Z+1
已同步: __about__.py / _version.py / pyproject.toml
```
