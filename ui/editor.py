import re
from typing import List
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QTextCursor,
    QKeySequence, QShortcut, QTextBlockFormat, QTextDocument
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLineEdit, QLabel,
    QComboBox, QToolButton, QTextEdit, QSizePolicy, QGraphicsDropShadowEffect
)
from core.database import Category
from .theme import THEMES, DEFAULT_THEME, get_editor_qss


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


def _build_md_formats(t: dict) -> dict:
    """Build markdown highlight QTextCharFormat from theme dict."""
    marker_hidden = QTextCharFormat()
    marker_hidden.setForeground(QColor(0, 0, 0, 0))

    marker_visible = _fmt(foreground=t["marker_visible"], letter_spacing_pct=0)
    marker_codeblock_fence = _fmt(
        foreground=t["codeblock_fence"], family="Consolas", size=11, letter_spacing_pct=0
    )
    code_inline_content = _fmt(
        foreground=t["inlinecode_fg"], background=t["inlinecode_bg"],
        family="Consolas", size=13, letter_spacing_pct=0
    )
    codeblock_content = _fmt(
        foreground=t["codeblock_fg"], background=t["codeblock_bg"],
        family="Consolas", size=12, letter_spacing_pct=0
    )
    block_quote_fmt = _fmt(
        foreground=t["quote_fg"], background=t["quote_bg"], letter_spacing_pct=0
    )
    ul_marker = _fmt(foreground=t["list_marker"], bold=True, letter_spacing_pct=0)
    ol_marker = _fmt(foreground=t["list_marker"], bold=True, letter_spacing_pct=0)
    link_text_fmt = _fmt(foreground=t["link"], underline=True, letter_spacing_pct=0)
    link_url_hidden = QTextCharFormat()
    link_url_hidden.setForeground(QColor(0, 0, 0, 0))

    h1 = _fmt(foreground=t["h1"], bold=True, size=22, letter_spacing_pct=0)
    h2 = _fmt(foreground=t["h2"], bold=True, size=18, letter_spacing_pct=0)
    h3 = _fmt(foreground=t["h3"], bold=True, size=16, letter_spacing_pct=0)
    h4 = _fmt(foreground=t["h4"], bold=True, size=14, letter_spacing_pct=0)
    h5 = _fmt(foreground=t["h5"], bold=True, size=13, letter_spacing_pct=0)
    h6 = _fmt(foreground=t["h6"], bold=True, size=12, letter_spacing_pct=0)
    bold = _fmt(bold=True, letter_spacing_pct=0)
    italic = _fmt(italic=True, letter_spacing_pct=0)
    bold_italic = _fmt(bold=True, italic=True, letter_spacing_pct=0)
    strike = _fmt(strike=True, letter_spacing_pct=0)

    return {
        "marker_hidden": marker_hidden,
        "marker_visible": marker_visible,
        "marker_codeblock_fence": marker_codeblock_fence,
        "code_inline_content": code_inline_content,
        "codeblock_content": codeblock_content,
        "block_quote_fmt": block_quote_fmt,
        "ul_marker": ul_marker,
        "ol_marker": ol_marker,
        "link_text_fmt": link_text_fmt,
        "link_url_hidden": link_url_hidden,
        "link_url_visible_fg": t["link_url"],
        "h1": h1, "h2": h2, "h3": h3, "h4": h4, "h5": h5, "h6": h6,
        "bold": bold, "italic": italic, "bold_italic": bold_italic, "strike": strike,
    }


HIDDEN_LETTER_SPACING = -95  # 兼容保留

RE_INLINE_CODE = re.compile(r"`([^`\n]+?)`")
RE_BOLD_ITALIC = re.compile(r"\*\*\*([^*]+?)\*\*\*")
RE_BOLD = re.compile(r"\*\*([^*]+?)\*\*")
RE_ITALIC = re.compile(r"(?<!\*)\*([^*\s][^*]*?)\*(?!\*)")
RE_STRIKE = re.compile(r"~~([^~]+?)~~")
RE_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


