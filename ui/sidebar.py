from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QLineEdit, QInputDialog, QMessageBox,
    QMenu, QSplitter, QComboBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QAction, QIcon, QFont
from typing import Optional, List
from core.database import DatabaseManager, Note, Category


class NoteListWidget(QListWidget):
    note_deleted = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.setStyleSheet("""
            QListWidget {
                border: none;
                background: #fafafa;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 10px 14px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background: #e8f0fe;
                color: #1a73e8;
            }
            QListWidget::item:hover {
                background: #f0f4f8;
            }
        """)

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

    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db
        self.current_category_id = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header = QFrame()
        header.setStyleSheet("background: #ffffff; border-bottom: 1px solid #e0e0e0;")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(16, 16, 16, 12)
        header_layout.setSpacing(10)

        title = QLabel("\U0001f4d2 Zhuibook")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #1a73e8;")
        header_layout.addWidget(title)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("\U0001f50d 搜索笔记...")
        self.search_edit.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                border: 1px solid #ddd;
                border-radius: 6px;
                background: #f5f5f5;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #1a73e8;
                background: #ffffff;
            }
        """)
        self.search_edit.textChanged.connect(self.search_text_changed.emit)
        header_layout.addWidget(self.search_edit)

        self.category_combo = QComboBox()
        self.category_combo.setStyleSheet("""
            QComboBox {
                padding: 7px 10px;
                border: 1px solid #ddd;
                border-radius: 6px;
                background: #ffffff;
                font-size: 13px;
            }
            QComboBox::drop-down { border: none; width: 24px; }
        """)
        self.category_combo.currentIndexChanged.connect(self._on_category_changed)
        header_layout.addWidget(self.category_combo)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.new_note_btn = QPushButton("\u270f\ufe0f  新建笔记")
        self.new_note_btn.setStyleSheet("""
            QPushButton {
                background: #1a73e8;
                color: white;
                border: none;
                padding: 8px 14px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover { background: #1557b0; }
            QPushButton:pressed { background: #0d47a1; }
        """)
        self.new_note_btn.clicked.connect(self.new_note_requested.emit)
        btn_row.addWidget(self.new_note_btn)

        self.manage_cat_btn = QPushButton("\U0001f4c1")
        self.manage_cat_btn.setFixedWidth(38)
        self.manage_cat_btn.setStyleSheet("""
            QPushButton {
                background: #f0f0f0;
                border: 1px solid #ddd;
                border-radius: 6px;
                font-size: 15px;
            }
            QPushButton:hover { background: #e8e8e8; }
        """)
        self.manage_cat_btn.clicked.connect(self._manage_categories)
        btn_row.addWidget(self.manage_cat_btn)

        header_layout.addLayout(btn_row)
        layout.addWidget(header)

        list_label = QLabel("    笔记列表")
        list_label.setStyleSheet("padding: 4px 16px; color: #666; font-size: 12px; font-weight: bold;")
        layout.addWidget(list_label)

        self.note_list = NoteListWidget()
        self.note_list.itemClicked.connect(self._on_note_clicked)
        self.note_list.note_deleted.connect(self._on_note_delete)
        layout.addWidget(self.note_list, 1)

        self.setMinimumWidth(300)
        self.setMaximumWidth(420)
        self.refresh_categories()
        self.refresh_notes()

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
