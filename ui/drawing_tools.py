"""
Zhuibook 画板工具集（BaseTool + 9 种绘图工具 + 9 种形状工具）

设计要点：
  - BaseTool 继承 QObject，持有 scene / view / editor_ref（画板视图引用）。
  - editor_ref 由前端 DrawingBoardView 提供，暴露：
      primary_color / secondary_color（可能是 QColor 或 hex 字符串）
      pen_width / filled / undo_stack / scene / view / _canvas_bg_item
  - 颜色统一经 _button_color 兼容 str 与 QColor 两种形式。
  - _active_button 同时处理 mouse_press（event.button()）与
    mouse_move/mouse_release（event.buttons()）两种情形。
  - 形状工具采用“按下创建预览 -> 移动更新几何 -> 释放提交撤销栈”模式；
    AddItemCommand.redo 幂等，故预览项可先加入场景，提交时无需先移除。
  - create_tool 兼容两种调用：
      create_tool(name, board)               —— 前端 drawing_board.py 实际调用
      create_tool(name, scene, view, editor) —— 任务规范签名
"""
from __future__ import annotations

import math
import random

from PyQt6.QtCore import Qt, QObject, pyqtSignal, QRectF, QRect, QPointF, QTimer
from PyQt6.QtGui import (
    QColor, QPen, QBrush, QPixmap, QPainter, QPainterPath, QImage, QFont,
    QPolygonF, QPalette, QAbstractTextDocumentLayout,
)
from PyQt6.QtWidgets import (
    QGraphicsItem, QGraphicsPathItem, QGraphicsLineItem, QGraphicsRectItem,
    QGraphicsEllipseItem, QGraphicsPolygonItem, QGraphicsPixmapItem,
    QGraphicsTextItem, QGraphicsItemGroup, QInputDialog,
)

# drawing_commands 仅依赖 PyQt6，无循环导入风险，可直接顶层导入
from .drawing_commands import AddItemCommand, MoveItemsCommand  # noqa: E402

# 防御性导入：工具光标（前端可能尚未实现 ui/drawing_cursors.py）
try:
    from .drawing_cursors import create_tool_cursor
except ImportError:
    create_tool_cursor = None

# 防御性导入：富文本格式工具栏（前端可能尚未实现 ui/drawing_text_editor.py）
try:
    from .drawing_text_editor import TextFormatToolbar
except ImportError:
    TextFormatToolbar = None

# 防御性导入：文字修改撤销命令（drawing_commands 中新增）
try:
    from .drawing_commands import ModifyTextCommand
except ImportError:
    ModifyTextCommand = None


# ===========================================================================
# 几何辅助函数
# ===========================================================================
def _normalized_rect(start: QPointF, end: QPointF) -> QRectF:
    """由两个端点构造标准化矩形（宽高非负）。"""
    x = min(start.x(), end.x())
    y = min(start.y(), end.y())
    w = abs(end.x() - start.x())
    h = abs(end.y() - start.y())
    return QRectF(x, y, w, h)


def _snap_45(start: QPointF, end: QPointF) -> QPointF:
    """将终点吸附到距离起点最近的 45° 方向（用于 Shift 锁定直线）。"""
    dx = end.x() - start.x()
    dy = end.y() - start.y()
    if dx == 0 and dy == 0:
        return end
    angle = round(math.atan2(dy, dx) / (math.pi / 4)) * (math.pi / 4)
    length = math.hypot(dx, dy)
    return QPointF(start.x() + length * math.cos(angle),
                   start.y() + length * math.sin(angle))


def _curve_path(start: QPointF, end: QPointF) -> QPainterPath:
    """构造 S 型三次贝塞尔曲线。"""
    path = QPainterPath(start)
    c1 = QPointF(start.x(), end.y())
    c2 = QPointF(end.x(), start.y())
    path.cubicTo(c1, c2, end)
    return path


def _triangle_polygon(rect: QRectF) -> QPolygonF:
    """等腰三角形（顶点在上，底边在下）。"""
    top = QPointF(rect.center().x(), rect.top())
    bl = QPointF(rect.left(), rect.bottom())
    br = QPointF(rect.right(), rect.bottom())
    return QPolygonF([top, bl, br])


