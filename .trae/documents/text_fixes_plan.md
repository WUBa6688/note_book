# 文字功能问题修复计划

## 问题分析（4 个问题）

| 问题 | 图片 | 根因 | 修复方案 |
|------|------|------|---------|
| ① 旋转有痕迹 | 图一 | `setRotation` 调用 `self.update()` 仅重绘当前 item，但场景缓存未清除旧位置残留 | 旋转时调用 `self.scene.invalidate()` 强制全场景刷新 |
| ② 度数显示 | 图二 | `paint()` 中硬编码了 `f"{self._rotation:.0f}°"` 绘制逻辑 | 删除旋转角度提示的绘制代码 |
| ③ 双输入框叠加 | 图三 | `_commit_edit()` 中先设 `NoTextInteraction` 退出编辑，但紧接着 `setSelected(True)` 进入选中态，导致 paint 中 `isSelected=True` + 残留编辑态边框同时绘制 | `_commit_edit` 中确保状态互斥：先完全退出编辑态，再进入选中态 |
| ④ 无闪烁光标 | 图四 | 文字处于 `TextEditorInteraction` 但无 `QGraphicsTextItem` 的光标自动绘制 | 利用 `QGraphicsTextItem` 自带的光标机制，确保编辑时 `setFocus()` 正确且 `textCursor().setPosition()` 有效 |

## 实施步骤

### 步骤 1：消除旋转痕迹（图一）
**文件**: `ui/drawing_tools.py` - `TextTool.mouse_move()` 中的 rotate 分支

**修改**：在 `set_rotation_angle()` 之后添加 `self.scene.invalidate()` 强制刷新场景，消除残影。

```python
# 当前代码
elif self._mode == "rotate" and self._rotate_item is not None:
    ...
    self._rotate_item.set_rotation_angle(new_rotation)

# 修改后
elif self._mode == "rotate" and self._rotate_item is not None:
    ...
    self._rotate_item.set_rotation_angle(new_rotation)
    self.scene.invalidate()  # 清除旋转痕迹
```

同样在 `_SelectToolBase.mouse_move()` 中做相同修改。

### 步骤 2：删除旋转度数显示（图二）
**文件**: `ui/drawing_tools.py` - `RotatableTextItem.paint()`

**修改**：删除选中态 paint 中的旋转角度提示代码块（约 L700-L709）

```python
# 删除以下代码块
if abs(self._rotation) > 0.5:
    painter.setPen(QPen(QColor("#1D4ED8")))
    font = painter.font()
    font.setPointSize(8)
    painter.setFont(font)
    painter.drawText(
        QRectF(0, rp_local.y() - 14, self._width + 2 * s, 12),
        Qt.AlignmentFlag.AlignCenter,
        f"{self._rotation:.0f}°")
```

### 步骤 3：修复双输入框问题（图三）
**文件**: `ui/drawing_tools.py` - `TextTool._commit_edit()`

**根因**：从编辑态退出时，`setTextInteractionFlags(NoTextInteraction)` 会清除 `TextEditorInteraction`，但 `paint()` 中的 `show_frame` 逻辑判断 `isSelected() or is_editing`——如果退出编辑后 `setSelected(True)` 生效，可能先绘制编辑态边框再绘制选中态边框，造成两个框。

**修改**：确保状态转换严格顺序——先清除编辑标志，再设置选中态。同时在 paint 中添加互斥条件。

```python
# _commit_edit 修改
# 先完全退出编辑
item.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, False)
# 再进入选中态
item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
item.setSelected(True)
```

同时在 paint 中确保不会同时绘制两种边框：
```python
# paint 中调整优先级
if self.isSelected():
    # 只绘制选中态边框（含手柄）
elif is_editing:
    # 只绘制编辑态边框
```

### 步骤 4：编辑态显示闪烁光标（图四）
**文件**: `ui/drawing_tools.py` - `TextTool.mouse_press()` / `_begin_edit()`

**原理**：`QGraphicsTextItem` 设置 `TextEditorInteraction` 后，只要获得焦点就会自动显示闪烁光标。问题可能是：
1. 创建空文字时光标位置未设置
2. `setFocus()` 时机不对
3. 文字内容为空时 `QTextDocument` 高度为 0 导致光标不可见

**修改**：
- 创建空文字后，确保光标在文档起始位置
- 在 `_begin_edit` 中调用 `item.setTextCursor(item.textCursor())` 强制刷新光标
- 设置 `item.setTextWidth()` 确保有可编辑区域

## 涉及文件
| 文件 | 修改内容 |
|------|---------|
| `ui/drawing_tools.py` | 4 处修改：旋转刷新、删除度数、状态互斥、光标显示 |

## 风险与应对
| 风险 | 应对 |
|------|------|
| `scene.invalidate()` 可能导致性能下降 | 仅在旋转/拖拽过程中调用，释放后停止 |
| 删除度数后用户失去角度感知 | 可考虑在旋转过程中短暂显示（mousemove 时显示，mouseup 时隐藏），当前用户明确要求消除，直接删除 |
