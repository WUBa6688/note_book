import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QColor, QImage
from PyQt6.QtWidgets import QApplication

from ui.editor import MarkdownEditor


_APP = None


def qapp():
    global _APP
    _APP = QApplication.instance() or QApplication([])
    return _APP


class MarkdownEditorTests(unittest.TestCase):
    def setUp(self):
        qapp()
        self.editor = MarkdownEditor()

    def tearDown(self):
        self.editor.close()

    def test_get_content_sync_preserves_rendered_image_markdown(self):
        image_path = os.path.join(tempfile.gettempdir(), "zhuibook_test_image.png")
        image = QImage(8, 8, QImage.Format.Format_RGB32)
        image.fill(QColor("red"))
        self.assertTrue(image.save(image_path, "PNG"))
        content = f"before\n\n![alt]({image_path})\n\nafter"
        self.editor.set_note(1, "title", content, None, [])

        self.assertEqual(self.editor.get_content_sync(), content)

    def test_flush_pending_save_emits_current_note_once(self):
        emitted = []
        self.editor.set_note(1, "old", "old body", None, [])
        self.editor.content_changed.connect(
            lambda title, content, category_id: emitted.append((title, content, category_id))
        )
        self.editor.title_edit.setText("new title")
        self.editor.edit.setPlainText("new body")

        self.editor.flush_pending_save()

        self.assertEqual(emitted, [("new title", "new body", None)])
        self.assertFalse(self.editor._save_timer.isActive())

    def test_non_persistent_style_controls_are_hidden(self):
        self.assertTrue(self.editor.font_size_label.isHidden())
        self.assertTrue(self.editor.font_size_combo.isHidden())
        self.assertTrue(self.editor.text_color_btn.isHidden())
        self.assertTrue(self.editor.highlight_color_btn.isHidden())


if __name__ == "__main__":
    unittest.main()
