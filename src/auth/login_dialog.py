"""
Login screen for DepthGuard.

Shown before the main window. On success, exposes the authenticated User
via `dialog.user`. Cancel / close returns None and the app exits.

Styling intentionally mirrors the cockpit/HUD theme of main_window.py so
the experience feels continuous from login -> simulation.
"""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFrame, QGraphicsDropShadowEffect, QMessageBox,
)

from src.auth.users import User, authenticate, list_demo_credentials, Role


# Color palette — kept in sync with main_window.py
C_BG_DEEP    = "#06080F"
C_BG_PANEL   = "#0C1021"
C_BG_CARD    = "#111627"
C_BORDER     = "#1A2038"
C_BORDER_LIT = "#2A3558"
C_TEXT       = "#E8ECF4"
C_TEXT_DIM   = "#6B7A99"
C_TEXT_MUTED = "#3E4C6A"
C_ACCENT     = "#00E5A0"
C_ACCENT_DIM = "#00B87D"
C_DANGER     = "#FF2D55"


class LoginDialog(QDialog):
    """
    Modal login dialog. Use as:

        dlg = LoginDialog()
        if dlg.exec_() == QDialog.Accepted:
            user = dlg.user
            window = MainWindow(user=user)
            ...
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.user: User | None = None

        self.setWindowTitle("DepthGuard — Sign In")
        self.setModal(True)
        self.setFixedSize(460, 540)
        self.setStyleSheet(f"QDialog {{ background-color: {C_BG_DEEP}; }}")

        self._build_ui()

    # ── UI ──────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(36, 32, 36, 28)
        root.setSpacing(14)

        # Logo / brand
        logo = QLabel("DEPTHGUARD")
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet(
            f"color: {C_ACCENT}; font-size: 22px; font-weight: 800;"
            f" letter-spacing: 6px; background: transparent;"
        )
        glow = QGraphicsDropShadowEffect()
        glow.setColor(QColor(C_ACCENT))
        glow.setBlurRadius(28)
        glow.setOffset(0, 0)
        logo.setGraphicsEffect(glow)

        tagline = QLabel("DRIVER SAFETY SYSTEM")
        tagline.setAlignment(Qt.AlignCenter)
        tagline.setStyleSheet(
            f"color: {C_TEXT_MUTED}; font-size: 10px; font-weight: 600;"
            f" letter-spacing: 3px; background: transparent;"
        )

        root.addWidget(logo)
        root.addWidget(tagline)
        root.addSpacing(18)

        # Card
        card = QFrame()
        card.setStyleSheet(
            f"background-color: {C_BG_PANEL}; border: 1px solid {C_BORDER};"
            f" border-radius: 12px;"
        )
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(24, 22, 24, 22)
        card_lay.setSpacing(12)

        section = QLabel("SIGN IN")
        section.setStyleSheet(
            f"color: {C_TEXT_DIM}; font-size: 10px; font-weight: 700;"
            f" letter-spacing: 2px; background: transparent; border: none;"
        )
        card_lay.addWidget(section)

        self.inp_user = QLineEdit()
        self.inp_user.setPlaceholderText("Username")
        self.inp_user.setMinimumHeight(38)
        self.inp_user.setStyleSheet(self._input_qss())

        self.inp_pass = QLineEdit()
        self.inp_pass.setPlaceholderText("Password")
        self.inp_pass.setEchoMode(QLineEdit.Password)
        self.inp_pass.setMinimumHeight(38)
        self.inp_pass.setStyleSheet(self._input_qss())
        self.inp_pass.returnPressed.connect(self._try_login)

        card_lay.addWidget(self.inp_user)
        card_lay.addWidget(self.inp_pass)

        # Inline error label (hidden until needed)
        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet(
            f"color: {C_DANGER}; font-size: 11px; font-weight: 600;"
            f" background: transparent; border: none;"
        )
        self.lbl_error.setVisible(False)
        card_lay.addWidget(self.lbl_error)

        # Sign-in button
        self.btn_login = QPushButton("SIGN IN")
        self.btn_login.setMinimumHeight(42)
        self.btn_login.setCursor(Qt.PointingHandCursor)
        self.btn_login.clicked.connect(self._try_login)
        self.btn_login.setStyleSheet(
            f"QPushButton {{ background-color: {C_ACCENT}; color: {C_BG_DEEP};"
            f" border: none; border-radius: 6px; font-weight: 800; font-size: 13px;"
            f" letter-spacing: 2px; }}"
            f"QPushButton:hover {{ background-color: #33EDBA; }}"
            f"QPushButton:pressed {{ background-color: {C_ACCENT_DIM}; }}"
        )
        card_lay.addSpacing(4)
        card_lay.addWidget(self.btn_login)

        # Cancel button (subtle)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setMinimumHeight(34)
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        btn_cancel.setStyleSheet(
            f"QPushButton {{ background-color: transparent; color: {C_TEXT_DIM};"
            f" border: 1px solid {C_BORDER}; border-radius: 6px; font-weight: 600;"
            f" font-size: 12px; letter-spacing: 1px; }}"
            f"QPushButton:hover {{ color: {C_TEXT}; border-color: {C_BORDER_LIT}; }}"
        )
        card_lay.addWidget(btn_cancel)

        root.addWidget(card)

        # Demo accounts hint (this is a research demo, not a deployed system)
        hint = self._build_demo_hint()
        root.addWidget(hint)
        root.addStretch()

        self.inp_user.setFocus()

    def _input_qss(self) -> str:
        return (
            f"QLineEdit {{ background-color: {C_BG_CARD}; border: 1px solid {C_BORDER};"
            f" color: {C_TEXT}; padding: 8px 12px; border-radius: 6px; font-size: 13px; }}"
            f"QLineEdit:focus {{ border-color: {C_ACCENT}; }}"
        )

    def _build_demo_hint(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            f"background-color: {C_BG_CARD}; border: 1px dashed {C_BORDER_LIT};"
            f" border-radius: 8px;"
        )
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(4)

        title = QLabel("DEMO ACCOUNTS (THESIS LAB ONLY)")
        title.setStyleSheet(
            f"color: {C_TEXT_DIM}; font-size: 9px; font-weight: 700;"
            f" letter-spacing: 1.5px; background: transparent; border: none;"
        )
        lay.addWidget(title)

        for username, password, role in list_demo_credentials():
            tag = "ADMIN" if role == Role.ADMIN else "DRIVER"
            color = C_ACCENT if role == Role.ADMIN else C_TEXT_DIM
            row = QLabel(
                f"<span style='color:{color}; font-weight:700;'>{tag:6}</span>"
                f"  <span style='color:{C_TEXT};'>{username}</span>"
                f"  <span style='color:{C_TEXT_MUTED};'>/  {password}</span>"
            )
            row.setStyleSheet(
                "background: transparent; border: none; font-size: 11px;"
                " font-family: Consolas, 'Courier New', monospace;"
            )
            row.setTextFormat(Qt.RichText)
            lay.addWidget(row)

        return frame

    # ── Auth ────────────────────────────────────────────────────────
    def _try_login(self):
        username = self.inp_user.text().strip()
        password = self.inp_pass.text()

        user = authenticate(username, password)
        if user is None:
            self.lbl_error.setText("Invalid username or password.")
            self.lbl_error.setVisible(True)
            self.inp_pass.clear()
            self.inp_pass.setFocus()
            return

        self.lbl_error.setVisible(False)
        self.user = user
        self.accept()
