# 私密笔记问题修复计划

## 问题诊断

### 问题1：设为私密后笔记仍然出现在左侧列表（与普通笔记混排）

**根因**：
1. 当前 `refresh_notes()` 在 `_private_unlocked=True` 状态下会将 **私密笔记 + 普通笔记全部渲染在同一列表**，没有区分显示。用户期望解锁后只显示私密笔记列表，与普通笔记完全分离。
2. 私密笔记项前有🔒标记，但和普通笔记混在一起视觉上没有隔离感，应该解锁后显示"私密笔记专区"。
3. 设为私密后，如果用户当前处于解锁状态，笔记不会从列表消失，缺少"设为私密 → 立即隐藏"的提示。

### 问题2：密码设置可以输入8位数字（非4或6位）

**根因**：
1. `QIntValidator(0, 999999)` 是**范围限制**（最多6位数 0-999999），**不是位数限制**。在某些输入场景下（如通过输入法粘贴数字），可能绕过 `setMaxLength(6)` 限制。
2. `_on_accept()` 虽通过 `is_valid_password_format()` 验证密码格式，但 `confirm_edit` 的长度和格式没有独立验证，并且输入过程中缺少实时拦截。

## 修复方案

### 修改文件：`ui/sidebar.py`

#### 修改点1：`refresh_notes()` — 解锁状态下只显示私密笔记

**目标**：私密笔记与普通笔记完全分离，两种列表不同时显示。

逻辑修改：
```python
def refresh_notes(self, keyword=None):
    self.note_list.clear()
    if self._private_unlocked:
        # 解锁状态：只显示私密笔记（不与普通笔记混排）
        self.list_label.setText("    \U0001f513 私密笔记（已解锁）")
        if keyword:
            notes = [n for n in self.db.search_notes(keyword) if n.is_private]
        else:
            notes = self.db.get_private_notes()
        for note in notes:
            self._add_note_item(note)
    else:
        # 正常状态：显示非私密笔记
        self.list_label.setText("    笔记列表")
        if keyword:
            notes = [n for n in self.db.search_notes(keyword) if not n.is_private]
        else:
            if self.current_category_id == -1:
                notes = [n for n in self.db.get_all_notes() if not n.is_private]
            else:
                notes = [n for n in self.db.get_notes_by_category(self.current_category_id) if not n.is_private]
        for note in notes:
            self._add_note_item(note)
```

#### 修改点2：`_on_toggle_private()` — 设为私密后立即隐藏

逻辑修改：
```python
def _on_toggle_private(self, note_id: int):
    note = self.db.get_note(note_id)
    if note is None:
        return
    if note.is_private:
        # 取消私密
        self.db.set_note_private(note_id, False)
        # 如果当前在解锁视图，取消私密后笔记会从私密列表消失，切换回正常视图
        if self._private_unlocked:
            self._private_unlocked = False
        self.refresh_notes()
    else:
        # 设为私密
        settings = load_settings()
        stored_hash = settings.get("private_password_hash", "")
        if not stored_hash:
            dialog = PasswordDialog(self, self.current_theme, mode="set")
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            password = dialog.get_password()
            stored_hash = hash_password(password)
            save_settings(private_password_hash=stored_hash)
        self.db.set_note_private(note_id, True)
        # 设为私密后立即从普通列表隐藏（重置解锁状态）
        self._private_unlocked = False
        self.refresh_notes()
```

#### 修改点3：`PasswordDialog` — 严格限制4/6位数字

**输入实时验证（替换 `QIntValidator` + `setMaxLength` 方案）**：

```python
from PyQt6.QtCore import QRegularExpression
from PyQt6.QtGui import QRegularExpressionValidator

# _build_ui() 内部改用：
# 使用 inputMask 让用户只能输入数字，位数根据输入动态限制（4或6）
# 两个输入框改用 setInputMask("000000")（最多6位数字，0 表示必须是数字）

self.pwd_edit.setInputMask("000000")   # 只能输入数字，最大6位
self.pwd_edit.setMaxLength(6)
# 去掉 QIntValidator

if self._mode == "set":
    self.confirm_edit.setInputMask("000000")
    self.confirm_edit.setMaxLength(6)
    # 去掉 QIntValidator
```

