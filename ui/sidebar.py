from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QLineEdit, QInputDialog, QMessageBox,
    QMenu, QSplitter, QComboBox, QFrame, QDialog, QDialogButtonBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QAction, QIcon, QFont, QIntValidator
from typing import Optional, List
from core.database import DatabaseManager, Note, Category
from core.settings import load_settings, save_settings
from core.security import hash_password, verify_password, is_valid_password_format
from .theme import THEMES, DEFAULT_THEME, get_sidebar_qss, get_sidebar_note_list_qss


class PasswordDialog(QDialog):
    """密码输入对话框：支持设置密码（含确认）和验证密码两种模式。"""

    def __init__(self, parent=None, theme_name: str = DEFAULT_THEME, mode: str = "verify"):
        super().__init__(parent)
        self._mode = mode
        self._theme_name = theme_name
        self.setWindowTitle("设置密码" if mode == "set" else "输入密码")
        self.setModal(True)
        self.setFixedWidth(340)
        self._build_ui()
        self._apply_theme()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(12)

        hint = QLabel("请设置私密笔记密码（4或6位数字）" if self._mode == "set"
                      else "请输入私密笔记密码（4或6位数字）")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.pwd_edit = QLineEdit()
        self.pwd_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd_edit.setMaxLength(6)
        self.pwd_edit.setValidator(QIntValidator(0, 999999))
        self.pwd_edit.setPlaceholderText("4或6位数字")
        layout.addWidget(self.pwd_edit)

        if self._mode == "set":
            confirm_hint = QLabel("请再次输入密码确认")
            layout.addWidget(confirm_hint)
            self.confirm_edit = QLineEdit()
            self.confirm_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.confirm_edit.setMaxLength(6)
            self.confirm_edit.setValidator(QIntValidator(0, 999999))
            self.confirm_edit.setPlaceholderText("再次输入密码")
            layout.addWidget(self.confirm_edit)
        else:
            self.confirm_edit = None

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self._on_accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _on_accept(self):
        pwd = self.pwd_edit.text().strip()
        if not is_valid_password_format(pwd):
            QMessageBox.warning(self, "格式错误",
                "密码格式不正确。\n请输入 4 位或 6 位纯数字（例如 1234 或 123456）。")
            self.pwd_edit.selectAll()
            self.pwd_edit.setFocus()
            return
        if self._mode == "set" and self.confirm_edit is not None:
            confirm = self.confirm_edit.text().strip()
            if not is_valid_password_format(confirm):
                QMessageBox.warning(self, "格式错误",
                    "确认密码格式不正确。\n请输入 4 位或 6 位纯数字。")
                self.confirm_edit.selectAll()
                self.confirm_edit.setFocus()
                return
            if pwd != confirm:
                QMessageBox.warning(self, "密码不一致",
                    "两次输入的密码不一致，请重新输入。")
                self.confirm_edit.selectAll()
                self.confirm_edit.setFocus()
                return
        self.accept()

    def get_password(self) -> str:
        return self.pwd_edit.text().strip()

    def _apply_theme(self):
        t = THEMES[self._theme_name]
        self.setStyleSheet(f"""
            QDialog {{ background: {t['card_bg']}; }}
            QLabel {{ color: {t['text_secondary']}; font-size: 13px; }}
            QLineEdit {{
                padding: 8px 12px;
                border: 1px solid {t['border']};
                border-radius: 8px;
                background: {t['input_bg']};
                color: {t['text_primary']};
                font-size: 16px;
                letter-spacing: 4px;
            }}
            QLineEdit:focus {{ border: 1px solid {t['primary']}; }}
        """)
        for btn in self.findChildren(QDialogButtonBox):
            btn.setStyleSheet(f"""
                QPushButton {{
                    padding: 6px 16px;
                    border: 1px solid {t['border']};
                    border-radius: 8px;
                    background: {t['card_bg']};
                    color: {t['text_primary']};
                    font-size: 13px;
                }}
                QPushButton:hover {{ background: {t['list_hover_bg']}; }}
                QPushButton:pressed {{ background: {t['selection_bg']}; }}
            """)


class NoteListWidget(QListWidget):
    note_deleted = pyqtSignal(int)
    note_toggle_private = pyqtSignal(int)  # note_id

    def __init__(self, parent=None, theme_name: str = DEFAULT_THEME):
        super().__init__(parent)
        self._theme_name = theme_name
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.apply_theme(theme_name)

    def apply_theme(self, theme_name: str):
        self._theme_name = theme_name
        self.setStyleSheet(get_sidebar_note_list_qss(THEMES[theme_name]))

    def _show_context_menu(self, pos):
        item = self.itemAt(pos)
        if item is None:
            return
        note_id = item.data(Qt.ItemDataRole.UserRole)
        is_private = item.data(Qt.ItemDataRole.UserRole + 1) or False

        menu = QMenu(self)
        # 私密切换
        if is_private:
            private_action = QAction("🔓 取消私密", self)
        else:
            private_action = QAction("🔒 设为私密笔记", self)
        private_action.triggered.connect(lambda: self.note_toggle_private.emit(note_id))
        menu.addAction(private_action)

        menu.addSeparator()

        delete_action = QAction("删除笔记", self)
        delete_action.triggered.connect(lambda: self.note_deleted.emit(note_id))
        menu.addAction(delete_action)
        menu.exec(self.mapToGlobal(pos))


