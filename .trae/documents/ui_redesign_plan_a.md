# 画板 UI 重构实施计划 — 方案 A（极简现代风）

## 目标

将当前"6 个折叠面板 2 列网格"布局重构为"顶部 Tab 切换 + 左侧垂直工具栏 + 画布"三栏布局，参考 Figma / Windows 11 画图的视觉语言。

## 当前问题

- 6 个 CollapsibleSection 平铺，信息密度过高，视觉拥挤
- 折叠/展开操作增加认知负担
- 工具栏占据画布上方大量垂直空间，画布可视面积小

## 重构后布局

```
┌──────────────────────────────────────────────────────────┐
│  [↶] [↷] [🗑]  |  [文件] [绘制] [形状] [颜色] [视图]    │ ← 顶部栏 48px
├──────┬───────────────────────────────────────────────────┤
│      │  [水平比例尺]                                      │
│  [笔]│ ┌───────────────────────────────────────────────┐ │
│  [喷]│ │                                             │ │
│  [刷]│ │             画布 800×600                     │ │
│  [擦]│ │           （白色，直角边）                    │ │
│  [取]│ │                                             │ │
│  [填]│ │                                             │ │
│  [字]│ │                                             │ │
│  ─── │ │                                             │ │
│  [选]│ │                                             │ │
│  [由]│ └───────────────────────────────────────────────┘ │
│      │  [垂直比例尺]                                      │
├──────┴───────────────────────────────────────────────────┤
│  坐标 (120, 85) · 缩放 100% · 工具：画笔 · 滚轮缩放: 关   │ ← 状态栏
└──────────────────────────────────────────────────────────┘
```

## 涉及文件

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| `ui/drawing_icons.py` | **新建** | 程序化生成 20×20 工具图标 QPixmap |
| `ui/drawing_board.py` | **重构** | 重写 `_build_ui`，新增 Tab 栏 + 左侧栏构建方法 |
| `ui/theme.py` | **更新** | 新增 tab_bar / left_toolbar / tool_icon_btn 样式 |
| `ui/collapsible_section.py` | **不改** | 保留组件但画板不再使用（其他模块可能引用） |

## 详细实施步骤

### 步骤 1：新建 `ui/drawing_icons.py`

创建 `DrawingIcon` 类，提供静态方法生成各工具的 20×20 图标 QPixmap：

```python
class DrawingIcon:
    """程序化生成工具图标（20×20 QPixmap，透明背景）。"""
    
    @staticmethod
    def create(name: str, color: str = "#2E3630") -> QPixmap:
        pm = QPixmap(20, 20)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # 按 name 分发到具体绘制函数
        ...
        p.end()
        return pm
```

图标设计（简洁线条风格，2px 描边）：
- `pen` → 斜线 + 笔尖三角
- `airbrush` → 圆点喷雾 pattern
- `brush` → 粗笔触弧线
- `eraser` → 矩形 + 斜线
- `color_picker` → 吸管形状
- `fill` → 油漆桶 + 液滴
- `text` → 字母 "T"
- `rect_select` → 虚线矩形
- `free_select` → 虚线曲线
- `line` → 斜直线
- `curve` → S 曲线
- `rectangle` → 矩形
- `round_rect` → 圆角矩形
- `ellipse` → 椭圆
- `triangle` → 三角形
- `star` → 五角星
- `arrow` → 箭头
- `dialog` → 对话框形状
- `undo` → 弯曲箭头向左
- `redo` → 弯曲箭头向右
- `clear` → 垃圾桶
- `save_file` → 软盘
- `insert_note` → 文档+箭头
- `zoom_in` → 放大镜+
- `zoom_out` → 放大镜-
- `zoom_100` → "1:1"
- `zoom_fit` → 全屏箭头
- `copy` → 两个重叠矩形
- `cut` → 剪刀
- `paste` → 剪贴板
- `select_all` → 虚线全选框
- `delete` → X
- `custom_color` → 调色盘
- `fill_toggle` → 实心/空心切换

### 步骤 2：重构 `ui/drawing_board.py`

#### 2a. 新增导入

```python
from .drawing_icons import DrawingIcon
from PyQt6.QtWidgets import QStackedWidget, QToolButton  # 新增
```

#### 2b. 重写 `_build_ui`

