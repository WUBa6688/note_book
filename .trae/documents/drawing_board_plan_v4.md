# Zhuibook 画板功能需求文档 V4（UI 重构 + 交互增强 + 趣味化版）

> 基于 V3 的 6 条用户诉求重新设计。核心：**Windows 画图风格 Ribbon 折叠面板**、**比例尺**、**滚轮缩放**、**按钮高亮**、**富文本（可拖动）**、**趣味工具光标**。

---

## 一、需求汇总

### 用户 6 条诉求
1. UI 重构为折叠分组面板（类 Windows 画图 Ribbon 风格）
2. 添加比例尺（画布上方 + 左侧）
3. 鼠标滚轮控制画板缩放
4. 点击按钮变色高亮
5. 文字工具改为富文本（字体/加粗等），可拖动
6. 工具光标趣味化（画笔变画笔形状等）

### 系统补充
7. 系统剪贴板 Ctrl+V 粘贴图片
8. 选中项 Delete 删除
9. 工具按钮 tooltip 显示快捷键
10. 缩放中心以鼠标位置为锚点
11. 文字双击二次编辑
12. 画板空白处右键菜单

---

## 二、实施分批

- **P1 快速见效**：滚轮缩放、按钮高亮、趣味光标、快捷键 tooltip
- **P2 核心增强**：比例尺、富文本、系统剪贴板、Delete 删除、右键菜单
- **P3 UI 重构**：折叠分组面板

---

## 三、新增/修改文件

| 文件 | 类型 | 职责 |
|------|------|------|
| `ui/drawing_cursors.py` | 新增 | 自定义光标生成 `create_tool_cursor(tool_name, size=32) -> Optional[QCursor]` |
| `ui/collapsible_section.py` | 新增 | 折叠分组面板 `CollapsibleSection(QWidget)` |
| `ui/drawing_ruler.py` | 新增 | 水平/垂直比例尺 `HorizontalRuler` / `VerticalRuler` |
| `ui/drawing_text_editor.py` | 新增 | 富文本格式工具栏 `TextFormatToolbar(QFrame)` |
| `ui/drawing_board.py` | 修改 | 工具栏重构、缩放、粘贴、Delete、右键菜单、tooltip |
| `ui/drawing_tools.py` | 修改 | 光标切换 activate/deactivate、TextTool 富文本改造 |
| `ui/drawing_commands.py` | 修改 | 新增 `ModifyTextCommand` |
| `ui/theme.py` | 修改 | 新增折叠面板/比例尺/工具栏 QSS |

---

## 四、接口契约（前后端并行开发）

### Frontend → Backend 可用接口
- `create_tool_cursor(tool_name, size=32) -> Optional[QCursor]`：返回 QCursor 或 None（None 表示用系统光标）
  - 返回自定义光标：pen, airbrush, brush, eraser, fill
  - 返回 None（用系统光标）：color_picker, text, rect_select, free_select, 所有形状工具
- `TextFormatToolbar` 类：`setTargetItem(QGraphicsTextItem)` 方法
- `DrawingBoardView.text_toolbar` 属性

### Backend → Frontend 可用接口
- `create_tool(name, board)` 返回的工具实例已调用 `activate()`
- `ModifyTextCommand(item, old_text, new_text, old_font, new_font, old_color, new_color)`
- 工具 deactivate() 恢复默认光标

### 防御性导入约定
双方均使用 try/except 导入对方模块，确保可独立编译运行。

---

## 五、验证清单

### P1 验证
- [ ] Ctrl+滚轮缩放，以鼠标位置为中心
- [ ] 选中画笔/橡皮按钮，背景变主题色高亮
- [ ] 画笔工具 → 光标变画笔形状
- [ ] 所有按钮 tooltip 显示快捷键

### P2 验证
- [ ] 画布上方水平比例尺，左侧垂直比例尺
- [ ] 缩放时刻度同步
- [ ] 鼠标移动时刻度显示蓝色指示线
- [ ] 文字工具 → 可直接在画布输入文字
- [ ] 文字可拖动、双击可二次编辑
- [ ] Ctrl+V 粘贴系统剪贴板图片
- [ ] Delete 删除选中项
- [ ] 右键菜单

### P3 验证
- [ ] 工具栏分为 6 个可折叠分组
- [ ] 点击标题可展开/收起
- [ ] 主题切换时样式同步
