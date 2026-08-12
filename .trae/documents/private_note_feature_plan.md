# 私密笔记功能实施计划

## 概述

在现有笔记应用基础上添加私密笔记功能：用户可将笔记标记为私密，通过全局密码（4或6位数字）保护，私密笔记默认隐藏，通过在搜索框输入 `/private` 指令触发密码验证后显示。

## 当前架构分析

- **数据库** (`core/database.py`): SQLite，`notes` 表字段为 `id, title, content, category_id, created_at, updated_at`
- **设置** (`core/settings.py`): JSON 文件存储在 `~/.zhuibook/settings.json`，目前仅有背景图设置
- **侧边栏** (`ui/sidebar.py`): `NoteListWidget` 右键菜单仅有「删除笔记」；`refresh_notes()` 从 DB 获取笔记并渲染
- **主窗口** (`ui/main_window.py`): 管理 sidebar + editor，处理笔记选中/创建/删除/保存
- **主题** (`ui/theme.py`): `get_sidebar_qss()` 返回侧边栏各组件样式，`get_sidebar_note_list_qss()` 返回列表样式

## 实施方案

### 第1步：数据库层 — 添加私密字段（`core/database.py`）

**修改 `init_database()` 方法**，为 `notes` 表添加列：
```sql
ALTER TABLE notes ADD COLUMN is_private INTEGER DEFAULT 0
```
使用 `try-except` 处理已存在的数据库（列已存在时忽略错误）。

**修改 `Note` dataclass**，添加字段：
```python
is_private: int = 0
```

**修改查询方法**，所有返回 Note 的查询自动包含 `is_private` 字段（`SELECT *` 已覆盖，无需改 SQL）。

**新增方法**：
- `set_note_private(note_id, is_private: bool)` — 设置/取消笔记私密状态
- `get_private_notes()` — 获取所有私密笔记
- `get_public_notes()` / 修改 `get_all_notes()` → 新增 `get_non_private_notes()` 获取非私密笔记

### 第2步：设置层 — 存储全局密码哈希（`core/settings.py`）

**修改 `_DEFAULT_SETTINGS`**，添加：
```python
"private_password_hash": "",  # SHA-256 hash of numeric password
```

`load_settings()` 和 `save_settings()` 无需修改逻辑，自动支持新字段。

### 第3步：密码工具模块（新建 `core/security.py`）

轻量级模块，提供：
```python
import hashlib

def hash_password(password: str) -> str:
    """SHA-256 哈希密码"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, stored_hash: str) -> bool:
    """验证密码是否匹配"""
    return hash_password(password) == stored_hash

def is_valid_password_format(password: str) -> bool:
    """检查密码格式：4位或6位纯数字"""
    return password.isdigit() and len(password) in (4, 6)
```

### 第4步：密码输入对话框（`ui/sidebar.py` 内实现）

在 `sidebar.py` 中新增 `PasswordDialog` 类（继承 `QDialog`），特点：
- 4位/6位数字密码输入框（`QLineEdit` 设置 `EchoMode.Password` + `setValidator` 限制纯数字 + `setMaxLength(6)`）
- 提示文字：「请输入私密笔记密码（4或6位数字）」
- 确认/取消按钮
- 样式使用当前主题色，与现有 `QInputDialog` 风格一致
- 首次设置密码时增加「确认密码」输入框

### 第5步：侧边栏逻辑改造（`ui/sidebar.py`）

#### 5.1 NoteListWidget 右键菜单增强

修改 `_show_context_menu()`，添加：
- 「🔒 设为私密笔记」— 当笔记非私密时显示
- 「🔓 取消私密」— 当笔记已设为私密时显示

#### 5.2 Sidebar 添加私密状态

新增属性：
```python
self._private_unlocked = False  # 私密笔记是否已解锁
```

#### 5.3 修改 `refresh_notes()` 方法

```python
def refresh_notes(self, keyword=None):
    self.note_list.clear()
    if keyword == "/private":
        # 触发密码验证流程
        self._try_unlock_private()
        return
    # 正常搜索/浏览
    if keyword:
        notes = self.db.search_notes(keyword)
    else:
        if self.current_category_id == -1:
            notes = self.db.get_all_notes()
        else:
            notes = self.db.get_notes_by_category(self.current_category_id)
    # 未解锁时过滤掉私密笔记
    if not self._private_unlocked:
        notes = [n for n in notes if not n.is_private]
    for note in notes:
        self._add_note_item(note)
```

#### 5.4 修改 `_add_note_item()` 方法

私密笔记在标题前添加 🔒 图标，区分显示。

