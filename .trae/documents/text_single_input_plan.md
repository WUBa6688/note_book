# 文字输入框重构计划

## 用户核心诉求（原话整理）
1. **一个画板有且只能出现一个输入框**
2. **光标要闪烁**（不是静态竖线）
3. **光标坐标要正确**
4. **点击文字时弹出一个可放大缩小的输入框**

## 现状分析

| 问题 | 根因 |
|------|------|
| 多个输入框同时出现 | 每个 `RotatableTextItem` 选中时都画自己的框，没做全局互斥 |
| 光标不闪烁 | 只是画了一根静态竖线，没有定时器驱动闪烁 |
| 光标位置错误 | `fm.horizontalAdvance()` 没考虑字体 DPI、变换矩阵，位置偏移 |

## 实施方案

### 核心原则：**全局唯一编辑态 + 定时器闪烁**

### 步骤 1：全局唯一编辑态
**思路**：在 `RotatableTextItem` 类中添加类变量 `_current_editing_item` 追踪当前正在编辑的文字项。

- 进入编辑时：如果已有其他 item 在编辑，先清除其编辑状态
- 退出编辑时：清除 `_current_editing_item`
- `paint()` 中只有 `self is _current_editing_item` 才画编辑框

```python
class RotatableTextItem(QGraphicsTextItem):
    _current_editing_item: 'RotatableTextItem | None' = None  # 类变量

    def paint(self, painter, option, widget):
        # 只有当前正在编辑的 item 才画虚线框
        is_editing = (self is RotatableTextItem._current_editing_item)
        is_selected = self.isSelected() and not is_editing
        ...
```

### 步骤 2：定时器实现光标闪烁
**思路**：用 `QTimer` 每 500ms 切换 `_cursor_visible` 标志，触发重绘。

```python
def __init__(self, ...):
    ...
    self._cursor_visible = True
    self._blink_timer = QTimer(self)
    self._blink_timer.timeout.connect(self._blink_cursor)

def _blink_cursor(self):
    self._cursor_visible = not self._cursor_visible
    self.update()  # 触发重绘

def start_cursor_blink(self):
    self._cursor_visible = True
    self._blink_timer.start(500)

def stop_cursor_blink(self):
    self._blink_timer.stop()
    self._cursor_visible = True
    self.update()
```

### 步骤 3：正确的光标位置计算
**思路**：使用 `QTextDocument` 的 `documentLayout()` 的 `blockBoundingRect()` + `QTextLine.cursorToX()` 计算精确位置。

```python
# 获取光标精确坐标
cursor = self.textCursor()
doc = self.document()
block = doc.findBlock(cursor.position())
line = block.begin()
# 遍历到光标所在的 line
while line.isValid():
    x = line.cursorToX(cursor.position())
    if x >= 0:
        break
    line = line.next()
```

### 步骤 4：状态互斥流程

```
点击文字 → 检查 _current_editing_item
  ├── 有其他 item 在编辑 → stop_cursor_blink() + 清除其编辑状态
  └── 无 → 直接进入编辑
→ 设置当前 item 为 _current_editing_item
→ start_cursor_blink()
→ 画一个虚线框 + 闪烁光标

提交文字 → stop_cursor_blink()
→ 清除 _current_editing_item
→ 转为选中态（画手柄）
```

## 涉及文件
| 文件 | 修改内容 |
|------|---------|
| `ui/drawing_tools.py` | RotatableTextItem: 类变量追踪、定时器闪烁、正确光标、paint 重写 |

## 风险
| 风险 | 应对 |
|------|------|
| 定时器在旋转/缩放下闪烁异常 | 定时器只在编辑态启动，拖拽操作暂停闪烁 |
| 多 item 切换时状态残留 | 每次进入新编辑前强制清除旧状态 |
