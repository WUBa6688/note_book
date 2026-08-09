from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter, QStatusBar,
    QLabel, QMessageBox, QGraphicsDropShadowEffect, QStackedWidget
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut, QColor
from typing import Optional
from core.database import DatabaseManager, Note
from .sidebar import Sidebar
from .editor import MarkdownEditor
from .top_tab_bar import TopTabBar
from .drawing_board import DrawingBoardView
from .theme import THEMES, DEFAULT_THEME, get_mainwindow_qss


class MainWindow(QMainWindow):
    def __init__(self, db: DatabaseManager, theme_name: str = DEFAULT_THEME):
        super().__init__()
        self.db = db
        self.current_theme = theme_name
        self.current_note_id: Optional[int] = None
        self._pending_save = False
        # 画板视图懒加载（首次切换到「画板」时创建）
        self.drawing_view: Optional[DrawingBoardView] = None
        self._drawing_placeholder: Optional[QWidget] = None
        self._build_ui()
        self.apply_theme_to_all(theme_name)
        self._build_shortcuts()
        QTimer.singleShot(100, self._load_first_note)

    def _build_ui(self):
        self.setWindowTitle("Zhuibook · 现代 Markdown 笔记")
        self.resize(1240, 780)
        self.setMinimumSize(960, 600)
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 1. 顶部 Tab 切换栏（📝 笔记 / 🖌 画板）
        self.tab_bar = TopTabBar(theme_name=self.current_theme)
        self.tab_bar.view_changed.connect(self._on_view_changed)
        root.addWidget(self.tab_bar)

        # 2. 下方 QStackedWidget：page 0 = 笔记视图，page 1 = 画板视图（懒加载）
        self.stack = QStackedWidget()
        self.stack.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.stack, 1)

        # ---- page 0：原 QSplitter(sidebar + editor) → NoteView ----
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(4)
        splitter.setStyleSheet("QSplitter::handle{background:transparent;} QSplitter::handle:hover{background:rgba(0,0,0,40);}")
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

        self.stack.addWidget(splitter)  # index 0

        # ---- page 1：画板占位（首次切换时替换为 DrawingBoardView）----
        self._drawing_placeholder = QWidget()
        self.stack.addWidget(self._drawing_placeholder)  # index 1

        # 默认显示笔记视图
        self.stack.setCurrentIndex(0)

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

    # -------------------------------------------------------------------
    # 视图切换（笔记 / 画板）
    # -------------------------------------------------------------------
    def _on_view_changed(self, view: str):
        """切换 QStackedWidget 页面，首次切换到 drawing 时创建画板视图。"""
        if view == "drawing":
            self._ensure_drawing_view()
            self.stack.setCurrentIndex(1)
        else:
            self.stack.setCurrentIndex(0)

    def _ensure_drawing_view(self):
        """懒加载创建画板视图，替换占位 widget。"""
        if self.drawing_view is not None:
            return
        self.drawing_view = DrawingBoardView(self.db, theme_name=self.current_theme)
        self.drawing_view.apply_theme(self.current_theme)
        self.drawing_view.insert_to_note_requested.connect(self._insert_drawing_to_note)
        # 替换占位 widget（保持 index=1）
        idx = self.stack.indexOf(self._drawing_placeholder) if self._drawing_placeholder else 1
        if self._drawing_placeholder is not None:
            self.stack.removeWidget(self._drawing_placeholder)
            self._drawing_placeholder.deleteLater()
            self._drawing_placeholder = None
        self.stack.insertWidget(idx, self.drawing_view)

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
        # 顶部 Tab 栏同步主题
        self.tab_bar.apply_theme(theme_name)
        # 画板视图同步主题（如已创建）
        if self.drawing_view is not None:
            self.drawing_view.apply_theme(theme_name)

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
        self._flush_editor_save()
        note = self.db.get_note(note_id)
        if not note:
            return
        self._save_current_if_needed()
        self._do_open_note(note)

    def _do_open_note(self, note: Note):
        self.current_note_id = note.id
        categories = self.db.get_all_categories()
        self.editor.set_note(note.id, note.title, note.content, note.category_id, categories)
        self._pending_save = False
        self._update_status(f"📝 打开笔记: {note.title or '无标题'}")

    def _save_current_if_needed(self):
        self._flush_editor_save()
        if not self.current_note_id or not self._pending_save:
            return
        title = self.editor.get_title_sync()
        content = self.editor.get_content_sync()
        cat_idx = self.editor.category_combo.currentIndex()
        cat_id = self.editor.category_combo.itemData(cat_idx) if cat_idx >= 0 else None
        self.db.update_note(self.current_note_id, title=title, content=content, category_id=cat_id)
        self._pending_save = False
        self.sidebar.refresh_notes()

    def _flush_editor_save(self):
        if self.current_note_id and hasattr(self.editor, "flush_pending_save"):
            self.editor.flush_pending_save()

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
        self.editor.set_note(note.id, note.title, note.content, note.category_id, categories)
        self._pending_save = True
        self.db.update_note(self.current_note_id, title=note.title, content=note.content, category_id=category_id)
        self._pending_save = False
        self.sidebar.refresh_notes()
        self._update_status(f"✨ 新建笔记: {note.title}")

    def _on_note_deleted(self, note_id: int):
        if note_id == self.current_note_id:
            self.current_note_id = None
            self.editor.set_note(None, "", "", None, self.db.get_all_categories())
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
        self._flush_editor_save()
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

    # -------------------------------------------------------------------
    # 画板内容嵌入当前笔记
    # -------------------------------------------------------------------
    def _insert_drawing_to_note(self):
        """将画板内容保存为图片并插入当前笔记的光标处。"""
        if self.drawing_view is None:
            return
        if not self.drawing_view.has_unsaved_content():
            self._update_status("⚠️ 画板为空，无内容可插入")
            return
        if not self.current_note_id:
            self._update_status("⚠️ 请先打开或新建一篇笔记")
            return
        try:
            md_path = self.drawing_view.insert_to_current_note(self.current_note_id)
        except Exception as e:
            self._update_status(f"⚠️ 插入画板失败：{e}")
            return
        if not md_path:
            self._update_status("⚠️ 插入画板失败：未生成图片路径")
            return
        # 切回笔记视图并插入图片引用
        self.tab_bar.set_current("note")
        self.stack.setCurrentIndex(0)
        self.editor.insert_image_at_cursor(md_path, alt="drawing")
        self._update_status(f"✅ 画板已插入笔记：{md_path}")

    def closeEvent(self, event):
        self._flush_editor_save()
        # 笔记未保存内容确认
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
        # 画板未保存内容确认
        if self.drawing_view is not None and self.drawing_view.has_unsaved_content():
            reply = QMessageBox.question(
                self, "画板内容", "画板上有未保存的内容，是否在退出前保存为文件？",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )
            if reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            if reply == QMessageBox.StandardButton.Save:
                self.drawing_view._save_to_file()
        event.accept()
