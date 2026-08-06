# 画板综合功能升级计划

## 用户核心诉求（逐条对应）

| # | 问题 | 现状分析 |
|---|------|---------|
| 1 | **光标坐标错误**：文字把光标挡住了，不在同一行 | `paint()` 中光标 Y 坐标使用 `doc.findBlock(pos).position()`（块全局偏移，非行内偏移），应该用 `painter.fontMetrics().ascent()` 或行高 |
| 2 | **显示网格无反应**：右键菜单点了没效果 | `_toggle_grid()` 只改 `show_grid` 标志，**没有实际绘制网格**（缺少 `drawForeground()` 或场景背景层） |
| 3 | **又出现两个输入框**：编辑态虚线框 + 选中态手柄同时可见 | 切换编辑 ↔ 选中时 `isSelected()` 未立即清除，导致两个状态同时成立 |
| 4 | **文字缩放不等比**：缩放时文字和框比例不协调 | 当前仅按高度比例缩放字号：`new_font = old * new_h/old_h`，应该改为统一缩放因子同时应用宽高 |
| 5 | **画笔/橡皮粗细可调范围不合理**：最小值太小、最大值太大 | 目前 slider 范围 1-30px，需针对不同工具设置合理 min/max |
| 6 | **形状工具功能不足**：缺少爱心、正方形、菱形、五边形等，需要拉杆粗细控制 | 目前只有 9 种形状，无统一粗细滑块 |
| 7 | **画笔类型不够多**：需要毛笔/书写笔/喷枪/油画笔/蜡笔/记号笔/铅笔/水彩笔 | 目前只有 pen/airbrush/brush/eraser 4 类 |

---

## 实施方案

### 任务 1：光标坐标修复（High）
**文件**：`ui/drawing_tools.py` - `RotatableTextItem.paint()`

```
错误：by = doc.findBlock(pos).position()  →  值始终≈0，光标跑到文字顶部
正确：by = fm.ascent()                     →  基于字体测量的基线上方高度
```

具体改动：
```python
fm = painter.fontMetrics()
text_before = self.toPlainText()[:pos]
cx = fm.horizontalAdvance(text_before)
by = fm.ascent() + 2  # 字体 ascent 表示基线到文字顶部的距离
# 光标高度使用 fm.height() 而非固定值
cy = fm.height()
painter.drawLine(QPointF(cx, 0), QPointF(cx, cy))  # 注意：文字从(0,0)开始画
```

### 任务 2：网格功能（High）
**文件**：`ui/drawing_board.py`

**思路**：在 `scene.setBackgroundBrush` 或 `QGraphicsView.drawForeground()` 绘制网格。

方案 A（推荐）：`_CanvasView` 重写 `drawForeground()`
```python
def drawForeground(self, painter, rect):
    if not self._board.show_grid:
        return
    grid_size = 20
    painter.save()
    pen = QPen(QColor("#E5E7EB"), 1)
    painter.setPen(pen)
    # 裁剪到可视区域（性能）
    left = int(rect.left()) - (int(rect.left()) % grid_size)
    top = int(rect.top()) - (int(rect.top()) % grid_size)
    # 画竖线
    for x in range(left, int(rect.right()) + grid_size, grid_size):
        painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
    # 画横线
    for y in range(top, int(rect.bottom()) + grid_size, grid_size):
        painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
    painter.restore()
```

还需在 `_toggle_grid()` 最后调用 `self.view.viewport().update()` 触发重绘。

### 任务 3：编辑态 ↔ 选中态严格互斥（High）
**文件**：`ui/drawing_tools.py`

**关键改动**：
1. `_begin_edit()` 中加入 `item.setSelected(False)` → 进入编辑立即清除选中
2. `_commit_edit()` 中已有 `item.setSelected(True)` → 保持选中显示手柄
3. `paint()` 判断条件改为严格互斥：
```python
is_editing = (self is RotatableTextItem._current_editing_item)
is_selected = self.isSelected() and not is_editing  # 关键：编辑态不画选中态
```

这样：**编辑中看不到手柄，选中后看不到编辑虚线框（手柄自带外框）**。

### 任务 4：文字等比缩放（High）
**文件**：`ui/drawing_tools.py` - `_do_resize()`

**当前代码**：
```python
scale = new_h / self._resize_start_h  # 只按高度
new_font = self._resize_start_font * scale
```

**改为**：统一用 `scale = min(new_w/old_w, new_h/old_h)` 保证字不会变形，同时如果是角手柄用 max，边手柄用对应边。

简化方案（角手柄用对角的平均，边手柄用该边的比例）：
```python
# 计算宽高两个方向的缩放
sx = new_w / self._resize_start_w if handle 涉及水平 else 1.0
sy = new_h / self._resize_start_h if handle 涉及垂直 else 1.0
# 字体取几何平均
scale = math.sqrt(sx * sy) if (sx > 0 and sy > 0) else max(sx, sy)
new_font = max(6.0, self._resize_start_font * scale)
```

### 任务 5：画笔粗细范围与标签（Medium）
**文件**：`ui/drawing_board.py`

