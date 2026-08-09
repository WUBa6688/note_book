import os
import tempfile
import unittest

from core.database import DatabaseManager


class DatabaseManagerTests(unittest.TestCase):
    def setUp(self):
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        handle.close()
        self.db_path = handle.name
        self.db = DatabaseManager(self.db_path)
        self.db.init_database()

    def tearDown(self):
        self.db.close()
        os.unlink(self.db_path)

    def test_update_note_can_clear_category(self):
        category = self.db.get_all_categories()[0]
        note = self.db.create_note("classified", "", category.id)

        updated = self.db.update_note(note.id, category_id=None)

        self.assertIsNotNone(updated)
        self.assertIsNone(updated.category_id)


if __name__ == "__main__":
    unittest.main()
