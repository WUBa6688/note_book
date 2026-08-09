"""
Zhuibook 画板工具图标生成器。

程序化生成 20×20 透明背景 QPixmap，简洁线条风格（2px 描边）。
不依赖外部图片资源，保证跨平台一致性。
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QPointF, QRectF, QLineF
from PyQt6.QtGui import (
    QPixmap, QPainter, QPen, QBrush, QColor, QFont, QPainterPath,
    QPolygonF,
)

_FONT_FAMILY = "Microsoft YaHei UI, Microsoft YaHei, PingFang SC, Segoe UI, Arial"


class DrawingIcon:
    """程序化生成工具图标（20×20 QPixmap，透明背景）。"""

    @staticmethod
    def create(name: str, color: str = "#2E3630") -> QPixmap:
        pm = QPixmap(20, 20)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(color), 1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        dispatch = {
            "pen": DrawingIcon._draw_pen,
            "brush_pen": DrawingIcon._draw_brush_pen,
            "writing_pen": DrawingIcon._draw_writing_pen,
            "airbrush": DrawingIcon._draw_airbrush,
            "oil_brush": DrawingIcon._draw_oil_brush,
            "crayon": DrawingIcon._draw_crayon,
            "marker": DrawingIcon._draw_marker,
            "pencil": DrawingIcon._draw_pencil,
            "watercolor": DrawingIcon._draw_watercolor,
            "brush": DrawingIcon._draw_brush,
            "eraser": DrawingIcon._draw_eraser,
            "color_picker": DrawingIcon._draw_color_picker,
            "fill": DrawingIcon._draw_fill,
            "text": DrawingIcon._draw_text,
            "rect_select": DrawingIcon._draw_rect_select,
            "free_select": DrawingIcon._draw_free_select,
            "line": DrawingIcon._draw_line,
            "curve": DrawingIcon._draw_curve,
            "rectangle": DrawingIcon._draw_rectangle,
            "round_rect": DrawingIcon._draw_round_rect,
            "ellipse": DrawingIcon._draw_ellipse,
            "triangle": DrawingIcon._draw_triangle,
            "square": DrawingIcon._draw_square,
            "circle": DrawingIcon._draw_circle,
            "diamond": DrawingIcon._draw_diamond,
            "pentagon": DrawingIcon._draw_pentagon,
            "hexagon": DrawingIcon._draw_hexagon,
            "star": DrawingIcon._draw_star,
            "arrow": DrawingIcon._draw_arrow,
            "dialog": DrawingIcon._draw_dialog,
            "heart": DrawingIcon._draw_heart,
            "right_triangle": DrawingIcon._draw_right_triangle,
            "parallelogram": DrawingIcon._draw_parallelogram,
            "undo": DrawingIcon._draw_undo,
            "redo": DrawingIcon._draw_redo,
            "clear": DrawingIcon._draw_clear,
            "save_file": DrawingIcon._draw_save_file,
            "insert_note": DrawingIcon._draw_insert_note,
            "zoom_in": DrawingIcon._draw_zoom_in,
            "zoom_out": DrawingIcon._draw_zoom_out,
            "zoom_100": DrawingIcon._draw_zoom_100,
            "zoom_fit": DrawingIcon._draw_zoom_fit,
            "copy": DrawingIcon._draw_copy,
            "cut": DrawingIcon._draw_cut,
            "paste": DrawingIcon._draw_paste,
            "select_all": DrawingIcon._draw_select_all,
            "delete": DrawingIcon._draw_delete,
            "custom_color": DrawingIcon._draw_custom_color,
            "fill_toggle": DrawingIcon._draw_fill_toggle,
            "wheel_zoom": DrawingIcon._draw_wheel_zoom,
        }
        func = dispatch.get(name)
        if func is not None:
            func(p, color)
        else:
            # 未注册的工具名 → 默认画一个小圆点图标（避免显示空白）
            p.setBrush(QBrush(QColor(color)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(10, 10), 4, 4)
        p.end()
        return pm

    # ---- 绘制工具 ----

    @staticmethod
    def _draw_pen(p: QPainter, color: str):
        # 斜线 + 笔尖三角
        p.drawLine(QPointF(3, 17), QPointF(13, 7))
        path = QPainterPath()
        path.moveTo(13, 7)
        path.lineTo(15, 5)
        path.lineTo(17, 7)
        path.lineTo(15, 9)
        path.closeSubpath()
        p.setBrush(QBrush(QColor(color)))
        p.drawPath(path)

    @staticmethod
    def _draw_airbrush(p: QPainter, color: str):
        # 喷雾圆点 pattern
        c = QColor(color)
        p.setBrush(QBrush(c))
        p.setPen(Qt.PenStyle.NoPen)
        import random
        rng = random.Random(42)
        for _ in range(12):
            cx = 4 + rng.randint(0, 12)
            cy = 3 + rng.randint(0, 12)
            r = rng.uniform(0.5, 1.5)
            p.drawEllipse(QPointF(cx, cy), r, r)

    @staticmethod
    def _draw_brush(p: QPainter, color: str):
        # 粗笔触弧线
        pen = p.pen()
        pen.setWidthF(3.0)
        p.setPen(pen)
        path = QPainterPath()
        path.moveTo(4, 16)
        path.cubicTo(7, 8, 12, 8, 16, 4)
        p.drawPath(path)

    @staticmethod
    def _draw_eraser(p: QPainter, color: str):
        # 橡皮块
        rect = QRectF(3, 6, 14, 8)
        p.drawRoundedRect(rect, 2, 2)
        p.drawLine(QPointF(3, 10), QPointF(17, 10))

    @staticmethod
    def _draw_color_picker(p: QPainter, color: str):
        # 吸管
        p.drawLine(QPointF(4, 16), QPointF(14, 6))
        path = QPainterPath()
        path.moveTo(14, 6)
        path.lineTo(16, 4)
        path.lineTo(17, 5)
        path.lineTo(15, 7)
        path.closeSubpath()
        p.setBrush(QBrush(QColor(color)))
        p.drawPath(path)

    @staticmethod
    def _draw_fill(p: QPainter, color: str):
        # 油漆桶 + 液滴
        path = QPainterPath()
        path.moveTo(5, 12)
        path.lineTo(10, 7)
        path.lineTo(15, 12)
        path.lineTo(11, 16)
        path.closeSubpath()
        p.drawPath(path)
        p.setBrush(QBrush(QColor(color)))
        p.drawEllipse(QPointF(15, 16), 1.5, 2)

    @staticmethod
    def _draw_text(p: QPainter, color: str):
        font = QFont(_FONT_FAMILY, 11, QFont.Weight.Bold)
        p.setFont(font)
        p.setPen(QPen(QColor(color)))
        p.drawText(QRectF(0, 0, 20, 20), Qt.AlignmentFlag.AlignCenter, "T")

    @staticmethod
    def _draw_rect_select(p: QPainter, color: str):
        pen = p.pen()
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setWidthF(1.5)
        p.setPen(pen)
        p.drawRect(QRectF(3, 3, 14, 14))

    @staticmethod
    def _draw_free_select(p: QPainter, color: str):
        pen = p.pen()
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setWidthF(1.5)
        p.setPen(pen)
        path = QPainterPath()
        path.moveTo(3, 10)
        path.cubicTo(5, 3, 12, 3, 17, 8)
        path.cubicTo(15, 17, 6, 17, 3, 10)
        p.drawPath(path)

    # ---- 形状工具 ----

    @staticmethod
    def _draw_line(p: QPainter, color: str):
        p.drawLine(QPointF(4, 16), QPointF(16, 4))

    @staticmethod
    def _draw_curve(p: QPainter, color: str):
        path = QPainterPath()
        path.moveTo(3, 16)
        path.cubicTo(7, 4, 13, 16, 17, 4)
        p.drawPath(path)

    @staticmethod
    def _draw_rectangle(p: QPainter, color: str):
        p.drawRect(QRectF(3, 5, 14, 10))

    @staticmethod
    def _draw_round_rect(p: QPainter, color: str):
        p.drawRoundedRect(QRectF(3, 5, 14, 10), 3, 3)

    @staticmethod
    def _draw_ellipse(p: QPainter, color: str):
        p.drawEllipse(QPointF(10, 10), 7, 5)

    @staticmethod
    def _draw_triangle(p: QPainter, color: str):
        poly = QPolygonF([QPointF(10, 3), QPointF(17, 16), QPointF(3, 16)])
        p.drawPolygon(poly)

    @staticmethod
    def _draw_star(p: QPainter, color: str):
        import math
        cx, cy, r1, r2 = 10, 10, 7, 3
        poly = QPolygonF()
        for i in range(10):
            angle = math.pi / 5 * i - math.pi / 2
            r = r1 if i % 2 == 0 else r2
            poly.append(QPointF(cx + r * math.cos(angle), cy + r * math.sin(angle)))
        p.drawPolygon(poly)

    @staticmethod
    def _draw_arrow(p: QPainter, color: str):
        p.drawLine(QPointF(3, 16), QPointF(16, 4))
        p.drawLine(QPointF(16, 4), QPointF(10, 4))
        p.drawLine(QPointF(16, 4), QPointF(16, 10))

    @staticmethod
    def _draw_dialog(p: QPainter, color: str):
        path = QPainterPath()
        path.moveTo(3, 4)
        path.lineTo(17, 4)
        path.lineTo(17, 12)
        path.lineTo(11, 12)
        path.lineTo(8, 16)
        path.lineTo(8, 12)
        path.lineTo(3, 12)
        path.closeSubpath()
        p.drawPath(path)

    # ---- 操作工具 ----

    @staticmethod
    def _draw_undo(p: QPainter, color: str):
        # 向左弯曲箭头（U形）
        pen = p.pen()
        p.drawArc(QRectF(6, 3, 8, 10), 90*16, 180*16)
        p.drawLine(QPointF(14, 13), QPointF(14, 8))
        p.drawLine(QPointF(14, 8), QPointF(11, 8))
        p.drawLine(QPointF(14, 8), QPointF(14, 11))
        # 箭头头
        poly = QPolygonF([QPointF(5, 13), QPointF(3, 9), QPointF(7, 10)])
        old_brush = p.brush()
        p.setBrush(QBrush(QColor(color)))
        p.drawPolygon(poly)
        p.setBrush(old_brush)

    @staticmethod
    def _draw_redo(p: QPainter, color: str):
        # 向右弯曲箭头（U形）
        p.drawArc(QRectF(6, 3, 8, 10), 270*16, -180*16)
        p.drawLine(QPointF(6, 13), QPointF(6, 8))
        p.drawLine(QPointF(6, 8), QPointF(9, 8))
        p.drawLine(QPointF(6, 8), QPointF(6, 11))
        poly = QPolygonF([QPointF(15, 13), QPointF(17, 9), QPointF(13, 10)])
        old_brush = p.brush()
        p.setBrush(QBrush(QColor(color)))
        p.drawPolygon(poly)
        p.setBrush(old_brush)

    @staticmethod
    def _draw_clear(p: QPainter, color: str):
        # 垃圾桶（简化版：三条竖线 + 横盖）
        p.drawLine(QPointF(4, 5), QPointF(16, 5))
        p.drawRect(QRectF(5, 5, 10, 12))
        p.drawLine(QPointF(8, 7), QPointF(8, 15))
        p.drawLine(QPointF(10, 7), QPointF(10, 15))
        p.drawLine(QPointF(12, 7), QPointF(12, 15))
        p.drawLine(QPointF(7, 3), QPointF(13, 3))
        p.drawLine(QPointF(7, 3), QPointF(7, 5))
        p.drawLine(QPointF(13, 3), QPointF(13, 5))

    @staticmethod
    def _draw_save_file(p: QPainter, color: str):
        # 软盘
        p.drawRect(QRectF(3, 3, 14, 14))
        p.setBrush(QBrush(QColor(color)))
        p.drawRect(QRectF(11, 3, 6, 5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(QRectF(6, 11, 8, 6))

    @staticmethod
    def _draw_insert_note(p: QPainter, color: str):
        # 文档 + 箭头
        path = QPainterPath()
        path.moveTo(4, 3)
        path.lineTo(11, 3)
        path.lineTo(13, 5)
        path.lineTo(13, 11)
        path.lineTo(4, 11)
        path.closeSubpath()
        p.drawPath(path)
        p.drawLine(QPointF(7, 16), QPointF(16, 16))
        p.drawLine(QPointF(14, 14), QPointF(16, 16))
        p.drawLine(QPointF(16, 16), QPointF(14, 18))

    @staticmethod
    def _draw_zoom_in(p: QPainter, color: str):
        p.drawEllipse(QPointF(8, 8), 5, 5)
        p.drawLine(QPointF(12, 12), QPointF(16, 16))
        p.drawLine(QPointF(6, 8), QPointF(10, 8))

    @staticmethod
    def _draw_zoom_out(p: QPainter, color: str):
        p.drawEllipse(QPointF(8, 8), 5, 5)
        p.drawLine(QPointF(12, 12), QPointF(16, 16))
        p.drawLine(QPointF(6, 8), QPointF(10, 8))

    @staticmethod
    def _draw_zoom_100(p: QPainter, color: str):
        font = QFont(_FONT_FAMILY, 7, QFont.Weight.Bold)
        p.setFont(font)
        p.setPen(QPen(QColor(color)))
        p.drawText(QRectF(0, 0, 20, 20), Qt.AlignmentFlag.AlignCenter, "1:1")

    @staticmethod
    def _draw_zoom_fit(p: QPainter, color: str):
        # 四角箭头
        corners = [
            (3, 3, 1, 0, 0, 1),
            (17, 3, -1, 0, 0, 1),
            (3, 17, 1, 0, 0, -1),
            (17, 17, -1, 0, 0, -1),
        ]
        for cx, cy, dx1, dy1, dx2, dy2 in corners:
            p.drawLine(QPointF(cx, cy), QPointF(cx + dx1 * 3, cy + dy1 * 3))
            p.drawLine(QPointF(cx, cy), QPointF(cx + dx2 * 3, cy + dy2 * 3))

    @staticmethod
    def _draw_copy(p: QPainter, color: str):
        # 两个重叠矩形
        p.drawRect(QRectF(4, 6, 9, 10))
        p.drawRect(QRectF(7, 3, 9, 10))

    @staticmethod
    def _draw_cut(p: QPainter, color: str):
        # 剪刀
        p.drawEllipse(QPointF(5, 5), 2, 2)
        p.drawEllipse(QPointF(5, 15), 2, 2)
        p.drawLine(QPointF(7, 6), QPointF(16, 14))
        p.drawLine(QPointF(7, 14), QPointF(16, 6))

    @staticmethod
    def _draw_paste(p: QPainter, color: str):
        # 剪贴板
        p.drawRoundedRect(QRectF(4, 4, 12, 14), 2, 2)
        p.setBrush(QBrush(QColor(color)))
        p.drawRect(QRectF(7, 2, 6, 3))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(QPointF(7, 10), QPointF(13, 10))
        p.drawLine(QPointF(7, 13), QPointF(13, 13))

    @staticmethod
    def _draw_select_all(p: QPainter, color: str):
        pen = p.pen()
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setWidthF(1.5)
        p.setPen(pen)
        p.drawRect(QRectF(2, 2, 16, 16))

    @staticmethod
    def _draw_delete(p: QPainter, color: str):
        # X
        p.drawLine(QPointF(5, 5), QPointF(15, 15))
        p.drawLine(QPointF(15, 5), QPointF(5, 15))

    @staticmethod
    def _draw_custom_color(p: QPainter, color: str):
        # 调色盘
        p.drawEllipse(QPointF(10, 10), 7, 7)
        p.setBrush(QBrush(QColor(color)))
        p.drawEllipse(QPointF(14, 6), 1.5, 1.5)
        p.setBrush(Qt.BrushStyle.NoBrush)

    @staticmethod
    def _draw_fill_toggle(p: QPainter, color: str):
        # 左半实心 + 右半空心
        p.drawRect(QRectF(3, 5, 14, 10))
        p.setBrush(QBrush(QColor(color)))
        p.drawRect(QRectF(3, 5, 7, 10))
        p.setBrush(Qt.BrushStyle.NoBrush)

    @staticmethod
    def _draw_wheel_zoom(p: QPainter, color: str):
        # 鼠标滚轮
        p.drawRoundedRect(QRectF(6, 3, 8, 14), 4, 4)
        p.setBrush(QBrush(QColor(color)))
        p.drawRect(QRectF(9, 5, 2, 6))
        p.setBrush(Qt.BrushStyle.NoBrush)

    # ---- 画笔变体 ----

    @staticmethod
    def _draw_brush_pen(p: QPainter, color: str):
        # 毛笔：粗笔触 + 尖头
        pen = p.pen()
        pen.setWidthF(4.0)
        p.setPen(pen)
        path = QPainterPath()
        path.moveTo(5, 16)
        path.cubicTo(8, 8, 12, 5, 16, 3)
        p.drawPath(path)
        # 尖头
        p.setBrush(QBrush(QColor(color)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(15, 3), 1.5, 1.5)

    @staticmethod
    def _draw_writing_pen(p: QPainter, color: str):
        # 书写笔：流畅曲线
        pen = p.pen()
        pen.setWidthF(2.0)
        p.setPen(pen)
        path = QPainterPath()
        path.moveTo(3, 15)
        path.cubicTo(6, 10, 10, 6, 17, 4)
        p.drawPath(path)

    @staticmethod
    def _draw_oil_brush(p: QPainter, color: str):
        # 油画笔：厚重笔触
        pen = p.pen()
        pen.setWidthF(5.0)
        p.setPen(pen)
        path = QPainterPath()
        path.moveTo(4, 16)
        path.cubicTo(10, 12, 14, 8, 17, 4)
        p.drawPath(path)
        # 油彩点
        p.setBrush(QBrush(QColor(color)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(5, 15), 2, 2)
        p.drawEllipse(QPointF(16, 5), 1.5, 1.5)

    @staticmethod
    def _draw_crayon(p: QPainter, color: str):
        # 蜡笔：粗短线条
        pen = p.pen()
        pen.setWidthF(4.0)
        pen.setCapStyle(Qt.PenCapStyle.SquareCap)
        p.setPen(pen)
        p.drawLine(QPointF(4, 16), QPointF(16, 6))

    @staticmethod
    def _draw_marker(p: QPainter, color: str):
        # 记号笔：粗直线 + 斜角
        pen = p.pen()
        pen.setWidthF(3.0)
        p.setPen(pen)
        p.drawLine(QPointF(3, 15), QPointF(15, 5))
        # 斜角尖端
        path = QPainterPath()
        path.moveTo(15, 5)
        path.lineTo(17, 3)
        path.lineTo(18, 4)
        path.lineTo(16, 6)
        path.closeSubpath()
        p.setBrush(QBrush(QColor(color)))
        p.drawPath(path)

    @staticmethod
    def _draw_pencil(p: QPainter, color: str):
        # 铅笔：经典形状
        p.drawLine(QPointF(3, 17), QPointF(14, 6))
        # 笔尖
        path = QPainterPath()
        path.moveTo(14, 6)
        path.lineTo(17, 3)
        path.lineTo(18, 5)
        path.lineTo(15, 8)
        path.closeSubpath()
        p.setBrush(QBrush(QColor(color)))
        p.drawPath(path)
        # 橡皮擦
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(QPointF(3, 17), QPointF(5, 15))

    @staticmethod
    def _draw_watercolor(p: QPainter, color: str):
        # 水彩笔：扩散笔触
        pen = p.pen()
        pen.setWidthF(2.5)
        p.setPen(pen)
        path = QPainterPath()
        path.moveTo(4, 16)
        path.cubicTo(7, 10, 12, 7, 17, 4)
        p.drawPath(path)
        # 水彩扩散点
        c = QColor(color)
        p.setBrush(QBrush(c))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(8, 13), 1, 1)
        p.drawEllipse(QPointF(12, 9), 1.2, 1.2)
        p.drawEllipse(QPointF(15, 6), 0.8, 0.8)

    # ---- 扩展形状 ----

    @staticmethod
    def _draw_square(p: QPainter, color: str):
        # 正方形
        p.drawRect(QRectF(4, 4, 12, 12))

    @staticmethod
    def _draw_circle(p: QPainter, color: str):
        # 正圆
        p.drawEllipse(QPointF(10, 10), 7, 7)

    @staticmethod
    def _draw_diamond(p: QPainter, color: str):
        # 菱形
        poly = QPolygonF([QPointF(10, 3), QPointF(17, 10), QPointF(10, 17), QPointF(3, 10)])
        p.drawPolygon(poly)

    @staticmethod
    def _draw_pentagon(p: QPainter, color: str):
        # 五边形
        import math
        cx, cy, r = 10, 10, 7
        poly = QPolygonF()
        for i in range(5):
            angle = -math.pi / 2 + 2 * math.pi / 5 * i
            poly.append(QPointF(cx + r * math.cos(angle), cy + r * math.sin(angle)))
        p.drawPolygon(poly)

    @staticmethod
    def _draw_hexagon(p: QPainter, color: str):
        # 六边形
        import math
        cx, cy, r = 10, 10, 7
        poly = QPolygonF()
        for i in range(6):
            angle = math.pi / 3 * i
            poly.append(QPointF(cx + r * math.cos(angle), cy + r * math.sin(angle)))
        p.drawPolygon(poly)

    @staticmethod
    def _draw_heart(p: QPainter, color: str):
        # 爱心
        path = QPainterPath()
        path.moveTo(10, 16)
        path.cubicTo(3, 10, 5, 3, 10, 7)
        path.cubicTo(15, 3, 17, 10, 10, 16)
        p.drawPath(path)

    @staticmethod
    def _draw_right_triangle(p: QPainter, color: str):
        # 直角三角形
        poly = QPolygonF([QPointF(4, 4), QPointF(4, 16), QPointF(16, 16)])
        p.drawPolygon(poly)

    @staticmethod
    def _draw_parallelogram(p: QPainter, color: str):
        # 平行四边形
        poly = QPolygonF([QPointF(5, 4), QPointF(17, 4), QPointF(15, 16), QPointF(3, 16)])
        p.drawPolygon(poly)
