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

from PyQt6.QtCore import Qt, QObject, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import (
    QColor, QPen, QBrush, QPixmap, QPainter, QPainterPath, QImage, QFont,
    QPolygonF,
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
        angle = -math.pi / 2 + i * math.pi / 5  # 从顶部开始
        r = outer if i % 2 == 0 else inner
        verts.append(QPointF(cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return QPolygonF(verts)


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


class TextTool(BaseTool):
    """文字工具：点击画布创建可编辑文字，支持富文本格式，可拖动。

    交互流程：
    1. 点击空白处 → 创建新 QGraphicsTextItem，进入编辑态
    2. 点击已有文字 → 进入编辑态（二次编辑）
    3. 编辑时显示格式工具栏
    4. 失焦时提交到撤销栈
    """

    def __init__(self, scene, view, editor_ref):
        super().__init__(scene, view, editor_ref)
        self._editing_item = None
        self._is_new_item = False
        self._old_text = ""
        self._old_font = None
        self._old_color = None

    def mouse_press(self, event, scene_pos):
        # 检查是否点击了已有的文字项
        bg = self._bg_item()
        items_here = [it for it in self.scene.items(scene_pos)
                      if it is not bg and isinstance(it, QGraphicsTextItem)]

        if items_here:
            # 二次编辑已有文字
            item = items_here[0]
            self._begin_edit(item, scene_pos, is_new=False)
        else:
            # 创建新文字
            item = QGraphicsTextItem("")
            item.setPos(scene_pos)
            # 使用当前颜色
            color = self._text_color(event)
            item.setDefaultTextColor(color)
            # 默认字体
            font = QFont()
            font.setPointSize(max(8, int(self.editor_ref.pen_width) + 8))
            font.setFamily("微软雅黑")
            item.setFont(font)
            # 设置可交互编辑 + 可拖动 + 可选择
            item.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, True)
            self.scene.addItem(item)
            # 焦点到文字项
            item.setFocus()
            self._begin_edit(item, scene_pos, is_new=True)

    def _begin_edit(self, item, scene_pos, is_new):
        """开始编辑文字项"""
        self._editing_item = item
        self._is_new_item = is_new
        self._old_text = item.toPlainText()
        self._old_font = QFont(item.font())
        self._old_color = QColor(item.defaultTextColor())

        # 显示格式工具栏（如果前端已创建）
        toolbar = getattr(self.editor_ref, "text_toolbar", None)
        if toolbar is not None and TextFormatToolbar is not None:
            toolbar.setTargetItem(item)
            toolbar.show()

        # 设置文字项为可编辑模式
        item.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
        item.setFocus()

    def mouse_move(self, event, scene_pos):
        pass

    def mouse_release(self, event, scene_pos):
        pass

    def deactivate(self):
        """工具切换时提交正在编辑的文字"""
        self._commit_edit()

    def _commit_edit(self):
        """提交编辑：将文字项加入撤销栈"""
        if self._editing_item is None:
            return
        item = self._editing_item
        new_text = item.toPlainText().strip()

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

            if self._is_new_item:
                # 新文字：push AddItemCommand（幂等 redo，项已在场景中不会重复添加）
                self.editor_ref.undo_stack.push(AddItemCommand(self.scene, item))
            else:
                # 修改已有文字：push ModifyTextCommand
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
    """选择工具基类：支持“框选/自由选区”与“拖动移动选中项”两种模式。"""

    def __init__(self, scene, view, editor_ref):
        super().__init__(scene, view, editor_ref)
        self._mode = None  # "select" / "move"
        self._start = None
        self._last_pos = None
        self._move_items = []
        self._old_positions = []

    def mouse_press(self, event, scene_pos):
        bg = self._bg_item()
        # 使用 BoundingRect 模式，即使细线条也能被检测到
        here = [it for it in self.scene.items(scene_pos, Qt.ItemSelectionMode.IntersectsItemBoundingRect) if it is not bg]
        if here and here[0].isSelected():
            # 点中已选中项 -> 移动当前选中集合
            self._begin_move(scene_pos)
        elif here:
            # 点中未选中项 -> 仅选中它并准备移动
            for it in self.scene.items():
                if it is not bg:
                    it.setSelected(False)
            here[0].setSelected(True)
            self._begin_move(scene_pos)
        else:
            # 空白处 -> 开始框选
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
        if self._mode == "move":
            if self._last_pos is not None:
                delta = scene_pos - self._last_pos
                for it in self._move_items:
                    it.moveBy(delta.x(), delta.y())
                self._last_pos = scene_pos
        elif self._mode == "select":
            self._update_select(scene_pos)

    def mouse_release(self, event, scene_pos):
        if self._mode == "move":
            new_positions = [it.pos() for it in self._move_items]
            if self._move_items and any(o != n for o, n in zip(self._old_positions, new_positions)):
                self.editor_ref.undo_stack.push(
                    MoveItemsCommand(self._move_items, self._old_positions, new_positions))
        elif self._mode == "select":
            self._finish_select(scene_pos)
        self._reset()

    def _reset(self):
        self._mode = None
        self._start = None
        self._last_pos = None
        self._move_items = []
        self._old_positions = []

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