#### 5.5 新增 `_try_unlock_private()` 方法

```python
def _try_unlock_private(self):
    # 检查是否已设置密码
    settings = load_settings()
    stored_hash = settings.get("private_password_hash", "")
    if not stored_hash:
        QMessageBox.information(self, "提示", "尚未设置私密笔记密码。请先将一篇笔记设为私密来创建密码。")
        self.search_edit.clear()
        return
    # 弹出密码输入框
    dialog = PasswordDialog(self, self.current_theme, mode="verify")
    if dialog.exec() == QDialog.Accepted:
        password = dialog.get_password()
        if verify_password(password, stored_hash):
            self._private_unlocked = True
            self.search_edit.clear()
            # 显示私密笔记
            notes = self.db.get_private_notes()
            for note in notes:
                self._add_note_item(note)
            self.list_label.setText("    🔓 私密笔记（已解锁）")
        else:
            QMessageBox.warning(self, "密码错误", "输入的密码不正确。")
            self.search_edit.clear()
```

#### 5.6 新增 `lock_private()` 方法

重新锁定私密笔记，恢复正常列表显示。

#### 5.7 新增「设为私密」处理流程

```python
def _set_note_private(self, note_id: int):
    settings = load_settings()
    stored_hash = settings.get("private_password_hash", "")
    if not stored_hash:
        # 首次设置密码
        dialog = PasswordDialog(self, self.current_theme, mode="set")
        if dialog.exec() != QDialog.Accepted:
            return
        password = dialog.get_password()
        if not is_valid_password_format(password):
            QMessageBox.warning(...)
            return
        stored_hash = hash_password(password)
        save_settings(private_password_hash=stored_hash)
    # 设置笔记为私密
    self.db.set_note_private(note_id, True)
    self.refresh_notes()
```

### 第6步：主窗口适配（`ui/main_window.py`）

- 在 `_on_note_deleted()` 中处理：如果删除的是当前打开的私密笔记且已锁定，清空编辑器
- 在 `closeEvent()` 中添加：退出时自动锁定私密笔记（重置 `_private_unlocked`）
- 搜索框 `/private` 指令处理：在 `_on_search()` 中透传给 sidebar，不额外处理

### 第7步：主题样式适配（`ui/theme.py`）

- 在 `get_sidebar_qss()` 中为密码对话框添加样式（复用现有 `input_bg`、`border`、`primary` 等色值）
- 私密笔记列表项的 🔒 图标不改变现有选中/hover 样式

## 文件变更清单

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `core/database.py` | 修改 | 添加 `is_private` 列、`Note` 字段、`set_note_private()` / `get_private_notes()` 方法 |
| `core/settings.py` | 修改 | `_DEFAULT_SETTINGS` 添加 `private_password_hash` |
| `core/security.py` | 新建 | 密码哈希/验证/格式检查工具函数 |
| `ui/sidebar.py` | 修改 | 密码对话框、右键菜单增强、私密笔记过滤/解锁逻辑 |
| `ui/main_window.py` | 修改 | 退出时锁定、删除私密笔记处理 |
| `ui/theme.py` | 修改 | 密码对话框样式 |

## 用户交互流程

### 设置私密笔记
1. 用户写完笔记 → 右键笔记列表项 → 点击「🔒 设为私密笔记」
2. 首次使用：弹出密码设置对话框 → 输入4或6位数字密码 → 确认密码 → 设置成功
3. 非首次：直接标记为私密，笔记从列表中消失（如未解锁）

### 查看私密笔记
1. 在搜索框输入 `/private` → 自动弹出密码输入框
2. 输入正确密码 → 列表切换为显示私密笔记，标题栏显示「🔓 私密笔记（已解锁）」
3. 查看完毕后清空搜索框或再次输入 `/private` → 重新锁定

### 取消私密
1. 解锁状态下右键私密笔记 → 点击「🔓 取消私密」→ 笔记恢复为普通笔记

## 验证步骤

1. 启动应用，右键任意笔记 → 应显示「设为私密笔记」选项
2. 首次设为私密 → 应弹出密码设置对话框（4或6位数字）
3. 设置密码后笔记从列表消失
4. 搜索框输入 `/private` → 弹出密码验证框
5. 输入正确密码 → 显示私密笔记列表（带🔒标记）
6. 输入错误密码 → 提示密码错误
7. 解锁状态下右键私密笔记 → 显示「取消私密」选项
8. 取消私密后笔记恢复普通显示
9. 重启应用 → 私密笔记默认隐藏，需重新输入 `/private` 解锁
10. 退出应用时自动锁定
