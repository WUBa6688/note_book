"""
Zhuibook 画板自定义工具光标生成器。

为绘图工具生成简易 QPixmap 光标，未覆盖的工具返回 None（使用系统光标）。
所有图标使用深色 #2C2C2C 绘制，开启抗锯齿。
"""
from __future__ import annotations

import math
import random
from typing import Optional

from PyQt6.QtCore import Qt, QPoint, QPointF
from PyQt6.QtGui import (
    QPixmap, QPainter, QColor, QPen, QBrush, QCursor, QPolygon,
)

_ICON_COLOR = "#2C2C2C"
_ERASER_COLOR = "#FFB6C1"


def _new_painter(pixmap: QPixmap) -> QPainter:
    """创建开启抗锯齿的 QPainter。"""
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    return painter


def _make_pen(color: str = _ICON_COLOR, width: int = 2) -> QPen:
    pen = QPen(QColor(color), width)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    return pen


def _pen_cursor(size: int) -> QCursor:
    """画笔：矩形笔头 8,4,16,20 + 三角笔尖，热点 (4,28)。"""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = _new_painter(pm)
    p.setPen(_make_pen(_ICON_COLOR, 2))
    p.setBrush(QBrush(QColor(_ICON_COLOR)))
    # 笔头矩形 (x=8, y=4, w=16, h=20)
    p.drawRect(8, 4, 16, 20)
    # 三角笔尖（从矩形底部向下延伸）
    triangle = QPolygon([
        QPoint(8, 24),
        QPoint(24, 24),
        QPoint(16, 32),
    ])
    p.drawPolygon(triangle)
    p.end()
    return QCursor(pm, 4, 28)


def _airbrush_cursor(size: int) -> QCursor:
    """喷枪：中心圆 + 周围散点，热点 (16,16)。"""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = _new_painter(pm)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(QColor(_ICON_COLOR)))
    # 中心圆
    p.drawEllipse(QPointF(16, 16), 4, 4)
    # 周围散点（固定种子保证每次一致）
    rng = random.Random(42)
    for _ in range(12):
        angle = rng.random() * 2 * math.pi
        r = 8 + rng.random() * 6
        x = 16 + r * math.cos(angle)
        y = 16 + r * math.sin(angle)
        p.drawEllipse(QPointF(x, y), 1.2, 1.2)
    p.end()
    return QCursor(pm, 16, 16)


def _brush_cursor(size: int) -> QCursor:
    """刷子：圆角矩形刷头 + 手柄，热点 (16,28)。"""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = _new_painter(pm)
    p.setPen(_make_pen(_ICON_COLOR, 2))
    p.setBrush(QBrush(QColor(_ICON_COLOR)))
    # 圆角矩形刷头（下方）
    p.drawRoundedRect(8, 20, 16, 8, 3, 3)
    # 手柄（从刷头向上）
    p.drawRect(14, 4, 4, 16)
    p.end()
    return QCursor(pm, 16, 28)


def _eraser_cursor(size: int) -> QCursor:
    """橡皮：圆角矩形（粉色 #FFB6C1 为主）+ 深色标签，热点 (16,28)。"""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = _new_painter(pm)
    p.setPen(_make_pen(_ICON_COLOR, 2))
    # 圆角矩形（粉色为主）
    p.setBrush(QBrush(QColor(_ERASER_COLOR)))
    p.drawRoundedRect(6, 18, 20, 10, 4, 4)
    # 上方深色小标签
    p.setBrush(QBrush(QColor(_ICON_COLOR)))
    p.drawRect(12, 4, 8, 14)
    p.end()
    return QCursor(pm, 16, 28)


def _fill_cursor(size: int) -> QCursor:
    """填充：梯形桶身 + 把手，热点 (6,28)。"""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = _new_painter(pm)
    p.setPen(_make_pen(_ICON_COLOR, 2))
    p.setBrush(QBrush(QColor(_ICON_COLOR)))
    # 梯形桶身
    bucket = QPolygon([
        QPoint(6, 10),
        QPoint(24, 10),
        QPoint(22, 24),
        QPoint(8, 24),
    ])
    p.drawPolygon(bucket)
    # 把手（顶部半圆弧）
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawArc(8, 4, 14, 12, 0, 180 * 16)
    p.end()
    return QCursor(pm, 6, 28)


def create_tool_cursor(tool_name: str, size: int = 32) -> Optional[QCursor]:
    """根据工具名生成自定义光标。

    返回 None 表示使用系统光标。
    """
    if tool_name == "pen":
        return _pen_cursor(size)
    if tool_name == "airbrush":
        return _airbrush_cursor(size)
    if tool_name == "brush":
        return _brush_cursor(size)
    if tool_name == "eraser":
        return _eraser_cursor(size)
    if tool_name == "fill":
        return _fill_cursor(size)
    return None