**`_on_accept()` 加强校验**：
```python
def _on_accept(self):
    pwd = self.pwd_edit.text().strip()
    if not is_valid_password_format(pwd):
        QMessageBox.warning(self, "格式错误",
            "密码格式不正确。\n请输入 4 位或 6 位纯数字（例如 1234 或 123456）。")
        self.pwd_edit.selectAll()
        self.pwd_edit.setFocus()
        return
    if self._mode == "set" and self.confirm_edit is not None:
        confirm = self.confirm_edit.text().strip()
        # 确认密码同样校验格式
        if not is_valid_password_format(confirm):
            QMessageBox.warning(self, "格式错误",
                "确认密码格式不正确。\n请输入 4 位或 6 位纯数字。")
            self.confirm_edit.selectAll()
            self.confirm_edit.setFocus()
            return
        if pwd != confirm:
            QMessageBox.warning(self, "密码不一致",
                "两次输入的密码不一致，请重新输入。")
            self.confirm_edit.selectAll()
            self.confirm_edit.setFocus()
            return
    self.accept()
```

#### 修改点4：`_try_unlock_private()` — 解锁后切换分类过滤

```python
def _try_unlock_private(self):
    ...
    if verify_password(password, stored_hash):
        self._private_unlocked = True
        # 解锁后清空搜索框和分类，显示私密笔记专区
        self.search_edit.blockSignals(True)
        self.search_edit.clear()
        self.search_edit.blockSignals(False)
        self.category_combo.blockSignals(True)
        self.category_combo.setCurrentIndex(0)
        self.category_combo.blockSignals(False)
        self.refresh_notes()  # 此时已设置 _private_unlocked=True，会只显示私密笔记
    else:
        ...
```

#### 修改点5：`_lock_private()` — 锁定时重置分类选择

```python
def _lock_private(self):
    self._private_unlocked = False
    self.category_combo.blockSignals(True)
    self.category_combo.setCurrentIndex(0)
    self.category_combo.blockSignals(False)
    self.refresh_notes()
```

#### 修改点6：`_add_note_item()` — 私密笔记解锁视图下标题可移除🔒前缀

解锁视图本身就是"私密笔记专区"，🔒 会显得冗余，可根据需要保留或移除。建议保留以增强视觉识别，但可以调整为：
- 普通视图：永不显示私密笔记（无论标题有没有🔒）
- 解锁视图：私密笔记标题前显示 `🔒` 标记

**无需改动**，当前代码在 `is_private` 时添加 `🔒`，两种视图都适用。

#### 修改点7：`_on_search_text_changed()` — 私密视图下搜索

解锁视图下，搜索框应限定只搜私密笔记。此逻辑已在修改点1的 `refresh_notes` 中处理（当 `_private_unlocked=True` 时，搜索结果会额外过滤 `if n.is_private`）。

#### 修改点8：`_on_category_changed()` — 私密视图下禁用分类切换

私密视图下用户只看私密笔记，分类下拉不应起作用。修改：

```python
def _on_category_changed(self, index: int):
    if index < 0:
        return
    data = self.category_combo.itemData(index)
    self.current_category_id = data
    self.search_edit.clear()
    # 解锁视图下忽略分类选择，始终显示全部私密笔记
    if self._private_unlocked:
        return
    self.refresh_notes()
```

### 验证步骤

1. **设为私密**：右键任意笔记 → 设为私密 → 设置4位密码（如 `1234`）→ 笔记应立即从列表消失
2. **8位密码应被拒绝**：设置密码时尝试 `12345678` → 应提示格式错误
3. **5位密码应被拒绝**：设置密码时尝试 `12345` → 应提示格式错误
4. **4位密码应成功**：设置密码时输入 `1234` + 确认 `1234` → 成功设置
5. **6位密码应成功**：重设密码，输入 `123456` + 确认 → 成功设置
6. **解锁查看**：搜索框输入 `/private` → 输入密码 → 列表应只显示私密笔记（标签：🔓 私密笔记（已解锁）），没有普通笔记
7. **重新锁定**：再次输入 `/private` → 恢复显示普通笔记，私密笔记消失
8. **取消私密**：解锁状态下右键私密笔记 → 取消私密 → 笔记出现在普通列表
9. **退出锁定**：解锁状态下关闭程序 → 重启 → 私密笔记默认隐藏
