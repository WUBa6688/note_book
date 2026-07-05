import re
from typing import List
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QTextCursor,
    QKeySequence, QShortcut, QTextBlockFormat, QTextDocument
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLineEdit, QLabel,
    QComboBox, QToolButton, QTextEdit, QSizePolicy
)
from core.database import Category


def _fmt(**kwargs):
    f = QTextCharFormat()
    for k, v in kwargs.items():
        if k == "foreground":
            f.setForeground(QColor(v))
        elif k == "background":
            f.setBackground(QColor(v))
        elif k == "bold":
            f.setFontWeight(QFont.Weight.Bold if v else QFont.Weight.Normal)
        elif k == "italic":
            f.setFontItalic(v)
        elif k == "strike":
            f.setFontStrikeOut(v)
        elif k == "size":
            f.setFontPointSize(v)
        elif k == "family":
            f.setFontFamilies([v])
        elif k == "underline":
            f.setFontUnderline(v)
        elif k == "letter_spacing_pct":
            if v == 0:
                continue
            font = f.font()
            font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, v)
            f.setFont(font)
        elif k == "font":
            f.setFont(v)
    return f


HIDDEN_LETTER_SPACING = -95  # 兼容保留，不再实际用于 marker 隐藏


_marker_hidden = None
_marker_visible = None
_marker_codeblock_fence = None
_code_inline_content = None
_codeblock_content = None
_block_quote_fmt = None
_ul_marker = None
_ol_marker = None
_link_text_fmt = None
_link_url_hidden = None


def _init_formats():
    global _marker_hidden, _marker_visible, _marker_codeblock_fence
    global _code_inline_content, _codeblock_content, _block_quote_fmt
    global _ul_marker, _ol_marker, _link_text_fmt, _link_url_hidden

    # marker 隐藏：仅前景完全透明（保留字符占位宽度，避免后续文字跳动/溢出左边距）
    _marker_hidden = QTextCharFormat()
    _marker_hidden.setForeground(QColor(0, 0, 0, 0))
    # 保留默认字距与字号 → 文字位置固定，和 Typora 行为一致

    _marker_visible = _fmt(foreground="#aab0b7", letter_spacing_pct=0)

    _marker_codeblock_fence = _fmt(foreground="#6a737d", family="Consolas", size=11, letter_spacing_pct=0)

    _code_inline_content = _fmt(
        foreground="#d6336c", background="#f6f8fa", family="Consolas", size=13, letter_spacing_pct=0
    )

    _codeblock_content = _fmt(
        foreground="#24292e", background="#f6f8fa", family="Consolas", size=12, letter_spacing_pct=0
    )

    _block_quote_fmt = _fmt(foreground="#37474f", background="#f0f7ff", letter_spacing_pct=0)

    _ul_marker = _fmt(foreground="#1a73e8", bold=True, letter_spacing_pct=0)
    _ol_marker = _fmt(foreground="#1a73e8", bold=True, letter_spacing_pct=0)

    _link_text_fmt = _fmt(foreground="#1a73e8", underline=True, letter_spacing_pct=0)

    # URL 部分隐藏：同样只设前景透明，保留占位宽度
    _link_url_hidden = QTextCharFormat()
    _link_url_hidden.setForeground(QColor(0, 0, 0, 0))


RE_INLINE_CODE = re.compile(r"`([^`\n]+?)`")
RE_BOLD_ITALIC = re.compile(r"\*\*\*([^*]+?)\*\*\*")
RE_BOLD = re.compile(r"\*\*([^*]+?)\*\*")
RE_ITALIC = re.compile(r"(?<!\*)\*([^*\s][^*]*?)\*(?!\*)")
RE_STRIKE = re.compile(r"~~([^~]+?)~~")
RE_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


