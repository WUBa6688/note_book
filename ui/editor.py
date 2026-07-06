import os
import re
import sys
import uuid
import random
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize, QMimeData, QRectF, QPointF, QRect
from PyQt6.QtGui import (
    QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QTextCursor,
    QKeySequence, QShortcut, QTextBlockFormat, QTextDocument,
    QPixmap, QPainter, QIcon, QBrush, QPen, QImage, QTextImageFormat, QPalette,
    QAction, QPainterPath, QFontMetrics
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLineEdit, QLabel,
    QComboBox, QToolButton, QTextEdit, QSizePolicy, QGraphicsDropShadowEffect,
    QColorDialog, QDialog, QSpinBox, QAbstractSpinBox, QMenu,
    QFileDialog, QSlider, QDialogButtonBox, QLayout, QLayoutItem
)
try:
    from pygments import lexers, styles, token as pyg_token
    from pygments.lexers import guess_lexer
    from pygments.styles import get_style_by_name
    from pygments.util import ClassNotFound
    _HAS_PYGMENTS = True
except Exception:
    _HAS_PYGMENTS = False
from core.database import Category, get_assets_dir, get_assets_root
from core.settings import load_settings, save_settings
from .theme import THEMES, DEFAULT_THEME, get_editor_qss


class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=4, spacing=-1, h_spacing=4, v_spacing=4):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self._spacing_x = spacing if spacing >= 0 else h_spacing
        self._spacing_y = spacing if spacing >= 0 else v_spacing
        self._item_list: List[QLayoutItem] = []

    def __del__(self):
        item = self.takeAt(0)
        while item is not None:
            del item
            item = self.takeAt(0)

    def addItem(self, item: QLayoutItem):
        self._item_list.append(item)

    def horizontal_spacing(self):
        return self._spacing_x

    def vertical_spacing(self):
        return self._spacing_y

    def count(self):
        return len(self._item_list)

    def itemAt(self, index: int):
        if 0 <= index < len(self._item_list):
            return self._item_list[index]
        return None

    def takeAt(self, index: int):
        if 0 <= index < len(self._item_list):
            return self._item_list.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width: int):
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect):
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    def _do_layout(self, rect: QRect, test_only: bool):
        m = self.contentsMargins()
        effective = rect.adjusted(+m.left(), +m.top(), -m.right(), -m.bottom())
        x = effective.x()
        y = effective.y()
        line_height = 0
        space_x = max(2, self._spacing_x)
        space_y = max(2, self._spacing_y)
        for item in self._item_list:
            if item is None:
                continue
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > effective.right() and line_height > 0:
                x = effective.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0
            if not test_only:
                sh = item.sizeHint()
                g = QRect(int(x), int(y), max(0, sh.width()), max(0, sh.height()))
                item.setGeometry(g)
            x = next_x
            line_height = max(line_height, item.sizeHint().height())
        return y + line_height - rect.y() + m.bottom()


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
    """Build markdown highlight QTextCharFormat from theme dict.

    NOTE: For *content* ranges (headings, link text, quote body, inline
    code, code block body) we deliberately do NOT set `foreground` in
    the syntax-highlighter layer, so the per-character colors the user
    applies via the "Text Color" tool are NOT overwritten on every
    rehighlight. Font styles (bold/size/family/underline) and block
    backgrounds are still applied by the highlighter.
    """
    mh_font = QFont()
    mh_font.setPointSizeF(0.5)
    marker_hidden = QTextCharFormat()
    marker_hidden.setForeground(QColor(0, 0, 0, 0))
    marker_hidden.setFont(mh_font)

    lu_font = QFont()
    lu_font.setPointSizeF(0.5)
    link_url_hidden = QTextCharFormat()
    link_url_hidden.setForeground(QColor(0, 0, 0, 0))
    link_url_hidden.setFont(lu_font)

    marker_visible = _fmt(foreground=t["marker_visible"], letter_spacing_pct=0)
    marker_codeblock_fence = _fmt(
        foreground=t["codeblock_fence"], family="Consolas", size=11, letter_spacing_pct=0
    )
    code_inline_content = _fmt(
        background=t["inlinecode_bg"],
        family="Consolas", size=13, letter_spacing_pct=0
    )
    codeblock_content = _fmt(
        background=t["codeblock_bg"],
        family="Consolas", size=12, letter_spacing_pct=0
    )
    block_quote_fmt = _fmt(
        background=t["quote_bg"], letter_spacing_pct=0
    )
    ul_marker = _fmt(foreground=t["list_marker"], bold=True, letter_spacing_pct=0)
    ol_marker = _fmt(foreground=t["list_marker"], bold=True, letter_spacing_pct=0)
    link_text_fmt = _fmt(underline=True, letter_spacing_pct=0)

    h1 = _fmt(bold=True, size=22, letter_spacing_pct=0)
    h2 = _fmt(bold=True, size=18, letter_spacing_pct=0)
    h3 = _fmt(bold=True, size=16, letter_spacing_pct=0)
    h4 = _fmt(bold=True, size=14, letter_spacing_pct=0)
    h5 = _fmt(bold=True, size=13, letter_spacing_pct=0)
    h6 = _fmt(bold=True, size=12, letter_spacing_pct=0)
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

