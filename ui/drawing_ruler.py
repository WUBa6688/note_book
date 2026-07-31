"""
Zhuibook 画板比例尺组件。

HorizontalRuler：高度 24px，画布上方。
VerticalRuler：宽度 32px，画布左侧。

刻度规则：
  - 主刻度每 100px（带数字标签）
  - 次刻度每 20px
  - 小刻度每 5px
  - 缩放 >200% 时刻度细分，<50% 时刻度合并
鼠标移动时绘制蓝色虚线指示线（颜色用 primary）。
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QFont, QPaintEvent,
)
from PyQt6.QtWidgets import QWidget

# 字体回退链：微软雅黑 UI → 微软雅黑 → PingFang SC → Segoe UI → Arial
_FONT_FAMILY = "Microsoft YaHei UI, Microsoft YaHei, PingFang SC, Segoe UI, Arial"


class _RulerBase(QWidget):
    """比例尺公共逻辑基类。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._zoom = 1.0
        self._canvas_dim = 800  # 画布对应方向尺寸
        self._mouse_pos: Optional[int] = None
        self._bg = "#F0F5ED"
        self._text_primary = "#2E3630"
        self._text_secondary = "#828E86"
        self._primary = "#5A9E7E"
        self._font = QFont(_FONT_FAMILY, 8)

    # ---- 子类覆写 ----
    def _set_dim(self, d: int):
        self._canvas_dim = max(1, d)
        self.update()

    def _tick_steps(self):
        """根据缩放返回 (主刻度, 次刻度, 小刻度) 的场景像素步长。"""
        z = self._zoom
        if z >= 2.0:
            # 缩放 >200%：细分
            return 50, 10, 5
        if z < 0.5:
            # 缩放 <50%：合并
            return 200, 100, 20
        return 100, 20, 5

    def apply_theme(self, t: dict):
        self._bg = t.get("toolbar_bg", "#F0F5ED")
        self._text_primary = t.get("text_primary", "#222222")
        self._text_secondary = t.get("text_secondary", "#888888")
        self._primary = t.get("primary", "#5A9E7E")
        self.update()


class HorizontalRuler(_RulerBase):
    """水平比例尺（画布上方）。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(24)

    def setZoom(self, zoom: float):
        self._zoom = max(0.01, zoom)
        self.update()

    def setMousePos(self, x: int):
        self._mouse_pos = x
        self.update()

    def setCanvasWidth(self, w: int):
        self._set_dim(w)

    def paintEvent(self, event: QPaintEvent):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w = self.width()
        h = self.height()
        # 背景
        p.fillRect(0, 0, w, h, QColor(self._bg))
        main, minor, small = self._tick_steps()
        step_main = main * self._zoom
        step_minor = minor * self._zoom
        step_small = small * self._zoom
        p.setFont(self._font)

        pen_main = QPen(QColor(self._text_primary), 1)
        pen_minor = QPen(QColor(self._text_secondary), 1)
        pen_small = QPen(QColor(self._text_secondary), 1)

        # 小刻度
        p.setPen(pen_small)
        x = 0.0
        while x <= w + 1:
            p.drawLine(int(x), h - 4, int(x), h)
            x += step_small
        # 次刻度
        p.setPen(pen_minor)
        x = 0.0
        while x <= w + 1:
            p.drawLine(int(x), h - 8, int(x), h)
            x += step_minor
        # 主刻度 + 数字标签
        p.setPen(pen_main)
        x = 0.0
        val = 0
        while x <= w + 1:
            p.drawLine(int(x), h - 12, int(x), h)
            if main >= 50 and int(x) + 2 < w:
                p.drawText(int(x) + 2, 12, str(val))
            val += main
            x += step_main

        # 鼠标指示线（蓝色虚线，颜色用 primary）
        if self._mouse_pos is not None:
            p.setPen(QPen(QColor(self._primary), 1, Qt.PenStyle.DashLine))
            p.drawLine(self._mouse_pos, 0, self._mouse_pos, h)
        p.end()


class VerticalRuler(_RulerBase):
    """垂直比例尺（画布左侧）。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(32)

    def setZoom(self, zoom: float):
        self._zoom = max(0.01, zoom)
        self.update()

    def setMousePos(self, y: int):
        self._mouse_pos = y
        self.update()

    def setCanvasHeight(self, h: int):
        self._set_dim(h)

    def paintEvent(self, event: QPaintEvent):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w = self.width()
        h = self.height()
        # 背景
        p.fillRect(0, 0, w, h, QColor(self._bg))
        main, minor, small = self._tick_steps()
        step_main = main * self._zoom
        step_minor = minor * self._zoom
        step_small = small * self._zoom
        p.setFont(self._font)

        pen_main = QPen(QColor(self._text_primary), 1)
        pen_minor = QPen(QColor(self._text_secondary), 1)
        pen_small = QPen(QColor(self._text_secondary), 1)

        # 小刻度
        p.setPen(pen_small)
        y = 0.0
        while y <= h + 1:
            p.drawLine(w - 4, int(y), w, int(y))
            y += step_small
        # 次刻度
        p.setPen(pen_minor)
        y = 0.0
        while y <= h + 1:
            p.drawLine(w - 8, int(y), w, int(y))
            y += step_minor
        # 主刻度 + 数字标签（旋转 -90°，自下而上阅读）
        p.setPen(pen_main)
        y = 0.0
        val = 0
        while y <= h + 1:
            p.drawLine(w - 12, int(y), w, int(y))
            if main >= 50 and int(y) + 4 < h:
                p.save()
                p.translate(10, int(y) + 2)
                p.rotate(-90)
                p.drawText(0, 0, str(val))
                p.restore()
            val += main
            y += step_main

        # 鼠标指示线
        if self._mouse_pos is not None:
            p.setPen(QPen(QColor(self._primary), 1, Qt.PenStyle.DashLine))
            p.drawLine(0, self._mouse_pos, w, self._mouse_pos)
        p.end()