def _star_polygon(rect: QRectF) -> QPolygonF:
    """五角星（10 个顶点：5 外 + 5 内交替）。"""
    cx = rect.center().x()
    cy = rect.center().y()
    outer = min(rect.width(), rect.height()) / 2.0
    if outer < 1:
        outer = 1.0
    inner = outer * 0.382
    verts = []
    for i in range(10):
        angle = -math.pi / 2 + i * math.pi / 5
        r = outer if i % 2 == 0 else inner
        verts.append(QPointF(cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return QPolygonF(verts)


def _diamond_polygon(rect: QRectF) -> QPolygonF:
    """菱形（4 顶点）。"""
    return QPolygonF([
        QPointF(rect.center().x(), rect.top()),
        QPointF(rect.right(), rect.center().y()),
        QPointF(rect.center().x(), rect.bottom()),
        QPointF(rect.left(), rect.center().y()),
    ])


def _regular_polygon(rect: QRectF, sides: int) -> QPolygonF:
    """正 n 边形（5=五边形，6=六边形，...），顶点从顶部开始顺时针排列。"""
    cx = rect.center().x()
    cy = rect.center().y()
    r = min(rect.width(), rect.height()) / 2.0
    if r < 1:
        r = 1.0
    verts = []
    for i in range(sides):
        angle = -math.pi / 2 + i * 2 * math.pi / sides
        verts.append(QPointF(cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return QPolygonF(verts)


def _heart_path(rect: QRectF) -> QPainterPath:
    """爱心参数方程（由 2 个半圆 + V 尖底组成）。"""
    w = max(1.0, rect.width())
    h = max(1.0, rect.height())
    x0 = rect.left()
    y0 = rect.top()
    path = QPainterPath()
    # 爱心顶点从底部尖出发，顺时针：左半圆 + 右半圆 + 底部连接
    # 使用三次贝塞尔近似，控制点用经典爱心参数
    left_cx = x0 + w * 0.25
    right_cx = x0 + w * 0.75
    cy_top = y0 + h * 0.25
    cy_mid = y0 + h * 0.55
    tip = QPointF(x0 + w * 0.5, y0 + h)
    top_left = QPointF(x0, cy_top)
    top_right = QPointF(x0 + w, cy_top)
    mid_top = QPointF(x0 + w * 0.5, cy_mid)
    path.moveTo(tip)
    # 左下曲线
    path.cubicTo(QPointF(x0, cy_mid), top_left, mid_top)
    # 右下曲线
    path.cubicTo(top_right, QPointF(x0 + w, cy_mid), tip)
    path.closeSubpath()
    return path


def _right_triangle_polygon(rect: QRectF) -> QPolygonF:
    """直角三角形（直角在左下角）。"""
    return QPolygonF([
        QPointF(rect.left(), rect.bottom()),
        QPointF(rect.right(), rect.bottom()),
        QPointF(rect.left(), rect.top()),
    ])


def _parallelogram_polygon(rect: QRectF) -> QPolygonF:
    """平行四边形（左移顶部 20% 宽度）。"""
    skew = rect.width() * 0.2
    return QPolygonF([
        QPointF(rect.left() + skew, rect.top()),
        QPointF(rect.right(), rect.top()),
        QPointF(rect.right() - skew, rect.bottom()),
        QPointF(rect.left(), rect.bottom()),
    ])


def _arrow_path(start: QPointF, end: QPointF, head: float = 15) -> QPainterPath:
    """箭头：主线 + 两条箭头线（箭头大小 head 像素）。"""
    path = QPainterPath(start)
    path.lineTo(end)
    dx = end.x() - start.x()
    dy = end.y() - start.y()
    length = math.hypot(dx, dy)
    if length < 1:
        return path
    angle = math.atan2(dy, dx)
    a1 = angle + math.radians(150)
    a2 = angle - math.radians(150)
    p1 = QPointF(end.x() + head * math.cos(a1), end.y() + head * math.sin(a1))
    p2 = QPointF(end.x() + head * math.cos(a2), end.y() + head * math.sin(a2))
    path.moveTo(end)
    path.lineTo(p1)
    path.moveTo(end)
    path.lineTo(p2)
    return path


def _callout_path(start: QPointF, end: QPointF) -> QPainterPath:
    """对话框：矩形 + 底部三角指针。"""
    rect = _normalized_rect(start, end)
    path = QPainterPath()
    path.addRect(rect)
    cx = rect.left() + rect.width() * 0.3
    bw = max(8.0, rect.width() * 0.15)   # 指针底宽
    ph = max(10.0, rect.height() * 0.2)  # 指针高度
    p1 = QPointF(cx, rect.bottom())
    p2 = QPointF(cx + bw, rect.bottom())
    p3 = QPointF(cx, rect.bottom() + ph)
    path.addPolygon(QPolygonF([p1, p2, p3]))
    return path


# ===========================================================================
# 工具基类
# ===========================================================================
class BaseTool(QObject):
    """所有画板工具的基类。"""

    def __init__(self, scene, view, editor_ref):
        super().__init__()
        self.scene = scene
        self.view = view
        self.editor_ref = editor_ref

    # ---- 鼠标事件（子类覆写）----
    def mouse_press(self, event, scene_pos):
        pass

    def mouse_move(self, event, scene_pos):
        pass

    def mouse_release(self, event, scene_pos):
        pass

    def double_click(self, event, scene_pos):
        """双击事件（用于文字二次编辑等场景）。"""
        pass

    # ---- 生命周期 ----
    def activate(self):
        """工具激活时切换光标"""
        # 优先从 editor_ref 获取工具名（最准确，含下划线命名如 color_picker/round_rect）
        tool_name = getattr(self.editor_ref, "current_tool_name", None)
        if not tool_name:
            # 回退：从类名推导（仅作兜底，可能对复合名不准确）
            tool_name = self.__class__.__name__.lower().replace("tool", "")
        if create_tool_cursor is not None and self.view:
            cursor = create_tool_cursor(tool_name)
            if cursor is not None:
                self.view.setCursor(cursor)
            else:
                # 对特定工具使用系统光标
                if tool_name in ("color_picker", "rect_select", "free_select"):
                    self.view.setCursor(Qt.CursorShape.CrossCursor)
                elif tool_name == "text":
                    self.view.setCursor(Qt.CursorShape.IBeamCursor)
                elif tool_name in ("line", "curve", "rect", "round_rect", "ellipse",
                                   "triangle", "star", "arrow", "callout"):
                    self.view.setCursor(Qt.CursorShape.CrossCursor)
                else:
                    self.view.setCursor(Qt.CursorShape.ArrowCursor)
        elif self.view:
            self.view.setCursor(Qt.CursorShape.ArrowCursor)

    def deactivate(self):
        """工具停用时恢复默认光标"""
        if self.view:
            self.view.setCursor(Qt.CursorShape.ArrowCursor)

    def cursor(self):
        return Qt.CursorShape.ArrowCursor

    # ---- 辅助 ----
    def _active_button(self, event) -> Qt.MouseButton:
        """识别当前按键：press 用 button()，move/release 用 buttons()。"""
        button = event.button() if hasattr(event, "button") else Qt.MouseButton.NoButton
        if button != Qt.MouseButton.NoButton:
            return button
        buttons = event.buttons() if hasattr(event, "buttons") else Qt.MouseButton.NoButton
        if buttons & Qt.MouseButton.RightButton:
            return Qt.MouseButton.RightButton
        if buttons & Qt.MouseButton.LeftButton:
            return Qt.MouseButton.LeftButton
        return Qt.MouseButton.LeftButton

    def _button_color(self, event):
        """根据按键返回主色/次色（可能是 str 或 QColor）。"""
        if self._active_button(event) == Qt.MouseButton.RightButton:
            return self.editor_ref.secondary_color
        return self.editor_ref.primary_color

    def _current_pen(self, event) -> QPen:
        """根据按键返回画笔：左键=主色，右键=次色，RoundJoin+RoundCap。"""
        color = self._button_color(event)
        if not isinstance(color, QColor):
            color = QColor(color)
        pen = QPen(color, self.editor_ref.pen_width)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        return pen

    def _bg_item(self):
        """画布背景项（选择/取色时需排除）。"""
        return getattr(self.editor_ref, "_canvas_bg_item", None)

    def _make_selectable(self, item):
        """为图形项启用可选择、可移动、可聚焦标志（选择/移动/删除依赖这些）。"""
        if item is None:
            return
        try:
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, True)
        except Exception:
            pass


# ===========================================================================
# 绘图工具：画笔 / 喷枪 / 刷子 / 橡皮 / 取色 / 填充 / 文字 / 矩形选择 / 自由选择
# ===========================================================================
class PenTool(BaseTool):
    """画笔：QGraphicsPathItem + QPainterPath，抗锯齿（由视图渲染提示保证）。"""

    def __init__(self, scene, view, editor_ref):
        super().__init__(scene, view, editor_ref)
        self._path = None
        self._item = None

    def _stroke_pen(self, event) -> QPen:
        return self._current_pen(event)

    def mouse_press(self, event, scene_pos):
        pen = self._stroke_pen(event)
        self._path = QPainterPath(scene_pos)
        self._path.lineTo(scene_pos)  # 单击也能产生圆点
        self._item = QGraphicsPathItem()
        self._item.setPen(pen)
        self._item.setPath(self._path)
        self._make_selectable(self._item)
        self.scene.addItem(self._item)

    def mouse_move(self, event, scene_pos):
        if self._path is not None and self._item is not None:
            self._path.lineTo(scene_pos)
            self._item.setPath(self._path)

    def mouse_release(self, event, scene_pos):
        if self._item is None:
            return
        if self._path is not None:
            self._path.lineTo(scene_pos)
            self._item.setPath(self._path)
        item = self._item
        self._item = None
        self._path = None
        # 幂等 redo：项已在场景中则不重复添加
        self.editor_ref.undo_stack.push(
            AddItemCommand(self.scene, item))

    def deactivate(self):
        # 工具切换时若仍有未提交笔画，则提交
        if self._item is not None:
            item = self._item
            self._item = None
            self._path = None
            self.editor_ref.undo_stack.push(
                AddItemCommand(self.scene, item))


class BrushTool(PenTool):
    """刷子：同画笔但更粗，支持 3 种刷头（圆/方/斜）。"""

    def __init__(self, scene, view, editor_ref):
        super().__init__(scene, view, editor_ref)
        self.brush_head = 0  # 0=圆 1=方 2=斜

    def _stroke_pen(self, event) -> QPen:
        color = self._button_color(event)
        if not isinstance(color, QColor):
            color = QColor(color)
        width = max(1, self.editor_ref.pen_width * 2)  # 更粗
        pen = QPen(color, width)
        if self.brush_head == 0:
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        elif self.brush_head == 1:
            pen.setCapStyle(Qt.PenCapStyle.SquareCap)
            pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        else:
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            pen.setJoinStyle(Qt.PenJoinStyle.BevelJoin)
        return pen


class EraserTool(PenTool):
    """橡皮擦：颜色固定白色，较粗。"""

    def _stroke_pen(self, event) -> QPen:
        width = max(1, self.editor_ref.pen_width + 8)
        pen = QPen(QColor("#FFFFFF"), width)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        return pen


class BrushPenTool(PenTool):
    """毛笔：速度慢则粗、快则细的模拟软毛笔。"""

    def __init__(self, scene, view, editor_ref):
        super().__init__(scene, view, editor_ref)
        self._last_mouse_time = 0.0
        self._last_distance = 0.0

    def _stroke_pen(self, event) -> QPen:
        color = self._button_color(event)
        if not isinstance(color, QColor):
            color = QColor(color)
        base_width = max(1, self.editor_ref.pen_width)
        width = base_width + 2
        pen = QPen(color, width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        return pen


class WritingPenTool(PenTool):
    """书写笔：扁平笔尖（方形 cap + miter join）。"""

    def _stroke_pen(self, event) -> QPen:
        color = self._button_color(event)
        if not isinstance(color, QColor):
            color = QColor(color)
        width = max(1, self.editor_ref.pen_width)
        pen = QPen(color, width)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        return pen


class OilBrushTool(PenTool):
    """油画笔：半透明（alpha 150），厚重重叠效果。"""

    def _stroke_pen(self, event) -> QPen:
        color = self._button_color(event)
        if not isinstance(color, QColor):
            color = QColor(color)
        color = QColor(color.red(), color.green(), color.blue(), 150)
        width = max(1, int(self.editor_ref.pen_width * 1.8))
        pen = QPen(color, width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        return pen


class CrayonTool(PenTool):
    """蜡笔：粗糙纹理（用 dash pattern + 半透明模拟）。"""

    def _stroke_pen(self, event) -> QPen:
        color = self._button_color(event)
        if not isinstance(color, QColor):
            color = QColor(color)
        color = QColor(color.red(), color.green(), color.blue(), 200)
        width = max(1, int(self.editor_ref.pen_width * 1.5))
        pen = QPen(color, width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setDashPattern([2, 1])
        return pen


class MarkerTool(PenTool):
    """记号笔：方头 + 半透明 180。"""

    def _stroke_pen(self, event) -> QPen:
        color = self._button_color(event)
        if not isinstance(color, QColor):
            color = QColor(color)
        color = QColor(color.red(), color.green(), color.blue(), 180)
        width = max(1, int(self.editor_ref.pen_width * 2))
        pen = QPen(color, width)
        pen.setCapStyle(Qt.PenCapStyle.SquareCap)
        pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        return pen


class PencilTool(PenTool):
    """普通铅笔：细 + 半透明 150，轻微抖动不透明度。"""

    def _stroke_pen(self, event) -> QPen:
        color = self._button_color(event)
        if not isinstance(color, QColor):
            color = QColor(color)
        color = QColor(color.red(), color.green(), color.blue(), 150)
        width = max(1, self.editor_ref.pen_width)
        pen = QPen(color, width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        return pen


class WatercolorTool(PenTool):
    """水彩画笔：大湿边 + 低不透明度 alpha=60。"""

    def _stroke_pen(self, event) -> QPen:
        color = self._button_color(event)
        if not isinstance(color, QColor):
            color = QColor(color)
        color = QColor(color.red(), color.green(), color.blue(), 60)
        width = max(1, int(self.editor_ref.pen_width * 3))
        pen = QPen(color, width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        return pen


class AirbrushTool(BaseTool):
    """喷枪：移动时在随机半径内绘制多个小圆点，密度随粗细可调。"""

    def __init__(self, scene, view, editor_ref):
        super().__init__(scene, view, editor_ref)
        self._dots = []
        self._color = None

    def mouse_press(self, event, scene_pos):
        color = self._button_color(event)
        if not isinstance(color, QColor):
            color = QColor(color)
        self._color = color
        self._dots = []
        self._spray(scene_pos)

    def mouse_move(self, event, scene_pos):
        if self._color is not None:
            self._spray(scene_pos)

    def _spray(self, center: QPointF):
        density = max(8, int(self.editor_ref.pen_width))  # 密度可调
        radius = self.editor_ref.pen_width * 2 + 4
        for _ in range(density):
            r = random.random() * radius
            a = random.random() * 2 * math.pi
            x = center.x() + r * math.cos(a)
            y = center.y() + r * math.sin(a)
            dot = QGraphicsEllipseItem(x - 0.5, y - 0.5, 1.0, 1.0)
            dot.setPen(QPen(Qt.PenStyle.NoPen))
            dot.setBrush(QBrush(self._color))
            self.scene.addItem(dot)
            self._dots.append(dot)

    def mouse_release(self, event, scene_pos):
        if not self._dots:
            self._color = None
            return
        # 打包为一组提交（单个撤销步骤）
        group = self.scene.createItemGroup(self._dots)
        self._dots = []
        self._make_selectable(group)
        # createItemGroup 已将 group 加入场景；移除后通过命令重新加入
        if group.scene() is self.scene:
            self.scene.removeItem(group)
        self.editor_ref.undo_stack.push(
            AddItemCommand(self.scene, group))
        self._color = None

    def deactivate(self):
        # 切换工具时提交已喷涂的点
        if self._dots:
            group = self.scene.createItemGroup(self._dots)
            self._dots = []
            self._make_selectable(group)
            if group.scene() is self.scene:
                self.scene.removeItem(group)
            self.editor_ref.undo_stack.push(
                AddItemCommand(self.scene, group))
        self._color = None


class ColorPickerTool(BaseTool):
    """取色器：渲染单像素 QImage 获取颜色，emit color_picked 信号。"""

    color_picked = pyqtSignal(QColor)

    def mouse_press(self, event, scene_pos):
        color = self._pick(scene_pos)
        if color is not None and color.isValid():
            self.color_picked.emit(color)
            # 同步到 editor_ref 当前激活色
            hex_color = color.name()
            if getattr(self.editor_ref, "active_color", "primary") == "secondary":
                self.editor_ref.secondary_color = hex_color
            else:
                self.editor_ref.primary_color = hex_color
            refresh = getattr(self.editor_ref, "_refresh_color_styles", None)
            if callable(refresh):
                refresh()

    def _pick(self, scene_pos: QPointF):
        img = QImage(1, 1, QImage.Format.Format_RGB32)
        img.fill(Qt.GlobalColor.white)
        painter = QPainter(img)
        target = QRectF(0, 0, 1, 1)
        source = QRectF(scene_pos.x(), scene_pos.y(), 1, 1)
        self.scene.render(painter, target, source)
        painter.end()
        return img.pixelColor(0, 0)

    def mouse_move(self, event, scene_pos):
        pass

    def mouse_release(self, event, scene_pos):
        pass


class FillTool(BaseTool):
    """填充：场景渲染为 QImage，BFS 洪水填充，结果作为 QGraphicsPixmapItem 添加。"""

    def mouse_press(self, event, scene_pos):
        self._fill(scene_pos, event)

    def mouse_move(self, event, scene_pos):
        pass

    def mouse_release(self, event, scene_pos):
        pass

    def _fill(self, scene_pos: QPointF, event):
        scene_rect = self.scene.sceneRect()
        w = max(1, int(scene_rect.width()))
        h = max(1, int(scene_rect.height()))
        img = QImage(w, h, QImage.Format.Format_RGB32)
        img.fill(Qt.GlobalColor.white)
        painter = QPainter(img)
        self.scene.render(painter, scene_rect, scene_rect)
        painter.end()

        sx = int(scene_pos.x())
        sy = int(scene_pos.y())
        if sx < 0 or sx >= w or sy < 0 or sy >= h:
            return
        target_rgb = img.pixel(sx, sy)

        color = self._button_color(event)
        if not isinstance(color, QColor):
            color = QColor(color)
        fill_rgb = color.rgba()
        if target_rgb == fill_rgb:
            return

        # BFS 洪水填充（使用 visited 掩码避免重复访问）
        visited = bytearray(w * h)
        stack = [(sx, sy)]
        while stack:
            x, y = stack.pop()
            if x < 0 or x >= w or y < 0 or y >= h:
                continue
            idx = y * w + x
            if visited[idx]:
                continue
            if img.pixel(x, y) != target_rgb:
                continue
            img.setPixel(x, y, fill_rgb)
            visited[idx] = 1
            stack.append((x + 1, y))
            stack.append((x - 1, y))
            stack.append((x, y + 1))
            stack.append((x, y - 1))

        pixmap = QPixmap.fromImage(img)
        item = QGraphicsPixmapItem(pixmap)
        item.setPos(0, 0)
        self._make_selectable(item)
        self.editor_ref.undo_stack.push(
            AddItemCommand(self.scene, item))


# ===========================================================================
# 可拖动 / 可旋转 / 可缩放文字项
# ===========================================================================
class RotatableTextItem(QGraphicsTextItem):
    """支持拖动、旋转、缩放的文字项。

    交互（选中后显示手柄）：
      - 8 个缩放手柄（4 角 + 4 边）：拖动改变文字框大小，字体自动适配。
      - 顶部旋转指示器：拖动旋转文字。
      - 文字本体：拖动移动。
      - 双击：进入编辑模式。
    """

    # 手柄位置枚举
    HANDLE_TL, HANDLE_T, HANDLE_TR = 0, 1, 2
    HANDLE_L,  HANDLE_R             = 3, 4
    HANDLE_BL, HANDLE_B, HANDLE_BR = 5, 6, 7
    HANDLE_ROTATE                   = 8

    HANDLE_SIZE = 8.0
    ROTATE_OFFSET = 28.0  # 旋转按钮距边框顶部的距离

    # 类变量：全局唯一的编辑项
    _current_editing_item: 'RotatableTextItem | None' = None

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self._rotation = 0.0
        self._font_size = 12.0
        self._width = 180.0
        self._height = 40.0

        # 光标闪烁
        self._cursor_visible = True
        self._blink_timer = QTimer()
        self._blink_timer.timeout.connect(self._blink_cursor)

        # 交互标志
        self._mode = None
        self._resize_handle = -1
        self._resize_start_pos = QPointF()
        self._resize_start_br = QRectF()
        self._rotate_start_angle = 0.0
        self._rotate_start_rotation = 0.0
        self._rotate_center = QPointF()
        self._move_start_pos = QPointF()

        # 默认可选中可移动
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, True)
        self.setAcceptHoverEvents(True)

    # ---- 几何与旋转 ----
    def rotation_angle(self) -> float:
        return self._rotation

    def set_rotation_angle(self, angle: float):
        self._rotation = angle
        self.prepareGeometryChange()
        # 旋转中心应为文字内容区中心（不是 boundingRect 中心）
        s = self.HANDLE_SIZE
        content_center = QPointF(s + self._width / 2, s + self._height / 2)
        self.setTransformOriginPoint(content_center)
        self.setRotation(angle)
        self.update()

    def reset_rotation(self):
        self._rotation = 0.0
        self.setRotation(0.0)
        self.update()

    def text_width(self) -> float:
        return self._width

    def text_height(self) -> float:
        return self._height

    def font_size(self) -> float:
        return self._font_size

    def set_text_size(self, width: float, height: float, font_size: float):
        self.prepareGeometryChange()
        self._width = max(30.0, width)
        self._height = max(20.0, height)
        self._font_size = max(6.0, font_size)
        font = self.font()
        font.setPointSizeF(self._font_size)
        self.setFont(font)
        self.update()

    def boundingRect(self):
        # 边框四周留出空间绘制手柄，顶部额外留出旋转按钮空间
        margin = self.HANDLE_SIZE
        return QRectF(-margin, -margin - self.ROTATE_OFFSET,
                      self._width + margin * 2,
                      self._height + margin * 2 + self.ROTATE_OFFSET)

    # ---- 手柄位置计算 ----
    def _handle_local_pos(self, handle: int) -> QPointF:
        """返回手柄在 item 本地坐标系中的位置。"""
        br = self.boundingRect()
        s = self.HANDLE_SIZE
        w, h = self._width, self._height
        # 边框内容区左上为 (s, s)，右下为 (s+w, s+h)
        positions = {
            self.HANDLE_TL: QPointF(s, s),
            self.HANDLE_T:  QPointF(s + w / 2, s),
            self.HANDLE_TR: QPointF(s + w, s),
            self.HANDLE_L:  QPointF(s, s + h / 2),
            self.HANDLE_R:  QPointF(s + w, s + h / 2),
            self.HANDLE_BL: QPointF(s, s + h),
            self.HANDLE_B:  QPointF(s + w / 2, s + h),
            self.HANDLE_BR: QPointF(s + w, s + h),
        }
        return positions.get(handle, QPointF())

    def _handle_scene_pos(self, handle: int) -> QPointF:
        local = self._handle_local_pos(handle)
        return self.sceneTransform().map(local)

    def _rotate_handle_local_pos(self) -> QPointF:
        """旋转按钮本地坐标（边框上方）。"""
        s = self.HANDLE_SIZE
        w = self._width
        return QPointF(s + w / 2, -self.ROTATE_OFFSET)

    def _rotate_handle_scene_pos(self) -> QPointF:
        return self.sceneTransform().map(self._rotate_handle_local_pos())

    # ---- 命中检测 ----
    def _hit_handle(self, scene_pos: QPointF) -> int:
        """返回命中的手柄编号，-1 表示未命中。"""
        if not self.isSelected():
            return -1
        # 先检查旋转按钮
        rp = self._rotate_handle_scene_pos()
        if (rp - scene_pos).manhattanLength() <= self.HANDLE_SIZE + 4:
            return self.HANDLE_ROTATE
        # 再检查 8 个缩放手柄
        for h in range(8):
            hp = self._handle_scene_pos(h)
            if (hp - scene_pos).manhattanLength() <= self.HANDLE_SIZE + 4:
                return h
        return -1

    # ---- 绘制 ----
    def paint(self, painter: QPainter, option, widget=None):
        s = self.HANDLE_SIZE
        w, h = self._width, self._height
        is_editing = (self is RotatableTextItem._current_editing_item)
        is_selected = self.isSelected() and not is_editing

        # 1. 绘制文字本体
        painter.save()
        text_rect = QRectF(s, s, w, h)
        painter.setClipRect(text_rect)
        doc = self.document()
        doc.setTextWidth(w)
        doc.setPlainText(self.toPlainText())
        doc.setDefaultFont(self.font())
        painter.translate(s, s)
        painter.setPen(QPen(QColor("#111111")))
        doc.drawContents(painter)

        # 编辑态：绘制闪烁光标
        if is_editing and self._cursor_visible:
            cursor = self.textCursor()
            pos = cursor.position()
            fm = painter.fontMetrics()
            text_before = self.toPlainText()[:pos]
            cx = fm.horizontalAdvance(text_before)
            cursor_y_top = 0
            cursor_y_bot = fm.height()
            painter.setClipping(False)
            painter.setPen(QPen(QColor("#111111"), 1))
            painter.drawLine(
                QPointF(cx, cursor_y_top),
                QPointF(cx, cursor_y_bot))
        painter.restore()

        # 2. 绘制边框（编辑态 / 选中态）
        if is_editing or is_selected:
            painter.save()
            frame = QRectF(s, s, w, h)
            pen = QPen(QColor("#2563EB"), 1.2 if is_editing else 1.5, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(QBrush(QColor(255, 255, 255, 30)))
            painter.drawRoundedRect(frame, 2, 2)

            # 选中态：手柄 + 旋转按钮
            if is_selected:
                for h_idx in range(8):
                    hp = self._handle_local_pos(h_idx)
                    painter.setPen(QPen(QColor("#2563EB"), 1.5))
                    painter.setBrush(QBrush(QColor("#FFFFFF")))
                    painter.drawRect(QRectF(
                        hp.x() - s / 2, hp.y() - s / 2, s, s))

                rp_local = self._rotate_handle_local_pos()
                painter.setPen(QPen(QColor("#2563EB"), 1.5, Qt.PenStyle.SolidLine))
                painter.drawLine(QPointF(s + w / 2, s), rp_local)

                painter.setPen(QPen(QColor("#2563EB"), 2))
                painter.setBrush(QBrush(QColor("#FFFFFF")))
                painter.drawEllipse(rp_local, self.HANDLE_SIZE, self.HANDLE_SIZE)
                painter.setPen(QPen(QColor("#2563EB"), 1.5))
                arc_rect = QRectF(rp_local.x() - 4, rp_local.y() - 4, 8, 8)
                painter.drawArc(arc_rect, 30 * 16, 300 * 16)
                angle = math.radians(330)
                ax = rp_local.x() + 4 * math.cos(angle)
                ay = rp_local.y() + 4 * math.sin(angle)
                painter.drawLine(QPointF(ax, ay),
                                 QPointF(ax + 3 * math.cos(angle + 0.4),
                                         ay + 3 * math.sin(angle + 0.4)))
                painter.drawLine(QPointF(ax, ay),
                                 QPointF(ax + 3 * math.cos(angle - 0.4),
                                         ay + 3 * math.sin(angle - 0.4)))
            painter.restore()

    # ---- 光标闪烁 ----
    def _blink_cursor(self):
        self._cursor_visible = not self._cursor_visible
        self.update()

    def start_cursor_blink(self):
        self._cursor_visible = True
        self._blink_timer.start(500)

    def stop_cursor_blink(self):
        self._blink_timer.stop()
        self._cursor_visible = True
        self.update()

    def shape(self):
        path = QPainterPath()
        br = self.boundingRect()
        path.addRect(br)
        # 包含旋转按钮
        rp = self._rotate_handle_local_pos()
        path.addEllipse(rp, self.HANDLE_SIZE + 4, self.HANDLE_SIZE + 4)
        return path

    # ---- 悬停光标 ----
    def hoverEvent(self, event):
        if not self.isSelected():
            self.unsetCursor()
            return
        handle = self._hit_handle(event.scenePos())
        if handle >= 0:
            cursor = self._cursor_for_handle(handle)
            self.setCursor(cursor)
        else:
            self.unsetCursor()

    def _cursor_for_handle(self, handle: int) -> Qt.CursorShape:
        if handle == self.HANDLE_ROTATE:
            return Qt.CursorShape.PointingHandCursor
        if handle in (self.HANDLE_L, self.HANDLE_R):
            return Qt.CursorShape.SizeHorCursor
        if handle in (self.HANDLE_T, self.HANDLE_B):
            return Qt.CursorShape.SizeVerCursor
        if handle in (self.HANDLE_TL, self.HANDLE_BR):
            return Qt.CursorShape.SizeAllCursor
        if handle in (self.HANDLE_TR, self.HANDLE_BL):
            return Qt.CursorShape.SizeAllCursor
        return Qt.CursorShape.ArrowCursor


class TextTool(BaseTool):
    """文字工具：点击画布创建可编辑文字，支持富文本格式，可拖动可旋转。

    交互流程：
    1. 点击空白处 → 创建新 RotatableTextItem，进入编辑态
    2. 点击已完成文字 → 选中并拖动（不再强制进入编辑）
    3. 双击已完成文字 → 进入编辑态（二次编辑）
    4. 编辑时显示格式工具栏
    5. 失焦时提交到撤销栈
    """

    def __init__(self, scene, view, editor_ref):
        super().__init__(scene, view, editor_ref)
        self._editing_item = None
        self._is_new_item = False
        self._old_text = ""
        self._old_font = None
        self._old_color = None
        # 状态
        self._mode = None  # "move" / "resize" / "rotate"
        self._move_items = []
        self._old_positions = []
        self._last_pos = None
        # 旋转
        self._rotate_item = None
        self._rotate_start_angle = 0.0
        self._rotate_start_rotation = 0.0
        self._rotate_center = QPointF()
        # 缩放
        self._resize_item = None
        self._resize_handle = -1
        self._resize_start_pos = QPointF()
        self._resize_start_w = 0.0
        self._resize_start_h = 0.0
        self._resize_start_font = 0.0
        self._resize_start_item_pos = QPointF()

    def mouse_press(self, event, scene_pos):
        bg = self._bg_item()

        items_here = [it for it in self.scene.items(scene_pos, Qt.ItemSelectionMode.IntersectsItemBoundingRect)
                      if it is not bg and isinstance(it, QGraphicsTextItem)]

        if items_here:
            item = items_here[0]
            # 如果文字正在编辑中，忽略
            if item.textInteractionFlags() & Qt.TextInteractionFlag.TextEditorInteraction:
                return

            # 如果是 RotatableTextItem 且已选中，检查是否命中手柄
            if isinstance(item, RotatableTextItem) and item.isSelected():
                handle = item._hit_handle(scene_pos)
                if handle == item.HANDLE_ROTATE:
                    self._mode = "rotate"
                    self._rotate_item = item
                    s = item.HANDLE_SIZE
                    local_center = QPointF(s + item.text_width() / 2,
                                           s + item.text_height() / 2)
                    self._rotate_center = item.sceneTransform().map(local_center)
                    self._rotate_start_angle = math.degrees(
                        math.atan2(scene_pos.y() - self._rotate_center.y(),
                                   scene_pos.x() - self._rotate_center.x()))
                    self._rotate_start_rotation = item.rotation_angle()
                    return
                elif handle >= 0:
                    # 缩放手柄
                    self._mode = "resize"
                    self._resize_item = item
                    self._resize_handle = handle
                    self._resize_start_pos = scene_pos
                    self._resize_start_w = item.text_width()
                    self._resize_start_h = item.text_height()
                    self._resize_start_font = item.font_size()
                    self._resize_start_item_pos = item.pos()
                    return

            # 否则：选中文字并准备拖动
            self.scene.clearSelection()
            item.setSelected(True)
            self._mode = "move"
            self._last_pos = scene_pos
            self._move_items = [item]
            self._old_positions = [item.pos()]
        else:
            # 点击空白处：提交当前编辑并创建新文字
            if self._editing_item is not None:
                self._commit_edit()
            item = RotatableTextItem("")
            item.setPos(scene_pos)
            color = self._text_color(event)
            item.setDefaultTextColor(color)
            font = QFont()
            font.setPointSize(max(8, int(self.editor_ref.pen_width) + 8))
            font.setFamily("微软雅黑")
            item.setFont(font)
            item.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
            self.scene.addItem(item)
            item.setFocus()
            self._begin_edit(item, scene_pos, is_new=True)

    def _begin_edit(self, item, scene_pos, is_new):
        """开始编辑文字项"""
        # 先清除其他正在编辑的 item
        if RotatableTextItem._current_editing_item is not None:
            old = RotatableTextItem._current_editing_item
            old.stop_cursor_blink()
            old.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
            old.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, False)
            old.update()

        self._editing_item = item
        self._is_new_item = is_new
        self._old_text = item.toPlainText()
        self._old_font = QFont(item.font())
        self._old_color = QColor(item.defaultTextColor())

        # 显示格式工具栏
        toolbar = getattr(self.editor_ref, "text_toolbar", None)
        if toolbar is not None and TextFormatToolbar is not None:
            toolbar.setTargetItem(item)
            toolbar.show()

        # 设置为当前编辑项（全局唯一）
        RotatableTextItem._current_editing_item = item
        item.setSelected(False)  # 编辑态立即清除选中态（避免编辑框+手柄同时显示）
        item.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, True)
        item.setFocus()

        # 光标定位到文本开头
        doc = item.document()
        doc.setTextWidth(item.text_width())
        cursor = item.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        item.setTextCursor(cursor)
        item.start_cursor_blink()
        item.update()

    def mouse_move(self, event, scene_pos):
        if self._mode == "move" and self._last_pos is not None:
            delta = scene_pos - self._last_pos
            for it in self._move_items:
                it.moveBy(delta.x(), delta.y())
            self.scene.invalidate()
            self._last_pos = scene_pos
        elif self._mode == "rotate" and self._rotate_item is not None:
            current_angle = math.degrees(
                math.atan2(scene_pos.y() - self._rotate_center.y(),
                           scene_pos.x() - self._rotate_center.x()))
            delta = current_angle - self._rotate_start_angle
            new_rotation = self._rotate_start_rotation + delta
            while new_rotation > 180:
                new_rotation -= 360
            while new_rotation < -180:
                new_rotation += 360
            self._rotate_item.set_rotation_angle(new_rotation)
            self.scene.invalidate()
        elif self._mode == "resize" and self._resize_item is not None:
            self._do_resize(scene_pos)

    def _do_resize(self, scene_pos):
        """根据当前手柄和鼠标位置调整文字框大小（文字与输入框等比缩放）。"""
        item = self._resize_item
        handle = self._resize_handle
        local_pos = item.sceneTransform().inverted()[0].map(scene_pos)
        s = item.HANDLE_SIZE
        frame_left = s
        frame_top = s
        frame_right = s + self._resize_start_w
        frame_bottom = s + self._resize_start_h

        if handle in (item.HANDLE_TL, item.HANDLE_L, item.HANDLE_BL):
            frame_left = local_pos.x()
        if handle in (item.HANDLE_TL, item.HANDLE_T, item.HANDLE_TR):
            frame_top = local_pos.y()
        if handle in (item.HANDLE_TR, item.HANDLE_R, item.HANDLE_BR):
            frame_right = local_pos.x()
        if handle in (item.HANDLE_BL, item.HANDLE_B, item.HANDLE_BR):
            frame_bottom = local_pos.y()

        new_w = max(30.0, frame_right - frame_left)
        new_h = max(20.0, frame_bottom - frame_top)

        # 计算各方向的缩放比例
        sx = new_w / self._resize_start_w
        sy = new_h / self._resize_start_h
        # 文字与输入框等比缩放：字号按几何平均，保证变形最小
        scale = math.sqrt(max(0.0001, sx * sy))
        new_font = max(6.0, self._resize_start_font * scale)

        # 调整位置（左上/上/右上/左/左下手柄需要移动 item）
        if handle in (item.HANDLE_TL, item.HANDLE_T, item.HANDLE_TR,
                      item.HANDLE_L, item.HANDLE_BL):
            dx_local = frame_left - s
            dy_local = frame_top - s
            transform = item.sceneTransform()
            dx_scene = transform.map(QPointF(dx_local, 0)).x() - transform.map(QPointF(0, 0)).x()
            dy_scene = transform.map(QPointF(0, dy_local)).y() - transform.map(QPointF(0, 0)).y()
            item.setPos(item.pos() + QPointF(dx_scene, dy_scene))

        item.set_text_size(new_w, new_h, new_font)
        self.scene.invalidate()

    def mouse_release(self, event, scene_pos):
        if self._mode == "move":
            new_positions = [it.pos() for it in self._move_items]
            if self._move_items and any(o != n for o, n in zip(self._old_positions, new_positions)):
                self.editor_ref.undo_stack.push(
                    MoveItemsCommand(self._move_items, self._old_positions, new_positions))
        elif self._mode == "resize":
            pass
        elif self._mode == "rotate":
            pass
        self._reset_drag()

    def _reset_drag(self):
        self._mode = None
        self._move_items = []
        self._old_positions = []
        self._last_pos = None
        self._rotate_item = None
        self._resize_item = None
        self._resize_handle = -1

    def deactivate(self):
        """工具切换时提交正在编辑的文字"""
        self._commit_edit()

    def double_click(self, event, scene_pos):
        """双击：进入文字二次编辑模式。"""
        bg = self._bg_item()
        items_here = [it for it in self.scene.items(scene_pos, Qt.ItemSelectionMode.IntersectsItemBoundingRect)
                      if it is not bg and isinstance(it, QGraphicsTextItem)]
        if items_here:
            item = items_here[0]
            # 提交当前编辑（如果有）
            if self._editing_item is not None and self._editing_item is not item:
                self._commit_edit()
            # 进入编辑模式
            self.scene.clearSelection()
            self._begin_edit(item, scene_pos, is_new=False)

    def _commit_edit(self):
        """提交编辑：将文字项加入撤销栈"""
        if self._editing_item is None:
            return
        item = self._editing_item
        new_text = item.toPlainText().strip()

        # 停止光标闪烁 + 清除全局编辑状态
        item.stop_cursor_blink()
        RotatableTextItem._current_editing_item = None

        # 隐藏格式工具栏
        toolbar = getattr(self.editor_ref, "text_toolbar", None)
        if toolbar is not None:
            toolbar.clearTarget()
            toolbar.hide()

        if not new_text:
            # 空文字：从场景中移除
            if item.scene() is self.scene:
                self.scene.removeItem(item)
        else:
            # 退出编辑模式，恢复为可选择+可拖动
            item.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, False)
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
            item.setSelected(True)
            item.update()

            if self._is_new_item:
                self.editor_ref.undo_stack.push(AddItemCommand(self.scene, item))
            else:
                if ModifyTextCommand is not None:
                    new_font = QFont(item.font())
                    new_color = QColor(item.defaultTextColor())
                    if new_text != self._old_text or new_font != self._old_font:
                        self.editor_ref.undo_stack.push(
                            ModifyTextCommand(item, self._old_text, new_text,
                                              self._old_font, new_font,
                                              self._old_color, new_color))

        self._editing_item = None
        self._is_new_item = False

    def _text_color(self, event) -> QColor:
        color = self._button_color(event)
        if not isinstance(color, QColor):
            color = QColor(color)
        return color


class _SelectToolBase(BaseTool):
    """选择工具基类：支持框选 / 移动 / 旋转 / 缩放。"""

    def __init__(self, scene, view, editor_ref):
        super().__init__(scene, view, editor_ref)
        self._mode = None  # "select" / "move" / "rotate" / "resize"
        self._start = None
        self._last_pos = None
        self._move_items = []
        self._old_positions = []
        # 旋转
        self._rotate_item = None
        self._rotate_start_angle = 0.0
        self._rotate_start_rotation = 0.0
        self._rotate_center = QPointF()
        # 缩放
        self._resize_item = None
        self._resize_handle = -1
        self._resize_start_pos = QPointF()
        self._resize_start_w = 0.0
        self._resize_start_h = 0.0
        self._resize_start_font = 0.0

    def mouse_press(self, event, scene_pos):
        bg = self._bg_item()

        # 如果有文字正在编辑，先停止其闪烁（TextTool 未激活时的兜底）
        editing = RotatableTextItem._current_editing_item
        if editing is not None:
            editing.stop_cursor_blink()
            RotatableTextItem._current_editing_item = None

        # 优先检查 RotatableTextItem 的手柄
        for it in self.scene.items(scene_pos, Qt.ItemSelectionMode.IntersectsItemBoundingRect):
            if it is bg:
                continue
            if isinstance(it, RotatableTextItem) and it.isSelected():
                handle = it._hit_handle(scene_pos)
                if handle == it.HANDLE_ROTATE:
                    self._mode = "rotate"
                    self._rotate_item = it
                    s = it.HANDLE_SIZE
                    local_center = QPointF(s + it.text_width() / 2,
                                           s + it.text_height() / 2)
                    self._rotate_center = it.sceneTransform().map(local_center)
                    self._rotate_start_angle = math.degrees(
                        math.atan2(scene_pos.y() - self._rotate_center.y(),
                                   scene_pos.x() - self._rotate_center.x()))
                    self._rotate_start_rotation = it.rotation_angle()
                    return
                elif handle >= 0:
                    self._mode = "resize"
                    self._resize_item = it
                    self._resize_handle = handle
                    self._resize_start_pos = scene_pos
                    self._resize_start_w = it.text_width()
                    self._resize_start_h = it.text_height()
                    self._resize_start_font = it.font_size()
                    return

        # 原有选择/移动逻辑
        here = [it for it in self.scene.items(scene_pos, Qt.ItemSelectionMode.IntersectsItemBoundingRect) if it is not bg]
        if here and here[0].isSelected():
            self._begin_move(scene_pos)
        elif here:
            for it in self.scene.items():
                if it is not bg:
                    it.setSelected(False)
            here[0].setSelected(True)
            self._begin_move(scene_pos)
        else:
            for it in self.scene.items():
                if it is not bg:
                    it.setSelected(False)
            self._mode = "select"
            self._start = scene_pos
            self._begin_select(scene_pos)

    def _begin_move(self, scene_pos):
        bg = self._bg_item()
        self._mode = "move"
        self._last_pos = scene_pos
        self._move_items = [it for it in self.scene.selectedItems() if it is not bg]
        self._old_positions = [it.pos() for it in self._move_items]

    def mouse_move(self, event, scene_pos):
        if self._mode == "move" and self._last_pos is not None:
            delta = scene_pos - self._last_pos
            for it in self._move_items:
                it.moveBy(delta.x(), delta.y())
            self.scene.invalidate()
            self._last_pos = scene_pos
        elif self._mode == "rotate" and self._rotate_item is not None:
            current_angle = math.degrees(
                math.atan2(scene_pos.y() - self._rotate_center.y(),
                           scene_pos.x() - self._rotate_center.x()))
            delta = current_angle - self._rotate_start_angle
            new_rotation = self._rotate_start_rotation + delta
            while new_rotation > 180:
                new_rotation -= 360
            while new_rotation < -180:
                new_rotation += 360
            self._rotate_item.set_rotation_angle(new_rotation)
            self.scene.invalidate()
        elif self._mode == "resize" and self._resize_item is not None:
            self._do_resize(scene_pos)
        elif self._mode == "select":
            self._update_select(scene_pos)

    def _do_resize(self, scene_pos):
        item = self._resize_item
        handle = self._resize_handle
        local_pos = item.sceneTransform().inverted()[0].map(scene_pos)
        s = item.HANDLE_SIZE
        frame_left = s
        frame_top = s
        frame_right = s + self._resize_start_w
        frame_bottom = s + self._resize_start_h

        if handle in (item.HANDLE_TL, item.HANDLE_L, item.HANDLE_BL):
            frame_left = local_pos.x()
        if handle in (item.HANDLE_TL, item.HANDLE_T, item.HANDLE_TR):
            frame_top = local_pos.y()
        if handle in (item.HANDLE_TR, item.HANDLE_R, item.HANDLE_BR):
            frame_right = local_pos.x()
        if handle in (item.HANDLE_BL, item.HANDLE_B, item.HANDLE_BR):
            frame_bottom = local_pos.y()

        new_w = max(30.0, frame_right - frame_left)
        new_h = max(20.0, frame_bottom - frame_top)
        scale = new_h / self._resize_start_h
        new_font = max(6.0, self._resize_start_font * scale)

        if handle in (item.HANDLE_TL, item.HANDLE_T, item.HANDLE_TR,
                      item.HANDLE_L, item.HANDLE_BL):
            dx_local = frame_left - s
            dy_local = frame_top - s
            transform = item.sceneTransform()
            dx_scene = transform.map(QPointF(dx_local, 0)).x() - transform.map(QPointF(0, 0)).x()
            dy_scene = transform.map(QPointF(0, dy_local)).y() - transform.map(QPointF(0, 0)).y()
            item.setPos(item.pos() + QPointF(dx_scene, dy_scene))

        item.set_text_size(new_w, new_h, new_font)
        self.scene.invalidate()

    def mouse_release(self, event, scene_pos):
        if self._mode == "move":
            new_positions = [it.pos() for it in self._move_items]
            if self._move_items and any(o != n for o, n in zip(self._old_positions, new_positions)):
                self.editor_ref.undo_stack.push(
                    MoveItemsCommand(self._move_items, self._old_positions, new_positions))
        elif self._mode in ("resize", "rotate"):
            pass
        elif self._mode == "select":
            self._finish_select(scene_pos)
        self._reset()

    def _reset(self):
        self._mode = None
        self._start = None
        self._last_pos = None
        self._move_items = []
        self._old_positions = []
        self._rotate_item = None
        self._resize_item = None
        self._resize_handle = -1

    def deactivate(self):
        self._reset()

    # 子类实现
    def _begin_select(self, scene_pos):
        pass

    def _update_select(self, scene_pos):
        pass

    def _finish_select(self, scene_pos):
        pass


class RectSelectTool(_SelectToolBase):
    """矩形选择：拖拽虚线矩形选区，可移动/删除选中项。"""

    def __init__(self, scene, view, editor_ref):
        super().__init__(scene, view, editor_ref)
        self._rect_item = None

    def _begin_select(self, scene_pos):
        pen = QPen(QColor("#000000"), 1, Qt.PenStyle.DashLine)
        self._rect_item = QGraphicsRectItem()
        self._rect_item.setPen(pen)
        self._rect_item.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        self._rect_item.setRect(QRectF(scene_pos, scene_pos))
        self.scene.addItem(self._rect_item)

    def _update_select(self, scene_pos):
        if self._rect_item is not None and self._start is not None:
            self._rect_item.setRect(QRectF(self._start, scene_pos).normalized())

    def _finish_select(self, scene_pos):
        if self._rect_item is None or self._start is None:
            return
        rect = QRectF(self._start, scene_pos).normalized()
        bg = self._bg_item()
        # 同时使用 Shape 和 BoundingRect 两种模式，确保细线条也能被选中
        selected_items = set()
        for mode in (Qt.ItemSelectionMode.IntersectsItemBoundingRect,
                     Qt.ItemSelectionMode.IntersectsItemShape):
            for it in self.scene.items(rect, mode):
                if it is not bg and it is not self._rect_item:
                    selected_items.add(it)
        for it in selected_items:
            it.setSelected(True)
        if self._rect_item.scene() is self.scene:
            self.scene.removeItem(self._rect_item)
        self._rect_item = None

    def deactivate(self):
        if self._rect_item is not None and self._rect_item.scene() is self.scene:
            self.scene.removeItem(self._rect_item)
        self._rect_item = None
        super().deactivate()


class FreeSelectTool(_SelectToolBase):
    """自由选择：QPainterPath 自由选区。"""

    def __init__(self, scene, view, editor_ref):
        super().__init__(scene, view, editor_ref)
        self._path = None
        self._path_item = None

    def _begin_select(self, scene_pos):
        self._path = QPainterPath(scene_pos)
        pen = QPen(QColor("#000000"), 1, Qt.PenStyle.DashLine)
        self._path_item = QGraphicsPathItem()
        self._path_item.setPen(pen)
        self._path_item.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        self._path_item.setPath(self._path)
        self.scene.addItem(self._path_item)

    def _update_select(self, scene_pos):
        if self._path is not None and self._path_item is not None:
            self._path.lineTo(scene_pos)
            self._path_item.setPath(self._path)

    def _finish_select(self, scene_pos):
        if self._path is None:
            return
        self._path.closeSubpath()
        if self._path_item is not None:
            self._path_item.setPath(self._path)
        bg = self._bg_item()
        # 同时使用 Shape 和 BoundingRect 两种模式
        selected_items = set()
        for mode in (Qt.ItemSelectionMode.IntersectsItemBoundingRect,
                     Qt.ItemSelectionMode.IntersectsItemShape):
            for it in self.scene.items(self._path, mode):
                if it is not bg and it is not self._path_item:
                    selected_items.add(it)
        for it in selected_items:
            it.setSelected(True)
        if self._path_item is not None and self._path_item.scene() is self.scene:
            self.scene.removeItem(self._path_item)
        self._path = None
        self._path_item = None

    def deactivate(self):
        if self._path_item is not None and self._path_item.scene() is self.scene:
            self.scene.removeItem(self._path_item)
        self._path = None
        self._path_item = None
        super().deactivate()


# ===========================================================================
# 形状工具基类
# ===========================================================================
class _ShapeToolBase(BaseTool):
    """形状工具基类：按下创建预览项，移动更新几何，释放提交到撤销栈。"""

    _fillable = False  # 子类覆写：是否支持填充

    def __init__(self, scene, view, editor_ref):
        super().__init__(scene, view, editor_ref)
        self._start = None
        self._end = None
        self._preview = None

    def mouse_press(self, event, scene_pos):
        self._start = scene_pos
        self._end = scene_pos
        self._preview = self._create_item(event)
        if self._preview is not None:
            self._style(self._preview, event)
            self._apply_geometry(self._preview, self._start, self._end, event)
            self.scene.addItem(self._preview)

    def mouse_move(self, event, scene_pos):
        if self._preview is None:
            return
        self._end = scene_pos
        self._apply_geometry(self._preview, self._start, self._end, event)

    def mouse_release(self, event, scene_pos):
        if self._preview is None:
            return
        self._end = scene_pos
        item = self._preview
        self._preview = None
        # 退化（单击）判定：移除预览且不提交
        d = math.hypot(self._end.x() - self._start.x(), self._end.y() - self._start.y())
        if d < 1.5:
            if item.scene() is self.scene:
                self.scene.removeItem(item)
            self._start = None
            self._end = None
            return
        self._apply_geometry(item, self._start, self._end, event)
        self._start = None
        self._end = None
        self.editor_ref.undo_stack.push(
            AddItemCommand(self.scene, item))

    def deactivate(self):
        if self._preview is not None and self._preview.scene() is self.scene:
            self.scene.removeItem(self._preview)
        self._preview = None
        self._start = None
        self._end = None

    def _style(self, item, event):
        pen = self._current_pen(event)
        item.setPen(pen)
        self._make_selectable(item)
        # QGraphicsLineItem 无 setBrush，需跳过；其余图形项设置填充
        if hasattr(item, "setBrush"):
            if self._fillable and getattr(self.editor_ref, "filled", False):
                item.setBrush(QBrush(pen.color()))
            else:
                item.setBrush(QBrush(Qt.BrushStyle.NoBrush))

    # 子类实现
    def _create_item(self, event):
        raise NotImplementedError

    def _apply_geometry(self, item, start, end, event):
        raise NotImplementedError


class LineTool(_ShapeToolBase):
    """直线：QGraphicsLineItem，Shift 锁 45°。"""
    _fillable = False

    def _create_item(self, event):
        return QGraphicsLineItem()

    def _apply_geometry(self, item, start, end, event):
        p = end
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            p = _snap_45(start, end)
        item.setLine(start.x(), start.y(), p.x(), p.y())


class CurveTool(_ShapeToolBase):
    """曲线：QPainterPath.cubicTo，QGraphicsPathItem。"""
    _fillable = False

    def _create_item(self, event):
        return QGraphicsPathItem()

    def _apply_geometry(self, item, start, end, event):
        item.setPath(_curve_path(start, end))


class RectTool(_ShapeToolBase):
    """矩形：QGraphicsRectItem，支持 filled。"""
    _fillable = True

    def _create_item(self, event):
        return QGraphicsRectItem()

    def _apply_geometry(self, item, start, end, event):
        item.setRect(_normalized_rect(start, end))


class RoundRectTool(_ShapeToolBase):
    """圆角矩形：QPainterPath.addRoundedRect，半径 10px。"""
    _fillable = True

    def _create_item(self, event):
        return QGraphicsPathItem()

    def _apply_geometry(self, item, start, end, event):
        path = QPainterPath()
        path.addRoundedRect(_normalized_rect(start, end), 10, 10)
        item.setPath(path)


class EllipseTool(_ShapeToolBase):
    """椭圆：QGraphicsEllipseItem，支持 filled。"""
    _fillable = True

    def _create_item(self, event):
        return QGraphicsEllipseItem()

    def _apply_geometry(self, item, start, end, event):
        item.setRect(_normalized_rect(start, end))


class TriangleTool(_ShapeToolBase):
    """三角形：QGraphicsPolygonItem，等腰。"""
    _fillable = True

    def _create_item(self, event):
        return QGraphicsPolygonItem()

    def _apply_geometry(self, item, start, end, event):
        item.setPolygon(_triangle_polygon(_normalized_rect(start, end)))


class StarTool(_ShapeToolBase):
    """星形：QGraphicsPolygonItem，五角星 10 顶点。"""
    _fillable = True

    def _create_item(self, event):
        return QGraphicsPolygonItem()

    def _apply_geometry(self, item, start, end, event):
        item.setPolygon(_star_polygon(_normalized_rect(start, end)))


class ArrowTool(_ShapeToolBase):
    """箭头：QGraphicsPathItem，主线 + 两条箭头线，箭头大小 15px。"""
    _fillable = False

    def _create_item(self, event):
        return QGraphicsPathItem()

    def _apply_geometry(self, item, start, end, event):
        item.setPath(_arrow_path(start, end, 15))


class CalloutTool(_ShapeToolBase):
    """对话框：QGraphicsPathItem，矩形 + 三角指针。"""
    _fillable = True

    def _create_item(self, event):
        return QGraphicsPathItem()

    def _apply_geometry(self, item, start, end, event):
        item.setPath(_callout_path(start, end))


class SquareTool(_ShapeToolBase):
    """正方形：强制宽高取 min。"""
    _fillable = True

    def _create_item(self, event):
        return QGraphicsRectItem()

    def _apply_geometry(self, item, start, end, event):
        r = _normalized_rect(start, end)
        side = min(r.width(), r.height())
        item.setRect(QRectF(r.left(), r.top(), side, side))


class CircleTool(_ShapeToolBase):
    """正圆：强制半径取 min(宽,高)/2。"""
    _fillable = True

    def _create_item(self, event):
        return QGraphicsEllipseItem()

    def _apply_geometry(self, item, start, end, event):
        r = _normalized_rect(start, end)
        side = min(r.width(), r.height())
        item.setRect(QRectF(r.left(), r.top(), side, side))


class DiamondTool(_ShapeToolBase):
    """菱形：4 顶点。"""
    _fillable = True

    def _create_item(self, event):
        return QGraphicsPolygonItem()

    def _apply_geometry(self, item, start, end, event):
        item.setPolygon(_diamond_polygon(_normalized_rect(start, end)))


class PentagonTool(_ShapeToolBase):
    """五边形：正 5 边形。"""
    _fillable = True

    def _create_item(self, event):
        return QGraphicsPolygonItem()

    def _apply_geometry(self, item, start, end, event):
        item.setPolygon(_regular_polygon(_normalized_rect(start, end), 5))


class HexagonTool(_ShapeToolBase):
    """六边形：正 6 边形。"""
    _fillable = True

    def _create_item(self, event):
        return QGraphicsPolygonItem()

    def _apply_geometry(self, item, start, end, event):
        item.setPolygon(_regular_polygon(_normalized_rect(start, end), 6))


class HeartTool(_ShapeToolBase):
    """爱心：贝塞尔曲线。"""
    _fillable = True

    def _create_item(self, event):
        return QGraphicsPathItem()

    def _apply_geometry(self, item, start, end, event):
        item.setPath(_heart_path(_normalized_rect(start, end)))


class RightTriangleTool(_ShapeToolBase):
    """直角三角形。"""
    _fillable = True

    def _create_item(self, event):
        return QGraphicsPolygonItem()

    def _apply_geometry(self, item, start, end, event):
        item.setPolygon(_right_triangle_polygon(_normalized_rect(start, end)))


class ParallelogramTool(_ShapeToolBase):
    """平行四边形。"""
    _fillable = True

    def _create_item(self, event):
        return QGraphicsPolygonItem()

    def _apply_geometry(self, item, start, end, event):
        item.setPolygon(_parallelogram_polygon(_normalized_rect(start, end)))


# ===========================================================================
# 工具注册表与工厂
# ===========================================================================
# 前端 drawing_board.py 使用 "rectangle" / "dialog" 命名，规范注册表使用
# "rect" / "callout"，此处通过别名映射兼容二者，注册表本身保持 18 个条目。
_TOOL_ALIASES = {
    "rectangle": "rect",
    "dialog": "callout",
}

TOOL_REGISTRY = {
    "pen": PenTool,
    "brush_pen": BrushPenTool,
    "writing_pen": WritingPenTool,
    "oil_brush": OilBrushTool,
    "crayon": CrayonTool,
    "marker": MarkerTool,
    "pencil": PencilTool,
    "watercolor": WatercolorTool,
    "airbrush": AirbrushTool,
    "brush": BrushTool,
    "eraser": EraserTool,
    "color_picker": ColorPickerTool,
    "fill": FillTool,
    "text": TextTool,
    "rect_select": RectSelectTool,
    "free_select": FreeSelectTool,
    "line": LineTool,
    "curve": CurveTool,
    "rect": RectTool,
    "round_rect": RoundRectTool,
    "ellipse": EllipseTool,
    "triangle": TriangleTool,
    "star": StarTool,
    "arrow": ArrowTool,
    "callout": CalloutTool,
    "square": SquareTool,
    "circle": CircleTool,
    "diamond": DiamondTool,
    "pentagon": PentagonTool,
    "hexagon": HexagonTool,
    "heart": HeartTool,
    "right_triangle": RightTriangleTool,
    "parallelogram": ParallelogramTool,
}


def create_tool(name, scene, view=None, editor_ref=None) -> BaseTool:
    """创建工具实例。

    兼容两种调用方式：
      create_tool(name, board)               —— board 即 DrawingBoardView
      create_tool(name, scene, view, editor) —— 显式传入
    """
    # 仅传 board（DrawingBoardView）的情形：从中提取 scene/view/editor_ref
    if view is None and editor_ref is None and hasattr(scene, "scene") and hasattr(scene, "view"):
        board = scene
        editor_ref = board
        scene = board.scene
        view = board.view
    key = _TOOL_ALIASES.get(name, name)
    cls = TOOL_REGISTRY.get(key)
    if cls is None:
        raise ValueError(f"Unknown tool: {name}")
    tool = cls(scene, view, editor_ref)
    tool.activate()
    return tool