```python
def _build_ui(self):
    root = QVBoxLayout(self)
    root.setContentsMargins(0, 0, 0, 0)
    root.setSpacing(0)

    # 顶部栏：快捷操作 + Tab 切换
    self._build_top_bar(root)

    # 中间区：左侧工具栏 + 画布
    middle = QHBoxLayout()
    middle.setContentsMargins(0, 0, 0, 0)
    middle.setSpacing(0)
    
    # 左侧垂直工具栏（QStackedWidget，跟随 Tab 切换）
    self._build_left_toolbar(middle)
    
    # 画布区（含比例尺）
    self._build_canvas_area(middle)
    
    root.addLayout(middle, 1)

    # 状态栏
    self.status_label = QLabel(...)
    root.addWidget(self.status_label)
```

#### 2c. 新增 `_build_top_bar`

```python
def _build_top_bar(self, root_layout):
    bar = QFrame()
    bar.setObjectName("drawing_top_bar")
    bar.setFixedHeight(48)
    layout = QHBoxLayout(bar)
    layout.setContentsMargins(8, 0, 8, 0)
    layout.setSpacing(4)

    # 左侧：快捷操作按钮（撤销/重做/清空）
    for name in ["undo", "redo", "clear"]:
        btn = QToolButton()
        btn.setIcon(QIcon(DrawingIcon.create(name)))
        btn.setToolTip(...)
        btn.clicked.connect(lambda n=name: self._on_action_clicked(n))
        layout.addWidget(btn)
    
    # 分隔线
    sep = QFrame()
    sep.setFixedWidth(1)
    layout.addWidget(sep)
    
    # 右侧：Tab 按钮（文件/绘制/形状/颜色/视图）
    self._tab_group = QButtonGroup(self)
    self._tab_group.setExclusive(True)
    for i, tab_name in enumerate(["文件", "绘制", "形状", "颜色", "视图"]):
        btn = QPushButton(tab_name)
        btn.setCheckable(True)
        btn.setObjectName("drawing_tab")
        self._tab_group.addButton(btn, i)
        layout.addWidget(btn)
    
    self._tab_group.idClicked.connect(self._on_tab_changed)
    layout.addStretch()
    
    # 默认选中"绘制" Tab
    self._tab_group.button(1).setChecked(True)
    
    root_layout.addWidget(bar)
```

#### 2d. 新增 `_build_left_toolbar`

```python
def _build_left_toolbar(self, middle_layout):
    self.left_toolbar = QFrame()
    self.left_toolbar.setObjectName("drawing_left_toolbar")
    self.left_toolbar.setFixedWidth(56)
    
    layout = QVBoxLayout(self.left_toolbar)
    layout.setContentsMargins(4, 4, 4, 4)
    layout.setSpacing(2)
    
    # QStackedWidget：5 个页面对应 5 个 Tab
    self.tool_stack = QStackedWidget()
    
    # 页面 0：文件
    self.tool_stack.addWidget(self._build_file_panel())
    # 页面 1：绘制（默认显示）
    self.tool_stack.addWidget(self._build_draw_panel())
    # 页面 2：形状
    self.tool_stack.addWidget(self._build_shape_panel())
    # 页面 3：颜色
    self.tool_stack.addWidget(self._build_color_panel())
    # 页面 4：视图
    self.tool_stack.addWidget(self._build_view_panel())
    
    self.tool_stack.setCurrentIndex(1)  # 默认"绘制"
    layout.addWidget(self.tool_stack)
    layout.addStretch()
    
    middle_layout.addWidget(self.left_toolbar)
```

#### 2e. 新增面板构建方法

每个面板创建对应工具的 `QToolButton`（图标 + tooltip），保留原有的 `checkable` / `ButtonGroup` 互斥逻辑：

- `_build_file_panel()`: save_file, insert_note (非互斥)
- `_build_draw_panel()`: pen, airbrush, brush, eraser, color_picker, fill, text + 分隔线 + rect_select, free_select (互斥)
- `_build_shape_panel()`: line, curve, rectangle, round_rect, ellipse, triangle, star, arrow, dialog (互斥)
- `_build_color_panel()`: 主/次色叠加 + 2列色板网格 + custom_color + 垂直粗细滑块 + fill_toggle
- `_build_view_panel()`: zoom_in, zoom_out, zoom_100, zoom_fit + 分隔线 + wheel_zoom_toggle + copy, cut, paste, select_all, delete