class MarkdownMixedHighlighter(QSyntaxHighlighter):
    def __init__(self, document, editor_ref):
        super().__init__(document)
        self.editor_ref = editor_ref
        self.active_block = -1
        self.active_col = -1
        self.block_meta = {}
        _init_formats()

        self._h1_title = _fmt(foreground="#1a73e8", bold=True, size=22, letter_spacing_pct=0)
        self._h2_title = _fmt(foreground="#1a73e8", bold=True, size=18, letter_spacing_pct=0)
        self._h3_title = _fmt(foreground="#1a73e8", bold=True, size=16, letter_spacing_pct=0)
        self._h4_title = _fmt(foreground="#202124", bold=True, size=14, letter_spacing_pct=0)
        self._h5_title = _fmt(foreground="#202124", bold=True, size=13, letter_spacing_pct=0)
        self._h6_title = _fmt(foreground="#6a737d", bold=True, size=12, letter_spacing_pct=0)
        self._bold_fmt = _fmt(bold=True, letter_spacing_pct=0)
        self._italic_fmt = _fmt(italic=True, letter_spacing_pct=0)
        self._bold_italic_fmt = _fmt(bold=True, italic=True, letter_spacing_pct=0)
        self._strike_fmt = _fmt(strike=True, letter_spacing_pct=0)

    def set_active_cursor(self, block_number: int, col: int):
        self.active_block = block_number
        self.active_col = col

    def _near(self, m_start, m_end) -> bool:
        if self.currentBlock().blockNumber() != self.active_block:
            return False
        pos = self.active_col
        return (m_start - 1) <= pos <= (m_end + 1)

    def _apply_marker(self, start: int, length: int, near: bool):
        if near:
            self.setFormat(start, length, _marker_visible)
        else:
            self.setFormat(start, length, _marker_hidden)

    def highlightBlock(self, text: str):
        block_num = self.currentBlock().blockNumber()
        prev_state = self.previousBlockState()

        if prev_state == 1:
            self.setFormat(0, len(text), _codeblock_content)
            if text.strip().startswith("```"):
                self.setFormat(0, min(3, len(text)), _marker_codeblock_fence)
                if len(text.strip()) > 3:
                    self.setFormat(3, len(text.strip()) - 3, _marker_codeblock_fence)
                self.setCurrentBlockState(0)
                self.block_meta[block_num] = "code"
            else:
                self.setCurrentBlockState(1)
                self.block_meta[block_num] = "code"
            return

        if text.strip().startswith("```"):
            self.setFormat(0, min(3, len(text)), _marker_codeblock_fence)
            lang_part_len = max(0, len(text.strip()) - 3)
            if lang_part_len > 0:
                self.setFormat(3, lang_part_len, _marker_codeblock_fence)
            self.setFormat(0, len(text), _codeblock_content)
            self.setFormat(0, min(3, len(text)), _marker_codeblock_fence)
            if lang_part_len > 0:
                self.setFormat(3, lang_part_len, _marker_codeblock_fence)
            self.setCurrentBlockState(1)
            self.block_meta[block_num] = "code"
            return

        self.setCurrentBlockState(0)

        line_stripped_len = len(text.lstrip())
        leading = len(text) - line_stripped_len
        ltext = text.lstrip()

        m = re.match(r"^(#{1,6})\s(.*)", ltext)
        if m:
            level = len(m.group(1))
            near = (leading <= self.active_col <= leading + len(m.group(0)) + 1
                    and block_num == self.active_block)
            self._apply_marker(leading, len(m.group(1)) + 1, near)
            title_start = leading + len(m.group(1)) + 1
            title_len = len(text) - title_start
            if title_len > 0:
                fmt = [self._h1_title, self._h2_title, self._h3_title,
                       self._h4_title, self._h5_title, self._h6_title][level - 1]
                self.setFormat(title_start, title_len, fmt)
            self.block_meta[block_num] = f"h{level}"
            return

        m = re.match(r"^([-*+])\s(.*)", ltext)
        if m:
            near = (leading <= self.active_col <= leading + 2
                    and block_num == self.active_block)
            self._apply_marker(leading, len(m.group(1)) + 1, near)
            self.setFormat(leading, 1, _ul_marker)
            self.block_meta[block_num] = "ul"
            return

        m = re.match(r"^(\d+\.)\s(.*)", ltext)
        if m:
            marker_len = len(m.group(1)) + 1
            near = (leading <= self.active_col <= leading + marker_len + 1
                    and block_num == self.active_block)
            self._apply_marker(leading, marker_len, near)
            self.setFormat(leading, marker_len - 1, _ol_marker)
            self.block_meta[block_num] = "ol"
            return

        m = re.match(r"^(>)\s?(.*)", ltext)
        if m:
            self.setFormat(0, len(text), _block_quote_fmt)
            near = (leading <= self.active_col <= leading + 2
                    and block_num == self.active_block)
            self._apply_marker(leading, 1, near)
            self.block_meta[block_num] = "quote"
            return

        self.block_meta[block_num] = "p"

        applied = [False] * (len(text) + 1)

        def mark(s, e):
            for i in range(s, e):
                applied[i] = True

        def range_free(s, e) -> bool:
            for i in range(s, e):
                if applied[i]:
                    return False
            return True

        for regex, content_fmt, left_len, right_len in [
            (RE_LINK, _link_text_fmt, -1, -1),
            (RE_BOLD_ITALIC, self._bold_italic_fmt, 3, 3),
            (RE_BOLD, self._bold_fmt, 2, 2),
            (RE_STRIKE, self._strike_fmt, 2, 2),
            (RE_ITALIC, self._italic_fmt, 1, 1),
            (RE_INLINE_CODE, _code_inline_content, 1, 1),
        ]:
            for match in regex.finditer(text):
                s, e = match.start(), match.end()
                if not range_free(s, e):
                    continue
                if regex == RE_LINK:
                    text_group = match.group(1)
                    url_group = match.group(2)
                    lb = s
                    rb = s + 1 + len(text_group)
                    lp = rb + 1
                    rp = e - 1
                    near = self._near(s, e)
                    self._apply_marker(lb, 1, near)
                    self._apply_marker(rb, 1, near)
                    self._apply_marker(lp, 1, near)
                    self._apply_marker(rp, 1, near)
                    self.setFormat(s + 1, len(text_group), content_fmt)
                    url_start = lp + 1
                    url_len = rp - url_start
                    if url_len > 0:
                        if near:
                            url_fmt = _fmt(foreground="#6a737d",
                                           family="Consolas",
                                           size=10, letter_spacing_pct=0)
                            self.setFormat(url_start, url_len, url_fmt)
                        else:
                            self.setFormat(url_start, url_len, _link_url_hidden)
                    mark(s, e)
                else:
                    near = self._near(s, e)
                    self._apply_marker(s, left_len, near)
                    self._apply_marker(e - right_len, right_len, near)
                    content_start = s + left_len
                    content_len = (e - right_len) - content_start
                    if content_len > 0:
                        self.setFormat(content_start, content_len, content_fmt)
                    mark(s, e)