**Slider 统一范围**：
| 工具 | 粗细范围（px） | 默认 |
|------|--------------|------|
| 画笔/刷子/记号笔/油画笔/毛笔/水彩 | 1-60 | 3 |
| 铅笔 | 0.5-10 | 1 |
| 橡皮 | 4-80 | 10 |
| 喷枪 | 5-100 | 20 |
| 蜡笔/书写笔 | 2-40 | 4 |
| 形状（线条） | 1-30 | 2 |

**实现**：
- 扩展 slider range：`self.thickness_slider.setRange(1, 100)`
- 每种工具激活时动态设置 min/max：在 `_on_tool_clicked` 中判断当前工具类型并调用 `self.thickness_slider.setRange(tool_min, tool_max)`
- 标签显示 "3px" 改为 "粗细 3px / 范围 1-60"

### 任务 6：新增形状 + 形状粗细拉杆（Medium）
**文件**：`ui/drawing_board.py` + `ui/drawing_tools.py`

**新增形状**（8 种）：
```python
_SHAPE_TOOLS = [
    # 原有
    ("line", "直线"), ("curve", "曲线"), ("rectangle", "矩形"), ("round_rect", "圆角矩形"),
    ("ellipse", "椭圆"), ("triangle", "三角形"), ("star", "星形"), ("arrow", "箭头"),
    ("dialog", "对话框"),
    # 新增
    ("square", "正方形"), ("circle", "正圆"), ("diamond", "菱形"),
    ("pentagon", "五边形"), ("hexagon", "六边形"), ("heart", "爱心"),
    ("right_triangle", "直角三角形"), ("parallelogram", "平行四边形"),
]
```

**对应工具类**（`drawing_tools.py`）：
- `SquareTool`: _apply_geometry 强制 square（宽高取 min）
- `CircleTool`: _apply_geometry 强制 circle（半径取 min）
- `DiamondTool`: 4 顶点多边形（中心对称）
- `PentagonTool` / `HexagonTool`: 正 n 边形（极坐标生成顶点）
- `HeartTool`: 心形参数方程（Bézier 曲线或 2 圆+1 三角）
- `RightTriangleTool`: 直角三角形（3 顶点）
- `ParallelogramTool`: 平行四边形（4 顶点倾斜）

**形状粗细**：
- 形状 tab 单独加一个垂直粗细 slider（跟颜色 tab 风格一致）
- 或：统一切换时改变全局 thickness（形状共用 `pen_width`，逻辑简单）

### 任务 7：新增画笔类型（Medium）
**文件**：`ui/drawing_board.py` + `ui/drawing_tools.py`

**新增画笔**（12 类 → 覆盖图五）：
```python
_DRAW_TOOLS = [
    ("pen", "画笔"),
    ("brush_pen", "毛笔"),          # 粗细随速度变化
    ("writing_pen", "书写笔"),       # 笔尖椭圆
    ("airbrush", "喷枪"),            # 已有，优化密度
    ("oil_brush", "油画笔"),         # 厚重笔刷（半透明叠加）
    ("crayon", "蜡笔"),              # 粗糙纹理
    ("marker", "记号笔"),            # 方头+半透明
    ("pencil", "普通铅笔"),          # 细+轻压感
    ("watercolor", "水彩画笔"),       # 大湿边+低不透明度
    ("brush", "刷子"),
    ("eraser", "橡皮"),
    ("color_picker", "取色"),
    ...
]
```

**各画笔实现思路**（`drawing_tools.py` 新增类）：
| 画笔 | 实现要点 |
|------|---------|
| 毛笔 | `mouse_move` 记录速度 `v = distance/dt`，速度慢则粗、快则细 |
| 书写笔 | 笔刷用 `FlatCap` + `MiterJoin`，模拟钢笔 |
| 油画笔 | 每帧叠加一层半透明（alpha 40%），路径略微抖动 |
| 蜡笔 | 沿线每隔 1-3px 画随机偏移的小圆点（噪声纹理） |
| 记号笔 | 颜色 alpha=180，方头 `SquareCap` |
| 铅笔 | 宽度=0.5-3，颜色 alpha=150，随机抖动 0.5px |
| 水彩 | 宽笔刷（width*2），alpha=60，边缘做高斯模糊（或多圈同心圆） |

---

## 涉及文件与改动量

| 文件 | 改动内容 | 复杂度 |
|------|---------|--------|
| `ui/drawing_tools.py` | 光标Y坐标 + 严格互斥 + 等比缩放 + 8种新形状类 + 7种新画笔类 | High |
| `ui/drawing_board.py` | 网格绘制 + slider 范围动态调整 + 新增工具按钮（形状8个+画笔8个） | High |
| 可能需改 QSS | 新工具按钮图标 / 样式 | Low |

---

## 排期优先级（按用户投诉顺序）

1. **HIGH**：光标坐标（任务1）/ 网格功能（任务2）/ 双框问题（任务3）/ 等比缩放（任务4）
2. **MEDIUM**：粗细范围（任务5）/ 新增形状（任务6）
3. **LOW**：新增画笔类型（任务7，工作量大，可后续迭代）

---

## 风险与注意
- **网格性能**：必须用 `drawForeground` + 只画可视区域的优化，不能画全 800×600
- **画笔类膨胀**：每个新画笔 20-60 行代码，8 种画笔约 +400 行，确保继承 `PenTool` 复用逻辑
- **Slider 联动**：工具切换时若当前值超出新范围，需自动 clamp（`setValue(min(max(current, min), max))`）
