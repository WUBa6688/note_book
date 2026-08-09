"""
Zhuibook 画板富文本格式工具栏。

工具栏固定在画布上方（非浮动），当 setTargetItem 被调用时显示，clearTarget 时隐藏。
控件：QFontComboBox（字体）、QSpinBox（字号 1-99，默认 12）、
B/I/U/S 四个可勾选按钮、左/中/右对齐按钮组、文字颜色按钮。
格式变化实时应用到目标 QGraphicsTextItem。
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QTextOption
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QFontComboBox, QSpinBox, QToolButton,
    QButtonGroup, QPushButton, QColorDialog, QGraphicsTextItem,
)

# 字体回退链
_FONT_FAMILY = "Microsoft YaHei UI, Microsoft YaHei, PingFang SC, Segoe UI, Arial"


class TextFormatToolbar(QFrame):
    """富文本格式工具栏。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("text_format_toolbar")
        self._target: Optional[QGraphicsTextItem] = None
        # 防止同步控件状态时反向触发格式应用
        self._updating = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        # 字体选择
        self.font_combo = QFontComboBox()
        self.font_combo.setCurrentFont(QFont(_FONT_FAMILY))
        self.font_combo.setToolTip("字体")
        self.font_combo.currentFontChanged.connect(self._on_font_changed)
        layout.addWidget(self.font_combo)

        # 字号
        self.size_spin = QSpinBox()
        self.size_spin.setRange(1, 99)
        self.size_spin.setValue(12)
        self.size_spin.setFixedWidth(56)
        self.size_spin.setToolTip("字号")
        self.size_spin.valueChanged.connect(self._on_size_changed)
        layout.addWidget(self.size_spin)

        # B / I / U / S
        self.bold_btn = self._make_toggle("B", "加粗 (Ctrl+B)")
        f = QFont(); f.setBold(True); self.bold_btn.setFont(f)
        self.bold_btn.toggled.connect(lambda _c: self._apply_font())

        self.italic_btn = self._make_toggle("I", "斜体 (Ctrl+I)")
        f = QFont(); f.setItalic(True); self.italic_btn.setFont(f)
        self.italic_btn.toggled.connect(lambda _c: self._apply_font())

        self.underline_btn = self._make_toggle("U", "下划线 (Ctrl+U)")
        f = QFont(); f.setUnderline(True); self.underline_btn.setFont(f)
        self.underline_btn.toggled.connect(lambda _c: self._apply_font())

        self.strike_btn = self._make_toggle("S", "删除线")
        f = QFont(); f.setStrikeOut(True); self.strike_btn.setFont(f)
        self.strike_btn.toggled.connect(lambda _c: self._apply_font())

        layout.addWidget(self.bold_btn)
        layout.addWidget(self.italic_btn)
        layout.addWidget(self.underline_btn)
        layout.addWidget(self.strike_btn)

        # 对齐按钮组（互斥）
        self.align_group = QButtonGroup(self)
        self.align_group.setExclusive(True)
        self.align_left = self._make_toggle("左", "左对齐")
        self.align_center = self._make_toggle("中", "居中对齐")
        self.align_right = self._make_toggle("右", "右对齐")
        self.align_group.addButton(self.align_left, 0)
        self.align_group.addButton(self.align_center, 1)
        self.align_group.addButton(self.align_right, 2)
        self.align_left.setChecked(True)
        self.align_group.idClicked.connect(self._on_align_changed)
        layout.addWidget(self.align_left)
        layout.addWidget(self.align_center)
        layout.addWidget(self.align_right)

        # 文字颜色
        self.color_btn = QPushButton("A")
        self.color_btn.setObjectName("text_color_btn")
        self.color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.color_btn.setToolTip("文字颜色")
        self.color_btn.setFixedWidth(32)
        f = QFont(); f.setBold(True); self.color_btn.setFont(f)
        self.color_btn.clicked.connect(self._on_color_clicked)
        layout.addWidget(self.color_btn)

        layout.addStretch(1)

        # 初始隐藏
        self.setVisible(False)

    # ------------------------------------------------------------------
    # 公共 API
    # ------------------------------------------------------------------
    def setTargetItem(self, item: QGraphicsTextItem):
        """设置目标文字项并显示工具栏，同步当前格式到控件。"""
        self._target = item
        if item is None:
            self.clearTarget()
            return
        self._updating = True
        font = item.font()
        self.font_combo.setCurrentFont(font)
        if hasattr(item, "font_size"):
            size = int(round(item.font_size()))
        else:
            size = font.pointSize() if font.pointSize() > 0 else 12
        self.size_spin.setValue(max(1, size))
        self.bold_btn.setChecked(font.bold())
        self.italic_btn.setChecked(font.italic())
        self.underline_btn.setChecked(font.underline())
        self.strike_btn.setChecked(font.strikeOut())
        # 同步对齐态
        try:
            align = item.document().defaultTextOption().alignment()
            if align & Qt.AlignmentFlag.AlignCenter:
                self.align_center.setChecked(True)
            elif align & Qt.AlignmentFlag.AlignRight:
                self.align_right.setChecked(True)
            else:
                self.align_left.setChecked(True)
        except Exception:
            self.align_left.setChecked(True)
        self._updating = False
        self.setVisible(True)

    def clearTarget(self):
        """清除目标并隐藏工具栏。"""
        self._target = None
        self.setVisible(False)

    def apply_theme(self, t: dict):
        card_bg = t.get("card_bg", "#FFFFFF")
        border = t.get("border", "#CCCCCC")
        text_primary = t.get("text_primary", "#222222")
        primary = t.get("primary", "#5A9E7E")
        list_hover_bg = t.get("list_hover_bg", "#EEEEEE")
        selection_bg = t.get("selection_bg", "#DDDDDD")
        self.setStyleSheet(f"""
            QFrame#text_format_toolbar {{
                background: {card_bg};
                border: 1px solid {border};
                border-radius: 8px;
            }}
            QFontComboBox, QSpinBox {{
                background: {card_bg};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 2px 6px;
                color: {text_primary};
                font-size: 12px;
            }}
            QFontComboBox:hover, QSpinBox:hover {{
                border: 1px solid {primary};
            }}
            QToolButton {{
                background: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 12px;
                color: {text_primary};
            }}
            QToolButton:hover {{
                background: {list_hover_bg};
                border-color: {border};
            }}
            QToolButton:checked {{
                background: {primary};
                color: #FFFFFF;
                border: 1px solid {primary};
            }}
            QPushButton#text_color_btn {{
                background: {card_bg};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 4px 8px;
                color: {text_primary};
                font-weight: bold;
            }}
            QPushButton#text_color_btn:hover {{
                background: {selection_bg};
                border-color: {primary};
            }}
        """)

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------
    def _make_toggle(self, text: str, tip: str) -> QToolButton:
        btn = QToolButton()
        btn.setText(text)
        btn.setCheckable(True)
        btn.setToolTip(tip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

    def _on_font_changed(self, _font: QFont):
        self._apply_font()

    def _on_size_changed(self, _value: int):
        self._apply_font()

    def _apply_font(self):
        if self._target is None or self._updating:
            return
        font = QFont(self.font_combo.currentFont())
        font.setPointSize(max(1, self.size_spin.value()))
        font.setBold(self.bold_btn.isChecked())
        font.setItalic(self.italic_btn.isChecked())
        font.setUnderline(self.underline_btn.isChecked())
        font.setStrikeOut(self.strike_btn.isChecked())
        if hasattr(self._target, "set_text_size") and hasattr(self._target, "text_width"):
            self._target.set_text_size(
                self._target.text_width(),
                self._target.text_height(),
                float(self.size_spin.value()),
            )
        else:
            self._target.setFont(font)
        self._target.setFont(font)
        self._target.update()

    def _on_align_changed(self, idx: int):
        if self._target is None or self._updating:
            return
        align_map = {
            0: Qt.AlignmentFlag.AlignLeft,
            1: Qt.AlignmentFlag.AlignCenter,
            2: Qt.AlignmentFlag.AlignRight,
        }
        try:
            doc = self._target.document()
            opt = doc.defaultTextOption()
            opt.setAlignment(align_map.get(idx, Qt.AlignmentFlag.AlignLeft))
            doc.setDefaultTextOption(opt)
        except Exception:
            pass

    def _on_color_clicked(self):
        if self._target is None:
            return
        initial = self._target.defaultTextColor()
        color = QColorDialog.getColor(initial, self, "选择文字颜色")
        if color.isValid():
            self._target.setDefaultTextColor(color)
