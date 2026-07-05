import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from ui.main_window import MainWindow
from core.database import DatabaseManager


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Zhuibook")
    app.setOrganizationName("Zhuibook")

    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    db = DatabaseManager()
    db.init_database()

    window = MainWindow(db)
    window.resize(1200, 800)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