class Sidebar(QWidget):
    note_selected = pyqtSignal(int)
    new_note_requested = pyqtSignal()
    note_delete_requested = pyqtSignal(int)
    search_text_changed = pyqtSignal(str)
    category_changed = pyqtSignal(int)
    theme_change_requested = pyqtSignal(str)
    private_note_opened = pyqtSignal(int)  # 当前打开的私密笔记ID（用于锁定时清空编辑器）

    def __init__(self, db: DatabaseManager, parent=None, theme_name: str = DEFAULT_THEME):
        super().__init__(parent)
        self.db = db
        self.current_category_id = None
        self.current_theme = theme_name
        self._private_unlocked = False
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
        self.search_edit.textChanged.connect(self._on_search_text_changed)
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

        # 笔记列表标题行 + 锁定按钮
        label_row = QHBoxLayout()
        label_row.setContentsMargins(0, 0, 0, 0)
        label_row.setSpacing(8)
        self.list_label = QLabel("    笔记列表")
        label_row.addWidget(self.list_label)
        label_row.addStretch()
        self.lock_btn = QPushButton("🔒 锁定")
        self.lock_btn.setFixedHeight(26)
        self.lock_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lock_btn.setToolTip("锁定私密笔记，返回全部笔记")
        self.lock_btn.clicked.connect(self._lock_private)
        self.lock_btn.hide()
        label_row.addWidget(self.lock_btn)
        layout.addLayout(label_row)

        self.note_list = NoteListWidget(theme_name=self.current_theme)
        self.note_list.itemClicked.connect(self._on_note_clicked)
        self.note_list.note_deleted.connect(self._on_note_delete)
        self.note_list.note_toggle_private.connect(self._on_toggle_private)
        layout.addWidget(self.note_list, 1)

        self.setMinimumWidth(300)
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
        self.theme_btn.setStyleSheet(qss.get("theme_btn", qss["cat_btn"]))
        self.list_label.setStyleSheet(qss["list_label"])
        lock_style = (
            f"QPushButton {{ background: {t['primary']}; border: none; color: #fff; font-size: 12px; border-radius: 6px; padding: 0 10px; }}"
            f"QPushButton:hover {{ background: {t['selection_bg']}; color: {t['primary']}; }}"
            f"QPushButton:pressed {{ background: {t['primary']}; }}"
        )
        self.lock_btn.setStyleSheet(lock_style)
        self.note_list.apply_theme(theme_name)

    def _show_theme_menu(self):
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QAction, QActionGroup
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        all_group = QActionGroup(menu)
        all_group.setExclusive(True)

        title_light = QAction("☀️ 浅色主题", self)
        title_light.setEnabled(False)
        font = title_light.font()
        font.setBold(True)
        title_light.setFont(font)
        menu.addAction(title_light)
        for key in ("matcha", "lemon", "fog"):
            t = THEMES[key]
            action = QAction("   " + t["name"], self)
            action.setCheckable(True)
            action.setChecked(key == self.current_theme)
            action.triggered.connect(lambda _=False, k=key: self.theme_change_requested.emit(k))
            all_group.addAction(action)
            menu.addAction(action)

        menu.addSeparator()

        title_dark = QAction("🌙 深色模式", self)
        title_dark.setEnabled(False)
        title_dark.setFont(font)
        menu.addAction(title_dark)
        for key in ("matcha_dark", "lemon_dark", "fog_dark"):
            t = THEMES[key]
            action = QAction("   " + t["name"], self)
            action.setCheckable(True)
            action.setChecked(key == self.current_theme)
            action.triggered.connect(lambda _=False, k=key: self.theme_change_requested.emit(k))
            all_group.addAction(action)
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

    def _on_search_text_changed(self, text: str):
        """搜索框文本变化：检测 /private 指令。"""
        stripped = text.strip()
        if stripped == "/private":
            self.search_edit.blockSignals(True)
            self.search_edit.clear()
            self.search_edit.blockSignals(False)
            if self._private_unlocked:
                # 已解锁 → 重新锁定
                self._lock_private()
            else:
                # 未解锁 → 触发密码验证
                self._try_unlock_private()
            return
        self.search_text_changed.emit(text)

    def refresh_notes(self, keyword=None):
        self.note_list.clear()
        if self._private_unlocked:
            # 解锁状态：只显示私密笔记（私密笔记专区）
            self.list_label.setText("    \U0001f513 私密笔记（已解锁）")
            self.lock_btn.show()
            if keyword:
                notes = [n for n in self.db.search_notes(keyword) if n.is_private]
            else:
                notes = self.db.get_private_notes()
        else:
            # 正常状态：只显示非私密笔记
            self.list_label.setText("    笔记列表")
            self.lock_btn.hide()
            if keyword:
                notes = [n for n in self.db.search_notes(keyword) if not n.is_private]
            else:
                if self.current_category_id == -1:
                    notes = [n for n in self.db.get_all_notes() if not n.is_private]
                else:
                    notes = [n for n in self.db.get_notes_by_category(self.current_category_id) if not n.is_private]
        for note in notes:
            self._add_note_item(note)

    def _add_note_item(self, note: Note):
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, note.id)
        item.setData(Qt.ItemDataRole.UserRole + 1, bool(note.is_private))
        title = note.title if note.title.strip() else "（无标题）"
        if note.is_private:
            title = f"\U0001f512 {title}"
        preview = ""
        content = note.content.strip()
        if content:
            lines = [l.strip().lstrip("#").strip() for l in content.splitlines() if l.strip()]
            preview = lines[0][:40] if lines else ""
        if preview and preview != note.title:
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
        # 解锁视图下忽略分类选择，始终显示全部私密笔记
        if self._private_unlocked:
            return
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
            self._check_and_clear_password_if_no_private()
            self.refresh_notes()

    # -------------------------------------------------------------------
    # 私密笔记逻辑
    # -------------------------------------------------------------------
    def _try_unlock_private(self):
        """尝试解锁私密笔记：弹出密码输入框验证。"""
        settings = load_settings()
        stored_hash = settings.get("private_password_hash", "")
        if not stored_hash:
            QMessageBox.information(
                self, "提示",
                "尚未设置私密笔记密码。\n请先将一篇笔记设为私密来创建密码。"
            )
            return
        dialog = PasswordDialog(self, self.current_theme, mode="verify")
        if dialog.exec() == QDialog.DialogCode.Accepted:
            password = dialog.get_password()
            if verify_password(password, stored_hash):
                self._private_unlocked = True
                # 解锁后清空搜索框和分类，切换到私密笔记专区
                self.search_edit.blockSignals(True)
                self.search_edit.clear()
                self.search_edit.blockSignals(False)
                self.category_combo.blockSignals(True)
                self.category_combo.setCurrentIndex(0)
                self.category_combo.blockSignals(False)
                self.refresh_notes()
            else:
                QMessageBox.warning(self, "密码错误", "输入的密码不正确。")
        else:
            self.refresh_notes()

    def _lock_private(self):
        """重新锁定私密笔记，恢复正常列表。"""
        self._private_unlocked = False
        self.category_combo.blockSignals(True)
        self.category_combo.setCurrentIndex(0)
        self.category_combo.blockSignals(False)
        self.refresh_notes()

    def lock_private(self):
        """外部调用：锁定私密笔记。"""
        self._lock_private()

    def _on_toggle_private(self, note_id: int):
        """切换笔记的私密状态。"""
        note = self.db.get_note(note_id)
        if note is None:
            return
        if note.is_private:
            # 取消私密：退出解锁视图，恢复正常列表
            self.db.set_note_private(note_id, False)
            if self._private_unlocked:
                self._private_unlocked = False
                self.category_combo.blockSignals(True)
                self.category_combo.setCurrentIndex(0)
                self.category_combo.blockSignals(False)
            self._check_and_clear_password_if_no_private()
            self.refresh_notes()
        else:
            # 设为私密
            settings = load_settings()
            stored_hash = settings.get("private_password_hash", "")
            if not stored_hash:
                dialog = PasswordDialog(self, self.current_theme, mode="set")
                if dialog.exec() != QDialog.DialogCode.Accepted:
                    return
                password = dialog.get_password()
                stored_hash = hash_password(password)
                save_settings(private_password_hash=stored_hash)
            self.db.set_note_private(note_id, True)
            # 设为私密后立即从普通列表隐藏（退出解锁状态，确保私密笔记不显示）
            self._private_unlocked = False
            self.refresh_notes()

    def _check_and_clear_password_if_no_private(self):
        """当所有私密笔记都被取消或删除后，清除已设置的密码。"""
        private_notes = self.db.get_private_notes()
        if not private_notes:
            settings = load_settings()
            if settings.get("private_password_hash", ""):
                save_settings(private_password_hash="")

    def is_private_unlocked(self) -> bool:
        return self._private_unlocked

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