RE_INLINE_CODE = re.compile(r"`([^`\n]+?)`")
RE_BOLD_ITALIC = re.compile(r"\*\*\*([^*]+?)\*\*\*")
RE_BOLD = re.compile(r"\*\*([^*]+?)\*\*")
RE_ITALIC = re.compile(r"(?<!\*)\*([^*\s][^*]*?)\*(?!\*)")
RE_STRIKE = re.compile(r"~~([^~]+?)~~")
RE_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


_PYGMENTS_LIGHT_STYLES = ("default", "friendly", "colorful")
_PYGMENTS_DARK_STYLES = ("monokai", "inkpot", "paraiso-dark")

def _pygments_style_for_theme(t: dict) -> str:
    if t.get("group") == "dark":
        return _PYGMENTS_DARK_STYLES[0]
    return _PYGMENTS_LIGHT_STYLES[0]

def _hex_to_qcolor(s: str, default: str) -> QColor:
    try:
        if not s:
            return QColor(default)
        return QColor(str(s))
    except Exception:
        return QColor(default)


class MarkdownMixedHighlighter(QSyntaxHighlighter):
    def __init__(self, document, editor_ref, theme_name: str = DEFAULT_THEME):
        import sys as _sys
        super().__init__(document)
        self.editor_ref = editor_ref
        self.active_block = -1
        self.active_col = -1
        self.block_meta: Dict[int, str] = {}
        self.code_block_info: Dict[int, Dict[str, Any]] = {}
        self.current_theme = theme_name
        self._in_rehighlight = False
        self._lexer_cache: Dict[str, Any] = {}
        self._pygments_style_cache: Dict[str, Any] = {}
        self._token_format_cache: Dict[str, Any] = {}
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
        self._lexer_cache.clear()
        self._pygments_style_cache.clear()
        self._token_format_cache.clear()
        if force_rehighlight:
            if not self._in_rehighlight:
                self._in_rehighlight = True
                try:
                    self.rehighlight()
                finally:
                    self._in_rehighlight = False

    def _current_theme_data(self) -> dict:
        return THEMES[self.current_theme]

    def _get_pygments_style(self):
        t = self._current_theme_data()
        name = _pygments_style_for_theme(t)
        if name in self._pygments_style_cache:
            return self._pygments_style_cache[name]
        if not _HAS_PYGMENTS:
            self._pygments_style_cache[name] = None
            return None
        try:
            style = get_style_by_name(name)
        except Exception:
            style = None
        self._pygments_style_cache[name] = style
        return style

    def _get_lexer(self, lang: str):
        if not _HAS_PYGMENTS or not lang:
            return None
        lang_key = lang.lower().strip()
        if lang_key in self._lexer_cache:
            return self._lexer_cache[lang_key]
        try:
            lx = lexers.get_lexer_by_name(lang_key, stripnl=False, ensurenl=False)
        except ClassNotFound:
            lx = None
        except Exception:
            lx = None
        self._lexer_cache[lang_key] = lx
        return lx

    def _format_for_ttype(self, ttype, base_bg: str) -> QTextCharFormat:
        style = self._get_pygments_style()
        bg_str = base_bg
        fg_str = None
        bold = False
        italic = False
        underline = False
        if style is not None:
            try:
                entry = style.style_for_token(ttype) or {}
                if entry.get("color"):
                    fg_str = "#" + entry["color"]
                if entry.get("bgcolor"):
                    bg_str = "#" + entry["bgcolor"]
                if entry.get("bold"):
                    bold = True
                if entry.get("italic"):
                    italic = True
                if entry.get("underline"):
                    underline = True
            except Exception:
                pass
        key_parts = [fg_str or "", bg_str, str(int(bold)), str(int(italic)), str(int(underline))]
        key = "|".join(key_parts)
        if key in self._token_format_cache:
            return self._token_format_cache[key]
        kwargs: Dict[str, Any] = {"family": "Consolas", "size": 12, "letter_spacing_pct": 0, "background": bg_str}
        if fg_str:
            kwargs["foreground"] = fg_str
        if bold:
            kwargs["bold"] = True
        if italic:
            kwargs["italic"] = True
        if underline:
            kwargs["underline"] = True
        fmt = _fmt(**kwargs)
        self._token_format_cache[key] = fmt
        return fmt

    def _highlight_code_line(self, text: str, lang: str, base_bg: str):
        if not text:
            return
        lx = self._get_lexer(lang) if lang else None
        if _HAS_PYGMENTS:
            try:
                default_fmt = self._format_for_ttype(pyg_token.Text, base_bg)
            except Exception:
                default_fmt = self._fmt["codeblock_content"]
        else:
            default_fmt = self._fmt["codeblock_content"]
        try:
            self.setFormat(0, len(text), default_fmt)
        except Exception:
            pass
        if (not _HAS_PYGMENTS) or lx is None:
            return
        try:
            idx = 0
            text_nl = text if text.endswith("\n") else text + "\n"
            for ttype, value in lx.get_tokens(text_nl):
                if not value:
                    continue
                ln = len(value)
                if idx + ln > len(text):
                    ln = len(text) - idx
                if ln > 0:
                    try:
                        fmt = self._format_for_ttype(ttype, base_bg)
                        self.setFormat(idx, ln, fmt)
                    except Exception:
                        pass
                idx += ln
                if idx >= len(text):
                    break
        except Exception:
            return

    @staticmethod
    def _parse_fence_lang(text: str) -> str:
        s = text.strip()
        if not s.startswith("```"):
            return ""
        tail = s[3:].strip()
        if not tail:
            return ""
        first_word = re.split(r"\s|,|;|:", tail, 1)[0]
        return first_word.lower().strip()

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
        t = self._current_theme_data()
        base_bg = t.get("codeblock_bg", "#F2EEE6")

        if prev_state == 1:
            if text.strip().startswith("```"):
                self.setFormat(0, min(3, len(text)), self._fmt["marker_codeblock_fence"])
                if len(text.strip()) > 3:
                    self.setFormat(3, len(text.strip()) - 3, self._fmt["marker_codeblock_fence"])
                self.setFormat(0, len(text), self._fmt["codeblock_content"])
                self.setFormat(0, min(3, len(text)), self._fmt["marker_codeblock_fence"])
                if len(text.strip()) > 3:
                    self.setFormat(3, len(text.strip()) - 3, self._fmt["marker_codeblock_fence"])
                self.setCurrentBlockState(0)
                self.block_meta[block_num] = "code_fence_end"
                for start_b, info in list(self.code_block_info.items()):
                    if info.get("end") is None and info.get("pending", True):
                        info["end"] = block_num
                        info["pending"] = False
                return
            else:
                self.setCurrentBlockState(1)
                self.block_meta[block_num] = "code_body"
                resolved_lang = ""
                for start_b, info in self.code_block_info.items():
                    if info.get("end") is None and info.get("pending", True) and (info.get("start") is None or block_num > info.get("start", -1)):
                        resolved_lang = info.get("lang", "") or ""
                        break
                self._highlight_code_line(text, resolved_lang, base_bg)
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
            lang = self._parse_fence_lang(text) or ""
            self.code_block_info[block_num] = {"start": block_num, "end": None, "lang": lang, "pending": True}
            self.block_meta[block_num] = "code_fence_start"
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
    paste_image_requested = pyqtSignal(QImage)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hl = None
        self._current_theme = DEFAULT_THEME
        self.setTabChangesFocus(False)
        self.setMouseTracking(False)
        self.setAcceptRichText(False)
        self.viewport().setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self._bg_raw_pixmap = None
        self._bg_path = ""
        self._bg_alpha = 0.18

    def set_highlighter(self, hl: MarkdownMixedHighlighter):
        self._hl = hl

    def set_theme_name(self, theme_name: str):
        if theme_name in THEMES:
            self._current_theme = theme_name
            self.viewport().update()

    def _current_theme(self) -> dict:
        return THEMES.get(self._current_theme, THEMES[DEFAULT_THEME])

    def _collect_code_blocks(self) -> List[Tuple[int, int, str]]:
        res: List[Tuple[int, int, str]] = []
        if self._hl is None:
            return res
        seen_starts = set()
        for start_b, info in self._hl.code_block_info.items():
            if start_b in seen_starts:
                continue
            end_b = info.get("end")
            if end_b is None or not isinstance(end_b, int):
                continue
            if start_b > end_b:
                continue
            lang = (info.get("lang") or "").strip()
            res.append((int(start_b), int(end_b), lang))
            seen_starts.add(start_b)
        res.sort(key=lambda x: x[0])
        return res

    def _block_viewport_rect(self, block_number: int) -> QRect:
        doc = self.document()
        if doc is None:
            return QRect()
        blk = doc.findBlockByNumber(block_number)
        if not blk.isValid():
            return QRect()
        curs = QTextCursor(blk)
        r1 = self.cursorRect(curs)
        curs.movePosition(QTextCursor.MoveOperation.EndOfBlock)
        r2 = self.cursorRect(curs)
        x = min(r1.x(), r2.x())
        y = min(r1.y(), r2.y())
        w = max(r1.right(), r2.right()) - x
        h = max(r1.bottom(), r2.bottom()) - y
        return QRect(x, y, w, max(h, r1.height()))

    @staticmethod
    def _rounded_rect_path(r: QRectF, radius: float) -> QPainterPath:
        path = QPainterPath()
        x, y, w, h = r.x(), r.y(), r.width(), r.height()
        if w <= 0 or h <= 0:
            return path
        path.addRoundedRect(QRectF(x, y, w, h), radius, radius)
        return path

    def _draw_code_block_background(self, painter: QPainter, start_b: int, end_b: int, lang: str):
        try:
            t = self._current_theme()
            is_dark = t.get("group") == "dark"
            start_rect = self._block_viewport_rect(start_b)
            end_rect = self._block_viewport_rect(end_b)
            if start_rect.isNull() or end_rect.isNull():
                return
            pad_l = 14
            pad_r = 14
            pad_top = 14
            pad_bottom = 20
            header_top = 22
            full_left = min(start_rect.left(), end_rect.left()) - pad_l
            full_top = min(start_rect.top(), end_rect.top()) - pad_top
            full_right = max(start_rect.right(), end_rect.right()) + pad_r
            full_bottom = max(start_rect.bottom(), end_rect.bottom()) + pad_bottom
            x = max(0, full_left)
            y = max(0, full_top)
            w = max(24, full_right - x)
            h = max(40, full_bottom - y)
            outer = QRectF(x, y, w, h)
            radius = 12.0

            painter.save()
            try:
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                base_bg = QColor(t.get("codeblock_bg", "#F2EEE6"))
                border_color = QColor(t.get("border", "#D6E0D1"))
                if is_dark:
                    if border_color.lightness() < 160:
                        border_color = border_color.lighter(120)
                painter.setPen(Qt.PenStyle.NoPen)

                shadow_color = QColor(0, 0, 0, 24) if not is_dark else QColor(0, 0, 0, 70)
                shadow = QRectF(x + 2, y + 4, w, h)
                painter.setBrush(QBrush(shadow_color))
                painter.drawPath(self._rounded_rect_path(shadow, radius))

                painter.setBrush(QBrush(base_bg))
                painter.drawPath(self._rounded_rect_path(outer, radius))

                pen = QPen(border_color)
                pen.setWidthF(1.0)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPath(self._rounded_rect_path(outer, radius))

                split_y = y + pad_top + header_top
                split_pen = QPen(border_color)
                split_pen.setWidthF(0.8)
                painter.setPen(split_pen)
                painter.drawLine(QPointF(x + pad_l, split_y), QPointF(x + w - pad_r, split_y))
            finally:
                painter.restore()
        except Exception:
            return

    def _draw_code_block_chrome(self, painter: QPainter, start_b: int, end_b: int, lang: str):
        try:
            t = self._current_theme()
            is_dark = t.get("group") == "dark"
            start_rect = self._block_viewport_rect(start_b)
            end_rect = self._block_viewport_rect(end_b)
            if start_rect.isNull() or end_rect.isNull():
                return
            pad_l = 14
            pad_r = 14
            pad_top = 14
            full_left = min(start_rect.left(), end_rect.left()) - pad_l
            full_top = min(start_rect.top(), end_rect.top()) - pad_top
            full_right = max(start_rect.right(), end_rect.right()) + pad_r
            full_bottom = max(start_rect.bottom(), end_rect.bottom()) + 20
            x = max(0, full_left)
            y = max(0, full_top)
            w = max(24, full_right - x)
            h = max(40, full_bottom - y)

            painter.save()
            try:
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

                dot_r = 4.2
                dot_gap = 9.0
                dot_y = y + pad_top + 8.0
                base_x = x + pad_l + 6.0
                dot_colors = ("#FF5F57", "#FEBC2E", "#28C840")
                painter.setPen(Qt.PenStyle.NoPen)
                for i, hexcol in enumerate(dot_colors):
                    cx = base_x + (dot_r * 2 + dot_gap) * i + dot_r
                    try:
                        pen_col = QColor(0, 0, 0, 30)
                        p = QPen(pen_col)
                        p.setWidthF(0.6)
                        painter.setPen(p)
                        painter.setBrush(QBrush(QColor(hexcol)))
                        painter.drawEllipse(QPointF(cx, dot_y), dot_r, dot_r)
                    except Exception:
                        continue
                painter.setPen(Qt.PenStyle.NoPen)

                label_lang = (lang or "").lower()
                if not label_lang:
                    label_lang = "code"
                label_font = QFont()
                label_font.setPointSize(9)
                try:
                    label_font.setWeight(500)
                except Exception:
                    label_font.setBold(True)
                fm = QFontMetrics(label_font)
                try:
                    adv = fm.horizontalAdvance(label_lang)
                except Exception:
                    adv = 30
                label_w = max(64, int(adv) + 22)
                label_h = 22
                label_x = x + w - pad_r - label_w
                label_y = y + h - 6
                label_rect = QRectF(label_x, label_y, label_w, label_h)
                label_bg = QColor(255, 255, 255, 160) if not is_dark else QColor(0, 0, 0, 120)
                label_text_fg = QColor("#3F4346") if not is_dark else QColor("#E3E6EA")
                label_border = QColor(0, 0, 0, 40) if not is_dark else QColor(255, 255, 255, 40)
                painter.setBrush(QBrush(label_bg))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawPath(self._rounded_rect_path(label_rect, 6.0))
                lpen = QPen(label_border)
                lpen.setWidthF(0.8)
                painter.setPen(lpen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPath(self._rounded_rect_path(label_rect, 6.0))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setPen(QPen(label_text_fg))
                painter.setFont(label_font)
                painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, label_lang)
            finally:
                painter.restore()
        except Exception:
            return

    def set_background_image(self, path: str, alpha=None):
        if path and isinstance(path, str):
            pm = QPixmap(path)
            if not pm.isNull():
                self._bg_raw_pixmap = pm
                self._bg_path = path
            else:
                self._bg_raw_pixmap = None
                self._bg_path = ""
        else:
            self._bg_raw_pixmap = None
            self._bg_path = ""
        if alpha is not None:
            try:
                a = float(alpha)
                if 0.0 <= a <= 1.0:
                    self._bg_alpha = a
            except Exception:
                pass
        self.viewport().update()

    def clear_background_image(self):
        self._bg_raw_pixmap = None
        self._bg_path = ""
        self.viewport().update()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.viewport().update()

    def paintEvent(self, e):
        vp = self.viewport()
        bg_painted = False
        if self._bg_raw_pixmap is not None and not self._bg_raw_pixmap.isNull():
            painter = QPainter(vp)
            try:
                painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
                painter.setOpacity(self._bg_alpha)
                draw_rect = vp.rect()
                pm = self._bg_raw_pixmap
                pw = pm.width()
                ph = pm.height()
                dw = draw_rect.width()
                dh = draw_rect.height()
                if pw > 0 and ph > 0 and dw > 0 and dh > 0:
                    src_ratio = pw / float(ph)
                    dst_ratio = dw / float(dh)
                    if src_ratio > dst_ratio:
                        new_h = dh
                        new_w = int(new_h * src_ratio)
                        x_off = int((dw - new_w) / 2)
                        y_off = 0
                    else:
                        new_w = dw
                        new_h = int(new_w / src_ratio)
                        x_off = 0
                        y_off = int((dh - new_h) / 2)
                    scaled = pm.scaled(
                        new_w, new_h,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    painter.drawPixmap(x_off, y_off, scaled)
                painter.setOpacity(1.0)
                pal = vp.palette()
                base_color = pal.color(QPalette.ColorRole.Base)
                base_color.setAlpha(220)
                painter.fillRect(draw_rect, base_color)
            finally:
                painter.end()
            bg_painted = True

        # 代码块背景圆角框（在文字内容之前画 → 背景）
        code_blocks = self._collect_code_blocks()
        if code_blocks:
            painter = QPainter(vp)
            try:
                for (sb, eb, lang) in code_blocks:
                    self._draw_code_block_background(painter, sb, eb, lang)
            finally:
                painter.end()

        super().paintEvent(e)

        # 代码块装饰：交通灯圆点 + 语言标签（在文字之上，不挡内容）
        if code_blocks:
            painter = QPainter(vp)
            try:
                for (sb, eb, lang) in code_blocks:
                    self._draw_code_block_chrome(painter, sb, eb, lang)
            finally:
                painter.end()

    def canInsertFromMimeData(self, source: QMimeData) -> bool:
        if source.hasImage():
            return True
        return super().canInsertFromMimeData(source)

    def insertFromMimeData(self, source: QMimeData):
        if source.hasImage():
            img = source.imageData()
            if isinstance(img, QImage) and not img.isNull():
                self.paste_image_requested.emit(img)
                return
        super().insertFromMimeData(source)


class MarkdownEditor(QWidget):
    content_changed = pyqtSignal(str, str, object)
    category_changed = pyqtSignal(object)
    force_save_request = pyqtSignal()

    def __init__(self, parent=None, theme_name: str = DEFAULT_THEME):
        import sys as _sys
        super().__init__(parent)
        self.current_category_id = None
        self.current_note_id = None
        self.current_theme = theme_name
        self._toolbar_btns = []
        self._toolbar_seps = []
        self._constructing = True
        self._build_ui()

        self._last_text_color = QColor("#1F2937")
        self._last_highlight_color = QColor("#FEF08A")
        self._update_color_button_icon(self.text_color_btn, self._last_text_color)
        self._update_color_button_icon(self.highlight_color_btn, self._last_highlight_color)
        self.font_size_combo.currentIndexChanged.connect(self._apply_font_size_to_selection)
        self.text_color_btn.clicked.connect(self._choose_text_color)
        self.highlight_color_btn.clicked.connect(self._choose_highlight_color)
        self.edit.paste_image_requested.connect(self._handle_paste_image)
        self.bg_image_btn.clicked.connect(self._show_background_menu)
        self._app_settings = load_settings()

        self.apply_theme(theme_name, initial=True)
        self.edit.set_background_image(
            self._app_settings.get("bg_image_path", ""),
            self._app_settings.get("bg_image_alpha", 0.18)
        )
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
        hdr_layout.setContentsMargins(64, 20, 64, 14)
        hdr_layout.setSpacing(12)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("未命名笔记")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        self.title_edit.setFont(title_font)
        self.title_edit.textChanged.connect(self._on_any_changed)
        hdr_layout.addWidget(self.title_edit)

        meta_row = FlowLayout(margin=0, spacing=10, h_spacing=10, v_spacing=8)
        meta_row.setSpacing(10)
        self.save_status = QLabel("✓ 已保存")
        self.dot = QLabel("·")
        self.word_count = QLabel("0 字")
        self.cat_label = QLabel("分类")
        self.category_combo = QComboBox()
        self.category_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.category_combo.setMinimumWidth(180)
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
        spacer_lbl = QLabel(" ")
        spacer_lbl.setFixedWidth(6)
        meta_row.addWidget(spacer_lbl)
        meta_row.addWidget(self.cat_label)
        meta_row.addWidget(self.category_combo)
        meta_row.addWidget(self.save_btn)
        hdr_layout.addLayout(meta_row)

        self.toolbar_container = QFrame()
        toolbar_layout_wrap = FlowLayout(self.toolbar_container, margin=6, spacing=3, h_spacing=3, v_spacing=5)
        toolbar_layout_wrap.setSpacing(3)
        toolbar_layout_wrap.setContentsMargins(6, 5, 6, 5)
        self._build_toolbar(toolbar_layout_wrap)
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
        self.edit.setViewportMargins(64, 40, 64, 48)
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
        self.edit.set_theme_name(theme_name)
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
        self.font_size_combo.setStyleSheet(qss["category_combo"])
        self.font_size_label.setStyleSheet(
            f"color:{t['text_secondary']}; font-size:12px; font-weight:500; padding:0 4px;"
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

    def _build_toolbar(self, bar):
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

        sep = QFrame()
        sep.setFixedWidth(1)
        self._toolbar_seps.append(sep)
        bar.addWidget(sep)

        self.font_size_label = QLabel("字号")
        bar.addWidget(self.font_size_label)
        self.font_size_combo = QComboBox()
        self.font_size_combo.setFixedWidth(98)
        self.font_size_combo.setToolTip("选中文本后调整字号（含中文字号：八号～一号）")
        _font_presets = [
            ("八号", 5.0), ("七号", 5.5), ("小六", 6.5), ("六号", 7.5),
            ("小五", 9.0), ("五号", 10.5), ("小四", 12.0), ("四号", 14.0),
            ("小三", 15.0), ("三号", 16.0), ("小二", 18.0), ("二号", 22.0),
            ("小一", 24.0), ("一号", 26.0), ("——", None),
            ("8pt", 8.0), ("28pt", 28.0), ("36pt", 36.0),
            ("48pt", 48.0), ("72pt", 72.0),
        ]
        for label, pt in _font_presets:
            self.font_size_combo.addItem(label, pt)
            if pt is None:
                idx = self.font_size_combo.count() - 1
                f = self.font_size_combo.model().item(idx)
                f.setEnabled(False)
                self.font_size_combo.model().item(idx).setFlags(
                    self.font_size_combo.model().item(idx).flags()
                    & ~Qt.ItemFlag.ItemIsEnabled
                )
        bar.addWidget(self.font_size_combo)

        sep = QFrame()
        sep.setFixedWidth(1)
        self._toolbar_seps.append(sep)
        bar.addWidget(sep)

        self.text_color_btn = QToolButton()
        self.text_color_btn.setText("A")
        self.text_color_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.text_color_btn.setToolTip("文字颜色：选中文字后点击修改前景色")
        self.text_color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        f = QFont()
        f.setBold(True)
        f.setUnderline(True)
        self.text_color_btn.setFont(f)
        self._toolbar_btns.append(self.text_color_btn)
        bar.addWidget(self.text_color_btn)

        self.highlight_color_btn = QToolButton()
        self.highlight_color_btn.setText("🖍")
        self.highlight_color_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.highlight_color_btn.setToolTip("文字高亮：选中文字后点击修改底色（文字填充颜色）")
        self.highlight_color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toolbar_btns.append(self.highlight_color_btn)
        bar.addWidget(self.highlight_color_btn)

        sep_bg = QFrame()
        sep_bg.setFixedWidth(1)
        self._toolbar_seps.append(sep_bg)
        bar.addWidget(sep_bg)

        self.bg_image_btn = QToolButton()
        self.bg_image_btn.setText("🖼 背景")
        self.bg_image_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.bg_image_btn.setToolTip("编辑器背景图：选择本地图片作为背景、调整透明度或清除")
        self.bg_image_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toolbar_btns.append(self.bg_image_btn)
        bar.addWidget(self.bg_image_btn)

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

    def _update_color_button_icon(self, btn: QToolButton, color: QColor):
        pm = QPixmap(22, 16)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(color))
        p.setPen(QPen(QColor(128, 128, 128, 180), 1))
        p.drawRoundedRect(1, 2, 20, 12, 3, 3)
        p.end()
        icon = QIcon(pm)
        btn.setIcon(icon)
        btn.setIconSize(QSize(22, 16))

    def _open_color_dialog(self, initial: QColor, title: str) -> QColor:
        dlg = QColorDialog(initial, self)
        dlg.setWindowTitle(title)
        dlg.setOption(QColorDialog.ColorDialogOption.ShowAlphaChannel, False)
        for sb in dlg.findChildren(QSpinBox):
            sb.setMinimumWidth(116)
            sb.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)
            sb.setStyleSheet(
                "QSpinBox { padding: 4px 26px 4px 8px; font-size: 13px; }"
                "QSpinBox::up-button, QSpinBox::down-button { width: 20px; }"
            )
            f = sb.font()
            f.setPointSize(11)
            sb.setFont(f)
        for le in dlg.findChildren(QLineEdit):
            le.setStyleSheet(
                "QLineEdit { padding: 5px 8px; font-size: 13px; min-height: 22px; }"
            )
            lf = le.font()
            lf.setPointSize(11)
            le.setFont(lf)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            return dlg.currentColor()
        return QColor()

    def _apply_font_size_to_selection(self, index: int):
        pt = self.font_size_combo.itemData(index)
        if pt is None:
            return
        cursor = self._get_cursor()
        fmt = QTextCharFormat()
        fmt.setFontPointSize(float(pt))
        if cursor.hasSelection():
            cursor.mergeCharFormat(fmt)
            self._set_cursor(cursor)
        else:
            self.edit.mergeCurrentCharFormat(fmt)
        self._on_any_changed()

    def _choose_text_color(self):
        color = self._open_color_dialog(
            self._last_text_color, "选择文字颜色（前景）"
        )
        if not color.isValid():
            return
        self._last_text_color = color
        self._update_color_button_icon(self.text_color_btn, color)
        cursor = self._get_cursor()
        fmt = QTextCharFormat()
        fmt.setForeground(color)
        if cursor.hasSelection():
            cursor.mergeCharFormat(fmt)
            self._set_cursor(cursor)
        else:
            self.edit.mergeCurrentCharFormat(fmt)
        self._on_any_changed()

    def _choose_highlight_color(self):
        color = self._open_color_dialog(
            self._last_highlight_color, "选择文字底色（高亮填充）"
        )
        if not color.isValid():
            return
        self._last_highlight_color = color
        self._update_color_button_icon(self.highlight_color_btn, color)
        cursor = self._get_cursor()
        fmt = QTextCharFormat()
        fmt.setBackground(color)
        if cursor.hasSelection():
            cursor.mergeCharFormat(fmt)
            self._set_cursor(cursor)
        else:
            self.edit.mergeCurrentCharFormat(fmt)
        self._on_any_changed()

    def _resolve_image_path(self, path: str) -> str:
        if not path:
            return ""
        p = path.strip()
        if os.path.isabs(p):
            return p
        if p.startswith("assets/") or p.startswith("./assets/"):
            if p.startswith("./"):
                p = p[2:]
            return os.path.join(get_assets_root(), os.path.relpath(p, "assets"))
        return p

    def _render_images_in_doc(self):
        doc = self.edit.document()
        md_img_re = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
        cursor = QTextCursor(doc)
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        while True:
            block = cursor.block()
            if not block.isValid():
                break
            text = block.text()
            matches = list(md_img_re.finditer(text))
            offset = 0
            for m in matches:
                alt = m.group(1) or "image"
                raw_path = m.group(2)
                abs_path = self._resolve_image_path(raw_path)
                if not os.path.exists(abs_path):
                    offset += 0
                    continue
                block_start = block.position()
                start_pos = block_start + m.start() - offset
                end_pos = block_start + m.end() - offset
                sel = QTextCursor(doc)
                sel.setPosition(start_pos)
                sel.setPosition(end_pos, QTextCursor.MoveMode.KeepAnchor)
                img_fmt = QTextImageFormat()
                img_fmt.setName(abs_path)
                img_fmt.setProperty(1001, raw_path)
                img_fmt.setProperty(1002, alt)
                max_w = self.edit.viewport().width() - 80
                img = QImage(abs_path)
                if not img.isNull() and img.width() > max_w:
                    ratio = max_w / float(img.width())
                    img_fmt.setWidth(img.width() * ratio)
                    img_fmt.setHeight(img.height() * ratio)
                sel.insertImage(img_fmt)
                offset += m.end() - m.start() + 1
            if not cursor.movePosition(QTextCursor.MoveOperation.NextBlock):
                break

    def _extract_markdown_from_doc(self) -> str:
        doc = self.edit.document()
        out_lines = []
        block = doc.begin()
        while block.isValid():
            it = block.begin()
            line_parts = []
            while not it.atEnd():
                frag = it.fragment()
                if frag.isValid():
                    fmt = frag.charFormat()
                    if fmt.isImageFormat():
                        raw_path = fmt.property(1001)
                        alt = fmt.property(1002) or ""
                        if isinstance(raw_path, str) and raw_path:
                            line_parts.append(f"![{alt}]({raw_path})")
                        else:
                            img_name = fmt.toImageFormat().name() or ""
                            line_parts.append(f"[]({img_name})")
                    else:
                        line_parts.append(frag.text())
                it += 1
            line_text = "".join(line_parts)
            if not line_text:
                out_lines.append("")
            else:
                out_lines.append(line_text)
            block = block.next()
        return "\n".join(out_lines).rstrip()

    def _handle_paste_image(self, img: QImage):
        if img.isNull():
            return
        assets_dir = get_assets_dir(self.current_note_id)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        rand4 = random.randint(1000, 9999)
        filename = f"paste_{ts}_{rand4}.png"
        full_path = os.path.join(assets_dir, filename)
        img.save(full_path, "PNG")
        if self.current_note_id and self.current_note_id > 0:
            rel_path = f"./assets/note_{self.current_note_id}_images/{filename}"
        else:
            rel_path = f"./assets/_unsaved_images/{filename}"
        alt_name = f"粘贴-{ts}"
        cursor = self.edit.textCursor()
        cursor.insertText(f"\n![{alt_name}]({rel_path})\n")
        self.edit.setTextCursor(cursor)
        self._render_images_in_doc()
        self._on_any_changed()

    def _show_background_menu(self):
        menu = QMenu(self)
        act_choose = QAction("📁 选择本地图片作为背景", self)
        act_choose.triggered.connect(self._choose_background_image)
        menu.addAction(act_choose)

        act_alpha = QAction("🕶 调整背景透明度", self)
        act_alpha.triggered.connect(self._adjust_bg_alpha)
        menu.addAction(act_alpha)

        menu.addSeparator()

        act_clear = QAction("❌ 清除背景图（恢复纯色主题）", self)
        act_clear.triggered.connect(self._clear_background_image)
        menu.addAction(act_clear)
        menu.exec(self.bg_image_btn.mapToGlobal(self.bg_image_btn.rect().bottomLeft()))

    def _choose_background_image(self):
        start_dir = os.path.expanduser("~")
        if self._app_settings.get("bg_image_path"):
            p = self._app_settings["bg_image_path"]
            if os.path.isdir(os.path.dirname(p)):
                start_dir = os.path.dirname(p)
        filename, _ = QFileDialog.getOpenFileName(
            self, "选择背景图片", start_dir,
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tif *.tiff);;所有文件 (*.*)"
        )
        if not filename or not os.path.exists(filename):
            return
        self._app_settings = save_settings(bg_image_path=filename)
        alpha = self._app_settings.get("bg_image_alpha", 0.18)
        self.edit.set_background_image(filename, alpha)

    def _adjust_bg_alpha(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("调整背景图透明度")
        dlg.setMinimumWidth(420)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(22, 20, 22, 18)
        cur_val = int(self._app_settings.get("bg_image_alpha", 0.18) * 100)
        top_row = QHBoxLayout()
        lbl = QLabel("透明度（值越小，背景图越淡）")
        top_row.addWidget(lbl)
        top_row.addStretch(1)
        val_lbl = QLabel(f"{cur_val}%")
        val_lbl.setMinimumWidth(46)
        val_lbl.setStyleSheet("font-weight:600;")
        top_row.addWidget(val_lbl)
        lay.addLayout(top_row)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(2, 90)
        slider.setValue(max(2, min(90, cur_val)))
        lay.addWidget(slider)
        tip = QLabel("建议值：浅背景 12%～25%，深色背景 20%～40%")
        tip.setStyleSheet("color:#888; font-size:12px;")
        lay.addWidget(tip)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.button(QDialogButtonBox.StandardButton.Ok).setText("确定")
        bb.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        lay.addWidget(bb)
        slider.valueChanged.connect(lambda v: val_lbl.setText(f"{v}%"))
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_alpha = slider.value() / 100.0
            self._app_settings = save_settings(bg_image_alpha=new_alpha)
            path = self._app_settings.get("bg_image_path", "")
            if path:
                self.edit.set_background_image(path, new_alpha)
            else:
                self.edit._bg_alpha = new_alpha
                self.edit.viewport().update()

    def _clear_background_image(self):
        self._app_settings = save_settings(bg_image_path="")
        self.edit.clear_background_image()

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
                    "h6":    (22, MIN, 8,  4),
                    "p":     (26, MIN, 5,  5),
                    "ul":    (25, MIN, 4,  3),
                    "ol":    (25, MIN, 4,  3),
                    "quote": (26, MIN, 6,  6),
                    "code":  (24, MIN, 2,  2),
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
        content = self._extract_markdown_from_doc()
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

    def set_note(self, note_id, title: str, content: str, category_id, categories: List[Category]):
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
        self.current_note_id = note_id

        self.title_edit.blockSignals(True)
        self.edit.blockSignals(True)
        self.title_edit.setText(title or "")
        self.edit.setPlainText(content or "")
        self._last_block_types.clear()
        self._highlighter.set_active_cursor(-1, -1)
        self._highlighter.rehighlight()
        self._apply_block_formats()
        self._render_images_in_doc()
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
