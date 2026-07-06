import os
import sys
import traceback
import faulthandler
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from PyQt6.QtCore import QtMsgType, qInstallMessageHandler
from ui.main_window import MainWindow
from core.database import DatabaseManager


CRASH_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash.log")
_fh_file = None


def _install_crash_handlers():
    global _fh_file
    try:
        _fh_file = open(CRASH_LOG, "w", encoding="utf-8")
        faulthandler.enable(file=_fh_file, all_threads=True)
    except Exception as e:
        sys.stderr.write(f"[crash handler] faulthandler enable failed: {e}\n")

    def _excepthook(exc_type, exc_value, exc_tb):
        msg_lines = traceback.format_exception(exc_type, exc_value, exc_tb)
        msg = "".join(msg_lines)
        sys.stderr.write("===== UNHANDLED PYTHON EXCEPTION =====\n")
        sys.stderr.write(msg)
        sys.stderr.write("======================================\n")
        sys.stderr.flush()
        try:
            with open(CRASH_LOG, "a", encoding="utf-8") as f:
                f.write("===== UNHANDLED PYTHON EXCEPTION =====\n")
                f.write(msg)
                f.write("======================================\n")
                f.flush()
        except Exception:
            pass
    sys.excepthook = _excepthook

    def _qt_msg_handler(msg_type: QtMsgType, context, msg: str):
        prefix = {
            QtMsgType.QtDebugMsg: "QtDebug",
            QtMsgType.QtInfoMsg: "QtInfo",
            QtMsgType.QtWarningMsg: "QtWarning",
            QtMsgType.QtCriticalMsg: "QtCritical",
            QtMsgType.QtFatalMsg: "QtFatal",
        }.get(msg_type, "Qt")
        line = f"[{prefix}] {msg}\n"
        if msg_type in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg):
            sys.stderr.write(line)
            sys.stderr.flush()
            try:
                with open(CRASH_LOG, "a", encoding="utf-8") as f:
                    f.write(line)
                    f.flush()
            except Exception:
                pass
    try:
        qInstallMessageHandler(_qt_msg_handler)
    except Exception:
        pass


def main():
    _install_crash_handlers()
    app = QApplication(sys.argv)
    app.setApplicationName("Zhuibook")
    app.setOrganizationName("Zhuibook")

    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    db = DatabaseManager()
    db.init_database()

    window = MainWindow(db)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
