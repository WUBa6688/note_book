"""
Zhuibook 画板主视图（参照 Windows 画图软件布局）

布局自上而下：
  顶部工具栏（FlowLayout 自动换行）
    ├ 工具组：画笔/喷枪/刷子/橡皮/取色/填充/文字/矩形选择/自由选择
    ├ 形状组：直线/曲线/矩形/圆角矩形/椭圆/三角形/星形/箭头/对话框
    ├ 操作组：撤销/重做/清空/复制/粘贴/剪切/全选
    ├ 视图组：放大/缩小/100%/适应窗口
    └ 文件组：保存为文件/插入到笔记
  颜色组：主/次色叠加 + 20 色预设调色板 + 自定义颜色
  粗细滑块（1~30px）+ 填充模式切换（空心/实心）
  画布区域：QGraphicsView + QGraphicsScene（800×600，白色背景）
  状态栏：坐标/缩放/画布尺寸/当前工具

后端依赖（drawing_tools / drawing_commands / save_drawing_to_note_assets）
由后端工程师同步开发，此处采用防御性导入 + 本地回退，保证 UI 可独立运行与验证。
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any

from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRect, QRectF, QPointF, QPoint
from PyQt6.QtGui import (
    QColor, QPen, QBrush, QPixmap, QPainter, QFont, QMouseEvent, QImage,
    QCursor, QKeySequence, QUndoCommand, QUndoStack
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QPushButton, QLabel, QSlider,
    QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsItem,
    QGraphicsPixmapItem, QGraphicsTextItem, QSizePolicy, QSpacerItem,
    QColorDialog, QFileDialog, QMessageBox, QButtonGroup, QMenu, QApplication,
    QLayout, QLayoutItem, QGridLayout
)

from core.database import DatabaseManager, get_assets_dir, get_assets_root
from .theme import THEMES, DEFAULT_THEME, get_drawing_board_qss
from .collapsible_section import CollapsibleSection
from .drawing_ruler import HorizontalRuler, VerticalRuler
from .drawing_text_editor import TextFormatToolbar
from .drawing_cursors import create_tool_cursor


# ===========================================================================
# FlowLayout —— 从 ui/editor.py 复制（自动换行布局，避免按钮被省略号截断）
# ===========================================================================
class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=4, spacing=-1, h_spacing=4, v_spacing=4):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self._spacing_x = spacing if spacing >= 0 else h_spacing
        self._spacing_y = spacing if spacing >= 0 else v_spacing
        self._item_list: List[QLayoutItem] = []

    def __del__(self):
        item = self.takeAt(0)
        while item is not None:
            del item
            item = self.takeAt(0)

    def addItem(self, item: QLayoutItem):
        self._item_list.append(item)

    def horizontal_spacing(self):
        return self._spacing_x

    def vertical_spacing(self):
        return self._spacing_y

    def count(self):
        return len(self._item_list)

    def itemAt(self, index: int):
        if 0 <= index < len(self._item_list):
            return self._item_list[index]
        return None

    def takeAt(self, index: int):
        if 0 <= index < len(self._item_list):
            return self._item_list.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width: int):
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect):
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    def _do_layout(self, rect: QRect, test_only: bool):
        m = self.contentsMargins()
        effective = rect.adjusted(+m.left(), +m.top(), -m.right(), -m.bottom())
        x = effective.x()
        y = effective.y()
        space_x = max(2, self._spacing_x)
        space_y = max(2, self._spacing_y)
        current_row: List[Tuple[QLayoutItem, int, int]] = []
        row_line_h = 0

        def flush_row(row_items, row_y, line_h):
            if not row_items:
                return line_h
            for (it, ix, ih) in row_items:
                top = row_y + max(0, (line_h - ih) // 2)
                sh = it.sizeHint()
                g = QRect(int(ix), int(top), max(0, sh.width()), max(0, sh.height()))
                if not test_only:
                    it.setGeometry(g)
            return line_h

        for item in self._item_list:
            if item is None:
                continue
            sh = item.sizeHint()
            iw = sh.width()
            ih = sh.height()
            next_x = x + iw + space_x
            need_newline = (row_line_h > 0) and (next_x - space_x > effective.right())
            if need_newline:
                flush_row(current_row, y, row_line_h)
                current_row = []
                y += row_line_h + space_y
                x = effective.x()
                next_x = x + iw + space_x
                row_line_h = 0
            current_row.append((item, x, ih))
            row_line_h = max(row_line_h, ih)
            x = next_x
        total_bottom = y + flush_row(current_row, y, row_line_h) - rect.y() + m.bottom()
        return max(0, total_bottom)


# ===========================================================================
# 后端依赖（防御性导入 + 本地回退）
# drawing_tools / drawing_commands / save_drawing_to_note_assets 由后端同步开发
# ===========================================================================
try:
    from .drawing_tools import TOOL_REGISTRY as _BACKEND_TOOL_REGISTRY, create_tool as _backend_create_tool, BaseTool as _BackendBaseTool  # type: ignore
    _HAS_DRAWING_TOOLS = True
except Exception:
    _HAS_DRAWING_TOOLS = False

    class _BackendBaseTool:
        """本地回退基类：后端未就绪时使用的占位工具基类。"""
        def __init__(self, board=None):
            self.board = board
        def mouse_press(self, event, scene_pos):
            pass
        def mouse_move(self, event, scene_pos):
            pass
        def mouse_release(self, event, scene_pos):
            pass
        def deactivate(self):
            pass

    _BACKEND_TOOL_REGISTRY = {}

    def _backend_create_tool(name, board):
        return None

try:
    from .drawing_commands import AddItemCommand, RemoveItemsCommand, ClearSceneCommand  # type: ignore
    _HAS_DRAWING_COMMANDS = True
except Exception:
    _HAS_DRAWING_COMMANDS = False

    class AddItemCommand(QUndoCommand):
        """本地回退命令：添加图形项到场景。"""
        def __init__(self, scene, item):
            super().__init__()
            self.scene = scene
            self.item = item
        def undo(self):
            if self.item is not None and self.item.scene() is self.scene:
                self.scene.removeItem(self.item)
        def redo(self):
            if self.item is not None and self.item.scene() is None:
                self.scene.addItem(self.item)

    class RemoveItemsCommand(QUndoCommand):
        """本地回退命令：移除图形项。"""
        def __init__(self, scene, items):
            super().__init__()
            self.scene = scene
            self.items = items
        def undo(self):
            for it in self.items:
                if it.scene() is None:
                    self.scene.addItem(it)
        def redo(self):
            for it in self.items:
                if it.scene() is self.scene:
                    self.scene.removeItem(it)

    class ClearSceneCommand(QUndoCommand):
        """本地回退命令：清空场景（保留背景项）。"""
        def __init__(self, scene, bg_item=None):
            super().__init__()
            self.scene = scene
            self._bg = bg_item
            self._saved = []
        def undo(self):
            for it in self._saved:
                if it.scene() is None:
                    self.scene.addItem(it)
            self._saved = []
        def redo(self):
            self._saved = [it for it in self.scene.items() if it is not self._bg]
            for it in self._saved:
                if it.scene() is self.scene:
                    self.scene.removeItem(it)


# ===========================================================================
# 工具目录（UI 层定义：按钮标签 / 分组；实际行为由后端 tool 实现）
# ===========================================================================
# 可绘制工具（选中互斥）
_DRAW_TOOLS: List[Tuple[str, str]] = [
    ("pen", "画笔"), ("airbrush", "喷枪"), ("brush", "刷子"), ("eraser", "橡皮"),
    ("color_picker", "取色"), ("fill", "填充"), ("text", "文字"),
    ("rect_select", "矩形选择"), ("free_select", "自由选择"),
]
# 形状工具（选中互斥，与绘图工具共用一组互斥）
_SHAPE_TOOLS: List[Tuple[str, str]] = [
    ("line", "直线"), ("curve", "曲线"), ("rectangle", "矩形"), ("round_rect", "圆角矩形"),
    ("ellipse", "椭圆"), ("triangle", "三角形"), ("star", "星形"), ("arrow", "箭头"),
    ("dialog", "对话框"),
]
# 操作（动作按钮，非互斥）
_OPERATION_TOOLS: List[Tuple[str, str]] = [
    ("undo", "撤销"), ("redo", "重做"), ("clear", "清空"),
    ("copy", "复制"), ("paste", "粘贴"), ("cut", "剪切"), ("select_all", "全选"),
]
# 视图（动作按钮）
_VIEW_TOOLS: List[Tuple[str, str]] = [
    ("zoom_in", "放大"), ("zoom_out", "缩小"), ("zoom_100", "100%"), ("zoom_fit", "适应窗口"),
]
# 文件（动作按钮）
_FILE_TOOLS: List[Tuple[str, str]] = [
    ("save_file", "保存为文件"), ("insert_note", "插入到笔记"),
]

# ---- 按钮 tooltip（中文名 (快捷键) - 功能简述）----
_DRAW_TOOLTIPS: Dict[str, str] = {
    "pen":          "画笔 (P) - 自由手绘线条",
    "airbrush":     "喷枪 (A) - 喷雾效果绘制",
    "brush":        "刷子 (B) - 较粗的笔触",
    "eraser":       "橡皮 (E) - 擦除内容（白色覆盖）",
    "color_picker": "取色 (D) - 从画布拾取颜色",
    "fill":         "填充 (F) - 洪水填充封闭区域",
    "text":         "文字 (T) - 插入文本",
}
_SHAPE_TOOLTIPS: Dict[str, str] = {
    "line":        "直线 (L) - 绘制直线, Shift 锁 45°",
    "curve":       "曲线 (C) - 绘制 S 型曲线",
    "rectangle":   "矩形 (R) - 绘制矩形",
    "round_rect":  "圆角矩形 (X) - 绘制圆角矩形",
    "ellipse":     "椭圆 (O) - 绘制椭圆",
    "triangle":    "三角形 (G) - 绘制三角形",
    "star":        "星形 (S) - 绘制五角星",
    "arrow":       "箭头 (W) - 绘制箭头",
    "dialog":      "对话框 (D) - 绘制对话框",
}
_SELECT_TOOLTIPS: Dict[str, str] = {
    "rect_select": "矩形选择 - 框选图形",
    "free_select": "自由选择 - 自由曲线选区",
    "select_all":  "全选 (Ctrl+A) - 选中所有图形",
    "copy":        "复制 (Ctrl+C) - 复制选中项",
    "cut":         "剪切 (Ctrl+X) - 剪切选中项",
    "paste":       "粘贴 (Ctrl+V) - 粘贴剪贴板",
    "delete":      "删除 (Delete) - 删除选中项",
    "undo":        "撤销 (Ctrl+Z) - 撤销上一步",
    "redo":        "重做 (Ctrl+Y) - 重做",
}
_VIEW_TOOLTIPS: Dict[str, str] = {
    "zoom_in":  "放大 - 放大画布",
    "zoom_out": "缩小 - 缩小画布",
    "zoom_100": "100% - 重置缩放",
    "zoom_fit": "适应窗口 - 适配窗口大小",
}
_FILE_TOOLTIPS: Dict[str, str] = {
    "save_file":  "保存为文件 - 导出为图片文件",
    "insert_note": "插入到笔记 - 插入当前笔记",
}

# 20 色预设调色板（黑/灰/深红/红/橙/黄/浅绿/绿/青/蓝/深蓝/紫/粉/棕/白/浅灰/浅红/浅黄/浅绿/浅蓝）
_PALETTE: List[Tuple[str, str]] = [
    ("black", "#000000"), ("gray", "#808080"), ("darkred", "#8B0000"), ("red", "#FF0000"),
    ("orange", "#FF8C00"), ("yellow", "#FFD700"), ("lightgreen", "#90EE90"), ("green", "#008000"),
    ("cyan", "#00FFFF"), ("blue", "#0000FF"), ("darkblue", "#00008B"), ("purple", "#800080"),
    ("pink", "#FFC0CB"), ("brown", "#8B4513"), ("white", "#FFFFFF"), ("lightgray", "#D3D3D3"),
    ("lightred", "#FFA0A0"), ("lightyellow", "#FFFFE0"), ("lightgreen2", "#C0FFC0"),
    ("lightblue", "#ADD8E6"),
]

CANVAS_WIDTH = 800
CANVAS_HEIGHT = 600


# ===========================================================================
# 自定义画布视图：将鼠标事件转发给当前工具
# ===========================================================================
class _CanvasView(QGraphicsView):
    """画布视图，转发鼠标事件到画板的当前工具。"""

    def __init__(self, board: "DrawingBoardView"):
        super().__init__()
        self._board = board
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

    def mousePressEvent(self, event: QMouseEvent):
        tool = self._board.current_tool
        if tool is not None:
            scene_pos = self.mapToScene(event.position().toPoint())
            tool.mouse_press(event, scene_pos)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        # 状态栏坐标更新（无论是否有工具）
        vp = event.position().toPoint()
        scene_pos = self.mapToScene(vp)
        self._board._update_status_coord(scene_pos)
        # 比例尺鼠标指示线联动
        self._board._update_ruler_mouse(vp.x(), vp.y())
        tool = self._board.current_tool
        if tool is not None:
            tool.mouse_move(event, scene_pos)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        tool = self._board.current_tool
        if tool is not None:
            scene_pos = self.mapToScene(event.position().toPoint())
            tool.mouse_release(event, scene_pos)
        else:
            super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        """Ctrl+滚轮缩放（25% 步进，范围 25-800%）；开启滚轮缩放时直接缩放；否则平移。"""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier or self._board.wheel_zoom_enabled:
            delta = event.angleDelta().y()
            step = 25 if delta > 0 else -25
            self._board.set_zoom(self._board.zoom_level + step)
            event.accept()
        else:
            super().wheelEvent(event)

    def keyPressEvent(self, event):
        """Delete 删除选中项；Ctrl+V 从系统剪贴板粘贴图片。"""
        # 文字项正在编辑时，Delete / Ctrl+V 等按键交给文本编辑器处理
        scene = self.scene()
        if scene is not None:
            focus_item = scene.focusItem()
            if focus_item is not None and isinstance(focus_item, QGraphicsTextItem):
                super().keyPressEvent(event)
                return
        if event.key() == Qt.Key.Key_Delete:
            self._board._delete_selected()
            event.accept()
            return
        if event.matches(QKeySequence.StandardKey.Paste):
            self._board._paste_from_system_clipboard()
            event.accept()
            return
        super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        """显示画布右键菜单。"""
        self._board._show_context_menu(event.globalPosition().toPoint())
        event.accept()


# ===========================================================================
# 画板主视图
# ===========================================================================
class DrawingBoardView(QWidget):
    # 请求将画板内容插入当前笔记
    insert_to_note_requested = pyqtSignal()
    # 主题变更通知（可选，内部切换主题时发出）
    theme_changed_internally = pyqtSignal(str)

    def __init__(self, db: DatabaseManager, theme_name: str = DEFAULT_THEME, parent=None):
        super().__init__(parent)
        self.db = db
        self.current_theme = theme_name

        # ---- 状态 ----
        self.current_tool_name: str = "pen"
        self.current_tool = None  # BaseTool 实例（后端未就绪时为 None）
        self.primary_color: str = "#000000"
        self.secondary_color: str = "#FFFFFF"
        self.active_color: str = "primary"  # "primary" / "secondary"
        self.pen_width: int = 2
        self.filled: bool = False
        self.zoom_level: int = 100
        # ---- V4 新增状态 ----
        self.wheel_zoom_enabled: bool = False  # 滚轮缩放开关
        self.show_grid: bool = False  # 显示网格（右键菜单切换）
        self._sections: List["CollapsibleSection"] = []
        self.text_toolbar: Optional[TextFormatToolbar] = None
        self.h_ruler: Optional[HorizontalRuler] = None
        self.v_ruler: Optional[VerticalRuler] = None

        # ---- 撤销栈（限制 50 步）----
        self.undo_stack = QUndoStack(self)
        self.undo_stack.setUndoLimit(50)

        # ---- 工具按钮分组（互斥）----
        self._tool_btn_group = QButtonGroup(self)
        self._tool_btn_group.setExclusive(True)
        self._tool_btn_group.idClicked.connect(self._on_tool_clicked)
        # 调色板色块分组（互斥，表示当前选中色）
        self._palette_group = QButtonGroup(self)
        self._palette_group.setExclusive(True)

        self._tool_buttons: Dict[str, QPushButton] = {}
        self._palette_buttons: Dict[str, QPushButton] = {}

        self._build_ui()
        self.apply_theme(theme_name)
        # 默认选中画笔工具
        self._set_tool("pen")

    # -------------------------------------------------------------------
    # UI 构建
    # -------------------------------------------------------------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        # 顶部工具栏（6 个 CollapsibleSection，QGridLayout 2 列布局）
        self.toolbar = QFrame()
        self.toolbar.setObjectName("drawing_toolbar")
        toolbar_outer = QVBoxLayout(self.toolbar)
        toolbar_outer.setContentsMargins(6, 6, 6, 6)
        toolbar_outer.setSpacing(6)

        # 使用 QGridLayout 2 列布局，确保布局稳定不跳行
        grid = QGridLayout()
        grid.setSpacing(6)
        grid.setContentsMargins(0, 0, 0, 0)

        self._sections: List["CollapsibleSection"] = []

        # 1. 文件 (row 0, col 0)
        sec = CollapsibleSection("文件")
        self._build_group(sec, _FILE_TOOLS, checkable=False, tooltips=_FILE_TOOLTIPS)
        self._sections.append(sec)
        grid.addWidget(sec, 0, 0)

        # 2. 绘制工具 (row 0, col 1)
        sec = CollapsibleSection("绘制工具")
        _draw_tools = [
            ("pen", "画笔"), ("airbrush", "喷枪"), ("brush", "刷子"),
            ("eraser", "橡皮"), ("color_picker", "取色"), ("fill", "填充"), ("text", "文字"),
        ]
        self._build_group(sec, _draw_tools, checkable=True, tooltips=_DRAW_TOOLTIPS)
        self._sections.append(sec)
        grid.addWidget(sec, 0, 1)

        # 3. 形状工具 (row 1, col 0)
        sec = CollapsibleSection("形状工具")
        self._build_group(sec, _SHAPE_TOOLS, checkable=True, tooltips=_SHAPE_TOOLTIPS)
        self._sections.append(sec)
        grid.addWidget(sec, 1, 0)

        # 4. 颜色样式 (row 1, col 1)
        sec = CollapsibleSection("颜色样式")
        self._build_color_section(sec)
        self._sections.append(sec)
        grid.addWidget(sec, 1, 1)

        # 5. 选择操作 (row 2, col 0)
        sec = CollapsibleSection("选择操作")
        self._build_select_ops_section(sec)
        self._sections.append(sec)
        grid.addWidget(sec, 2, 0)

        # 6. 视图控制 (row 2, col 1)
        sec = CollapsibleSection("视图控制")
        self._build_view_section(sec)
        self._sections.append(sec)
        grid.addWidget(sec, 2, 1)

        # 让两列等宽
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        toolbar_outer.addLayout(grid)

        # 保存 grid 布局引用用于主题更新
        self.toolbar_layout = grid

        root.addWidget(self.toolbar)

        # 富文本格式工具栏（画布上方，初始隐藏）
        self.text_toolbar = TextFormatToolbar(self)
        root.addWidget(self.text_toolbar)

        # 画布区（含比例尺）
        self._build_canvas_area(root)

        # 状态栏
        self.status_label = QLabel("就绪 · 画布 800×600 · 缩放 100% · 工具：画笔 · 滚轮缩放: 关")
        self.status_label.setObjectName("drawing_status")
        root.addWidget(self.status_label)

    def _build_group(self, section: "CollapsibleSection", tools: List[Tuple[str, str]],
                     checkable: bool, tooltips: Optional[Dict[str, str]] = None):
        """构建一组按钮放入指定 CollapsibleSection（内部用 FlowLayout 自动换行）。

        保留原有的按钮创建 / checkable / ButtonGroup 互斥逻辑，
        只是把按钮放入 section 而非直接加入 toolbar_layout。
        """
        container = QWidget()
        flow = FlowLayout(container, margin=4, h_spacing=8, v_spacing=8)
        for name, text in tools:
            btn = QPushButton(text)
            btn.setObjectName(f"tool_{name}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("tool_name", name)
            if tooltips and name in tooltips:
                btn.setToolTip(tooltips[name])
            if checkable:
                btn.setCheckable(True)
                self._tool_btn_group.addButton(btn)
                self._tool_btn_group.setId(btn, len(self._tool_buttons))
            else:
                # 操作/视图/文件按钮通过 clicked 信号处理
                btn.clicked.connect(lambda _checked=False, n=name: self._on_action_clicked(n))
            self._tool_buttons[name] = btn
            flow.addWidget(btn)
        section.addWidget(container)

    def _build_color_section(self, section: "CollapsibleSection"):
        """颜色样式分组：主/次色 + 调色板 + 自定义色 + 粗细 + 空心/实心。"""
        row = QFrame()
        row.setObjectName("drawing_group")
        fl = FlowLayout(row, margin=4, h_spacing=6, v_spacing=4)

        # 主色/次色叠加显示
        self.primary_swatch = QPushButton()
        self.primary_swatch.setObjectName("primary_swatch")
        self.primary_swatch.setFixedSize(34, 34)
        self.primary_switch = QPushButton()
        self.primary_swatch.setCursor(Qt.CursorShape.PointingHandCursor)
        self.primary_switch.setCursor(Qt.CursorShape.PointingHandCursor)
        self.primary_swatch.clicked.connect(lambda: self._set_active_color("primary"))
        self.primary_switch.clicked.connect(lambda: self._set_active_color("secondary"))
        self.primary_swatch.setToolTip("主色（左键绘制颜色），点击切换为激活色")
        self.primary_switch.setToolTip("次色（右键绘制颜色），点击切换为激活色")
        self.primary_switch.setObjectName("primary_switch")
        self.primary_switch.setFixedSize(34, 34)
        # 叠加：把两个色块用样式表示，主色在前/次色在后；用透明叠放
        wrap = QFrame()
        wrap.setFixedSize(44, 40)
        wrap_layout = QHBoxLayout(wrap)
        wrap_layout.setContentsMargins(2, 2, 2, 2)
        wrap_layout.setSpacing(2)
        wrap_layout.addWidget(self.primary_swatch)
        wrap_layout.addWidget(self.primary_switch)
        wrap_layout.setSpacing(-10)
        fl.addWidget(wrap)

        # 预设调色板
        pal_label = QLabel("色板")
        pal_label.setObjectName("drawing_group_label")
        fl.addWidget(pal_label)
        for name, hex_color in _PALETTE:
            sw = QPushButton()
            sw.setObjectName(f"swatch_{name}")
            sw.setCursor(Qt.CursorShape.PointingHandCursor)
            sw.setFixedSize(22, 22)
            sw.setCheckable(True)
            sw.setToolTip(hex_color)
            sw._color_hex = hex_color  # type: ignore
            sw.clicked.connect(lambda _c=False, b=sw: self._on_palette_clicked(b))
            self._palette_group.addButton(sw)
            self._palette_buttons[name] = sw
            fl.addWidget(sw)

        # 自定义颜色按钮
        self.custom_color_btn = QPushButton("🎨 自定义")
        self.custom_color_btn.setObjectName("tool_custom_color")
        self.custom_color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.custom_color_btn.clicked.connect(self._on_custom_color)
        fl.addWidget(self.custom_color_btn)

        # 粗细滑块
        thick_label = QLabel("粗细")
        thick_label.setObjectName("drawing_group_label")
        fl.addWidget(thick_label)
        self.thickness_slider = QSlider(Qt.Orientation.Horizontal)
        self.thickness_slider.setRange(1, 30)
        self.thickness_slider.setValue(self.pen_width)
        self.thickness_slider.setFixedWidth(120)
        self.thickness_slider.valueChanged.connect(self._on_thickness_changed)
        fl.addWidget(self.thickness_slider)
        self.thickness_value_label = QLabel(f"{self.pen_width}px")
        self.thickness_value_label.setObjectName("drawing_group_label")
        self.thickness_value_label.setMinimumWidth(34)
        fl.addWidget(self.thickness_value_label)

        # 填充模式切换（空心/实心）
        self.fill_btn = QPushButton("▢ 空心")
        self.fill_btn.setObjectName("tool_fill_toggle")
        self.fill_btn.setCheckable(True)
        self.fill_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fill_btn.setToolTip("切换形状填充模式：空心 / 实心（仅形状工具有效）")
        self.fill_btn.clicked.connect(self._on_fill_toggled)
        fl.addWidget(self.fill_btn)

        fl.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        row.setLayout(fl)
        section.addWidget(row)

    def _build_select_ops_section(self, section: "CollapsibleSection"):
        """选择操作分组：矩形/自由选择（互斥）+ 选择/剪贴板/撤销动作。"""
        container = QWidget()
        flow = FlowLayout(container, margin=2, h_spacing=6, v_spacing=6)
        # 互斥选择工具
        for name, text in [("rect_select", "矩形选择"), ("free_select", "自由选择")]:
            btn = QPushButton(text)
            btn.setObjectName(f"tool_{name}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("tool_name", name)
            btn.setCheckable(True)
            btn.setToolTip(_SELECT_TOOLTIPS.get(name, ""))
            self._tool_btn_group.addButton(btn)
            self._tool_btn_group.setId(btn, len(self._tool_buttons))
            self._tool_buttons[name] = btn
            flow.addWidget(btn)
        # 动作按钮
        for name, text in [
            ("select_all", "全选"), ("copy", "复制"), ("cut", "剪切"), ("paste", "粘贴"),
            ("delete", "删除"), ("undo", "撤销"), ("redo", "重做"), ("clear", "清空"),
        ]:
            btn = QPushButton(text)
            btn.setObjectName(f"tool_{name}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("tool_name", name)
            btn.setToolTip(_SELECT_TOOLTIPS.get(name, ""))
            btn.clicked.connect(lambda _c=False, n=name: self._on_action_clicked(n))
            self._tool_buttons[name] = btn
            flow.addWidget(btn)
        section.addWidget(container)

    def _build_view_section(self, section: "CollapsibleSection"):
        """视图控制分组：放大/缩小/100%/适应窗口 + 滚轮缩放开关。"""
        container = QWidget()
        flow = FlowLayout(container, margin=2, h_spacing=6, v_spacing=6)
        for name, text in _VIEW_TOOLS:
            btn = QPushButton(text)
            btn.setObjectName(f"tool_{name}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("tool_name", name)
            btn.setToolTip(_VIEW_TOOLTIPS.get(name, ""))
            btn.clicked.connect(lambda _c=False, n=name: self._on_action_clicked(n))
            self._tool_buttons[name] = btn
            flow.addWidget(btn)
        # 滚轮缩放开关（可勾选，不加入互斥工具组）
        wz = QPushButton("滚轮缩放: 关")
        wz.setObjectName("tool_wheel_zoom_toggle")
        wz.setCursor(Qt.CursorShape.PointingHandCursor)
        wz.setCheckable(True)
        wz.setToolTip("切换滚轮缩放模式 (开: 滚轮直接缩放; 关: 滚轮平移, Ctrl+滚轮缩放)")
        wz.toggled.connect(self._toggle_wheel_zoom)
        self._tool_buttons["wheel_zoom_toggle"] = wz
        flow.addWidget(wz)
        section.addWidget(container)

    def _build_canvas_area(self, root_layout: QVBoxLayout):
        """画布区：顶部水平比例尺 + 左侧垂直比例尺 + 画布视图。"""
        # 水平比例尺
        self.h_ruler = HorizontalRuler()
        self.h_ruler.setCanvasWidth(CANVAS_WIDTH)
        # 顶部行：左侧占位（对齐垂直尺宽度）+ 水平尺
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(0)
        top_row.addSpacing(self.v_ruler_width())
        top_row.addWidget(self.h_ruler, 1)
        root_layout.addLayout(top_row)

        # 中间行：垂直尺 + 画布
        middle = QHBoxLayout()
        middle.setContentsMargins(0, 0, 0, 0)
        middle.setSpacing(0)
        self.v_ruler = VerticalRuler()
        self.v_ruler.setCanvasHeight(CANVAS_HEIGHT)
        middle.addWidget(self.v_ruler)
        self._build_canvas(middle)
        root_layout.addLayout(middle, 1)

    def v_ruler_width(self) -> int:
        """垂直比例尺宽度（用于顶部占位对齐）。"""
        return 32

    def _build_canvas(self, middle_layout: QHBoxLayout):
        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT)
        # 白色画布背景（无论主题都保持白色，符合 Windows 画图习惯）
        self._canvas_bg_item = QGraphicsRectItem(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT)
        self._canvas_bg_item.setBrush(QBrush(QColor("#FFFFFF")))
        self._canvas_bg_item.setPen(QPen(QColor("#FFFFFF")))
        self._canvas_bg_item.setZValue(-1000)
        self.scene.addItem(self._canvas_bg_item)
        # 选中文字项时联动富文本工具栏
        self.scene.selectionChanged.connect(self._on_scene_selection_changed)

        self.view = _CanvasView(self)
        self.view.setScene(self.scene)
        self.view.setObjectName("drawing_canvas_view")
        self.view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        middle_layout.addWidget(self.view, 1)

    # -------------------------------------------------------------------
    # 工具切换 / 颜色 / 粗细 / 填充
    # -------------------------------------------------------------------
    def _on_tool_clicked(self, btn_id: int):
        btn = self._tool_btn_group.button(btn_id)
        if btn is None:
            return
        name = btn.property("tool_name")
        if name:
            self._set_tool(name)

    def _on_action_clicked(self, name: str):
        # 操作 / 视图 / 文件 动作
        if name == "undo":
            self.undo_stack.undo()
        elif name == "redo":
            self.undo_stack.redo()
        elif name == "clear":
            self.clear_canvas()
        elif name == "copy":
            self._copy_selection()
        elif name == "paste":
            self._paste()
        elif name == "cut":
            self._cut_selection()
        elif name == "delete":
            self._delete_selected()
        elif name == "select_all":
            self._select_all()
        elif name == "zoom_in":
            self.set_zoom(min(800, self.zoom_level + 25))
        elif name == "zoom_out":
            self.set_zoom(max(25, self.zoom_level - 25))
        elif name == "zoom_100":
            self.set_zoom(100)
        elif name == "zoom_fit":
            self._fit_to_window()
        elif name == "save_file":
            self._save_to_file()
        elif name == "insert_note":
            self.insert_to_note_requested.emit()

    def _set_tool(self, name: str):
        """切换当前工具：deactivate 旧工具，实例化新工具。"""
        # deactivate 旧工具
        if self.current_tool is not None:
            try:
                self.current_tool.deactivate()
            except Exception:
                pass
        self.current_tool_name = name
        # 实例化新工具（后端未就绪时返回 None）
        try:
            self.current_tool = _backend_create_tool(name, self)
        except Exception:
            self.current_tool = None
        # 同步按钮选中态
        btn = self._tool_buttons.get(name)
        if btn is not None and btn.isCheckable() and not btn.isChecked():
            btn.setChecked(True)
        # 设置画布光标：有自定义光标则覆盖；无则保留 activate() 设置的系统光标；
        # 仅当工具创建失败（current_tool 为 None）时回退到箭头光标
        cursor = create_tool_cursor(name)
        if cursor is not None:
            self.view.setCursor(cursor)
        elif self.current_tool is None:
            self.view.setCursor(Qt.CursorShape.ArrowCursor)
        self._update_status_tool()

    def _set_active_color(self, which: str):
        """切换激活色（primary / secondary）。"""
        if which not in ("primary", "secondary"):
            return
        self.active_color = which
        self._refresh_color_styles()

    def _on_palette_clicked(self, btn: QPushButton):
        hex_color = getattr(btn, "_color_hex", "#000000")
        # 写入当前激活色
        if self.active_color == "primary":
            self.primary_color = hex_color
        else:
            self.secondary_color = hex_color
        self._refresh_color_styles()

    def _on_custom_color(self):
        initial = QColor(self.primary_color if self.active_color == "primary" else self.secondary_color)
        color = QColorDialog.getColor(initial, self, "选择自定义颜色")
        if color.isValid():
            hex_color = color.name()
            if self.active_color == "primary":
                self.primary_color = hex_color
            else:
                self.secondary_color = hex_color
            self._refresh_color_styles()

    def _on_thickness_changed(self, value: int):
        self.pen_width = value
        self.thickness_value_label.setText(f"{value}px")

    def _on_fill_toggled(self, checked: bool):
        self.filled = checked
        self.fill_btn.setText("■ 实心" if checked else "▢ 空心")

    def _current_pen(self, button) -> QPen:
        """根据鼠标按键返回画笔（左键=主色，右键=次色）。"""
        if button == Qt.MouseButton.RightButton:
            color = QColor(self.secondary_color)
        else:
            color = QColor(self.primary_color)
        pen = QPen(color, self.pen_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        return pen

    # -------------------------------------------------------------------
    # 选区 / 剪贴板（基础实现）
    # -------------------------------------------------------------------
    def _selected_items(self):
        return [it for it in self.scene.selectedItems() if it is not self._canvas_bg_item]

    def _copy_selection(self):
        items = self._selected_items()
        if not items:
            self._update_status("无选中项可复制")
            return
        # 深拷贝选中项（复制语义：粘贴时生成副本，原项保留）
        self._clipboard = [self._clone_item(it) for it in items]
        self._clipboard_origin = "copy"
        self._update_status(f"已复制 {len(items)} 项")

    def _cut_selection(self):
        items = self._selected_items()
        if not items:
            self._update_status("无选中项可剪切")
            return
        # 剪切保存引用（移动语义：粘贴时复用原项）
        self._clipboard = items
        self._clipboard_origin = "cut"
        if _HAS_DRAWING_COMMANDS:
            self.undo_stack.push(RemoveItemsCommand(self.scene, items))
        else:
            for it in items:
                self.scene.removeItem(it)
        self._update_status(f"已剪切 {len(items)} 项")

    def _clone_item(self, item):
        """深拷贝图形项，生成可独立添加到场景的副本。"""
        from PyQt6.QtWidgets import (
            QGraphicsPathItem, QGraphicsLineItem, QGraphicsRectItem,
            QGraphicsEllipseItem, QGraphicsPolygonItem, QGraphicsPixmapItem,
            QGraphicsTextItem, QGraphicsItemGroup, QGraphicsItem,
        )
        clone = None
        # 按类型重建图形项，复制关键属性
        if isinstance(item, QGraphicsPathItem):
            clone = QGraphicsPathItem(item.path())
            clone.setPen(item.pen())
        elif isinstance(item, QGraphicsLineItem):
            clone = QGraphicsLineItem(item.line())
            clone.setPen(item.pen())
        elif isinstance(item, QGraphicsRectItem):
            clone = QGraphicsRectItem(item.rect())
            clone.setPen(item.pen())
            clone.setBrush(item.brush())
        elif isinstance(item, QGraphicsEllipseItem):
            clone = QGraphicsEllipseItem(item.rect())
            clone.setPen(item.pen())
            clone.setBrush(item.brush())
        elif isinstance(item, QGraphicsPolygonItem):
            clone = QGraphicsPolygonItem(item.polygon())
            clone.setPen(item.pen())
            clone.setBrush(item.brush())
        elif isinstance(item, QGraphicsPixmapItem):
            clone = QGraphicsPixmapItem(item.pixmap())
        elif isinstance(item, QGraphicsTextItem):
            clone = QGraphicsTextItem(item.toPlainText())
            clone.setFont(item.font())
            clone.setDefaultTextColor(item.defaultTextColor())
        elif isinstance(item, QGraphicsItemGroup):
            # 组合项：递归克隆子项再组合
            clone = QGraphicsItemGroup()
            for child in item.childItems():
                child_clone = self._clone_item(child)
                if child_clone is not None:
                    clone.addToGroup(child_clone)
        if clone is not None:
            clone.setPos(item.pos())
            clone.setRotation(item.rotation())
            clone.setOpacity(item.opacity())
            clone.setZValue(item.zValue())
            try:
                clone.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
            except Exception:
                pass
        return clone

    def _paste(self):
        cb = getattr(self, "_clipboard", None)
        if not cb:
            self._update_status("剪贴板为空")
            return
        origin = getattr(self, "_clipboard_origin", "copy")
        if origin == "cut":
            # 剪切粘贴：移动语义，复用原项（已从场景移除）
            for it in cb:
                if _HAS_DRAWING_COMMANDS:
                    self.undo_stack.push(AddItemCommand(self.scene, it))
                elif it.scene() is None:
                    self.scene.addItem(it)
            # 剪切粘贴后清空剪贴板（避免重复粘贴）
            self._clipboard = None
            self._update_status(f"已粘贴 {len(cb)} 项（移动）")
        else:
            # 复制粘贴：生成新副本，偏移 10px 避免完全重叠
            for it in cb:
                clone = self._clone_item(it)
                if clone is not None:
                    clone.moveBy(10, 10)
                    if _HAS_DRAWING_COMMANDS:
                        self.undo_stack.push(AddItemCommand(self.scene, clone))
                    else:
                        self.scene.addItem(clone)
            self._update_status(f"已粘贴 {len(cb)} 项副本")

    def _select_all(self):
        for it in self.scene.items():
            if it is not self._canvas_bg_item:
                it.setSelected(True)

    # -------------------------------------------------------------------
    # V4 新增：删除 / 系统剪贴板粘贴 / 滚轮缩放 / 右键菜单 / 文字工具栏联动
    # -------------------------------------------------------------------
    def _delete_selected(self):
        """删除当前选中项（push RemoveItemsCommand）。"""
        items = self._selected_items()
        if not items:
            self._update_status("无选中项可删除")
            return
        if _HAS_DRAWING_COMMANDS:
            self.undo_stack.push(RemoveItemsCommand(self.scene, items))
        else:
            for it in items:
                self.scene.removeItem(it)
        self._update_status(f"已删除 {len(items)} 项")

    def _paste_from_system_clipboard(self):
        """从系统剪贴板获取图片，创建 QGraphicsPixmapItem 加入场景与撤销栈。"""
        cb = QApplication.clipboard()
        pm = cb.pixmap()
        if pm is None or pm.isNull():
            self._update_status("系统剪贴板无图片")
            return
        item = QGraphicsPixmapItem(pm)
        item.setPos(0, 0)
        try:
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        except Exception:
            pass
        if _HAS_DRAWING_COMMANDS:
            self.undo_stack.push(AddItemCommand(self.scene, item))
        else:
            self.scene.addItem(item)
        self._update_status("已从系统剪贴板粘贴图片")

    def _toggle_wheel_zoom(self, checked: bool):
        """切换滚轮缩放模式。"""
        self.wheel_zoom_enabled = checked
        btn = self._tool_buttons.get("wheel_zoom_toggle")
        if btn is not None:
            btn.setText("滚轮缩放: 开" if checked else "滚轮缩放: 关")
        self._update_status(f"滚轮缩放: {'开' if checked else '关'}")

    def _show_context_menu(self, pos: QPoint):
        """画布右键菜单：粘贴 / 全选 / 适应窗口 / 100% / 画布背景色 / 显示网格。"""
        menu = QMenu(self)
        menu.setObjectName("drawing_context_menu")
        act_paste = menu.addAction("粘贴")
        act_select_all = menu.addAction("全选")
        menu.addSeparator()
        act_fit = menu.addAction("适应窗口")
        act_100 = menu.addAction("100%")
        menu.addSeparator()
        act_bg = menu.addAction("画布背景色...")
        act_grid = menu.addAction("显示网格")
        act_grid.setCheckable(True)
        act_grid.setChecked(self.show_grid)
        # 信号绑定
        act_paste.triggered.connect(self._paste_from_system_clipboard)
        act_select_all.triggered.connect(self._select_all)
        act_fit.triggered.connect(self._fit_to_window)
        act_100.triggered.connect(lambda: self.set_zoom(100))
        act_bg.triggered.connect(self._choose_canvas_bg)
        act_grid.toggled.connect(self._toggle_grid)
        # 主题样式
        t = THEMES[self.current_theme]
        qss = get_drawing_board_qss(t)
        menu.setStyleSheet(qss["context_menu"])
        menu.exec(pos)

    def _choose_canvas_bg(self):
        """选择画布背景色。"""
        initial = self._canvas_bg_item.brush().color()
        color = QColorDialog.getColor(initial, self, "选择画布背景色")
        if color.isValid():
            self._canvas_bg_item.setBrush(QBrush(color))
            self._canvas_bg_item.setPen(QPen(color))
            self._update_status(f"画布背景色已设置为 {color.name()}")

    def _toggle_grid(self, checked: bool):
        """切换网格显示（记录状态）。"""
        self.show_grid = checked
        self._update_status(f"显示网格: {'开' if checked else '关'}")

    def _on_scene_selection_changed(self):
        """场景选中变化时联动富文本工具栏：选中文字项则显示，否则隐藏。"""
        text_item: Optional[QGraphicsTextItem] = None
        for it in self.scene.selectedItems():
            if isinstance(it, QGraphicsTextItem) and it is not self._canvas_bg_item:
                text_item = it
                break
        if text_item is not None and self.text_toolbar is not None:
            self.text_toolbar.setTargetItem(text_item)
        elif self.text_toolbar is not None:
            self.text_toolbar.clearTarget()

    # -------------------------------------------------------------------
    # 视图缩放
    # -------------------------------------------------------------------
    def set_zoom(self, level: int):
        """设置缩放（25~800）。"""
        level = max(25, min(800, int(level)))
        self.zoom_level = level
        factor = level / 100.0
        self.view.resetTransform()
        self.view.scale(factor, factor)
        # 通知比例尺更新刻度
        if self.h_ruler is not None:
            self.h_ruler.setZoom(factor)
        if self.v_ruler is not None:
            self.v_ruler.setZoom(factor)
        self._update_status_zoom()

    def _update_ruler_mouse(self, x: int, y: int):
        """比例尺鼠标指示线联动（来自画布视图的视口坐标）。"""
        if self.h_ruler is not None:
            self.h_ruler.setMousePos(x)
        if self.v_ruler is not None:
            self.v_ruler.setMousePos(y)

    def _fit_to_window(self):
        margin = 24
        vw = max(1, self.view.viewport().width() - margin)
        vh = max(1, self.view.viewport().height() - margin)
        factor = min(vw / CANVAS_WIDTH, vh / CANVAS_HEIGHT)
        level = max(25, min(800, int(factor * 100)))
        self.set_zoom(level)

    # -------------------------------------------------------------------
    # 渲染 / 保存 / 插入
    # -------------------------------------------------------------------
    def has_unsaved_content(self) -> bool:
        """画板是否有内容（除背景外的图形项）。"""
        for it in self.scene.items():
            if it is not self._canvas_bg_item:
                return True
        return False

    def render_to_pixmap(self) -> QPixmap:
        """将 scene 渲染为 QPixmap（800×600，白色背景）。"""
        pm = QPixmap(CANVAS_WIDTH, CANVAS_HEIGHT)
        pm.fill(Qt.GlobalColor.white)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        target_rect = QRectF(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT)
        source_rect = QRectF(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT)
        self.scene.render(painter, target_rect, source_rect, Qt.AspectRatioMode.KeepAspectRatio)
        painter.end()
        return pm

    def insert_to_current_note(self, note_id: int) -> str:
        """将画板内容保存为图片并返回 Markdown 引用路径。

        后端约定 `from core.database import save_drawing_to_note_assets`，
        此处优先使用后端实现；若后端未就绪，使用本地回退（基于 get_assets_dir）。
        """
        pixmap = self.render_to_pixmap()
        try:
            from core.database import save_drawing_to_note_assets  # type: ignore
            md_path = save_drawing_to_note_assets(note_id, pixmap)
            if md_path:
                return md_path
        except Exception:
            pass
        # 本地回退实现
        return self._save_drawing_local(note_id, pixmap)

    def _save_drawing_local(self, note_id: int, pixmap: QPixmap) -> str:
        """本地回退：保存图片到笔记资产目录，返回 Markdown 引用路径。"""
        assets_dir = get_assets_dir(note_id)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"drawing_{ts}.png"
        abs_path = os.path.join(assets_dir, filename)
        pixmap.save(abs_path, "PNG")
        # 返回相对 assets 根目录的 Markdown 引用路径（与 editor 粘贴图片约定一致）
        try:
            rel = os.path.relpath(abs_path, get_assets_root())
            rel = rel.replace("\\", "/")
            return f"./assets/{rel}"
        except Exception:
            return abs_path

    def clear_canvas(self):
        """清空画布（带二次确认）。"""
        if not self.has_unsaved_content():
            self._update_status("画布已为空")
            return
        reply = QMessageBox.question(
            self, "清空画布", "确定要清空整个画布吗？此操作不可撤销恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if _HAS_DRAWING_COMMANDS:
            # 后端 ClearSceneCommand(scene, bg_item) 跳过背景项，保留白色画布
            self.undo_stack.push(ClearSceneCommand(self.scene, self._canvas_bg_item))
        else:
            # 本地回退：传入背景项以保留白色画布
            self.undo_stack.push(ClearSceneCommand(self.scene, self._canvas_bg_item))
        self._update_status("画布已清空")

    def _save_to_file(self):
        """保存为 PNG 文件。"""
        default_name = f"drawing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        path, _ = QFileDialog.getSaveFileName(
            self, "保存画板为图片", default_name, "PNG 图片 (*.png);;JPEG 图片 (*.jpg);;BMP 图片 (*.bmp)"
        )
        if not path:
            return
        pm = self.render_to_pixmap()
        if pm.save(path):
            self._update_status(f"已保存到：{path}")
        else:
            self._update_status("保存失败")

    # -------------------------------------------------------------------
    # 状态栏
    # -------------------------------------------------------------------
    def _update_status_tool(self):
        label = dict(_DRAW_TOOLS + _SHAPE_TOOLS).get(self.current_tool_name, self.current_tool_name)
        self._update_status()

    def _update_status_coord(self, scene_pos: QPointF):
        self._last_coord = (int(scene_pos.x()), int(scene_pos.y()))
        self._update_status()

    def _update_status_zoom(self):
        self._update_status()

    def _update_status(self, msg: Optional[str] = None):
        coord = getattr(self, "_last_coord", (0, 0))
        label = dict(_DRAW_TOOLS + _SHAPE_TOOLS).get(self.current_tool_name, self.current_tool_name)
        wheel = "开" if self.wheel_zoom_enabled else "关"
        prefix = f"{msg} · " if msg else ""
        self.status_label.setText(
            f"{prefix}坐标 ({coord[0]}, {coord[1]}) · 画布 {CANVAS_WIDTH}×{CANVAS_HEIGHT} · "
            f"缩放 {self.zoom_level}% · 工具：{label} · 滚轮缩放: {wheel}"
        )

    # -------------------------------------------------------------------
    # 主题
    # -------------------------------------------------------------------
    def apply_theme(self, theme_name: str):
        """刷新所有子组件样式。"""
        self.current_theme = theme_name
        t = THEMES[theme_name]
        qss = get_drawing_board_qss(t)
        self.toolbar.setStyleSheet(qss["toolbar"])
        # 折叠分组面板
        for sec in self._sections:
            sec.apply_theme(t)
        # 比例尺
        if self.h_ruler is not None:
            self.h_ruler.setStyleSheet(qss["ruler"])
            self.h_ruler.apply_theme(t)
        if self.v_ruler is not None:
            self.v_ruler.setStyleSheet(qss["ruler"])
            self.v_ruler.apply_theme(t)
        # 富文本工具栏
        if self.text_toolbar is not None:
            self.text_toolbar.setStyleSheet(qss["text_toolbar"])
            self.text_toolbar.apply_theme(t)
        # 分组标签
        for child in self.toolbar.findChildren(QLabel):
            child.setStyleSheet(qss["tool_group_label"])
        # 颜色行内的标签
        cw = self.findChild(QFrame, "drawing_group")
        if cw is not None:
            for lbl in cw.findChildren(QLabel):
                lbl.setStyleSheet(qss["tool_group_label"])
        # 工具按钮（区分选中/未选中）
        for name, btn in self._tool_buttons.items():
            if btn.isCheckable():
                btn.setStyleSheet(qss["tool_button_checked"] if btn.isChecked() else qss["tool_button"])
            else:
                btn.setStyleSheet(qss["tool_button"])
        # 操作/视图/文件按钮（非互斥）
        for name in [n for n, _ in (_OPERATION_TOOLS + _VIEW_TOOLS + _FILE_TOOLS)]:
            btn = self._tool_buttons.get(name)
            if btn is not None:
                btn.setStyleSheet(qss["tool_button"])
        # 自定义颜色按钮 / 填充按钮 / 粗细标签
        if hasattr(self, "custom_color_btn"):
            self.custom_color_btn.setStyleSheet(qss["tool_button"])
        if hasattr(self, "fill_btn"):
            self.fill_btn.setStyleSheet(qss["tool_button_checked"] if self.fill_btn.isChecked() else qss["tool_button"])
        # 调色板色块
        for name, btn in self._palette_buttons.items():
            hex_color = btn._color_hex  # type: ignore
            active = (self._palette_group.checkedButton() is btn)
            base = qss["color_swatch_active"] if active else qss["color_swatch"]
            btn.setStyleSheet(f"{base}\nQPushButton {{ background-color: {hex_color}; }}")
        # 主/次色块
        self._refresh_color_styles()
        # 画布视图
        self.view.setStyleSheet(qss["canvas_view"])
        self.view.setBackgroundBrush(QColor(t['toolbar_bg']))
        # 状态栏
        self.status_label.setStyleSheet(qss["status_bar"])
        # 粗细滑块
        self.thickness_slider.setStyleSheet(qss["slider"])
        self.thickness_value_label.setStyleSheet(qss["tool_group_label"])

    def _refresh_color_styles(self):
        """刷新主/次色块样式（叠加显示 + 激活态高亮）。"""
        t = THEMES[self.current_theme]
        qss = get_drawing_board_qss(t)
        primary_active = (self.active_color == "primary")
        secondary_active = (self.active_color == "secondary")
        # 主色块
        self.primary_swatch.setStyleSheet(
            f"QPushButton {{ background-color: {self.primary_color};"
            f" border: {3 if primary_active else 1}px solid {t['primary'] if primary_active else t['border']};"
            f" border-radius: 6px; }}"
        )
        # 次色块
        self.primary_switch.setStyleSheet(
            f"QPushButton {{ background-color: {self.secondary_color};"
            f" border: {3 if secondary_active else 1}px solid {t['primary'] if secondary_active else t['border']};"
            f" border-radius: 6px; }}"
        )
        # 调色板色块
        for name, btn in self._palette_buttons.items():
            hex_color = btn._color_hex  # type: ignore
            active = (self._palette_group.checkedButton() is btn)
            base = qss["color_swatch_active"] if active else qss["color_swatch"]
            btn.setStyleSheet(f"{base}\nQPushButton {{ background-color: {hex_color}; }}")

    # -------------------------------------------------------------------
    # 事件 / 资源清理
    # -------------------------------------------------------------------
    def closeEvent(self, event):
        # 清理工具资源
        if self.current_tool is not None:
            try:
                self.current_tool.deactivate()
            except Exception:
                pass
        self.current_tool = None
        self.undo_stack.clear()
        event.accept()
