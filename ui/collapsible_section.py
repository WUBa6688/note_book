"""
Zhuibook 画板折叠分组面板组件。

标题栏可点击切换 ▼/▶，内容区包含时显示、折叠时隐藏。
折叠时高度仅约 36px（标题栏），展开时自适应内容。
背景 card_bg，圆角 10px，边框 border，标题栏 hover 时背景变 list_hover_bg。
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QFrame, QSizePolicy, QLayout,
)


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
        self._title_btn = QPushButton(self._display_text())
        self._title_btn.setObjectName("collapsible_section_title")
        self._title_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._title_btn.setFlat(True)
        self._title_btn.setFixedHeight(36)
        self._title_btn.setCheckable(False)
        self._title_btn.clicked.connect(self.toggle)
        outer.addWidget(self._title_btn)

        # 内容区
        self._content = QWidget()
        self._content.setObjectName("collapsible_section_content")
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(8, 4, 8, 8)
        self._content_layout.setSpacing(4)
        outer.addWidget(self._content)

    # ------------------------------------------------------------------
    # 公共 API
    # ------------------------------------------------------------------
    def addWidget(self, widget: QWidget):
        """添加控件到内容区。"""
        self._content_layout.addWidget(widget)

    def addLayout(self, layout: QLayout):
        """添加布局到内容区。"""
        self._content_layout.addLayout(layout)

    def setCollapsed(self, collapsed: bool):
        if collapsed == self._collapsed:
            return
        self._collapsed = collapsed
        self._content.setVisible(not collapsed)
        self._title_btn.setText(self._display_text())
        self.collapsedChanged.emit(collapsed)

    def isCollapsed(self) -> bool:
        return self._collapsed

    def toggle(self):
        self.setCollapsed(not self._collapsed)

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------
    def _display_text(self) -> str:
        return ("▶ " if self._collapsed else "▼ ") + self._title

    def apply_theme(self, t: dict):
        """应用主题。t 为 theme.py 中的主题字典。"""
        card_bg = t.get("card_bg", "#FFFFFF")
        border = t.get("border", "#CCCCCC")
        text_primary = t.get("text_primary", "#222222")
        list_hover_bg = t.get("list_hover_bg", "#EEEEEE")
        primary = t.get("primary", "#5A9E7E")
        self.setStyleSheet(f"""
            QFrame#collapsible_section {{
                background: {card_bg};
                border: 1px solid {border};
                border-radius: 10px;
            }}
            QPushButton#collapsible_section_title {{
                background: transparent;
                border: none;
                border-radius: 10px;
                text-align: left;
                padding: 6px 12px;
                color: {text_primary};
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton#collapsible_section_title:hover {{
                background: {list_hover_bg};
                color: {primary};
            }}
            QWidget#collapsible_section_content {{
                background: transparent;
            }}
        """)