class MarkdownMixedHighlighter(QSyntaxHighlighter):
    def __init__(self, document, editor_ref, theme_name: str = DEFAULT_THEME):
        import sys as _sys
        super().__init__(document)
        self.editor_ref = editor_ref
        self.active_block = -1
        self.active_col = -1
        self.block_meta = {}
        self.current_theme = theme_name
        self._in_rehighlight = False
        self.apply_theme(theme_name, force_rehighlight=False)

    def apply_theme(self, theme_name: str, force_rehighlight: bool = True):
        self.current_theme = theme_name
        t = THEMES[theme_name]
        self._fmt = _build_md_formats(t)
        self._h1_title = self._fmt["h1"]
        self._h2_title = self._fmt["h2"]
        self._h3_title = self._fmt["h3"]
        self._h4_title = self._fmt["h4"]
        self._h5_title = self._fmt["h5"]
        self._h6_title = self._fmt["h6"]
        self._bold_fmt = self._fmt["bold"]
        self._italic_fmt = self._fmt["italic"]
        self._bold_italic_fmt = self._fmt["bold_italic"]
        self._strike_fmt = self._fmt["strike"]
        if force_rehighlight:
            if not self._in_rehighlight:
                self._in_rehighlight = True
                try:
                    self.rehighlight()
                finally:
                    self._in_rehighlight = False

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
            self.setFormat(start, length, self._fmt["marker_visible"])
        else:
            self.setFormat(start, length, self._fmt["marker_hidden"])

    def highlightBlock(self, text: str):
        block_num = self.currentBlock().blockNumber()
        prev_state = self.previousBlockState()

        if prev_state == 1:
            self.setFormat(0, len(text), self._fmt["codeblock_content"])
            if text.strip().startswith("```"):
                self.setFormat(0, min(3, len(text)), self._fmt["marker_codeblock_fence"])
                if len(text.strip()) > 3:
                    self.setFormat(3, len(text.strip()) - 3, self._fmt["marker_codeblock_fence"])
                self.setCurrentBlockState(0)
                self.block_meta[block_num] = "code"
            else:
                self.setCurrentBlockState(1)
                self.block_meta[block_num] = "code"
            return

        if text.strip().startswith("```"):
            self.setFormat(0, min(3, len(text)), self._fmt["marker_codeblock_fence"])
            lang_part_len = max(0, len(text.strip()) - 3)
            if lang_part_len > 0:
                self.setFormat(3, lang_part_len, self._fmt["marker_codeblock_fence"])
            self.setFormat(0, len(text), self._fmt["codeblock_content"])
            self.setFormat(0, min(3, len(text)), self._fmt["marker_codeblock_fence"])
            if lang_part_len > 0:
                self.setFormat(3, lang_part_len, self._fmt["marker_codeblock_fence"])
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
            self.setFormat(leading, 1, self._fmt["ul_marker"])
            self.block_meta[block_num] = "ul"
            return

        m = re.match(r"^(\d+\.)\s(.*)", ltext)
        if m:
            marker_len = len(m.group(1)) + 1
            near = (leading <= self.active_col <= leading + marker_len + 1
                    and block_num == self.active_block)
            self._apply_marker(leading, marker_len, near)
            self.setFormat(leading, marker_len - 1, self._fmt["ol_marker"])
            self.block_meta[block_num] = "ol"
            return

        m = re.match(r"^(>)\s?(.*)", ltext)
        if m:
            self.setFormat(0, len(text), self._fmt["block_quote_fmt"])
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
            (RE_LINK, self._fmt["link_text_fmt"], -1, -1),
            (RE_BOLD_ITALIC, self._bold_italic_fmt, 3, 3),
            (RE_BOLD, self._bold_fmt, 2, 2),
            (RE_STRIKE, self._strike_fmt, 2, 2),
            (RE_ITALIC, self._italic_fmt, 1, 1),
            (RE_INLINE_CODE, self._fmt["code_inline_content"], 1, 1),
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
                            url_fmt = _fmt(
                                foreground=self._fmt["link_url_visible_fg"],
                                family="Consolas",
                                size=10, letter_spacing_pct=0,
                            )
                            self.setFormat(url_start, url_len, url_fmt)
                        else:
                            self.setFormat(url_start, url_len, self._fmt["link_url_hidden"])
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

    def __init__(self, parent=None, theme_name: str = DEFAULT_THEME):
        import sys as _sys
        super().__init__(parent)
        self.current_category_id = None
        self.current_theme = theme_name
        self._toolbar_btns = []
        self._toolbar_seps = []
        self._constructing = True
        self._build_ui()
        self.apply_theme(theme_name, initial=True)
        self._constructing = False
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(800)
        self._save_timer.timeout.connect(self._do_notify_save)
        self._dirty = False

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.header = QFrame()
        self.hdr_shadow = QGraphicsDropShadowEffect()
        self.hdr_shadow.setBlurRadius(18)
        self.hdr_shadow.setXOffset(0)
        self.hdr_shadow.setYOffset(2)
        self.hdr_shadow.setColor(QColor(110, 100, 80, 30))
        self.header.setGraphicsEffect(self.hdr_shadow)

        hdr_layout = QVBoxLayout(self.header)
        hdr_layout.setContentsMargins(60, 28, 60, 18)
        hdr_layout.setSpacing(14)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("未命名笔记")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        self.title_edit.setFont(title_font)
        self.title_edit.textChanged.connect(self._on_any_changed)
        hdr_layout.addWidget(self.title_edit)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(12)
        self.save_status = QLabel("✓ 已保存")
        self.dot = QLabel("·")
        self.word_count = QLabel("0 字")
        self.cat_label = QLabel("分类")
        self.category_combo = QComboBox()
        self.category_combo.currentIndexChanged.connect(self._on_category_changed_ui)

        self.save_btn = QToolButton()
        self.save_btn.setText("💾  保存")
        self.save_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.save_btn.setShortcut(QKeySequence.StandardKey.Save)
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.clicked.connect(self._do_notify_save)

        meta_row.addWidget(self.save_status)
        meta_row.addWidget(self.dot)
        meta_row.addWidget(self.word_count)
        meta_row.addSpacing(16)
        meta_row.addWidget(self.cat_label)
        meta_row.addWidget(self.category_combo, 1)
        meta_row.addWidget(self.save_btn)
        hdr_layout.addLayout(meta_row)

        self.toolbar_container = QFrame()
        toolbar_layout_wrap = QHBoxLayout(self.toolbar_container)
        toolbar_layout_wrap.setContentsMargins(6, 4, 6, 4)
        toolbar_layout_wrap.setSpacing(0)
        toolbar = self._build_toolbar()
        toolbar_layout_wrap.addLayout(toolbar)
        hdr_layout.addWidget(self.toolbar_container)

        root.addWidget(self.header)

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
        hl = MarkdownMixedHighlighter(self.edit.document(), self.edit, theme_name=self.current_theme)
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

    def apply_theme(self, theme_name: str, initial: bool = False):
        import sys as _sys
        self.current_theme = theme_name
        t = THEMES[theme_name]
        qss = get_editor_qss(t)
        self.header.setStyleSheet(qss["header"])
        self.title_edit.setStyleSheet(qss["title_edit"])
        self.category_combo.setStyleSheet(qss["category_combo"])
        self.save_btn.setStyleSheet(qss["save_btn"])
        self.toolbar_container.setStyleSheet(qss["toolbar_container"])
        self.edit.setStyleSheet(qss["textedit"])
        self.save_status.setStyleSheet(
            f"color:{t['save_color']}; font-size:12px; font-weight:500;"
        )
        self.word_count.setStyleSheet(
            f"color:{t['text_secondary']}; font-size:12px;"
        )
        self.dot.setStyleSheet(
            f"color:{t['text_tertiary']}; font-size:13px;"
        )
        self.cat_label.setStyleSheet(
            f"color:{t['text_secondary']}; font-size:12px; font-weight:500;"
        )
        for sep in self._toolbar_seps:
            sep.setStyleSheet(qss["toolbar_sep"])
        for btn in self._toolbar_btns:
            btn.setStyleSheet(qss["toolbar_btn"])
        doc = self.edit.document()
        empty_doc = (doc.blockCount() <= 1 and not (doc.toPlainText() or "").strip())
        if initial or empty_doc:
            # 构造期 / 空文档：跳过 rehighlight，避免 Qt 内部崩
            self._highlighter.apply_theme(theme_name, force_rehighlight=False)
        else:
            self._highlighter.apply_theme(theme_name, force_rehighlight=True)

    def _install_shortcuts(self):
        b_sc = QShortcut(QKeySequence("Ctrl+B"), self.edit)
        b_sc.activated.connect(self._wrap_bold)
        i_sc = QShortcut(QKeySequence("Ctrl+I"), self.edit)
        i_sc.activated.connect(self._wrap_italic)
        k_sc = QShortcut(QKeySequence("Ctrl+`"), self.edit)
        k_sc.activated.connect(self._wrap_code)

    def _build_toolbar(self):
        bar = QHBoxLayout()
        bar.setSpacing(2)
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
                self._toolbar_seps.append(sep)
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
            btn.clicked.connect(func)
            self._toolbar_btns.append(btn)
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
        hl = self._highlighter
        if not getattr(hl, "_in_rehighlight", False):
            hl._in_rehighlight = True
            try:
                hl.rehighlight()
            finally:
                hl._in_rehighlight = False
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
