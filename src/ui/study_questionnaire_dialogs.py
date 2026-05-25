"""Data-entry dialogs for the DepthGuard HCI study measures."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


PANEL_STYLE = """
QDialog, QWidget { background-color: #0C1021; color: #E8ECF4; }
QLabel { color: #E8ECF4; }
QGroupBox { color: #00E5A0; border: 1px solid #1A2038; border-radius: 8px;
            margin-top: 14px; padding-top: 14px; font-weight: 700; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 6px; }
QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit, QTextEdit {
    background-color: #111627; border: 1px solid #2A3558; border-radius: 5px;
    padding: 5px; color: #E8ECF4;
}
QDialogButtonBox QPushButton {
    background-color: #00E5A0; color: #06080F; border: none; border-radius: 6px;
    padding: 8px 18px; font-weight: 700;
}
"""


class NASATLXDialog(QDialog):
    """Collect one raw NASA-TLX response after a completed condition block."""

    ITEMS = [
        ("mental_demand", "Mental demand"),
        ("physical_demand", "Physical demand"),
        ("temporal_demand", "Temporal demand"),
        ("performance", "Performance difficulty"),
        ("effort", "Effort"),
        ("frustration", "Frustration"),
    ]

    def __init__(self, block_num: int, condition: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("NASA-TLX Workload")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setStyleSheet(PANEL_STYLE)

        layout = QVBoxLayout(self)
        title = QLabel(f"NASA-TLX - Block {block_num}: {condition}")
        title.setStyleSheet("color: #00E5A0; font-size: 18px; font-weight: 800;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        note = QLabel("Rate each dimension from 0 (very low) to 100 (very high).")
        note.setAlignment(Qt.AlignCenter)
        note.setStyleSheet("color: #6B7A99;")
        layout.addWidget(note)

        form = QFormLayout()
        self.inputs = {}
        for key, label in self.ITEMS:
            field = QSpinBox()
            field.setRange(0, 100)
            field.setSingleStep(5)
            field.setValue(50)
            field.setSuffix(" / 100")
            self.inputs[key] = field
            form.addRow(label, field)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def scores(self) -> dict:
        return {key: widget.value() for key, widget in self.inputs.items()}


class FinalQuestionnaireDialog(QDialog):
    """Collect end-of-session SUS, trust and participant background data."""

    SUS_ITEMS = [
        "I would like to use this system frequently.",
        "I found the system unnecessarily complex.",
        "I thought the system was easy to use.",
        "I would need technical support to use this system.",
        "The functions in this system were well integrated.",
        "There was too much inconsistency in this system.",
        "Most people would learn to use this system quickly.",
        "I found the system very cumbersome to use.",
        "I felt very confident using this system.",
        "I needed to learn a lot before using this system.",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Final Study Questionnaire")
        self.setModal(True)
        self.resize(720, 760)
        self.setStyleSheet(PANEL_STYLE)

        root = QVBoxLayout(self)
        title = QLabel("FINAL STUDY QUESTIONNAIRE")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #00E5A0; font-size: 18px; font-weight: 800;")
        root.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        body_layout = QVBoxLayout(body)

        sus_group = QGroupBox("System Usability Scale (1 = strongly disagree, 5 = strongly agree)")
        sus_form = QFormLayout(sus_group)
        self.sus_inputs = {}
        for index, question in enumerate(self.SUS_ITEMS, start=1):
            field = self._rating_combo()
            self.sus_inputs[f"sus_{index}"] = field
            sus_form.addRow(f"{index}. {question}", field)
        body_layout.addWidget(sus_group)

        opinion_group = QGroupBox("Experience Ratings")
        opinion_form = QFormLayout(opinion_group)
        self.sound_distracting = self._rating_combo()
        self.ar_helpful = self._rating_combo()
        self.trust = self._rating_combo()
        opinion_form.addRow("Alert sound was distracting (1-5)", self.sound_distracting)
        opinion_form.addRow("AR overlay was helpful (1-5)", self.ar_helpful)
        opinion_form.addRow("I trusted the system alerts (1-5)", self.trust)
        body_layout.addWidget(opinion_group)

        demo_group = QGroupBox("Participant Background")
        demo_form = QFormLayout(demo_group)
        self.age = QSpinBox()
        self.age.setRange(18, 100)
        self.gender = QLineEdit()
        self.gender.setPlaceholderText("Optional / prefer not to say")
        self.has_license = self._choice_combo(["Yes", "No"])
        self.license_years = QDoubleSpinBox()
        self.license_years.setRange(0, 80)
        self.license_years.setDecimals(1)
        self.driving_frequency = self._choice_combo(["Daily", "Weekly", "Monthly", "Rarely", "Never"])
        self.prior_adas = self._choice_combo(["Yes", "No"])
        self.adas_details = QLineEdit()
        self.adas_details.setPlaceholderText("Optional: system used")
        self.feedback = QTextEdit()
        self.feedback.setMaximumHeight(72)
        demo_form.addRow("Age", self.age)
        demo_form.addRow("Gender", self.gender)
        demo_form.addRow("Driving licence", self.has_license)
        demo_form.addRow("Years licensed", self.license_years)
        demo_form.addRow("Driving frequency", self.driving_frequency)
        demo_form.addRow("Previously used ADAS/dashcam", self.prior_adas)
        demo_form.addRow("ADAS/dashcam details", self.adas_details)
        demo_form.addRow("Additional feedback", self.feedback)
        body_layout.addWidget(demo_group)

        scroll.setWidget(body)
        root.addWidget(scroll)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    @staticmethod
    def _rating_combo() -> QComboBox:
        field = QComboBox()
        field.addItem("Select rating", None)
        for value in range(1, 6):
            field.addItem(str(value), value)
        return field

    @staticmethod
    def _choice_combo(items: list[str]) -> QComboBox:
        field = QComboBox()
        field.addItems(items)
        return field

    def accept(self):
        required = list(self.sus_inputs.values()) + [
            self.sound_distracting,
            self.ar_helpful,
            self.trust,
        ]
        if any(field.currentData() is None for field in required):
            QMessageBox.warning(self, "Incomplete Questionnaire", "Select every 1-5 rating before saving.")
            return
        super().accept()

    def sus_responses(self) -> dict:
        return {key: field.currentData() for key, field in self.sus_inputs.items()}

    def responses(self) -> dict:
        return {
            "age": self.age.value(),
            "gender": self.gender.text().strip(),
            "has_driving_license": self.has_license.currentText(),
            "driving_experience_years": self.license_years.value(),
            "driving_frequency": self.driving_frequency.currentText(),
            "prior_adas_or_dashcam": self.prior_adas.currentText(),
            "adas_details": self.adas_details.text().strip(),
            "sound_distracting": self.sound_distracting.currentData(),
            "ar_helpful": self.ar_helpful.currentData(),
            "trust_score": self.trust.currentData(),
            "feedback": self.feedback.toPlainText().strip(),
        }