class _MixedTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._hl = None
        self.setTabChangesFocus(False)
        self.setMouseTracking(False)
        self.setAcceptRichText(False)

    def set_highlighter(self, hl: MarkdownMixedHighlighter):
        self._hl = hl


class MarkdownEditor(QWidget):
    content_changed = pyqtSignal(str, str, object)
    category_changed = pyqtSignal(object)
    force_save_request = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_category_id = None
        self._build_ui()
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(800)
        self._save_timer.timeout.connect(self._do_notify_save)
        self._dirty = False

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame()
        header.setStyleSheet("background:#ffffff; border-bottom:1px solid #e6e6e6;")
        hdr_layout = QVBoxLayout(header)
        hdr_layout.setContentsMargins(40, 24, 40, 16)
        hdr_layout.setSpacing(10)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("未命名笔记")
        title_font = QFont()
        title_font.setPointSize(22)
        title_font.setBold(True)
        self.title_edit.setFont(title_font)
        self.title_edit.setStyleSheet("""
            QLineEdit {
                border: none;
                outline: none;
                color: #202124;
                padding: 4px 0;
                background: transparent;
            }
        """)
        self.title_edit.textChanged.connect(self._on_any_changed)
        hdr_layout.addWidget(self.title_edit)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(14)
        self.save_status = QLabel("✓ 已保存")
        self.save_status.setStyleSheet("color:#34a853; font-size:12px;")
        self.word_count = QLabel("0 字")
        self.word_count.setStyleSheet("color:#888; font-size:12px;")
        dot = QLabel("·")
        dot.setStyleSheet("color:#bbb; font-size:12px;")
        cat_label = QLabel("分类:")
        cat_label.setStyleSheet("color:#666; font-size:12px;")
        self.category_combo = QComboBox()
        self.category_combo.setStyleSheet("""
            QComboBox {
                padding: 3px 10px; border: 1px solid #e0e0e0;
                border-radius: 5px; background: #fff; font-size: 12px;
            }
        """)
        self.category_combo.currentIndexChanged.connect(self._on_category_changed_ui)

        self.mode_label = QLabel("✨ 混合所见即所得")
        self.mode_label.setStyleSheet(
            "color:#1a73e8; font-size:12px; background:#eaf2fe;"
            "padding:3px 8px; border-radius:4px;"
        )

        save_btn = QToolButton()
        save_btn.setText("💾 保存")
        save_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        save_btn.setShortcut(QKeySequence.StandardKey.Save)
        save_btn.setStyleSheet(
            "QToolButton{padding:3px 10px; border:1px solid #1a73e8;"
            "border-radius:5px; font-size:12px; color:#1a73e8; background:#eaf2fe;}"
        )
        save_btn.clicked.connect(self._do_notify_save)

        meta_row.addWidget(self.save_status)
        meta_row.addWidget(dot)
        meta_row.addWidget(self.word_count)
        meta_row.addSpacing(12)
        meta_row.addWidget(cat_label)
        meta_row.addWidget(self.category_combo, 1)
        meta_row.addWidget(self.mode_label)
        meta_row.addWidget(save_btn)
        hdr_layout.addLayout(meta_row)

        toolbar = self._build_toolbar()
        hdr_layout.addLayout(toolbar)

        root.addWidget(header)

        self.edit = _MixedTextEdit()
        self.edit.setPlaceholderText(
            "在这里写笔记，Markdown 语法会自动渲染...\n"
            "示例：**粗体**  *斜体*  `代码`  ~~删除线~~  [链接](https://example.com)\n"
            "# 一级标题  ## 二级标题  > 引用  - 列表  1. 有序  ```代码块```\n\n"
            "移动光标到语法附近，源码符号会自动显示出来 ✨"
        )
        base_font = QFont()
        base_font.setPointSize(13)
        base_font.setFamilies([
            "-apple-system", "BlinkMacSystemFont", "Segoe UI",
            "Microsoft YaHei", "PingFang SC", "Hiragino Sans GB", "sans-serif"
        ])
        self.edit.setFont(base_font)
        self.edit.setStyleSheet("""
            QTextEdit {
                background: #ffffff;
                border: none;
                selection-background-color: #d2e3fc;
                color: #24292e;
                font-family: "Microsoft YaHei", "PingFang SC", "Segoe UI", sans-serif;
                font-size: 13px;
            }
            QScrollBar:vertical { width: 10px; }
            QScrollBar:horizontal { height: 10px; }
        """)
        self.edit.setViewportMargins(80, 80, 80, 160)
        doc = self.edit.document()
        doc.setDocumentMargin(0)
        root_frame = doc.rootFrame()
        rf = root_frame.frameFormat()
        rf.setPadding(0)
        rf.setBorder(0)
        rf.setMargin(0)
        root_frame.setFrameFormat(rf)
        self.edit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        hl = MarkdownMixedHighlighter(self.edit.document(), self.edit)
        self.edit.set_highlighter(hl)
        self._highlighter = hl
        self._highlighter.block_meta = {}
        self._applying_block_fmts = False
        self._cached_bfm = None
        self._last_block_types = {}
        self._apply_timer = QTimer(self)
        self._apply_timer.setSingleShot(True)
        self._apply_timer.setInterval(50)
        self._apply_timer.timeout.connect(self._apply_block_formats)
        self.edit.cursorPositionChanged.connect(self._on_cursor_changed)
        self.edit.textChanged.connect(self._on_src_changed)
        self._install_shortcuts()

        root.addWidget(self.edit, 1)

    def _install_shortcuts(self):
        b_sc = QShortcut(QKeySequence("Ctrl+B"), self.edit)
        b_sc.activated.connect(self._wrap_bold)
        i_sc = QShortcut(QKeySequence("Ctrl+I"), self.edit)
        i_sc.activated.connect(self._wrap_italic)
        k_sc = QShortcut(QKeySequence("Ctrl+`"), self.edit)
        k_sc.activated.connect(self._wrap_code)

    def _build_toolbar(self):
        bar = QHBoxLayout()
        bar.setSpacing(4)
        actions = [
            ("B", self._wrap_bold, "粗体 Ctrl+B", True),
            ("I", self._wrap_italic, "斜体 Ctrl+I", True),
            ("S", self._wrap_strike, "删除线 ~~text~~", True),
            ("`", self._wrap_code, "行内代码 Ctrl+`", True),
            ("", None, None, False),
            ("H1", lambda: self._prepend_line("# "), "一级标题", False),
            ("H2", lambda: self._prepend_line("## "), "二级标题", False),
            ("H3", lambda: self._prepend_line("### "), "三级标题", False),
            ("", None, None, False),
            ("• 列表", lambda: self._prepend_line("- "), "无序列表", False),
            ("1. 列表", lambda: self._prepend_line("1. "), "有序列表", False),
            ("❝ 引用", lambda: self._prepend_line("> "), "引用块", False),
            ("--- 分隔", lambda: self._insert_text("\n\n---\n\n"), "水平分割线", False),
            ("", None, None, False),
            ("``` 代码块", self._insert_codeblock, "代码块", False),
            ("🔗 链接", self._insert_link, "插入链接", False),
            ("📊 表格", self._insert_table, "插入表格", False),
        ]
        for text, func, tip, is_fmt in actions:
            if func is None:
                sep = QFrame()
                sep.setFixedWidth(1)
                sep.setStyleSheet("background:#eee; margin:4px 0;")
                bar.addWidget(sep)
                continue
            btn = QToolButton()
            btn.setText(text if text else " ")
            btn.setToolTip(tip)
            if is_fmt:
                f = QFont()
                f.setBold(text == "B")
                f.setItalic(text == "I")
                if text == "S":
                    f.setStrikeOut(True)
                if text == "`":
                    f.setFamily("Consolas")
                btn.setFont(f)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QToolButton {
                    padding: 5px 10px;
                    border: 1px solid transparent;
                    border-radius: 5px;
                    font-size: 12px;
                    color: #444;
                    background: transparent;
                }
                QToolButton:hover { background: #eef3f9; border-color: #d8e2f0; }
                QToolButton:pressed { background: #e0eaf6; }
            """)
            btn.clicked.connect(func)
            bar.addWidget(btn)
        bar.addStretch(1)
        return bar

    def _get_cursor(self):
        return self.edit.textCursor()

    def _set_cursor(self, cursor):
        self.edit.setTextCursor(cursor)

    def _selected_text(self):
        return self._get_cursor().selectedText() or "text"

    def _wrap_text(self, before, after):
        cursor = self._get_cursor()
        text = self._selected_text()
        cursor.insertText(f"{before}{text}{after}")
        if before and after and text == "text":
            new_cursor = self._get_cursor()
            pos = new_cursor.position()
            new_cursor.setPosition(pos - len(after) - 4)
            new_cursor.setPosition(pos - len(after), QTextCursor.MoveMode.KeepAnchor)
            self._set_cursor(new_cursor)

    def _wrap_bold(self): self._wrap_text("**", "**")

    def _wrap_italic(self): self._wrap_text("*", "*")

    def _wrap_strike(self): self._wrap_text("~~", "~~")

    def _wrap_code(self): self._wrap_text("`", "`")

    def _insert_text(self, txt):
        self.edit.textCursor().insertText(txt)

    def _prepend_line(self, prefix):
        cursor = self._get_cursor()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.insertText(prefix)

    def _insert_codeblock(self):
        cursor = self._get_cursor()
        if cursor.block().text().strip():
            cursor.insertText("\n\n```python\n\n```\n")
        else:
            cursor.insertText("```python\n\n```\n")
        cursor.movePosition(QTextCursor.MoveOperation.Up, QTextCursor.MoveMode.MoveAnchor, 1)
        self._set_cursor(cursor)

    def _insert_link(self):
        cursor = self._get_cursor()
        text = cursor.selectedText() or "链接文本"
        cursor.insertText(f"[{text}](https://)")

    def _insert_table(self):
        self._insert_text(
            "\n| 列1 | 列2 | 列3 |\n"
            "|-----|-----|-----|\n"
            "| A   | B   | C   |\n"
        )

    def _on_src_changed(self):
        self._on_any_changed()
        self._apply_timer.start()

    def _on_any_changed(self):
        self._set_save_status("saving")
        self._update_word_count()
        if not self._save_timer.isActive():
            self._dirty = True
        self._save_timer.start()

    def _on_cursor_changed(self):
        cursor = self._get_cursor()
        block = cursor.block()
        col = cursor.position() - block.position()
        self._highlighter.set_active_cursor(block.blockNumber(), col)
        self._highlighter.rehighlight()
        self._apply_timer.start()

    def _update_word_count(self):
        text = (self.title_edit.text() or "") + (self.edit.toPlainText() or "")
        count = len(re.sub(r"\s", "", text))
        self.word_count.setText(f"{count} 字")

    def _apply_block_formats(self, *_):
        if getattr(self, "_applying_block_fmts", False):
            return
        self._applying_block_fmts = True
        try:
            if self._cached_bfm is None:
                MIN = QTextBlockFormat.LineHeightTypes.MinimumHeight.value if hasattr(
                    QTextBlockFormat.LineHeightTypes, "MinimumHeight") else 2
                presets = {
                    "h1":    (42, MIN, 22, 14),
                    "h2":    (36, MIN, 18, 12),
                    "h3":    (32, MIN, 14, 10),
                    "h4":    (28, MIN, 12, 8),
                    "h5":    (24, MIN, 10, 6),
                    "h6":    (22, MIN, 8, 4),
                    "p":     (26, MIN, 5, 5),
                    "ul":    (25, MIN, 4, 3),
                    "ol":    (25, MIN, 4, 3),
                    "quote": (26, MIN, 6, 6),
                    "code":  (24, MIN, 2, 2),
                }
                cached = {}
                for t, (lh, lht, tm, bm) in presets.items():
                    bf = QTextBlockFormat()
                    bf.setLineHeight(lh, lht)
                    bf.setTopMargin(tm)
                    bf.setBottomMargin(bm)
                    cached[t] = bf
                self._cached_bfm = cached
            fmt_by_type = self._cached_bfm
            doc = self.edit.document()
            block = doc.begin()
            idx = 0
            changes = []
            total = doc.blockCount()
            while block.isValid() and idx <= total + 10:
                t = self._highlighter.block_meta.get(idx, "p")
                t = t if t in fmt_by_type else "p"
                last_t = self._last_block_types.get(idx)
                if last_t != t:
                    changes.append((block.position(), fmt_by_type[t]))
                    self._last_block_types[idx] = t
                idx += 1
                block = block.next()
            stale = [k for k in self._last_block_types if k >= idx]
            for k in stale:
                del self._last_block_types[k]
            if changes:
                cursor = QTextCursor(doc)
                for pos, fmt in changes:
                    cursor.setPosition(pos)
                    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock,
                                        QTextCursor.MoveMode.KeepAnchor)
                    cursor.setBlockFormat(fmt)
        finally:
            self._applying_block_fmts = False

    def _set_save_status(self, state):
        if state == "saving":
            self.save_status.setText("⏳ 保存中...")
            self.save_status.setStyleSheet("color:#fbbc04; font-size:12px;")
        else:
            self.save_status.setText("✓ 已保存")
            self.save_status.setStyleSheet("color:#34a853; font-size:12px;")

    def _do_notify_save(self):
        self._dirty = False
        self._set_save_status("saved")
        title = self.title_edit.text()
        content = self.edit.toPlainText()
        cat_id = self._current_category_id()
        self.content_changed.emit(title, content, cat_id)

    def _current_category_id(self):
        idx = self.category_combo.currentIndex()
        if idx < 0:
            return None
        return self.category_combo.itemData(idx)

    def _on_category_changed_ui(self, idx):
        self._on_any_changed()
        self.category_changed.emit(self._current_category_id())

    def set_note(self, title: str, content: str, category_id, categories: List[Category]):
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        self.category_combo.addItem("未分类", None)
        for c in categories:
            self.category_combo.addItem(c.name, c.id)
        if category_id is None:
            self.category_combo.setCurrentIndex(0)
        else:
            found = False
            for i in range(self.category_combo.count()):
                if self.category_combo.itemData(i) == category_id:
                    self.category_combo.setCurrentIndex(i)
                    found = True
                    break
            if not found:
                self.category_combo.setCurrentIndex(0)
        self.category_combo.blockSignals(False)
        self.current_category_id = category_id

        self.title_edit.blockSignals(True)
        self.edit.blockSignals(True)
        self.title_edit.setText(title or "")
        self.edit.setPlainText(content or "")
        self._last_block_types.clear()
        self._highlighter.set_active_cursor(-1, -1)
        self._highlighter.rehighlight()
        self._apply_block_formats()
        self.title_edit.blockSignals(False)
        self.edit.blockSignals(False)

        self._update_word_count()
        self._set_save_status("saved")
        self._dirty = False

    def update_categories(self, categories: List[Category], current_category_id):
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        self.category_combo.addItem("未分类", None)
        for c in categories:
            self.category_combo.addItem(c.name, c.id)
        if current_category_id is None:
            self.category_combo.setCurrentIndex(0)
        else:
            for i in range(self.category_combo.count()):
                if self.category_combo.itemData(i) == current_category_id:
                    self.category_combo.setCurrentIndex(i)
                    break
        self.category_combo.blockSignals(False)

    def get_title_sync(self) -> str:
        return self.title_edit.text()

    def get_content_sync(self) -> str:
        return self.edit.toPlainText()
