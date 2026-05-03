"""
Modal loading dialog with an animated dot spinner and a worker thread
to keep the UI responsive while a heavy model loads (downloads, weights, etc.).
"""

from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QDialog, QLabel, QVBoxLayout


# Match palette in main_window.py
C_BG_PANEL = "#0C1021"
C_BORDER = "#1A2038"
C_TEXT = "#E8ECF4"
C_TEXT_DIM = "#6B7A99"
C_ACCENT = "#00E5A0"


class ModelLoaderThread(QThread):
    """Runs a callable in a background thread and emits the result or an error."""

    finished_ok = pyqtSignal(object)
    finished_err = pyqtSignal(Exception)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self._fn = fn

    def run(self):
        try:
            result = self._fn()
            self.finished_ok.emit(result)
        except Exception as e:
            self.finished_err.emit(e)


class LoadingDialog(QDialog):
    """
    Modal dialog with title + animated dots. Use:

        dlg = LoadingDialog("Loading MiDaS Small...", parent)
        worker = ModelLoaderThread(lambda: build_model(...), parent)
        worker.finished_ok.connect(lambda obj: handle_success(obj, dlg))
        worker.finished_err.connect(lambda e: handle_error(e, dlg))
        worker.start()
        dlg.exec_()  # blocks until accept() / reject() called
    """

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setModal(True)
        self.setFixedSize(420, 160)
        self.setStyleSheet(
            f"QDialog {{ background-color: {C_BG_PANEL};"
            f" border: 1px solid {C_BORDER}; border-radius: 12px; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(12)

        self._title_label = QLabel(title)
        self._title_label.setAlignment(Qt.AlignCenter)
        self._title_label.setStyleSheet(
            f"color: {C_TEXT}; font-size: 14px; font-weight: 700;"
            f" letter-spacing: 1px; background: transparent; border: none;"
        )

        self._dots_label = QLabel("●  ●  ●")
        self._dots_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(20)
        self._dots_label.setFont(font)
        self._dots_label.setStyleSheet(
            f"color: {C_ACCENT}; background: transparent; border: none;"
        )

        self._hint = QLabel("First load downloads weights — may take a minute")
        self._hint.setAlignment(Qt.AlignCenter)
        self._hint.setStyleSheet(
            f"color: {C_TEXT_DIM}; font-size: 11px; font-weight: 500;"
            f" background: transparent; border: none;"
        )

        layout.addWidget(self._title_label)
        layout.addWidget(self._dots_label)
        layout.addWidget(self._hint)

        # Animation: cycle dot opacity
        self._dot_phase = 0
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._tick)
        self._anim_timer.start(280)

    def _tick(self):
        states = ["●  ○  ○", "●  ●  ○", "●  ●  ●", "○  ●  ●", "○  ○  ●", "○  ○  ○"]
        self._dot_phase = (self._dot_phase + 1) % len(states)
        self._dots_label.setText(states[self._dot_phase])

    def set_message(self, text: str):
        self._title_label.setText(text)

    def closeEvent(self, event):
        self._anim_timer.stop()
        super().closeEvent(event)
