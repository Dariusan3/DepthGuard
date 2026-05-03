"""
Modal dialog shown between blocks of the HCI session.

Pauses the experiment so the researcher can:
    1. Hand the participant the NASA-TLX questionnaire for the just-finished block
    2. Brief the upcoming condition
    3. Click Continue to start the next block
"""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout


C_BG_PANEL = "#0C1021"
C_BORDER = "#1A2038"
C_TEXT = "#E8ECF4"
C_TEXT_DIM = "#6B7A99"
C_ACCENT = "#00E5A0"
C_BG_DEEP = "#06080F"


class BlockPauseDialog(QDialog):
    """
    Args:
        completed_block: int (1-3) — block that just ended (0 if pre-session)
        completed_condition: str display name of just-finished condition
        next_block: int (1-3) — block about to start
        next_condition: str display name of next condition
        is_final: bool — if True, this is the post-block-3 dialog (study end)
    """

    def __init__(self, completed_block: int, completed_condition: str,
                 next_block: int, next_condition: str, is_final: bool = False,
                 parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setModal(True)
        self.setFixedSize(560, 320)
        self.setStyleSheet(
            f"QDialog {{ background-color: {C_BG_PANEL};"
            f" border: 1px solid {C_BORDER}; border-radius: 14px; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 32, 36, 28)
        layout.setSpacing(14)

        if is_final:
            heading = QLabel("SESSION COMPLETE")
            sub = QLabel(
                f"Block {completed_block} ({completed_condition}) finished.\n"
                "Hand the participant the final questionnaires (NASA-TLX, SUS, demographics)."
            )
        elif completed_block == 0:
            heading = QLabel("READY TO BEGIN")
            sub = QLabel(
                f"Block 1 of 3 will use the {next_condition} condition.\n"
                "Confirm the participant is comfortable, then continue."
            )
        else:
            heading = QLabel(f"BLOCK {completed_block} COMPLETE")
            sub = QLabel(
                f"Just finished: {completed_condition}.\n"
                f"Hand the participant the NASA-TLX for this block.\n\n"
                f"Up next — Block {next_block}: {next_condition}."
            )

        heading.setAlignment(Qt.AlignCenter)
        heading.setStyleSheet(
            f"color: {C_ACCENT}; font-size: 20px; font-weight: 800;"
            f" letter-spacing: 2px; background: transparent; border: none;"
        )

        sub.setAlignment(Qt.AlignCenter)
        sub.setWordWrap(True)
        sub.setStyleSheet(
            f"color: {C_TEXT}; font-size: 13px; font-weight: 500;"
            f" line-height: 150%; background: transparent; border: none;"
        )

        layout.addWidget(heading)
        layout.addSpacing(8)
        layout.addWidget(sub)
        layout.addStretch()

        # Action buttons
        if is_final:
            btn = QPushButton("Finish")
        elif completed_block == 0:
            btn = QPushButton("Start Block 1")
        else:
            btn = QPushButton(f"Start Block {next_block}")

        btn.setFixedHeight(40)
        btn.setStyleSheet(
            f"background-color: {C_ACCENT}; color: {C_BG_DEEP};"
            f" border: none; border-radius: 8px; padding: 8px 24px;"
            f" font-weight: 700; font-size: 13px; letter-spacing: 1px;"
        )
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)
