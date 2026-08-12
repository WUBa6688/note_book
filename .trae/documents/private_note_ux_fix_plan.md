# 私密笔记体验问题修复计划

## 问题诊断

### 问题1：解锁后无法方便地回到普通笔记视图（图一）

**根因**：解锁后侧边栏只显示「🔒 私密笔记（已解锁）」列表，没有明显的"回到全部笔记"入口。用户只能通过再次在搜索框输入 `/private` 来锁定，但这个交互不直观，用户可能不知道。

**修复方案**：在解锁视图的标签旁添加一个小「🔒」锁定按钮，点击后立即锁定并回到全部笔记视图。

### 问题2：密码输入框显示6个下划线占位符（图二）

**根因**：`setInputMask("000000")` 在 `EchoMode.Password` 模式下仍会显示下划线占位符 `______`（表示输入位置），与 `placeholderText` "4或6位数字" 视觉冲突，导致混乱显示。

**修复方案**：移除 `setInputMask`，改用 `setValidator(QIntValidator(0, 999999))` + `setMaxLength(6)`。Validator 限制只能输入数字，maxLength 限制最多6位字符，不会显示下划线。配合 `_on_accept` 中的 `is_valid_password_format` 严格校验 4 或 6 位数字，安全性不受影响。

## 修改文件：`ui/sidebar.py`

### 修改点1：PasswordDialog 密码框（修复图二）

**位置**：`_build_ui()` 方法中的密码输入框创建代码

将：
```python
self.pwd_edit.setInputMask("000000")
```
改为：
```python
self.pwd_edit.setValidator(QIntValidator(0, 999999))
```

两个输入框（`pwd_edit` 和 `confirm_edit`）都需要修改。

### 修改点2：解锁视图添加锁定按钮（修复图一）

**位置**：`Sidebar._build_ui()` 方法中 `list_label` 创建后，以及 `_add_note_item` 附近逻辑

在 `list_label` 所在行的右侧添加一个小锁定按钮 `self.lock_btn`：
- 初始隐藏（`hide()`）
- 解锁状态下显示
- 点击后调用 `_lock_private()` 回到普通视图
- 图标使用「🔒」，固定宽度 32px，样式与现有按钮一致

需要修改的方法：
- `_build_ui()`：在 list_label 后添加 lock_btn
- `refresh_notes()`：解锁时显示 lock_btn，锁定时隐藏
- `_try_unlock_private()`：解锁成功后显示 lock_btn
- `_lock_private()`：锁定时隐藏 lock_btn
- `_on_toggle_private()`：设为私密时隐藏 lock_btn

## 验证步骤

1. 启动应用，设置一篇笔记为私密 → 输入密码 → 笔记从列表消失
2. 搜索框输入 `/private` → 密码对话框正常显示（**不再有下划线占位符**，只显示 placeholder 文字 "4或6位数字"）
3. 输入4位密码 `1234` → 解锁成功
4. 解锁后侧边栏显示「🔒 私密笔记（已解锁）」+ **右侧有 🔒 锁定按钮**
5. 点击 🔒 锁定按钮 → 立即回到「全部笔记」视图，私密笔记隐藏
6. 再次输入 `/private` → 输入密码 → 解锁
7. 解锁状态下右键私密笔记 → 取消私密 → 笔记出现在普通列表
8. 5位数字密码被拒绝（"密码格式不正确，请输入4位或6位纯数字"）
9. 非数字密码被拒绝
