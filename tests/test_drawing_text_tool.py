import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QUndoStack
from PyQt6.QtWidgets import QApplication, QGraphicsRectItem, QGraphicsScene, QGraphicsView

from ui.drawing_tools import RotatableTextItem, TextTool
from ui.drawing_text_editor import TextFormatToolbar
from ui.drawing_board import DrawingBoardView
from core.database import DatabaseManager


_APP = None


def qapp():
    global _APP
    _APP = QApplication.instance() or QApplication([])
    return _APP


class _FakeMouseEvent:
    def __init__(self, button=Qt.MouseButton.LeftButton):
        self._button = button

    def button(self):
        return self._button

    def buttons(self):
        return self._button


class _FakeToolbar:
    def __init__(self):
        self.target = None
        self.visible = False

    def setTargetItem(self, item):
        self.target = item
        self.visible = True

    def clearTarget(self):
        self.target = None
        self.visible = False

    def show(self):
        self.visible = True

    def hide(self):
        self.visible = False


class _FakeBoard:
    def __init__(self, scene, view, bg_item):
        self.scene = scene
        self.view = view
        self._canvas_bg_item = bg_item
        self.primary_color = "#111111"
        self.secondary_color = "#FFFFFF"
        self.pen_width = 4
        self.undo_stack = QUndoStack()
        self.text_toolbar = _FakeToolbar()


class DrawingTextToolTests(unittest.TestCase):
    def setUp(self):
        qapp()
        RotatableTextItem._current_editing_item = None
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.bg_item = QGraphicsRectItem(0, 0, 800, 600)
        self.scene.addItem(self.bg_item)
        self.board = _FakeBoard(self.scene, self.view, self.bg_item)
        self.tool = TextTool(self.scene, self.view, self.board)

    def tearDown(self):
        RotatableTextItem._current_editing_item = None
        self.view.close()
        self.scene.clear()

    def _text_items(self):
        return [it for it in self.scene.items() if isinstance(it, RotatableTextItem)]

    def test_creating_second_text_removes_empty_first_editor(self):
        self.tool.mouse_press(_FakeMouseEvent(), QPointF(100, 100))
        first = RotatableTextItem._current_editing_item
        self.assertIsNotNone(first)

        self.tool.mouse_press(_FakeMouseEvent(), QPointF(220, 160))

        self.assertIsNot(first, RotatableTextItem._current_editing_item)
        self.assertEqual(len(self._text_items()), 1)
        self.assertIs(RotatableTextItem._current_editing_item, self._text_items()[0])

    def test_committed_text_switches_from_editing_to_selected_object(self):
        self.tool.mouse_press(_FakeMouseEvent(), QPointF(100, 100))
        item = RotatableTextItem._current_editing_item
        item.setPlainText("你好")

        self.tool._commit_edit()

        self.assertIsNone(RotatableTextItem._current_editing_item)
        self.assertFalse(item.textInteractionFlags() & Qt.TextInteractionFlag.TextEditorInteraction)
        self.assertTrue(item.isSelected())
        self.assertFalse(self.board.text_toolbar.visible)

    def test_begin_edit_does_not_leave_previous_text_interactive(self):
        first = RotatableTextItem("first")
        second = RotatableTextItem("second")
        self.scene.addItem(first)
        self.scene.addItem(second)

        self.tool._begin_edit(first, QPointF(100, 100), is_new=False)
        self.tool._begin_edit(second, QPointF(200, 100), is_new=False)

        self.assertIs(RotatableTextItem._current_editing_item, second)
        self.assertFalse(first.textInteractionFlags() & Qt.TextInteractionFlag.TextEditorInteraction)
        self.assertTrue(second.textInteractionFlags() & Qt.TextInteractionFlag.TextEditorInteraction)

    def test_side_resize_changes_width_without_changing_font_size(self):
        item = RotatableTextItem("hello")
        item.set_text_size(120, 40, 18)
        self.scene.addItem(item)
        self.tool._resize_item = item
        self.tool._resize_handle = item.HANDLE_R
        self.tool._resize_start_w = item.text_width()
        self.tool._resize_start_h = item.text_height()
        self.tool._resize_start_font = item.font_size()

        self.tool._do_resize(QPointF(item.HANDLE_SIZE + 220, item.HANDLE_SIZE + 20))

        self.assertGreater(item.text_width(), 120)
        self.assertEqual(item.font_size(), 18)

    def test_vertical_resize_changes_height_without_changing_font_size(self):
        item = RotatableTextItem("hello")
        item.set_text_size(120, 40, 18)
        self.scene.addItem(item)
        self.tool._resize_item = item
        self.tool._resize_handle = item.HANDLE_B
        self.tool._resize_start_w = item.text_width()
        self.tool._resize_start_h = item.text_height()
        self.tool._resize_start_font = item.font_size()

        self.tool._do_resize(QPointF(60, 90))

        self.assertGreater(item.text_height(), 40)
        self.assertEqual(item.font_size(), 18)

    def test_corner_resize_scales_font_size(self):
        item = RotatableTextItem("hello")
        item.set_text_size(120, 40, 18)
        self.scene.addItem(item)
        self.tool._resize_item = item
        self.tool._resize_handle = item.HANDLE_BR
        self.tool._resize_start_w = item.text_width()
        self.tool._resize_start_h = item.text_height()
        self.tool._resize_start_font = item.font_size()

        self.tool._do_resize(QPointF(item.HANDLE_SIZE + 240, item.HANDLE_SIZE + 80))

        self.assertGreater(item.text_width(), 120)
        self.assertGreater(item.text_height(), 40)
        self.assertGreater(item.font_size(), 18)

    def test_text_toolbar_size_change_updates_item_geometry_font_size(self):
        item = RotatableTextItem("hello")
        item.set_text_size(120, 40, 12)
        self.scene.addItem(item)
        toolbar = TextFormatToolbar()
        toolbar.setTargetItem(item)

        toolbar.size_spin.setValue(20)

        self.assertEqual(item.font_size(), 20)
        self.assertEqual(item.font().pointSize(), 20)

    def test_board_selection_keeps_toolbar_bound_to_current_editor(self):
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        handle.close()
        db = DatabaseManager(handle.name)
        db.init_database()
        board = DrawingBoardView(db)
        try:
            editing = RotatableTextItem("editing")
            selected = RotatableTextItem("selected")
            board.scene.addItem(editing)
            board.scene.addItem(selected)
            RotatableTextItem._current_editing_item = editing
            selected.setSelected(True)

            board._on_scene_selection_changed()

            self.assertIs(board.text_toolbar._target, editing)
        finally:
            board.close()
            db.close()
            os.unlink(handle.name)


if __name__ == "__main__":
    unittest.main()
