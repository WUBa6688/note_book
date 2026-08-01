"""
Zhuibook 画板折叠分组面板组件。

标题栏左侧有 3px 宽的主题色条装饰，右侧显示 ▼/▶ 箭头。
标题使用纯文字，去掉 emoji 以确保跨平台渲染一致。
折叠时高度仅约 32px（标题栏），展开时自适应内容。
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPainter, QColor, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QFrame, QSizePolicy, QLayout,
)


class _TitleButton(QPushButton):
    """带左侧色条的标题按钮。"""

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self._text = text
        self._collapsed = False
        self._accent_color = QColor("#5A9E7E")
        self.setObjectName("collapsible_section_title")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFlat(True)
        self.setFixedHeight(32)

    def set_collapsed(self, collapsed: bool):
        self._collapsed = collapsed
        self.setText(self._display_text())
        self.update()

    def set_accent_color(self, color: str):
        self._accent_color = QColor(color)
        self.update()

    def minimumSizeHint(self) -> QSize:
        fm = self.fontMetrics()
        arrow = "▶" if self._collapsed else "▼"
        w = fm.horizontalAdvance(arrow + " " + self._text) + 32
        h = 32
        return QSize(w, h)

    def sizeHint(self) -> QSize:
        return self.minimumSizeHint()

    def _display_text(self) -> str:
        arrow = "▶" if self._collapsed else "▼"
        return f"{arrow}  {self._text}"

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 左侧色条（3px 宽，标题栏高度的 60%）
        bar_h = int(self.height() * 0.6)
        bar_y = (self.height() - bar_h) // 2
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._accent_color)
        p.drawRoundedRect(4, bar_y, 3, bar_h, 1, 1)

        # 绘制文字
        p.setPen(self.palette().windowText().color())
        font = self.font()
        font.setWeight(QFont.Weight.DemiBold)
        font.setPointSize(10)
        p.setFont(font)
        arrow = "▶" if self._collapsed else "▼"
        text = f"{arrow}  {self._text}"
        text_rect = self.rect().adjusted(12, 0, 8, 0)
        p.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)

        p.end()


class CollapsibleSection(QFrame):
    """可折叠的分组面板。"""

    collapsedChanged = pyqtSignal(bool)

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("collapsible_section")
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

        self._collapsed = False
        self._title = title

        # 主布局：标题栏 + 内容区
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 标题栏（可点击切换）
        self._title_btn = _TitleButton(title)
        self._title_btn.clicked.connect(self.toggle)
        outer.addWidget(self._title_btn)

        # 内容区
        self._content = QWidget()
        self._content.setObjectName("collapsible_section_content")
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(8, 4, 8, 8)
        self._content_layout.setSpacing(4)
        outer.addWidget(self._content)

    def addWidget(self, widget: QWidget):
        self._content_layout.addWidget(widget)

    def addLayout(self, layout: QLayout):
        self._content_layout.addLayout(layout)

    def setCollapsed(self, collapsed: bool):
        if collapsed == self._collapsed:
            return
        self._collapsed = collapsed
        self._content.setVisible(not collapsed)
        self._title_btn.set_collapsed(collapsed)
        self.collapsedChanged.emit(collapsed)

    def isCollapsed(self) -> bool:
        return self._collapsed

    def toggle(self):
        self.setCollapsed(not self._collapsed)

    def apply_theme(self, t: dict):
        card_bg = t.get("card_bg", "#FFFFFF")
        border = t.get("border", "#CCCCCC")
        text_primary = t.get("text_primary", "#222222")
        list_hover_bg = t.get("list_hover_bg", "#EEEEEE")
        primary = t.get("primary", "#5A9E7E")
        self.setStyleSheet(f"""
            QFrame#collapsible_section {{
                background: {card_bg};
                border: 1px solid {border};
                border-radius: 8px;
            }}
            QWidget#collapsible_section_content {{
                background: transparent;
            }}
        """)
        self._title_btn.set_accent_color(primary)
        self._title_btn.setStyleSheet(f"""
            QPushButton#collapsible_section_title {{
                background: transparent;
                border: none;
                border-radius: 8px;
                text-align: left;
                padding: 0px;
                color: {text_primary};
            }}
            QPushButton#collapsible_section_title:hover {{
                background: {list_hover_bg};
            }}
        """)
