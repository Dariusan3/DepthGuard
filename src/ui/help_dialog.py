"""
Role-specific quick-start guide shown after login and reopenable from the
header's "? GUIDE" button.

Admin (researcher) sees the full workflow: models, conditions, playlists,
sessions, WebXR, exports. Driver (participant) sees only what they need:
watch the road, press SPACE on danger.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QDialog, QLabel, QPushButton, QVBoxLayout,
                             QScrollArea, QWidget)

C_BG_PANEL = "#0C1021"
C_BG_DEEP = "#06080F"
C_BORDER = "#1A2038"
C_TEXT = "#E8ECF4"
C_TEXT_DIM = "#6B7A99"
C_ACCENT = "#00E5A0"
C_CAUTION = "#FFD60A"


ADMIN_GUIDE = f"""
<h2 style='color:{C_ACCENT}; letter-spacing:2px;'>RESEARCHER QUICK-START</h2>

<h3 style='color:{C_TEXT};'>1 &nbsp;Pick a depth model</h3>
<p style='color:{C_TEXT_DIM};'>MODEL dropdown → <b style='color:{C_TEXT};'>MiDaS Small</b> is the recommended
default (real depth, runs smoothly). Mock Model is for quick UI checks only.
First MiDaS load downloads weights — wait for the dialog to close.</p>

<h3 style='color:{C_TEXT};'>2 &nbsp;Pick a condition</h3>
<p style='color:{C_TEXT_DIM};'>CONDITION dropdown → <b style='color:{C_TEXT};'>No Alert</b> (silent baseline),
<b style='color:{C_TEXT};'>Standard</b> (alert bar + dashboard icon + beeps),
<b style='color:{C_TEXT};'>AR HUD</b> (overlay + soft chirps). In a structured session the
planner sets this automatically per block.</p>

<h3 style='color:{C_TEXT};'>3 &nbsp;Load scenarios — two ways</h3>
<p style='color:{C_TEXT_DIM};'>
<b style='color:{C_TEXT};'>Load Playlist</b> (solo testing / demos): pick any scenario CSV from <code>data/</code>:<br>
&nbsp;&nbsp;• <code>scenarios.csv</code> — all 16 clips<br>
&nbsp;&nbsp;• <code>scenarios_pedestrian.csv</code> / <code>scenarios_brake_lights.csv</code> / <code>scenarios_safe.csv</code> — one event type<br>
&nbsp;&nbsp;• <code>scenarios_360.csv</code> — 360° clips (forward view auto-cropped)<br><br>
<b style='color:{C_TEXT};'>Start Session</b> (real participant): enter a participant ID (P01, P02…) first.
Uses the master CSV + Latin-square block ordering with NASA-TLX pauses between blocks.</p>

<h3 style='color:{C_TEXT};'>Adding your own test file</h3>
<p style='color:{C_TEXT_DIM};'>1. Put the clip in <code>data/scenarios/</code> (mp4, 5–10&nbsp;s)<br>
2. Add a row to a CSV with: id, filename, event_type, expected_alert_level,
event_start_ms (when the hazard appears — this scores reaction time), duration_ms,
source, license, notes, projection (<code>flat</code> or <code>equirectangular</code> for 360°)<br>
3. Load that CSV via Load Playlist. Run <code>python scripts/smoke_test.py</code> to verify.</p>

<h3 style='color:{C_TEXT};'>4 &nbsp;VR (optional)</h3>
<p style='color:{C_TEXT_DIM};'>Click <b style='color:{C_TEXT};'>📡 WebXR</b> → open the green link on the headset's browser
(bookmark: DepthGuard) → ENTER VR. Trigger or left X/Y = brake. The red BRAKE
panel button flashes on every press so you can confirm input registered.</p>

<h3 style='color:{C_TEXT};'>5 &nbsp;Save the data</h3>
<p style='color:{C_TEXT_DIM};'><b style='color:{C_TEXT};'>Save Session</b> → pick a folder (defaults to Desktop) →
3 files: per-frame log, reactions CSV (with condition + outcome per press), text report.</p>
"""

DRIVER_GUIDE = f"""
<h2 style='color:{C_CAUTION}; letter-spacing:2px;'>PARTICIPANT GUIDE</h2>

<h3 style='color:{C_TEXT};'>Your task</h3>
<p style='color:{C_TEXT_DIM}; font-size:14px;'>You'll watch short driving clips
(5–10 seconds each). Imagine you are the driver.</p>

<h3 style='color:{C_TEXT};'>One rule</h3>
<p style='color:{C_TEXT}; font-size:16px;'><b>Press SPACE as soon as you see a danger</b><br>
<span style='color:{C_TEXT_DIM}; font-size:13px;'>— a pedestrian, a braking car, anything you would brake for.</span></p>

<p style='color:{C_TEXT_DIM};'>Some clips have no danger — in those, don't press anything.<br>
The clips advance automatically. Between blocks you'll fill in a short questionnaire.</p>

<p style='color:{C_TEXT_DIM};'>In VR: press the <b style='color:{C_TEXT};'>controller trigger</b> instead of SPACE.</p>

<p style='color:{C_ACCENT};'>That's all — the researcher handles everything else.</p>
"""


class HelpDialog(QDialog):
    def __init__(self, is_admin: bool, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DepthGuard — Guide")
        self.setModal(True)
        self.setFixedSize(640, 560 if is_admin else 420)
        self.setStyleSheet(
            f"QDialog {{ background-color: {C_BG_PANEL};"
            f" border: 1px solid {C_BORDER}; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 12)
        layout.setSpacing(8)

        content = QLabel(ADMIN_GUIDE if is_admin else DRIVER_GUIDE)
        content.setTextFormat(Qt.RichText)
        content.setWordWrap(True)
        content.setStyleSheet("background: transparent; border: none; padding: 12px;")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        scroll.setStyleSheet(
            f"QScrollArea {{ background: {C_BG_PANEL}; border: none; }}"
        )
        layout.addWidget(scroll)

        btn = QPushButton("Got it")
        btn.setFixedHeight(38)
        btn.setStyleSheet(
            f"background-color: {C_ACCENT}; color: {C_BG_DEEP};"
            f" border: none; border-radius: 8px; font-weight: 700;"
            f" font-size: 13px; letter-spacing: 1px;"
        )
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)
