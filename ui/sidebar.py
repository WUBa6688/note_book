from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QLineEdit, QInputDialog, QMessageBox,
    QMenu, QSplitter, QComboBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QAction, QIcon, QFont
from typing import Optional, List
from core.database import DatabaseManager, Note, Category
from .theme import THEMES, DEFAULT_THEME, get_sidebar_qss, get_sidebar_note_list_qss


class NoteListWidget(QListWidget):
    note_deleted = pyqtSignal(int)

    def __init__(self, parent=None, theme_name: str = DEFAULT_THEME):
        super().__init__(parent)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.apply_theme(theme_name)

    def apply_theme(self, theme_name: str):
        self.setStyleSheet(get_sidebar_note_list_qss(THEMES[theme_name]))

    def _show_context_menu(self, pos):
        item = self.itemAt(pos)
        if item is None:
            return
        menu = QMenu(self)
        delete_action = QAction("删除笔记", self)
        delete_action.triggered.connect(
            lambda: self.note_deleted.emit(item.data(Qt.ItemDataRole.UserRole))
        )
        menu.addAction(delete_action)
        menu.exec(self.mapToGlobal(pos))


class Sidebar(QWidget):
    note_selected = pyqtSignal(int)
    new_note_requested = pyqtSignal()
    note_delete_requested = pyqtSignal(int)
    search_text_changed = pyqtSignal(str)
    category_changed = pyqtSignal(int)
    theme_change_requested = pyqtSignal(str)

    def __init__(self, db: DatabaseManager, parent=None, theme_name: str = DEFAULT_THEME):
        super().__init__(parent)
        self.db = db
        self.current_category_id = None
        self.current_theme = theme_name
        self._build_ui()
        self.apply_theme(theme_name)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.header = QFrame()
        header_layout = QVBoxLayout(self.header)
        header_layout.setContentsMargins(20, 20, 20, 16)
        header_layout.setSpacing(12)

        self.title_label = QLabel("\U0001f4d2 Zhuibook")
        title_font = QFont()
        title_font.setPointSize(17)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        header_layout.addWidget(self.title_label)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("\U0001f50d  搜索笔记标题或内容...")
        self.search_edit.textChanged.connect(self.search_text_changed.emit)
        header_layout.addWidget(self.search_edit)

        self.category_combo = QComboBox()
        self.category_combo.currentIndexChanged.connect(self._on_category_changed)
        header_layout.addWidget(self.category_combo)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.new_note_btn = QPushButton("\u270f\ufe0f  新建笔记")
        self.new_note_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_note_btn.clicked.connect(self.new_note_requested.emit)
        btn_row.addWidget(self.new_note_btn)

        self.manage_cat_btn = QPushButton("\U0001f4c1")
        self.manage_cat_btn.setFixedWidth(40)
        self.manage_cat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.manage_cat_btn.clicked.connect(self._manage_categories)
        btn_row.addWidget(self.manage_cat_btn)

        self.theme_btn = QPushButton("\U0001f3a8")
        self.theme_btn.setFixedWidth(40)
        self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_btn.setToolTip("切换主题配色")
        self.theme_btn.clicked.connect(self._show_theme_menu)
        self._theme_menu = None
        btn_row.addWidget(self.theme_btn)

        header_layout.addLayout(btn_row)
        layout.addWidget(self.header)

        self.list_label = QLabel("    笔记列表")
        layout.addWidget(self.list_label)

        self.note_list = NoteListWidget(theme_name=self.current_theme)
        self.note_list.itemClicked.connect(self._on_note_clicked)
        self.note_list.note_deleted.connect(self._on_note_delete)
        layout.addWidget(self.note_list, 1)

        self.setMinimumWidth(300)
        self.setMaximumWidth(420)
        self.refresh_categories()
        self.refresh_notes()

    def apply_theme(self, theme_name: str):
        self.current_theme = theme_name
        t = THEMES[theme_name]
        qss = get_sidebar_qss(t)
        self.header.setStyleSheet(qss["header"])
        self.title_label.setStyleSheet(qss["title"])
        self.search_edit.setStyleSheet(qss["search"])
        self.category_combo.setStyleSheet(qss["combo"])
        self.new_note_btn.setStyleSheet(qss["new_btn"])
        self.manage_cat_btn.setStyleSheet(qss["cat_btn"])
        self.theme_btn.setStyleSheet(qss["cat_btn"])
        self.list_label.setStyleSheet(qss["list_label"])
        self.note_list.apply_theme(theme_name)

    def _show_theme_menu(self):
        from PyQt6.QtGui import QAction
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        for key in ("matcha", "lemon", "fog"):
            t = THEMES[key]
            action = QAction(t["name"], self)
            action.setCheckable(True)
            action.setChecked(key == self.current_theme)
            action.triggered.connect(lambda _=False, k=key: self.theme_change_requested.emit(k))
            menu.addAction(action)
        menu.exec(self.theme_btn.mapToGlobal(self.theme_btn.rect().bottomLeft()))

    def refresh_categories(self):
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        self.category_combo.addItem("\U0001f4da 全部笔记", -1)
        self.category_combo.addItem("\U0001f4c4 未分类", None)
        for cat in self.db.get_all_categories():
            self.category_combo.addItem(f"\U0001f4c1 {cat.name}", cat.id)
        self.category_combo.blockSignals(False)
        self.category_combo.setCurrentIndex(0)
        self.current_category_id = -1

    def refresh_notes(self, keyword=None):
        self.note_list.clear()
        if keyword:
            notes = self.db.search_notes(keyword)
        else:
            if self.current_category_id == -1:
                notes = self.db.get_all_notes()
            else:
                notes = self.db.get_notes_by_category(self.current_category_id)
        for note in notes:
            self._add_note_item(note)

    def _add_note_item(self, note: Note):
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, note.id)
        title = note.title if note.title.strip() else "（无标题）"
        preview = ""
        content = note.content.strip()
        if content:
            lines = [l.strip().lstrip("#").strip() for l in content.splitlines() if l.strip()]
            preview = lines[0][:40] if lines else ""
        if preview and preview != title:
            item.setText(f"{title}\n   \U0001f32b  {preview}")
        else:
            item.setText(title)
        self.note_list.addItem(item)

    def _on_category_changed(self, index: int):
        if index < 0:
            return
        data = self.category_combo.itemData(index)
        self.current_category_id = data
        self.search_edit.clear()
        self.refresh_notes()

    def _on_note_clicked(self, item: QListWidgetItem):
        note_id = item.data(Qt.ItemDataRole.UserRole)
        self.note_selected.emit(note_id)

    def select_note_by_id(self, note_id: int):
        for i in range(self.note_list.count()):
            it = self.note_list.item(i)
            if int(it.data(Qt.ItemDataRole.UserRole) or 0) == int(note_id):
                self.note_list.setCurrentItem(it)
                self._on_note_clicked(it)
                return True
        return False

    def _on_note_delete(self, note_id: int):
        reply = QMessageBox.question(
            self, "删除笔记", "确定要删除这篇笔记吗？此操作无法撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db.delete_note(note_id)
            self.note_delete_requested.emit(note_id)
            self.refresh_notes()

    def _manage_categories(self):
        menu = QMenu(self)
        new_cat = QAction("\u2795 新建分类", self)
        new_cat.triggered.connect(self._new_category)
        menu.addAction(new_cat)
        rename_cat = QAction("\u270f\ufe0f  重命名分类", self)
        rename_cat.triggered.connect(self._rename_category)
        menu.addAction(rename_cat)
        del_cat = QAction("\U0001f5d1  删除分类", self)
        del_cat.triggered.connect(self._delete_category)
        menu.addAction(del_cat)
        menu.exec(self.manage_cat_btn.mapToGlobal(self.manage_cat_btn.rect().bottomLeft()))

    def _new_category(self):
        name, ok = QInputDialog.getText(self, "新建分类", "请输入分类名称：")
        if ok and name.strip():
            try:
                self.db.create_category(name.strip())
                self.refresh_categories()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"创建失败：{e}")

    def _rename_category(self):
        cats = self.db.get_all_categories()
        if not cats:
            QMessageBox.information(self, "提示", "暂无分类可重命名。")
            return
        items = [c.name for c in cats]
        choice, ok = QInputDialog.getItem(self, "选择分类", "选择要重命名的分类：", items, 0, False)
        if not ok:
            return
        cat = next(c for c in cats if c.name == choice)
        new_name, ok2 = QInputDialog.getText(self, "重命名", "输入新名称：", text=cat.name)
        if ok2 and new_name.strip():
            try:
                self.db.update_category(cat.id, new_name.strip())
                self.refresh_categories()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"重命名失败：{e}")

    def _delete_category(self):
        cats = self.db.get_all_categories()
        if not cats:
            QMessageBox.information(self, "提示", "暂无分类可删除。")
            return
        items = [c.name for c in cats]
        choice, ok = QInputDialog.getItem(self, "删除分类", "选择要删除的分类（笔记不会被删除）：", items, 0, False)
        if not ok:
            return
        cat = next(c for c in cats if c.name == choice)
        reply = QMessageBox.question(
            self, "删除分类", f"确定删除分类「{cat.name}」？该分类下的笔记将变为未分类。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db.delete_category(cat.id)
            self.refresh_categories()
            self.refresh_notes()