按钮创建逻辑复用 `_build_group` 的核心：设置 `objectName`、`tool_name` property、`checkable`、加入 `_tool_btn_group`、记录到 `_tool_buttons` dict。

#### 2f. 新增 `_on_tab_changed`

```python
def _on_tab_changed(self, tab_id: int):
    self.tool_stack.setCurrentIndex(tab_id)
```

#### 2g. 更新 `apply_theme`

- 新增 `self.top_bar.setStyleSheet(qss["top_bar"])`
- 新增 `self.left_toolbar.setStyleSheet(qss["left_toolbar"])`
- 遍历 `_tool_buttons` 时使用 `tool_icon_btn` / `tool_icon_btn_checked` 样式
- 保留画布视图、状态栏、比例尺、滑块、色板的主题刷新逻辑
- **删除** `self._sections` 的遍历（不再使用 CollapsibleSection）

#### 2h. 删除旧方法

- 删除 `_build_group`（被新面板构建方法替代）
- 删除 `_build_color_section`（被 `_build_color_panel` 替代）
- 删除 `_build_select_ops_section`（被 `_build_draw_panel` / `_build_view_panel` 替代）
- 删除 `_build_view_section`（被 `_build_view_panel` 替代）

### 步骤 3：更新 `ui/theme.py`

在 `get_drawing_board_qss` 返回的 dict 中新增：

```python
"top_bar": f"""
    QFrame#drawing_top_bar {{
        background: {t['card_bg']};
        border-bottom: 1px solid {t['border']};
    }}
    QFrame#drawing_top_bar > QFrame {{
        background: {t['border']};
    }}
""",
"tab_button": f"""
    QPushButton#drawing_tab {{
        background: transparent;
        border: none;
        border-radius: 6px;
        padding: 6px 16px;
        font-size: 13px;
        color: {t['text_secondary']};
    }}
    QPushButton#drawing_tab:hover {{
        background: {t['list_hover_bg']};
        color: {t['text_primary']};
    }}
    QPushButton#drawing_tab:checked {{
        background: {t['primary']};
        color: #FFFFFF;
        font-weight: 600;
    }}
""",
"left_toolbar": f"""
    QFrame#drawing_left_toolbar {{
        background: {t['card_bg']};
        border-right: 1px solid {t['border']};
    }}
""",
"tool_icon_btn": f"""
    QToolButton {{
        background: transparent;
        border: none;
        border-radius: 8px;
        padding: 6px;
        margin: 1px;
    }}
    QToolButton:hover {{
        background: {t['list_hover_bg']};
    }}
    QToolButton:checked {{
        background: {t['primary']};
    }}
""",
```

保留现有的 `canvas_view`、`status_bar`、`slider`、`color_swatch` 等样式。

### 步骤 4：验证

- 运行 `python main.py`，切换到画板 Tab
- 验证 5 个 Tab 切换正常，左侧工具栏跟随切换
- 验证工具选中态（主色背景 + 白色图标）
- 验证快捷操作按钮（撤销/重做/清空）功能正常
- 验证颜色面板：色板点击、自定义色、粗细滑块、空心/实心切换
- 验证视图面板：缩放、滚轮缩放开关、复制/剪切/粘贴/删除
- 验证状态栏信息更新
- 验证主题切换（Matcha / Sand / Paper / Dark）

## 风险与注意事项

1. **按钮引用一致性**：重构后 `_tool_buttons` dict 仍需保持 key 为工具名，确保 `_set_tool` / `_on_action_clicked` 等方法正常工作
2. **ButtonGroup 互斥**：绘制工具和形状工具共用同一个 `_tool_btn_group`，切换 Tab 时不会影响互斥逻辑
3. **色板布局**：56px 宽度下色板用 2 列网格（22×22 色块），粗细用垂直滑块
4. **图标渲染**：QPainter 程序化生成的图标需在不同 DPI 下清晰，使用 20×20 逻辑像素 + Antialiasing
5. **主题兼容**：所有新样式需适配 4 个主题（Matcha / Sand / Paper / Dark）
6. **FlowLayout 保留**：FlowLayout 类保留在 drawing_board.py 中（颜色面板内部可能用到）
