"""
Zhuibook 顶部 Tab 切换栏组件
用于主窗口顶部切换「📝 笔记」与「🖌 画板」视图。

设计要点：
- 两个 checkable QPushButton，通过 QButtonGroup 实现互斥（QPushButton 互斥的标准惯用法，
  等价于 QActionGroup 互斥语义）。
- 选中态：下划线 2px（主题 primary），文字 text_primary，13pt 加粗。
- 未选中态：文字 text_secondary，13pt 常规。
- 背景：toolbar_bg（次级背景层）；上方两角 8px 圆角，下方 0px。
- padding：12px 24px。
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QButtonGroup, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal

from .theme import THEMES, DEFAULT_THEME, get_top_tab_bar_qss


class TopTabBar(QWidget):
    # 参数为 "note" 或 "drawing"
    view_changed = pyqtSignal(str)

    def __init__(self, parent=None, theme_name: str = DEFAULT_THEME):
        super().__init__(parent)
        self.current_theme = theme_name
        self._current_view = "note"
        self._build_ui()
        self.apply_theme(theme_name)

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.container = QFrame()
        self.container.setObjectName("top_tab_container")
        cl = QHBoxLayout(self.container)
        cl.setContentsMargins(8, 0, 8, 0)
        cl.setSpacing(4)

        # 笔记 Tab
        self.note_btn = QPushButton("📝  笔记")
        self.note_btn.setCheckable(True)
        self.note_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.note_btn.setObjectName("tab_note")

        # 画板 Tab
        self.drawing_btn = QPushButton("🖌  画板")
        self.drawing_btn.setCheckable(True)
        self.drawing_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.drawing_btn.setObjectName("tab_drawing")

        # 互斥分组（QButtonGroup 是 QPushButton checkable 互斥的标准做法）
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._group.addButton(self.note_btn, 0)
        self._group.addButton(self.drawing_btn, 1)
        self._group.idClicked.connect(self._on_group_clicked)

        cl.addWidget(self.note_btn)
        cl.addWidget(self.drawing_btn)
        cl.addStretch(1)

        root.addWidget(self.container)

        # 默认选中笔记
        self.note_btn.setChecked(True)

    def _on_group_clicked(self, btn_id: int):
        view = "note" if btn_id == 0 else "drawing"
        self._current_view = view
        self._refresh_tab_styles()
        self.view_changed.emit(view)

    def set_current(self, view: str):
        """设置当前视图（'note' / 'drawing'），触发 view_changed 信号。"""
        if view not in ("note", "drawing"):
            return
        self._current_view = view
        target = self.note_btn if view == "note" else self.drawing_btn
        if not target.isChecked():
            target.setChecked(True)
        self._refresh_tab_styles()
        self.view_changed.emit(view)

    def apply_theme(self, theme_name: str):
        """应用主题，刷新所有子组件样式。"""
        self.current_theme = theme_name
        t = THEMES[theme_name]
        qss = get_top_tab_bar_qss(t)
        self.container.setStyleSheet(qss["container"])
        # 选中 / 未选中样式分别应用
        self.note_btn.setStyleSheet(qss["tab_checked"] if self.note_btn.isChecked() else qss["tab_unchecked"])
        self.drawing_btn.setStyleSheet(qss["tab_checked"] if self.drawing_btn.isChecked() else qss["tab_unchecked"])

    def _refresh_tab_styles(self):
        """根据当前选中态刷新两个 Tab 的样式（切换后调用）。"""
        t = THEMES[self.current_theme]
        qss = get_top_tab_bar_qss(t)
        self.note_btn.setStyleSheet(qss["tab_checked"] if self.note_btn.isChecked() else qss["tab_unchecked"])
        self.drawing_btn.setStyleSheet(qss["tab_checked"] if self.drawing_btn.isChecked() else qss["tab_unchecked"])
