from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QSplitter, QStatusBar, QLabel,
    QMessageBox, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut, QColor
from typing import Optional
from core.database import DatabaseManager, Note
from .sidebar import Sidebar
from .editor import MarkdownEditor
from .theme import THEMES, DEFAULT_THEME, get_mainwindow_qss


class MainWindow(QMainWindow):
    def __init__(self, db: DatabaseManager, theme_name: str = DEFAULT_THEME):
        super().__init__()
        self.db = db
        self.current_theme = theme_name
        self.current_note_id: Optional[int] = None
        self._pending_save = False
        self._build_ui()
        self.apply_theme_to_all(theme_name)
        self._build_shortcuts()
        QTimer.singleShot(100, self._load_first_note)

    def _build_ui(self):
        self.setWindowTitle("Zhuibook · 现代 Markdown 笔记")
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(1)
        self.splitter = splitter

        self.sidebar = Sidebar(self.db, theme_name=self.current_theme)
        self.editor = MarkdownEditor(theme_name=self.current_theme)

        sidebar_shadow = QGraphicsDropShadowEffect()
        sidebar_shadow.setBlurRadius(24)
        sidebar_shadow.setXOffset(2)
        sidebar_shadow.setYOffset(0)
        sidebar_shadow.setColor(QColor(110, 100, 80, 28))
        self.sidebar.setGraphicsEffect(sidebar_shadow)

        splitter.addWidget(self.sidebar)
        splitter.addWidget(self.editor)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([340, 900])

        root.addWidget(splitter)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status_label = QLabel("💡 提示：Ctrl+N 新建 · Ctrl+S 保存 · 移动光标到语法标记附近可查看源码")
        self.status.addPermanentWidget(self.status_label)

        self.sidebar.note_selected.connect(self._on_note_selected)
        self.sidebar.new_note_requested.connect(self._on_new_note)
        self.sidebar.note_delete_requested.connect(self._on_note_deleted)
        self.sidebar.search_text_changed.connect(self._on_search)
        self.sidebar.category_changed.connect(lambda _: self._refresh_editor_categories())
        self.sidebar.theme_change_requested.connect(self.apply_theme_to_all)

        self.editor.content_changed.connect(self._on_editor_content_changed)
        self.editor.category_changed.connect(self._on_editor_category_changed)

    def apply_theme_to_all(self, theme_name: str):
        self.current_theme = theme_name
        t = THEMES[theme_name]
        qss = get_mainwindow_qss(t)
        self.setStyleSheet(qss["global"])
        self.status.setStyleSheet(qss["status_bar"])
        self.status_label.setStyleSheet(
            f"color: {t['text_secondary']}; padding: 2px 8px; font-size: 12px;"
        )
        self.sidebar.apply_theme(theme_name)
        self.editor.apply_theme(theme_name)

    def _build_shortcuts(self):
        new_sc = QShortcut(QKeySequence.StandardKey.New, self)
        new_sc.activated.connect(self._on_new_note)
        save_sc = QShortcut(QKeySequence.StandardKey.Save, self)
        save_sc.activated.connect(self._force_save_current)

    def _load_first_note(self):
        notes = self.db.get_all_notes()
        if notes:
            self._open_note(notes[0].id)

    def _open_note(self, note_id: int):
        note = self.db.get_note(note_id)
        if not note:
            return
        self._save_current_if_needed()
        self._do_open_note(note)

    def _do_open_note(self, note: Note):
        self.current_note_id = note.id
        categories = self.db.get_all_categories()
        self.editor.set_note(note.title, note.content, note.category_id, categories)
        self._pending_save = False
        self._update_status(f"📝 打开笔记: {note.title or '无标题'}")

    def _save_current_if_needed(self):
        if not self.current_note_id or not self._pending_save:
            return
        title = self.editor.get_title_sync()
        content = self.editor.get_content_sync()
        cat_idx = self.editor.category_combo.currentIndex()
        cat_id = self.editor.category_combo.itemData(cat_idx) if cat_idx >= 0 else None
        self.db.update_note(self.current_note_id, title=title, content=content, category_id=cat_id)
        self._pending_save = False
        self.sidebar.refresh_notes()

    def _refresh_editor_categories(self):
        categories = self.db.get_all_categories()
        current_cat = None
        if self.current_note_id:
            note = self.db.get_note(self.current_note_id)
            if note:
                current_cat = note.category_id
        self.editor.update_categories(categories, current_cat)

    def _on_note_selected(self, note_id: int):
        self._open_note(note_id)

    def _on_new_note(self):
        self._save_current_if_needed()
        self._do_create_note()

    def _do_create_note(self):
        category_id = self.sidebar.current_category_id
        if category_id == -1:
            cats = self.db.get_all_categories()
            category_id = cats[0].id if cats else None
        note = self.db.create_note("未命名笔记", "", category_id=category_id)
        self.current_note_id = note.id
        categories = self.db.get_all_categories()
        self.editor.set_note(note.title, note.content, note.category_id, categories)
        self._pending_save = True
        self.db.update_note(self.current_note_id, title=note.title, content=note.content, category_id=category_id)
        self._pending_save = False
        self.sidebar.refresh_notes()
        self._update_status(f"✨ 新建笔记: {note.title}")

    def _on_note_deleted(self, note_id: int):
        if note_id == self.current_note_id:
            self.current_note_id = None
            self.editor.set_note("", "", None, self.db.get_all_categories())
            self._pending_save = False
        notes = self.db.get_all_notes()
        if self.current_note_id is None and notes:
            self._open_note(notes[0].id)

    def _on_search(self, keyword: str):
        self.sidebar.refresh_notes(keyword.strip() if keyword.strip() else None)

    def _on_editor_content_changed(self, title: str, content: str, category_id):
        if not self.current_note_id:
            return
        self._pending_save = True
        self.db.update_note(
            self.current_note_id,
            title=title,
            content=content,
            category_id=category_id
        )
        self._pending_save = False
        QTimer.singleShot(30, self.sidebar.refresh_notes)

    def _on_editor_category_changed(self, category_id):
        if not self.current_note_id:
            return
        self._pending_save = True
        self.db.update_note(self.current_note_id, category_id=category_id)
        self._pending_save = False
        self.sidebar.refresh_notes()

    def _force_save_current(self):
        if not self.current_note_id:
            self._update_status("⚠️ 当前没有打开的笔记")
            return
        title = self.editor.get_title_sync()
        content = self.editor.get_content_sync()
        cat_idx = self.editor.category_combo.currentIndex()
        cat_id = self.editor.category_combo.itemData(cat_idx) if cat_idx >= 0 else None
        self.db.update_note(self.current_note_id, title=title, content=content, category_id=cat_id)
        self._pending_save = False
        self.sidebar.refresh_notes()
        self.editor._set_save_status("saved")
        self._update_status("💾 笔记已保存")

    def _update_status(self, msg: str):
        self.status.showMessage(msg, 4000)

    def closeEvent(self, event):
        if self._pending_save and self.current_note_id:
            reply = QMessageBox.question(
                self, "保存确认", "是否保存当前笔记的更改？",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )
            if reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            if reply == QMessageBox.StandardButton.Save:
                self._force_save_current()
        event.accept()
