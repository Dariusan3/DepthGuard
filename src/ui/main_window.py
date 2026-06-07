import sys
import os
import cv2
import time
import json
from pathlib import Path
from urllib.request import urlopen
import numpy as np
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QTabWidget, QLabel, QPushButton, QComboBox,
                             QSlider, QLineEdit, QTableWidget, QTableWidgetItem,
                             QHeaderView, QFileDialog, QMessageBox, QGroupBox,
                             QGridLayout, QFrame, QSizePolicy, QGraphicsDropShadowEffect,
                             QSpacerItem, QDialog)
from PyQt5.QtCore import (Qt, QTimer, QProcess, pyqtSignal, pyqtSlot,
                          QPropertyAnimation, QEasingCurve, QSize)
from PyQt5.QtGui import QImage, QPixmap, QFont, QColor, QFontDatabase, QLinearGradient, QPalette
import pyqtgraph as pg

# Local imports
from src.models.mock_model import MockModel
from src.core.alert_system import SafetyAlertSystem
from src.core.performance_monitor import PerformanceMonitor
from src.core.data_logger import DataLogger
from src.core.audio_alerts import AudioAlertSystem
from src.core.playlist import PlaylistManager
from src.core.object_detector import YOLOObjectDetector

# Lazy import for MiDaS (requires torch — may not be installed)
MiDaSModel = None

# ── Color Palette ──────────────────────────────────────────────
# Deep blacks with electric accent colors for a cockpit/HUD feel
C_BG_DEEP      = "#06080F"   # near-black with blue undertone
C_BG_PANEL     = "#0C1021"   # raised panel surface
C_BG_CARD      = "#111627"   # card/input surface
C_BORDER       = "#1A2038"   # subtle borders
C_BORDER_LIT   = "#2A3558"   # highlighted border
C_TEXT          = "#E8ECF4"   # primary text
C_TEXT_DIM      = "#6B7A99"   # secondary text
C_TEXT_MUTED    = "#3E4C6A"   # muted labels
C_ACCENT        = "#00E5A0"   # electric mint — primary accent
C_ACCENT_DIM    = "#00B87D"   # dimmed accent
C_ACCENT_GLOW   = "#00E5A033" # accent with alpha for glows
C_DANGER        = "#FF2D55"   # alert red
C_DANGER_DIM    = "#CC1B3E"   # dimmed red
C_WARN          = "#FF9F0A"   # warning amber
C_CAUTION       = "#FFD60A"   # caution yellow
C_SAFE          = "#30D158"   # safe green
WEBXR_PUBLIC_URL = "https://ichthyosaurian-nonsatiric-kellan.ngrok-free.dev/"
NGROK_API_URL = "http://127.0.0.1:4040/api/tunnels"

STYLESHEET = f"""
/* ── Global ──────────────────────────────────────── */
QMainWindow {{
    background-color: {C_BG_DEEP};
}}
QWidget {{
    background-color: {C_BG_DEEP};
    color: {C_TEXT};
    font-family: "SF Pro Display", "Segoe UI", "Helvetica Neue", sans-serif;
    font-size: 13px;
}}

/* ── Tabs ────────────────────────────────────────── */
QTabWidget::pane {{
    border: none;
    background: {C_BG_DEEP};
    margin-top: -1px;
}}
QTabBar {{
    background: transparent;
}}
QTabBar::tab {{
    background: transparent;
    color: {C_TEXT_DIM};
    padding: 12px 32px;
    margin-right: 4px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 13px;
    font-weight: 600;
    min-width: 110px;
}}
QTabBar::tab:hover {{
    color: {C_TEXT};
}}
QTabBar::tab:selected {{
    color: {C_ACCENT};
    border-bottom: 2px solid {C_ACCENT};
}}

/* ── Buttons ─────────────────────────────────────── */
QPushButton {{
    background-color: {C_BG_CARD};
    border: 1px solid {C_BORDER};
    color: {C_TEXT};
    padding: 10px 20px;
    border-radius: 6px;
    font-weight: 600;
    font-size: 12px;
    letter-spacing: 0.3px;
}}
QPushButton:hover {{
    background-color: {C_BORDER};
    border-color: {C_BORDER_LIT};
}}
QPushButton:pressed {{
    background-color: {C_BG_PANEL};
}}
QPushButton:disabled {{
    color: {C_TEXT_MUTED};
    border-color: {C_BORDER};
}}

/* ── Brake Button ────────────────────────────────── */
QPushButton#BrakeBtn {{
    background-color: {C_DANGER};
    color: white;
    font-size: 18px;
    font-weight: 800;
    letter-spacing: 1px;
    border-radius: 10px;
    border: 2px solid {C_DANGER};
    padding: 14px 24px;
    min-height: 48px;
}}
QPushButton#BrakeBtn:hover {{
    background-color: #FF4D6F;
    border-color: #FF4D6F;
}}
QPushButton#BrakeBtn:pressed {{
    background-color: {C_DANGER_DIM};
}}

/* ── Accent Buttons ──────────────────────────────── */
QPushButton#AccentBtn {{
    background-color: {C_ACCENT};
    color: {C_BG_DEEP};
    border: none;
    font-weight: 700;
}}
QPushButton#AccentBtn:hover {{
    background-color: #33EDBA;
}}

/* ── GroupBox ─────────────────────────────────────── */
QGroupBox {{
    border: 1px solid {C_BORDER};
    border-radius: 10px;
    margin-top: 20px;
    padding-top: 28px;
    font-weight: 600;
    background-color: {C_BG_PANEL};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 16px;
    padding: 2px 10px;
    color: {C_TEXT_DIM};
    font-size: 11px;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    background-color: {C_BG_PANEL};
    border-radius: 4px;
}}

/* ── Inputs ──────────────────────────────────────── */
QComboBox, QLineEdit {{
    background-color: {C_BG_CARD};
    border: 1px solid {C_BORDER};
    color: {C_TEXT};
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 12px;
    selection-background-color: {C_ACCENT_DIM};
}}
QComboBox:focus, QLineEdit:focus {{
    border-color: {C_ACCENT};
}}
QComboBox QAbstractItemView {{
    background-color: {C_BG_CARD};
    color: {C_TEXT};
    selection-background-color: {C_BORDER};
    border: 1px solid {C_BORDER};
    border-radius: 6px;
    padding: 4px;
}}
QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
}}

/* ── Table ───────────────────────────────────────── */
QTableWidget {{
    background-color: {C_BG_PANEL};
    border: 1px solid {C_BORDER};
    border-radius: 8px;
    gridline-color: {C_BORDER};
    color: {C_TEXT};
    font-size: 12px;
}}
QTableWidget::item {{
    padding: 6px 10px;
    border-bottom: 1px solid {C_BORDER};
}}
QTableWidget::item:selected {{
    background-color: {C_BORDER};
}}
QHeaderView::section {{
    background-color: {C_BG_CARD};
    color: {C_TEXT_DIM};
    padding: 8px 10px;
    border: none;
    border-bottom: 1px solid {C_BORDER};
    font-weight: 600;
    font-size: 11px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}}

/* ── Slider ──────────────────────────────────────── */
QSlider::groove:horizontal {{
    border: none;
    height: 4px;
    background: {C_BORDER};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {C_ACCENT};
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}
QSlider::sub-page:horizontal {{
    background: {C_ACCENT};
    border-radius: 2px;
}}

/* ── Scrollbar ───────────────────────────────────── */
QScrollBar:vertical {{
    background: {C_BG_DEEP};
    width: 8px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: {C_BORDER};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

/* ── Label Variants (via property) ───────────────── */
QLabel#SectionLabel {{
    color: {C_TEXT_DIM};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
}}
QLabel#MetricValue {{
    color: {C_TEXT};
    font-size: 28px;
    font-weight: 700;
}}
QLabel#MetricLabel {{
    color: {C_TEXT_DIM};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
}}
"""

class MainWindow(QMainWindow):
    remote_brake_received = pyqtSignal(dict)
    remote_control_received = pyqtSignal(dict)

    def __init__(self, user=None):
        super().__init__()
        # Authenticated user (driver or admin). When None we default to admin
        # so the window remains usable in scripts/tests that bypass the login flow.
        from src.auth.users import User, Role
        if user is None:
            user = User(username="admin", role=Role.ADMIN, display_name="Researcher")
        self.user = user
        # Set by _logout() so main.py knows to re-show the login screen instead of exiting.
        self._logout_requested = False

        self.setWindowTitle(f"DepthGuard — {user.display_name}")
        self.resize(1440, 900)
        self.setMinimumSize(1100, 750)
        self.setStyleSheet(STYLESHEET)
        self.showMaximized()

        # Core components
        self.model = MockModel()
        self.alert_system = SafetyAlertSystem()
        self.object_detector = YOLOObjectDetector()
        self.perf_monitor = PerformanceMonitor()
        self.data_logger = DataLogger()
        self.audio_system = AudioAlertSystem()

        from src.ui.ar_overlay import AROverlay
        from src.core.experiment import ExperimentCondition, flags_for
        self.ar_overlay = AROverlay()
        self.condition = ExperimentCondition.STANDARD
        self.condition_flags = flags_for(self.condition)
        # Backwards-compat shim — anything that still reads ar_mode_enabled
        self.ar_mode_enabled = self.condition_flags.ar_overlay_enabled

        # WebXR companion (Option B) — lazy-init when user toggles it on
        self.webxr_server = None
        self._last_webxr_push_t = 0.0  # for throttling the frame push
        self._tunnel_process = None
        self._tunnel_public_url = None
        self._wrong_tunnel_upstream = None
        self._tunnel_probe_attempts = 0
        self._tunnel_probe_timer = QTimer(self)
        self._tunnel_probe_timer.setInterval(500)
        self._tunnel_probe_timer.timeout.connect(self._probe_tunnel_status)
        self.remote_brake_received.connect(self._apply_remote_brake)
        self.remote_control_received.connect(self._apply_remote_control)

        # State variables
        self.cap = None
        self.is_playing = False
        self.is_looping = False
        self.total_frames = 0
        self.current_frame = 0
        self.fps = 30
        self.target_fps = 30
        self._alert_flash_on = False
        self._last_object_detections = []
        # Reuse real YOLO detections between runs to keep boxes visible while
        # leaving more time for smooth desktop playback.
        self._object_detection_stride = 4
        self._last_detector_status = "YOLO: waiting"

        # Playlist state (HCI study mode)
        self.playlist: PlaylistManager | None = None
        self.current_trial: dict | None = None
        self.trial_start_time: float | None = None  # wall-clock at trial start
        self._between_trials = False  # blank-screen pause between clips
        self._smoothed_threat_box: tuple | None = None  # for tracking jitter reduction

        # Multi-participant session state (block-based)
        self.session_mode = False           # True if running a structured Latin-square session
        self.session_plan = None            # SessionPlan from session_planner
        self.session_block_index = 0        # 0-based index into plan.blocks

        # Slider drag state
        self._was_playing_before_seek = False
        self._seek_preview_timer = QTimer(self)
        self._seek_preview_timer.setSingleShot(True)
        self._seek_preview_timer.timeout.connect(self._render_seek_preview)

        # Timers
        self.playback_timer = QTimer(self)
        self.playback_timer.timeout.connect(self.process_next_frame)
        self.monitor_timer = QTimer(self)
        self.monitor_timer.timeout.connect(self.update_monitor_tab)
        self.monitor_timer.start(500)

        # Flash timer for critical alert pulsing
        self._flash_timer = QTimer(self)
        self._flash_timer.timeout.connect(self._toggle_flash)
        self._flash_timer.setInterval(400)

        self.setup_ui()
        self._setup_shortcuts()
        self._apply_role_visibility()
        QTimer.singleShot(0, self._start_webxr_stack)

    def _setup_shortcuts(self):
        """Keyboard shortcuts for participant-friendly use."""
        from PyQt5.QtWidgets import QShortcut
        from PyQt5.QtGui import QKeySequence

        # SPACE = brake (the critical one for HCI study)
        QShortcut(QKeySequence(Qt.Key_Space), self, activated=self.record_reaction)
        # ESC = pause / resume
        QShortcut(QKeySequence(Qt.Key_Escape), self, activated=self.toggle_play)
        # F11 = fullscreen toggle
        QShortcut(QKeySequence(Qt.Key_F11), self, activated=self._toggle_fullscreen)

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showMaximized()
        else:
            self.showFullScreen()

    # ── Role-based UI gating ─────────────────────────────────────
    def _apply_role_visibility(self):
        """
        Hide researcher-only controls when a DRIVER is signed in.

        Drivers see: video panels, alert strip, progress bar, transport
        buttons (Load/Play/Stop/Loop), and the BRAKE button. Everything
        else — model/mode/condition selectors, session row, Performance
        tab, Analysis tab — is researcher-only and hidden.
        """
        if self.user.is_admin:
            return

        # Admin-only widgets on the SIMULATION tab
        for w in (
            self.condition_frame,
            self._sim_vsep,
            self.lbl_model, self.cb_model,
            self.lbl_mode, self.cb_mode,
            self._session_row,
        ):
            w.setVisible(False)

        # Remove researcher-only tabs (highest index first to keep indices stable)
        # Index 2 = ANALYSIS, Index 1 = PERFORMANCE.
        if self.tabs.count() > 2:
            self.tabs.removeTab(2)
        if self.tabs.count() > 1:
            self.tabs.removeTab(1)

        # No need to keep the perf monitor timer running for drivers.
        self.monitor_timer.stop()

    def _logout(self):
        """Sign out and return to the login screen.

        main.py loops on this flag so the app re-shows the login dialog
        instead of exiting.
        """
        self._logout_requested = True
        self.close()

    # ── Helpers ──────────────────────────────────────────────────
    @staticmethod
    def _make_separator():
        """Thin horizontal rule."""
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color: {C_BORDER}; max-height: 1px;")
        return sep

    @staticmethod
    def _make_section_label(text):
        lbl = QLabel(text)
        lbl.setObjectName("SectionLabel")
        lbl.setStyleSheet(
            f"color: {C_TEXT_DIM}; font-size: 10px; font-weight: 700;"
            f" letter-spacing: 2px; text-transform: uppercase; padding: 0;"
            f" background: transparent;"
        )
        return lbl

    @staticmethod
    def _make_metric_card(title, value="--"):
        """Creates a styled metric card (returns frame, value_label)."""
        card = QFrame()
        card.setStyleSheet(
            f"background-color: {C_BG_PANEL};"
            f" border: 1px solid {C_BORDER};"
            f" border-radius: 10px;"
            f" padding: 0px;"
        )
        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(4)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(
            f"color: {C_TEXT_DIM}; font-size: 11px; font-weight: 600;"
            f" letter-spacing: 0.5px; border: none; background: transparent;"
        )

        lbl_value = QLabel(value)
        lbl_value.setStyleSheet(
            f"color: {C_TEXT}; font-size: 26px; font-weight: 700;"
            f" border: none; background: transparent;"
        )

        lay.addWidget(lbl_title)
        lay.addWidget(lbl_value)
        return card, lbl_value

    def _glow_effect(self, color=C_ACCENT, radius=20, offset_y=2):
        effect = QGraphicsDropShadowEffect()
        effect.setColor(QColor(color))
        effect.setBlurRadius(radius)
        effect.setOffset(0, offset_y)
        return effect

    # ── UI Setup ─────────────────────────────────────────────────
    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Header bar ──
        header = QFrame()
        header.setFixedHeight(52)
        header.setStyleSheet(
            f"background-color: {C_BG_PANEL};"
            f" border-bottom: 1px solid {C_BORDER};"
        )
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(20, 0, 20, 0)

        logo = QLabel("DEPTHGUARD")
        logo.setStyleSheet(
            f"color: {C_ACCENT}; font-size: 15px; font-weight: 800;"
            f" letter-spacing: 3px; background: transparent; border: none;"
        )
        logo.setGraphicsEffect(self._glow_effect(C_ACCENT_GLOW, 30, 0))

        tag = QLabel("DRIVER SAFETY SYSTEM")
        tag.setStyleSheet(
            f"color: {C_TEXT_MUTED}; font-size: 10px; font-weight: 600;"
            f" letter-spacing: 2px; background: transparent; border: none;"
        )

        self.lbl_current_fps = QLabel("-- FPS")
        self.lbl_current_fps.setMinimumWidth(70)
        self.lbl_current_fps.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_current_fps.setStyleSheet(
            f"color: {C_TEXT_DIM}; font-size: 12px; font-weight: 600;"
            f" background: transparent; border: none;"
        )

        # User pill — shows the signed-in user's role and display name. Clickable
        # → log out (returns to the login screen).
        role_tag = "ADMIN" if self.user.is_admin else "DRIVER"
        role_color = C_ACCENT if self.user.is_admin else C_CAUTION
        self.lbl_user_pill = QLabel(
            f"<span style='color:{role_color}; font-weight:700; letter-spacing:1.5px;'>{role_tag}</span>"
            f"  <span style='color:{C_TEXT};'>{self.user.display_name}</span>"
        )
        self.lbl_user_pill.setTextFormat(Qt.RichText)
        self.lbl_user_pill.setStyleSheet(
            f"background-color: {C_BG_CARD}; border: 1px solid {C_BORDER};"
            f" border-radius: 14px; padding: 4px 12px; font-size: 11px;"
        )

        self.btn_logout = QPushButton("LOG OUT")
        self.btn_logout.setCursor(Qt.PointingHandCursor)
        self.btn_logout.setFocusPolicy(Qt.NoFocus)
        self.btn_logout.clicked.connect(self._logout)
        self.btn_logout.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {C_TEXT_DIM};"
            f" border: 1px solid {C_BORDER}; border-radius: 14px;"
            f" padding: 4px 12px; font-size: 10px; font-weight: 700;"
            f" letter-spacing: 1.5px; }}"
            f"QPushButton:hover {{ color: {C_DANGER}; border-color: {C_DANGER}; }}"
        )

        h_lay.addWidget(logo)
        h_lay.addSpacing(12)
        h_lay.addWidget(tag)
        h_lay.addStretch()
        h_lay.addWidget(self.lbl_current_fps)
        h_lay.addSpacing(16)
        h_lay.addWidget(self.lbl_user_pill)
        h_lay.addSpacing(6)
        h_lay.addWidget(self.btn_logout)

        main_layout.addWidget(header)

        # ── Tabs ──
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        main_layout.addWidget(self.tabs)

        self.setup_sim_tab()
        self.setup_monitor_tab()
        self.setup_analysis_tab()

    # ── TAB 1: SIMULATION ────────────────────────────────────────
    def setup_sim_tab(self):
        sim_tab = QWidget()
        layout = QVBoxLayout(sim_tab)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # ── Video Panels ──
        video_layout = QHBoxLayout()
        video_layout.setSpacing(10)

        self.lbl_driver_view = QLabel("LOAD VIDEO TO BEGIN")
        self.lbl_driver_view.setAlignment(Qt.AlignCenter)
        self.lbl_driver_view.setMinimumSize(860, 480)
        self.lbl_driver_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.lbl_driver_view.setStyleSheet(
            f"background-color: {C_BG_PANEL}; border: 1px solid {C_BORDER};"
            f" border-radius: 10px; color: {C_TEXT_MUTED};"
            f" font-size: 13px; font-weight: 600; letter-spacing: 1px;"
        )

        self.lbl_depth_view = QLabel("DEPTH MAP")
        self.lbl_depth_view.setAlignment(Qt.AlignCenter)
        self.lbl_depth_view.setMinimumSize(420, 240)
        self.lbl_depth_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.lbl_depth_view.setStyleSheet(
            f"background-color: {C_BG_PANEL}; border: 1px solid {C_BORDER};"
            f" border-radius: 10px; color: {C_TEXT_MUTED};"
            f" font-size: 13px; font-weight: 600; letter-spacing: 1px;"
        )
        self.lbl_depth_view.hide()

        video_layout.addWidget(self.lbl_driver_view)
        layout.addLayout(video_layout, stretch=1)

        # ── Alert Status Strip ──
        status_frame = QFrame()
        status_frame.setStyleSheet(
            f"background-color: {C_BG_PANEL}; border: 1px solid {C_BORDER};"
            f" border-radius: 10px;"
        )
        status_lay = QVBoxLayout(status_frame)
        status_lay.setContentsMargins(20, 12, 20, 12)
        status_lay.setSpacing(4)

        self.lbl_status_box = QLabel("READY")
        self.lbl_status_box.setAlignment(Qt.AlignCenter)
        self.lbl_status_box.setMinimumHeight(56)
        self.lbl_status_box.setMaximumHeight(72)
        font_status = QFont()
        font_status.setPointSize(20)
        font_status.setWeight(QFont.Black)
        font_status.setLetterSpacing(QFont.AbsoluteSpacing, 1)
        self.lbl_status_box.setFont(font_status)
        self.lbl_status_box.setStyleSheet(
            f"background-color: {C_BORDER}; color: {C_TEXT_DIM};"
            f" border-radius: 8px; border: none;"
        )

        self.lbl_status_metrics = QLabel("MIN DEPTH: --    AVG DEPTH: --")
        self.lbl_status_metrics.setAlignment(Qt.AlignCenter)
        self.lbl_status_metrics.setStyleSheet(
            f"color: {C_TEXT_DIM}; font-size: 11px; font-weight: 600;"
            f" letter-spacing: 1px; border: none; background: transparent;"
        )

        self.lbl_trial_counter = QLabel("")
        self.lbl_trial_counter.setAlignment(Qt.AlignCenter)
        self.lbl_trial_counter.setStyleSheet(
            f"color: {C_ACCENT}; font-size: 12px; font-weight: 700;"
            f" letter-spacing: 2px; border: none; background: transparent;"
        )

        status_lay.addWidget(self.lbl_trial_counter)
        status_lay.addWidget(self.lbl_status_box)
        status_lay.addWidget(self.lbl_status_metrics)
        layout.addWidget(status_frame)

        # ── Progress Bar ──
        progress_lay = QHBoxLayout()
        progress_lay.setSpacing(12)
        self.slider_progress = QSlider(Qt.Horizontal)
        self.slider_progress.setEnabled(False)
        self.slider_progress.sliderPressed.connect(self._on_slider_pressed)
        self.slider_progress.sliderMoved.connect(self._on_slider_moved)
        self.slider_progress.sliderReleased.connect(self._on_slider_released)
        self.lbl_time = QLabel("00:00 / 00:00")
        self.lbl_time.setStyleSheet(
            f"color: {C_TEXT_DIM}; font-size: 12px; font-weight: 600;"
            f" font-variant-numeric: tabular-nums;"
        )
        self.lbl_time.setFixedWidth(100)
        progress_lay.addWidget(self.slider_progress)
        progress_lay.addWidget(self.lbl_time)
        layout.addLayout(progress_lay)

        # ── Controls Row ──
        controls_frame = QFrame()
        controls_frame.setStyleSheet(
            f"background-color: {C_BG_PANEL}; border: 1px solid {C_BORDER};"
            f" border-radius: 10px;"
        )
        ctrl_lay = QHBoxLayout(controls_frame)
        ctrl_lay.setContentsMargins(14, 10, 14, 10)
        ctrl_lay.setSpacing(8)

        # Transport buttons
        btn_load = QPushButton("  Load Video")
        btn_load.clicked.connect(self.load_video)

        self.btn_play = QPushButton("  Play")
        self.btn_play.clicked.connect(self.toggle_play)
        self.btn_play.setEnabled(False)

        self.btn_stop = QPushButton("  Stop")
        self.btn_stop.clicked.connect(self.stop_video)
        self.btn_stop.setEnabled(False)

        self.btn_loop = QPushButton("  Loop: OFF")
        self.btn_loop.setCheckable(True)
        self.btn_loop.clicked.connect(self.toggle_loop)

        # ── Condition selector (3-way segmented control) ──
        from src.core.experiment import ExperimentCondition

        self.condition_frame = QFrame()
        self.condition_frame.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self.condition_frame.setStyleSheet(
            f"background-color: {C_BG_CARD}; border: 1px solid {C_BORDER};"
            f" border-radius: 6px;"
        )
        cond_lay = QHBoxLayout(self.condition_frame)
        cond_lay.setContentsMargins(8, 4, 8, 4)
        cond_lay.setSpacing(4)

        cond_lbl = QLabel("CONDITION")
        cond_lbl.setMinimumWidth(90)
        cond_lbl.setStyleSheet(
            f"color: {C_TEXT_MUTED}; font-size: 10px; font-weight: 700;"
            f" padding: 0 10px; background: transparent; border: none;"
        )
        cond_lay.addWidget(cond_lbl)

        # Condition dropdown — replaces the cramped 3-button segmented control
        self.cb_condition = QComboBox()
        self.cb_condition.addItem("No Alert", ExperimentCondition.NO_ALERT)
        self.cb_condition.addItem("Standard", ExperimentCondition.STANDARD)
        self.cb_condition.addItem("AR HUD", ExperimentCondition.AR_HUD)
        self.cb_condition.setFixedSize(150, 32)
        f = self.cb_condition.font()
        f.setPointSize(12)
        f.setWeight(QFont.DemiBold)
        self.cb_condition.setFont(f)
        self.cb_condition.setStyleSheet(
            f"QComboBox {{ background-color: {C_BG_PANEL}; color: {C_ACCENT};"
            f" border: 1px solid {C_BORDER_LIT}; border-radius: 6px; padding: 4px 10px; }}"
            f"QComboBox::drop-down {{ border: none; padding-right: 8px; }}"
            f"QComboBox QAbstractItemView {{ background-color: {C_BG_CARD}; color: {C_TEXT};"
            f" selection-background-color: {C_ACCENT}; selection-color: {C_BG_DEEP};"
            f" border: 1px solid {C_BORDER}; }}"
        )
        self.cb_condition.currentIndexChanged.connect(self._on_condition_dropdown_changed)
        cond_lay.addWidget(self.cb_condition)
        self._refresh_condition_buttons()  # sync initial selection

        ctrl_lay.addWidget(btn_load)
        ctrl_lay.addWidget(self.btn_play)
        ctrl_lay.addWidget(self.btn_stop)
        ctrl_lay.addWidget(self.btn_loop)
        ctrl_lay.addSpacing(8)
        ctrl_lay.addWidget(self.condition_frame)

        # Separator
        ctrl_lay.addSpacing(8)
        self._sim_vsep = QFrame()
        self._sim_vsep.setFrameShape(QFrame.VLine)
        self._sim_vsep.setStyleSheet(f"color: {C_BORDER}; max-width: 1px;")
        ctrl_lay.addWidget(self._sim_vsep)
        ctrl_lay.addSpacing(8)

        # Model / Mode selectors
        self.lbl_model = QLabel("MODEL")
        self.lbl_model.setStyleSheet(
            f"color: {C_TEXT_MUTED}; font-size: 10px; font-weight: 700;"
            f" letter-spacing: 1px; background: transparent; border: none;"
        )
        self.cb_model = QComboBox()
        self.cb_model.addItems([
            "Mock Model",
            "MiDaS Small",
            "MiDaS Hybrid",
            "MiDaS Large",
            "DepthPro (Pretrained)",
            "Your Model (DepthPro)",
        ])
        self.cb_model.setFixedWidth(190)
        self.cb_model.currentIndexChanged.connect(self.switch_model)

        self.lbl_mode = QLabel("MODE")
        self.lbl_mode.setStyleSheet(
            f"color: {C_TEXT_MUTED}; font-size: 10px; font-weight: 700;"
            f" letter-spacing: 1px; background: transparent; border: none;"
        )
        self.cb_mode = QComboBox()
        self.cb_mode.addItems(["Desktop (Full)", "Jetson Nano (15 FPS)", "Jetson Xavier (30 FPS)"])
        self.cb_mode.currentIndexChanged.connect(self.update_simulation_mode)
        self.cb_mode.setFixedWidth(180)

        ctrl_lay.addWidget(self.lbl_model)
        ctrl_lay.addWidget(self.cb_model)
        ctrl_lay.addSpacing(8)
        ctrl_lay.addWidget(self.lbl_mode)
        ctrl_lay.addWidget(self.cb_mode)
        ctrl_lay.addStretch()

        # ── BRAKE button — right edge, always visible ──
        self.btn_brake = QPushButton("BRAKE  ⎵")
        self.btn_brake.setObjectName("BrakeBtn")
        self.btn_brake.clicked.connect(self.record_reaction)
        self.btn_brake.setFixedWidth(180)
        self.btn_brake.setFocusPolicy(Qt.NoFocus)  # avoid double-fire with SPACE shortcut
        self.btn_brake.setGraphicsEffect(self._glow_effect(C_DANGER, 24, 3))
        ctrl_lay.addWidget(self.btn_brake)

        layout.addWidget(controls_frame)

        # ── Session Row ──
        self._session_row = QFrame()
        self._session_row.setStyleSheet("background: transparent; border: none;")
        session_lay = QHBoxLayout(self._session_row)
        session_lay.setContentsMargins(0, 0, 0, 0)
        session_lay.setSpacing(8)

        self.lbl_pid = QLabel("PARTICIPANT")
        self.lbl_pid.setStyleSheet(
            f"color: {C_TEXT_MUTED}; font-size: 10px; font-weight: 700;"
            f" letter-spacing: 1px;"
        )
        self.inp_participant = QLineEdit()
        self.inp_participant.setPlaceholderText("Enter participant ID...")
        self.inp_participant.setFixedWidth(200)

        self.btn_start_session = QPushButton("  Start Session")
        self.btn_start_session.setObjectName("AccentBtn")
        self.btn_start_session.clicked.connect(self.start_session)

        self.btn_load_playlist = QPushButton("  📋  Load Playlist")
        self.btn_load_playlist.setObjectName("AccentBtn")
        self.btn_load_playlist.clicked.connect(self.load_playlist)

        self.btn_save_session = QPushButton("  Save Session")
        self.btn_save_session.clicked.connect(self.save_session)

        self.btn_webxr = QPushButton("  📡  WebXR: OFF")
        self.btn_webxr.setCheckable(True)
        self.btn_webxr.clicked.connect(self.toggle_webxr_server)

        # Persistent clickable URL — only visible when the WebXR server is running
        self.lbl_webxr_url = QLabel("")
        self.lbl_webxr_url.setTextFormat(Qt.RichText)
        self.lbl_webxr_url.setOpenExternalLinks(True)
        self.lbl_webxr_url.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.lbl_webxr_url.setStyleSheet(
            f"color: {C_ACCENT}; font-size: 11px; font-weight: 700;"
            f" padding: 0 8px; background: transparent; border: none;"
        )
        self.lbl_webxr_url.hide()

        session_lay.addWidget(self.lbl_pid)
        session_lay.addWidget(self.inp_participant)
        session_lay.addWidget(self.btn_start_session)
        session_lay.addWidget(self.btn_load_playlist)
        session_lay.addWidget(self.btn_save_session)
        session_lay.addWidget(self.btn_webxr)
        session_lay.addWidget(self.lbl_webxr_url)
        session_lay.addStretch()

        layout.addWidget(self._session_row)

        self.tabs.addTab(sim_tab, "SIMULATION")

    # ── TAB 2: PERFORMANCE MONITOR ───────────────────────────────
    def setup_monitor_tab(self):
        monitor_tab = QWidget()
        layout = QVBoxLayout(monitor_tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # ── Metric Cards Row ──
        cards_lay = QHBoxLayout()
        cards_lay.setSpacing(12)

        card_fps, self.lbl_mon_fps = self._make_metric_card("FPS", "0.0")
        card_target, self.lbl_mon_target = self._make_metric_card("TARGET FPS", "30")
        card_latency, self.lbl_mon_latency = self._make_metric_card("LATENCY", "0 ms")
        card_gpu, self.lbl_mon_gpu = self._make_metric_card("GPU MEMORY", "0 / 4096 MB")
        card_cpu, self.lbl_mon_cpu = self._make_metric_card("CPU USAGE", "0%")

        for card in [card_fps, card_target, card_latency, card_gpu, card_cpu]:
            cards_lay.addWidget(card)

        layout.addLayout(cards_lay)

        # ── Compatibility Badge ──
        self.lbl_mon_badge = QLabel("  JETSON NANO COMPATIBLE")
        self.lbl_mon_badge.setAlignment(Qt.AlignCenter)
        self.lbl_mon_badge.setFixedHeight(40)
        self.lbl_mon_badge.setStyleSheet(
            f"background-color: {C_BG_PANEL}; color: {C_SAFE};"
            f" border: 1px solid {C_SAFE}40; border-radius: 8px;"
            f" font-size: 12px; font-weight: 700; letter-spacing: 1.5px;"
        )
        layout.addWidget(self.lbl_mon_badge)

        # ── Charts ──
        pg.setConfigOption('background', C_BG_PANEL)
        pg.setConfigOption('foreground', C_TEXT_DIM)

        charts_lay = QHBoxLayout()
        charts_lay.setSpacing(12)

        # FPS chart
        fps_frame = QFrame()
        fps_frame.setStyleSheet(
            f"background-color: {C_BG_PANEL}; border: 1px solid {C_BORDER};"
            f" border-radius: 10px;"
        )
        fps_inner = QVBoxLayout(fps_frame)
        fps_inner.setContentsMargins(12, 10, 12, 10)

        fps_title = self._make_section_label("FPS HISTORY")
        self.fps_plot = pg.PlotWidget()
        self.fps_plot.setBackground(C_BG_PANEL)
        self.fps_plot.showGrid(x=False, y=True, alpha=0.1)
        self.fps_plot.getAxis('left').setPen(pg.mkPen(C_BORDER_LIT))
        self.fps_plot.getAxis('bottom').setPen(pg.mkPen(C_BORDER_LIT))
        self.fps_curve = self.fps_plot.plot(pen=pg.mkPen(C_ACCENT, width=2))
        self.fps_plot.setYRange(0, 60)

        fps_inner.addWidget(fps_title)
        fps_inner.addWidget(self.fps_plot)

        # Latency chart
        lat_frame = QFrame()
        lat_frame.setStyleSheet(
            f"background-color: {C_BG_PANEL}; border: 1px solid {C_BORDER};"
            f" border-radius: 10px;"
        )
        lat_inner = QVBoxLayout(lat_frame)
        lat_inner.setContentsMargins(12, 10, 12, 10)

        lat_title = self._make_section_label("LATENCY HISTORY (MS)")
        self.latency_plot = pg.PlotWidget()
        self.latency_plot.setBackground(C_BG_PANEL)
        self.latency_plot.showGrid(x=False, y=True, alpha=0.1)
        self.latency_plot.getAxis('left').setPen(pg.mkPen(C_BORDER_LIT))
        self.latency_plot.getAxis('bottom').setPen(pg.mkPen(C_BORDER_LIT))
        self.latency_curve = self.latency_plot.plot(pen=pg.mkPen(C_WARN, width=2))
        self.latency_plot.setYRange(0, 100)

        lat_inner.addWidget(lat_title)
        lat_inner.addWidget(self.latency_plot)

        charts_lay.addWidget(fps_frame)
        charts_lay.addWidget(lat_frame)

        layout.addLayout(charts_lay, stretch=1)

        self.tabs.addTab(monitor_tab, "PERFORMANCE")

    # ── TAB 3: SESSION ANALYSIS ──────────────────────────────────
    def setup_analysis_tab(self):
        analysis_tab = QWidget()
        layout = QVBoxLayout(analysis_tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # ── Stats Cards ──
        stats_lay = QHBoxLayout()
        stats_lay.setSpacing(12)

        card_hits, self.lbl_stat_hits = self._make_metric_card("HITS", "0")
        card_misses, self.lbl_stat_misses = self._make_metric_card("MISSES", "0")
        card_avg, self.lbl_stat_avg = self._make_metric_card("AVG REACTION TIME", "-- ms")
        card_correct, self.lbl_stat_detection = self._make_metric_card("DETECTION RATE", "0%")
        card_false, self.lbl_stat_false = self._make_metric_card("FALSE ALARMS", "0")

        self.lbl_stat_hits.setStyleSheet(
            f"color: {C_ACCENT}; font-size: 26px; font-weight: 700;"
            f" border: none; background: transparent;"
        )
        self.lbl_stat_detection.setStyleSheet(
            f"color: {C_ACCENT}; font-size: 26px; font-weight: 700;"
            f" border: none; background: transparent;"
        )
        self.lbl_stat_misses.setStyleSheet(
            f"color: {C_DANGER}; font-size: 26px; font-weight: 700;"
            f" border: none; background: transparent;"
        )
        self.lbl_stat_false.setStyleSheet(
            f"color: {C_DANGER}; font-size: 26px; font-weight: 700;"
            f" border: none; background: transparent;"
        )

        for card in [card_hits, card_misses, card_avg, card_correct, card_false]:
            stats_lay.addWidget(card)

        layout.addLayout(stats_lay)

        self.lbl_questionnaire_status = QLabel("NASA-TLX: 0/3 blocks  |  SUS: pending  |  Trust: pending")
        self.lbl_questionnaire_status.setStyleSheet(
            f"color: {C_TEXT_DIM}; font-size: 12px; font-weight: 600;"
            f" letter-spacing: 1px; padding: 8px 4px;"
        )
        layout.addWidget(self.lbl_questionnaire_status)

        # ── Reaction Log Table ──
        table_label = self._make_section_label("TRIAL OUTCOMES")
        layout.addWidget(table_label)

        self.table_logs = QTableWidget(0, 9)
        self.table_logs.setHorizontalHeaderLabels(
            ["TIME", "SOURCE", "CONDITION", "TRIAL", "EVENT", "EXPECTED", "OUTCOME", "RT (MS)", "NET (MS)"]
        )
        self.table_logs.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_logs.verticalHeader().setVisible(False)
        self.table_logs.setAlternatingRowColors(True)
        self.table_logs.setStyleSheet(
            self.table_logs.styleSheet() +
            f" QTableWidget::item:alternate {{ background-color: {C_BG_CARD}; }}"
        )
        self.table_logs.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table_logs, stretch=1)

        # ── Action Buttons ──
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_report = QPushButton("  Generate Report")
        btn_report.setObjectName("AccentBtn")
        btn_report.clicked.connect(self.update_analysis_tab)

        btn_csv = QPushButton("  Export CSV")
        btn_csv.clicked.connect(self.save_session)

        btn_clear = QPushButton("  Clear Session")
        btn_clear.setStyleSheet(
            f"background-color: transparent; border: 1px solid {C_DANGER}40;"
            f" color: {C_DANGER}; font-weight: 600;"
        )
        btn_clear.clicked.connect(self.clear_session)

        btn_layout.addWidget(btn_report)
        btn_layout.addSpacing(8)
        btn_layout.addWidget(btn_csv)
        btn_layout.addSpacing(8)
        btn_layout.addWidget(btn_clear)
        layout.addLayout(btn_layout)

        self.tabs.addTab(analysis_tab, "ANALYSIS")

    # ── Alert color mapping ────────────────────────────────────────
    ALERT_STYLES = {
        "SAFE":     {"bg": C_SAFE,    "text": "#FFFFFF", "border": C_SAFE},
        "CAUTION":  {"bg": C_CAUTION, "text": "#1A1A00", "border": C_CAUTION},
        "WARNING":  {"bg": C_WARN,    "text": "#FFFFFF", "border": C_WARN},
        "CRITICAL": {"bg": C_DANGER,  "text": "#FFFFFF", "border": C_DANGER},
    }

    # ── Video & Simulation Logic ─────────────────────────────────
    def load_video(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open Video", "",
            "Video Files (*.mp4 *.avi *.mkv);;All Files (*)"
        )
        if filename:
            # Loading a single video clears any active playlist
            self.playlist = None
            self.current_trial = None
            self.lbl_trial_counter.setText("")
            self._open_video_file(filename)

    def _open_video_file(self, filename: str):
        """Opens a video file and prepares the player. Used by both single-load and playlist."""
        if self.cap is not None:
            self.cap.release()
        self.cap = cv2.VideoCapture(filename)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.slider_progress.setMaximum(self.total_frames)

        self.btn_play.setEnabled(True)
        self.btn_stop.setEnabled(True)
        self.slider_progress.setEnabled(True)

        self.set_frame_position(0)
        self.process_next_frame(update_progress_only=True)

    def load_playlist(self):
        """
        Solo-test mode: load scenarios.csv and walk through all trials in the
        currently-selected condition. Use this for self-testing or quick demos.
        For structured multi-participant sessions with Latin-square ordering,
        use 'Start Session' instead.
        """
        csv_path, _ = QFileDialog.getOpenFileName(
            self, "Open scenarios.csv", "data",
            "CSV Files (*.csv);;All Files (*)"
        )
        if not csv_path:
            return

        try:
            self.playlist = PlaylistManager(csv_path, base_dir="data/scenarios", shuffle=True)
        except Exception as e:
            QMessageBox.critical(self, "Playlist Error", f"Could not load playlist:\n{e}")
            return

        # Solo mode — make sure block-end logic doesn't fire
        self.session_mode = False
        self.session_plan = None

        if self.playlist.total == 0:
            QMessageBox.warning(self, "Empty Playlist", "No scenarios found in CSV.")
            self.playlist = None
            return

        QMessageBox.information(
            self, "Playlist Loaded",
            f"Loaded {self.playlist.total} scenarios.\n\nClick Play to start the session.\n"
            f"Press SPACE during a trial to BRAKE."
        )

        self._advance_to_next_trial()

    def _handle_block_end(self):
        """Block done. If more blocks remain, show pause dialog + start next; else end session."""
        from src.core.experiment import display_name
        from src.ui.block_pause_dialog import BlockPauseDialog

        # Pause playback hard
        self.is_playing = False
        self.playback_timer.stop()
        self._flash_timer.stop()
        self.audio_system.set_alert_level("SAFE")
        self.btn_play.setText("  Play")

        finished = self.session_plan.blocks[self.session_block_index]
        next_idx = self.session_block_index + 1

        if not self._capture_tlx_response(finished.block_num, display_name(finished.condition), finished.condition.value):
            return

        if next_idx >= len(self.session_plan.blocks):
            if not self._capture_final_questionnaire():
                return
            self._show_session_complete_screen()
            return

        nxt = self.session_plan.blocks[next_idx]
        dlg = BlockPauseDialog(
            completed_block=finished.block_num,
            completed_condition=display_name(finished.condition),
            next_block=nxt.block_num,
            next_condition=display_name(nxt.condition),
            parent=self,
        )
        dlg.exec_()  # blocks until researcher clicks Continue
        self._start_block(next_idx)

    def _capture_tlx_response(self, block_num: int, condition_label: str, condition_value: str) -> bool:
        from src.ui.study_questionnaire_dialogs import NASATLXDialog

        dialog = NASATLXDialog(block_num, condition_label, parent=self)
        if dialog.exec_() != QDialog.Accepted:
            QMessageBox.warning(
                self,
                "NASA-TLX Not Saved",
                "This block is paused. The NASA-TLX response is required before continuing.",
            )
            return False
        self.data_logger.log_nasa_tlx(block_num, condition_value, dialog.scores())
        self.update_analysis_tab()
        return True

    def _capture_final_questionnaire(self) -> bool:
        from src.ui.study_questionnaire_dialogs import FinalQuestionnaireDialog

        dialog = FinalQuestionnaireDialog(parent=self)
        if dialog.exec_() != QDialog.Accepted:
            QMessageBox.warning(
                self,
                "Final Questionnaire Not Saved",
                "The final SUS, trust and demographics form is required before completing the session.",
            )
            return False
        self.data_logger.log_final_questionnaire(
            dialog.sus_responses(),
            dialog.responses(),
        )
        self.update_analysis_tab()
        return True

    def _show_session_complete_screen(self):
        """End-of-session UI state."""
        self.is_playing = False
        self.playback_timer.stop()
        self._flash_timer.stop()
        self.btn_play.setText("  Play")
        if hasattr(self, "lbl_trial_counter"):
            self.lbl_trial_counter.setText("SESSION COMPLETE")
        self._apply_status_style("SAFE", "--", "--")
        self.audio_system.set_alert_level("SAFE")
        self.lbl_driver_view.setText("SESSION COMPLETE\n\nSave the session from the controls below.")
        self.lbl_driver_view.setPixmap(QPixmap())
        self.lbl_depth_view.setText("")
        self.lbl_depth_view.setPixmap(QPixmap())
        self.session_mode = False
        QMessageBox.information(
            self, "Session Complete",
            "All trials done. Click 'Save Session' to export the data."
        )

    def _advance_to_next_trial(self):
        """Load the next clip from the playlist, or end the session if none left."""
        if self.playlist is None:
            return

        self._between_trials = False
        self._smoothed_threat_box = None  # fresh tracker for new clip
        self._last_object_detections = []
        scenario = self.playlist.next()

        if scenario is None:
            # Block / playlist ended — branch on whether we're in session mode
            if self.session_mode and self.session_plan is not None:
                self._handle_block_end()
                return
            # Solo playlist mode — full stop
            self._show_session_complete_screen()
            return

        self.current_trial = scenario
        self.trial_start_time = time.time()

        self.lbl_trial_counter.setText(
            f"TRIAL {self.playlist.trial_num} OF {self.playlist.total}  "
            f"·  {scenario['event_type'].upper()}"
        )

        self._open_video_file(scenario["full_path"])

        # Auto-start playback
        if not self.is_playing:
            self.toggle_play()

    def _handle_trial_end(self):
        """Called when a playlist clip finishes — show 2-s blank, then load next."""
        self.is_playing = False
        self.playback_timer.stop()
        self._flash_timer.stop()
        self.audio_system.set_alert_level("SAFE")
        self.btn_play.setText("  Play")

        # Score any missed-event for this trial
        self._score_trial_miss()

        # Show inter-trial blank
        self._between_trials = True
        self.lbl_driver_view.clear()
        self.lbl_driver_view.setText("• • •")
        self.lbl_driver_view.setStyleSheet(
            f"background-color: {C_BG_DEEP}; border: 1px solid {C_BORDER};"
            f" border-radius: 10px; color: {C_TEXT_MUTED};"
            f" font-size: 24px; font-weight: 700; letter-spacing: 8px;"
        )
        self.lbl_depth_view.clear()
        self.lbl_depth_view.setText("")
        self._apply_status_style("SAFE", "--", "--")

        # Schedule next trial after 2 s
        QTimer.singleShot(2000, self._advance_to_next_trial)

    def _score_trial_miss(self):
        """If the participant didn't brake on a critical/warning trial, log a miss."""
        if self.current_trial is None:
            return

        expected = self.current_trial.get("expected_alert_level", "SAFE")
        if expected in ("CRITICAL", "WARNING"):
            # Out-of-window presses still count as a miss, but score each trial once.
            already_scored = any(
                r.get("trial_id") == self.current_trial["id"]
                and r.get("outcome") in ("hit", "miss")
                for r in self.data_logger.reaction_data
            )
            if not already_scored:
                self.data_logger.log_miss(
                    trial_id=self.current_trial["id"],
                    event_type=self.current_trial["event_type"],
                    expected_level=expected,
                    condition=self.condition.value,
                    event_start_ms=int(self.current_trial.get("event_start_ms", 0)),
                )
                self.update_analysis_tab()
        elif expected == "SAFE":
            already_scored = any(
                r.get("trial_id") == self.current_trial["id"]
                and r.get("outcome") in ("false_alarm", "correct_rejection")
                for r in self.data_logger.reaction_data
            )
            if not already_scored:
                self.data_logger.log_correct_rejection(
                    trial_id=self.current_trial["id"],
                    event_type=self.current_trial["event_type"],
                    condition=self.condition.value,
                )
                self.update_analysis_tab()

    def toggle_play(self):
        if not self.cap or not self.cap.isOpened():
            return
        if self.is_playing:
            self.is_playing = False
            self.playback_timer.stop()
            self._flash_timer.stop()
            self.btn_play.setText("  Play")
            self.audio_system.set_alert_level("SAFE")
        else:
            self.is_playing = True
            delay = int(1000 / self.target_fps)
            self.playback_timer.start(delay)
            self.btn_play.setText("  Pause")
        # Mirror playback state to any connected WebXR / VR clients
        if self.webxr_server is not None and self.webxr_server.is_running():
            self.webxr_server.push_event("playback", {"playing": self.is_playing})

    def stop_video(self):
        self.is_playing = False
        self.playback_timer.stop()
        self._flash_timer.stop()
        self.btn_play.setText("  Play")
        self.set_frame_position(0)
        self.process_next_frame(update_progress_only=True)
        self.audio_system.set_alert_level("SAFE")
        self._apply_status_style("SAFE", "--", "--")
        self._smoothed_threat_box = None
        self._last_object_detections = []
        if self.webxr_server is not None and self.webxr_server.is_running():
            self.webxr_server.push_event("playback", {"playing": False})

    def toggle_loop(self):
        self.is_looping = self.btn_loop.isChecked()
        self.btn_loop.setText(f"  Loop: {'ON' if self.is_looping else 'OFF'}")

    def _on_condition_dropdown_changed(self, index: int):
        """Forward dropdown changes into set_condition()."""
        condition = self.cb_condition.itemData(index)
        if condition is not None:
            self.set_condition(condition)

    def _refresh_condition_buttons(self):
        """Sync the dropdown selection to the current condition (call after set_condition)."""
        from src.core.experiment import ExperimentCondition
        idx_map = {
            ExperimentCondition.NO_ALERT: 0,
            ExperimentCondition.STANDARD: 1,
            ExperimentCondition.AR_HUD: 2,
        }
        target = idx_map.get(self.condition, 1)
        if self.cb_condition.currentIndex() != target:
            self.cb_condition.blockSignals(True)
            self.cb_condition.setCurrentIndex(target)
            self.cb_condition.blockSignals(False)

    def set_condition(self, condition):
        """Activate one of the three experimental conditions."""
        from src.core.experiment import flags_for
        self.condition = condition
        self.condition_flags = flags_for(condition)
        self.ar_mode_enabled = self.condition_flags.ar_overlay_enabled
        self._refresh_condition_buttons()

        # Swap the audio palette to match the experimental condition so
        # STANDARD vs AR_HUD feels acoustically different to the participant
        self.audio_system.set_condition(condition.value)

        # Stop audio immediately if condition disables it (otherwise loop continues briefly)
        if not self.condition_flags.audio_enabled:
            self.audio_system.set_alert_level("SAFE")

        # Mirror the active condition to any connected WebXR clients
        if self.webxr_server is not None and self.webxr_server.is_running():
            self.webxr_server.push_condition(condition.value)

        # Re-render the current paused frame so the change is visible
        if self.cap and not self.is_playing:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
            self.process_next_frame(update_progress_only=True)
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)

    def switch_model(self, index):
        """Switch depth estimation model based on combo selection."""
        global MiDaSModel

        was_playing = self.is_playing
        if was_playing:
            self.toggle_play()  # pause during switch

        if index == 0:
            # Mock Model
            self.model = MockModel()
        elif index in (1, 2, 3):
            # MiDaS variants: 1=small, 2=hybrid, 3=large
            variant = ["small", "hybrid", "large"][index - 1]
            if not self._load_model_safe(
                lambda: self._load_midas(variant),
                f"LOADING MIDAS {variant.upper()}...",
                "MiDaS requires PyTorch.\n\npip install torch torchvision timm"
            ):
                return
        elif index == 4:
            # DepthPro pretrained (no custom weights)
            if not self._load_model_safe(
                lambda: self._load_depthpro(checkpoint=None),
                "LOADING DEPTHPRO...",
                "DepthPro not installed.\n\n"
                "Install from your repo:\n"
                "  git clone https://github.com/Dariusan3/ml-depth-pro.git\n"
                "  cd ml-depth-pro && pip install -e .\n"
                "  source get_pretrained_models.sh"
            ):
                return
        elif index == 5:
            # Your trained model (DepthPro backbone + your self-supervised weights)
            weights_path = os.path.join("checkpoints", "latest.pt")
            if not os.path.exists(weights_path):
                QMessageBox.warning(
                    self, "No Trained Weights",
                    f"No checkpoint found at:\n  {os.path.abspath(weights_path)}\n\n"
                    "Train your model first:\n"
                    "  python train.py --data data/driving --epochs 20"
                )
                self.cb_model.blockSignals(True)
                self.cb_model.setCurrentIndex(0)
                self.cb_model.blockSignals(False)
                return
            if not self._load_model_safe(
                lambda: self._load_depthpro(checkpoint=weights_path),
                "LOADING YOUR MODEL...",
                "DepthPro not installed.\n\n"
                "Install from your repo:\n"
                "  git clone https://github.com/Dariusan3/ml-depth-pro.git\n"
                "  cd ml-depth-pro && pip install -e .\n"
                "  source get_pretrained_models.sh"
            ):
                return

        self._apply_status_style("SAFE", "--", "--")
        if was_playing:
            self.toggle_play()

    def _show_loading(self, text):
        """Set the alert-bar to a loading state (still used as a hint while dialog is up)."""
        self.lbl_status_box.setText(text)
        self.lbl_status_box.setStyleSheet(
            f"background-color: {C_BORDER}; color: {C_ACCENT};"
            f" border-radius: 8px; border: none;"
        )

    def _load_model_safe(self, loader_fn, loading_text, install_msg):
        """
        Try loading a model in a background thread, with a modal loading dialog.
        Returns True on success, False on failure (with the model dropdown reset).
        """
        from src.ui.loading_dialog import LoadingDialog, ModelLoaderThread

        self._show_loading(loading_text)
        dialog = LoadingDialog(loading_text, parent=self)

        result = {"success": False, "error": None, "model": None}

        worker = ModelLoaderThread(loader_fn, parent=self)

        def on_ok(model):
            result["success"] = True
            result["model"] = model
            dialog.accept()

        def on_err(err):
            result["error"] = err
            dialog.reject()

        worker.finished_ok.connect(on_ok)
        worker.finished_err.connect(on_err)
        worker.start()

        # Block on dialog until worker finishes (or user closes — but it's frameless)
        dialog.exec_()
        worker.wait(50)  # cleanup

        if result["success"]:
            self.model = result["model"]
            return True

        err = result["error"]
        if isinstance(err, ImportError):
            QMessageBox.critical(self, "Missing Dependencies", install_msg)
        else:
            QMessageBox.critical(self, "Model Error", str(err) if err else "Unknown error")

        self.cb_model.blockSignals(True)
        self.cb_model.setCurrentIndex(0)
        self.cb_model.blockSignals(False)
        return False

    def _load_midas(self, variant):
        global MiDaSModel
        if MiDaSModel is None:
            from src.models.midas_model import MiDaSModel as _M
            MiDaSModel = _M
        return MiDaSModel(variant=variant)

    def _load_depthpro(self, checkpoint=None):
        from src.models.depth_pro_model import DepthProModel
        return DepthProModel(checkpoint=checkpoint)

    def update_simulation_mode(self):
        mode = self.cb_mode.currentIndex()
        if mode == 0:
            self.target_fps = 30
        elif mode == 1:
            self.target_fps = 15
        elif mode == 2:
            self.target_fps = 30

        self.lbl_mon_target.setText(str(self.target_fps))
        if self.is_playing:
            self.playback_timer.setInterval(int(1000 / self.target_fps))

    def set_frame_position(self, frame_num):
        if self.cap:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            self.current_frame = frame_num
            self._update_time_label()

    # ── Slider drag (scrubbing) ──────────────────────────────────
    def _on_slider_pressed(self):
        """User started dragging — pause playback (will resume on release)."""
        self._was_playing_before_seek = self.is_playing
        if self.is_playing:
            self.is_playing = False
            self.playback_timer.stop()
            self._flash_timer.stop()
            self.btn_play.setText("  Play")
            self.audio_system.set_alert_level("SAFE")

    def _on_slider_moved(self, frame_num):
        """User dragging — seek cursor + label live; debounce frame render."""
        self.set_frame_position(frame_num)
        # Debounce expensive inference: render 80 ms after the user stops moving
        self._seek_preview_timer.start(80)

    def _on_slider_released(self):
        """User released — render the final frame and resume if it was playing."""
        self._seek_preview_timer.stop()
        self._render_seek_preview()
        if self._was_playing_before_seek:
            # Re-seek to keep the just-displayed frame on screen, then resume
            self.set_frame_position(self.current_frame)
            self.toggle_play()
        self._was_playing_before_seek = False

    def _render_seek_preview(self, mirror_to_webxr=False):
        """Render the frame at the current cursor without advancing alerts/logs."""
        if self.cap is None:
            return
        # Re-seek (cap.read() in process_next_frame consumes one frame)
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        self._smoothed_threat_box = None  # reset tracker — discontinuity
        self._last_object_detections = []
        self.process_next_frame(update_progress_only=True, mirror_to_webxr=mirror_to_webxr)
        # Re-seek again so the next read picks up from the right place
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)

    def process_next_frame(self, update_progress_only=False, mirror_to_webxr=False):
        if self.cap is None:
            return

        ret, frame = self.cap.read()
        if not ret:
            # Clip ended
            if self.playlist is not None:
                self._handle_trial_end()
                return
            elif self.is_looping:
                self.set_frame_position(0)
                return self.process_next_frame()
            else:
                self.stop_video()
                return

        # If this trial is a 360° equirectangular clip, crop to the forward view
        # so the depth model + alert ROI work on a normal-looking rectangle.
        if self.current_trial and self.current_trial.get("projection") == "equirectangular":
            frame = self._crop_equirectangular_forward(frame)

        self.current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        if not update_progress_only:
            self.slider_progress.setValue(self.current_frame)
            self._update_time_label()

            # ── CORE SIMULATION PIPELINE ──
            t0 = time.time()
            raw_depth = self.model.inference(frame)
            alert_res = self.alert_system.process_depth(raw_depth)
            detections = self._detect_objects_for_frame(frame, raw_depth)
            alert_res["objects"] = self._detection_payloads(detections)
            alert_res["detector_status"] = self._last_detector_status
            latency_ms = (time.time() - t0) * 1000

            self.perf_monitor.record_frame(latency_ms)

            if self.current_frame % 10 == 0:
                self.data_logger.log_frame(
                    self.current_frame,
                    alert_res["level"],
                    alert_res["min_depth"],
                    condition=self.condition.value,
                    trial_id=self.current_trial.get("id", "") if self.current_trial else "",
                )

            # Audio gated by current condition (NO_ALERT condition silences it)
            if self.condition_flags.audio_enabled:
                self.audio_system.set_alert_level(alert_res["level"])
            else:
                self.audio_system.set_alert_level("SAFE")
            self.update_video_panels(frame, raw_depth, alert_res, detections)

            # Push to WebXR clients (throttled to ~15 FPS to keep bandwidth sane)
            if self.webxr_server is not None and self.webxr_server.is_running():
                now = time.time()
                if now - self._last_webxr_push_t >= 1.0 / 15.0:
                    self._last_webxr_push_t = now
                    trial_meta = None
                    if self.current_trial is not None:
                        trial_meta = {
                            "trial_id": self.current_trial.get("id"),
                            "trial_num": getattr(self.playlist, "trial_num", 0),
                            "total": getattr(self.playlist, "total", 0),
                            "event_type": self.current_trial.get("event_type"),
                            "label": f"Trial {getattr(self.playlist, 'trial_num', 0)}/"
                                     f"{getattr(self.playlist, 'total', 0)}",
                        }
                    self.webxr_server.push_frame(
                        frame, raw_depth, alert_res, trial_meta, detections
                    )

            self._apply_status_style(
                alert_res["level"], alert_res["min_depth"], alert_res["avg_depth"]
            )
        else:
            depth = self.model.inference(frame)
            alert_res = self.alert_system.process_depth(depth)
            detections = self._detect_objects_for_frame(frame, depth)
            alert_res["objects"] = self._detection_payloads(detections)
            alert_res["detector_status"] = self._last_detector_status
            self.update_video_panels(frame, depth, alert_res, detections)
            if mirror_to_webxr and self.webxr_server is not None and self.webxr_server.is_running():
                self.webxr_server.push_frame(frame, depth, alert_res, None, detections)

    def _detect_objects_for_frame(self, frame, depth_map):
        """
        Run YOLO every few frames and reuse the last result between runs.

        This keeps the overlay realistic without making the UI wait for object
        detection on every rendered frame. If YOLO is unavailable, this returns
        an empty list and the old depth-contour tracker still provides a box.
        """
        if self.current_frame % self._object_detection_stride != 0:
            return self._last_object_detections

        detections = self.object_detector.detect(frame, depth_map)
        self._last_object_detections = detections
        if self.object_detector.error:
            self._last_detector_status = f"YOLO unavailable: {self.object_detector.error}"
        elif not self.object_detector.enabled:
            self._last_detector_status = "YOLO disabled"
        else:
            self._last_detector_status = (
                f"YOLO {self.object_detector.model_name}: {len(detections)} objects"
            )
        return detections

    @staticmethod
    def _detection_payloads(detections):
        return [d.to_payload() if hasattr(d, "to_payload") else d for d in detections]

    def _primary_detection_box(self, detections, alert_res):
        if not detections:
            return None

        level = alert_res.get("level", "SAFE")
        if level == "SAFE":
            return None

        rx1, ry1, rx2, ry2 = alert_res["roi_coords"]
        best = None
        best_score = -1.0
        for det in detections:
            x1, y1, x2, y2 = det.bbox
            cx, cy = det.center
            in_roi = rx1 <= cx <= rx2 and ry1 <= cy <= ry2
            depth = 0.5 if det.depth is None else det.depth
            score = det.importance + (0.35 if in_roi else 0.0) + (0.20 * (1.0 - depth))
            if score > best_score:
                best = (x1, y1, x2, y2)
                best_score = score
        return best

    def _find_threat_box(self, depth_map, alert_res):
        """
        Locate the closest threat object in the frame and return its bbox.

        Heuristics:
        - Skip top 15% (sky) and bottom 22% (hood/road) of the frame.
        - Use the 2nd percentile depth as the threshold — robust to outliers
          and adapts to per-frame depth distribution. Capped relative to the
          alert anchor depth so we don't expand into the road.
        - Filter contours by size, aspect ratio, and width-fraction (drop the
          road which spans the full width).
        - Score remaining candidates by area + center-bias and pick the best.

        Returns None if alert is SAFE or no plausible threat is found.
        """
        level = alert_res["level"]
        if level == "SAFE":
            return None

        h, w = depth_map.shape[:2]
        sy1, sy2 = int(h * 0.15), int(h * 0.78)
        search = depth_map[sy1:sy2, :]

        # Percentile-based threshold — closest 2% of pixels in the region
        cutoff = float(np.percentile(search, 2.0))
        # Don't let the cutoff drift far from the alert-system's anchor
        anchor = float(alert_res["min_depth"])
        cutoff = min(cutoff + 0.03, anchor + 0.10)

        mask = (search <= cutoff).astype(np.uint8) * 255
        if mask.sum() < 100 * 255:
            return None

        # Heavy morphological cleanup
        kernel = np.ones((9, 9), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        candidates = []
        frame_cx = w / 2.0
        # Don't surface threats that are too small relative to the frame —
        # those are far-away objects the driver doesn't need to react to yet.
        # 0.5% of the frame area = ~3000 px on a 720p image, roughly a
        # pedestrian-sized blob at moderate distance.
        MIN_AREA_FRAC = 0.005
        frame_area = w * h
        for c in contours:
            area = cv2.contourArea(c)
            if area < 250:
                continue
            if area / frame_area < MIN_AREA_FRAC:
                # Too small on screen → too far away to alert on
                continue
            bx, by, bw, bh = cv2.boundingRect(c)

            # Drop tiny detections
            if bw < 30 or bh < 30:
                continue
            # Drop blobs spanning the whole width — those are road / horizon, not objects
            if bw > w * 0.80:
                continue
            # Drop implausible aspect ratios (very wide thin or extremely tall thin)
            aspect = bh / max(bw, 1)
            if aspect < 0.20 or aspect > 5.0:
                continue

            # Score: bigger + closer-to-center is better
            cx = bx + bw / 2.0
            center_penalty = abs(cx - frame_cx) / frame_cx  # 0 at center, 1 at edge
            score = area * (1.0 - 0.35 * center_penalty)

            candidates.append((score, (bx, sy1 + by, bx + bw, sy1 + by + bh)))

        if not candidates:
            return None

        candidates.sort(key=lambda t: t[0], reverse=True)
        return candidates[0][1]

    @staticmethod
    def _box_iou(a, b):
        """Intersection-over-union for two (x1, y1, x2, y2) boxes."""
        ix1 = max(a[0], b[0])
        iy1 = max(a[1], b[1])
        ix2 = min(a[2], b[2])
        iy2 = min(a[3], b[3])
        iw = max(0, ix2 - ix1)
        ih = max(0, iy2 - iy1)
        inter = iw * ih
        if inter == 0:
            return 0.0
        area_a = max(1, (a[2] - a[0]) * (a[3] - a[1]))
        area_b = max(1, (b[2] - b[0]) * (b[3] - b[1]))
        return inter / (area_a + area_b - inter)

    def _smooth_box(self, new_box, alpha=0.25):
        """
        EMA smoothing on the threat box with two added behaviors:

        - **Stability gate**: a new threat must persist for >= STABILITY_FRAMES
          before it appears on screen. Prevents single-frame flashes.
        - **Grace frames**: when the detector temporarily loses the threat
          (e.g. occlusion), keep showing the last box for GRACE_FRAMES.
        - **Jump detection**: if the new detection is far from the smoothed
          one (low IoU), treat it as a new object and snap rather than drift.
        """
        STABILITY_FRAMES = 3
        GRACE_FRAMES = 6
        SNAP_IOU = 0.15

        # Init bookkeeping fields lazily
        if not hasattr(self, "_box_grace"):
            self._box_grace = 0
            self._box_stable_count = 0
            self._pending_box = None

        if new_box is None:
            # Threat gone — keep showing for a few frames then drop
            if self._box_grace > 0 and self._smoothed_threat_box is not None:
                self._box_grace -= 1
                return self._smoothed_threat_box
            self._smoothed_threat_box = None
            self._pending_box = None
            self._box_stable_count = 0
            return None

        # Refresh the grace counter — we have a detection
        self._box_grace = GRACE_FRAMES

        # No active box yet — go through the stability gate
        if self._smoothed_threat_box is None:
            if self._pending_box is None or self._box_iou(new_box, self._pending_box) < SNAP_IOU:
                self._pending_box = new_box
                self._box_stable_count = 1
            else:
                self._box_stable_count += 1
            if self._box_stable_count >= STABILITY_FRAMES:
                self._smoothed_threat_box = new_box
                self._pending_box = None
            return self._smoothed_threat_box  # may be None until stable

        # Active box already on screen
        if self._box_iou(new_box, self._smoothed_threat_box) < SNAP_IOU:
            # Detection jumped — likely a different object. Snap.
            self._smoothed_threat_box = new_box
        else:
            # Smooth update
            self._smoothed_threat_box = tuple(
                int(alpha * n + (1 - alpha) * o)
                for n, o in zip(new_box, self._smoothed_threat_box)
            )
        return self._smoothed_threat_box

    def _draw_object_boxes(self, image, detections, primary_box=None, subtle=False):
        if not detections:
            return image

        for det in detections:
            x1, y1, x2, y2 = det.bbox
            color = self._object_box_color(det.label, det.depth)
            is_primary = primary_box is not None and self._box_iou((x1, y1, x2, y2), primary_box) > 0.50
            thickness = 3 if is_primary else (1 if subtle else 2)
            cv2.rectangle(image, (x1, y1), (x2, y2), color, thickness)

            label = det.label.upper()
            if det.confidence is not None:
                label = f"{label} {det.confidence:.2f}"
            if det.depth is not None:
                label = f"{label} d={det.depth:.2f}"

            font_scale = 0.45 if subtle else 0.52
            (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)
            label_y1 = max(0, y1 - lh - 8)
            label_y2 = label_y1 + lh + 6
            overlay = image.copy()
            cv2.rectangle(overlay, (x1, label_y1), (min(image.shape[1] - 1, x1 + lw + 10), label_y2), color, -1)
            alpha = 0.70 if subtle else 0.90
            cv2.addWeighted(overlay, alpha, image, 1.0 - alpha, 0, image)
            cv2.putText(
                image,
                label,
                (x1 + 5, label_y2 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )
        return image

    def _draw_detector_status(self, image, detections):
        if detections:
            return image
        status = getattr(self, "_last_detector_status", "")
        if not status or status == "YOLO: waiting":
            return image

        text = status
        if len(text) > 86:
            text = text[:83] + "..."
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 0.46
        (tw, th), _ = cv2.getTextSize(text, font, scale, 1)
        x, y = 14, 28
        overlay = image.copy()
        cv2.rectangle(overlay, (x - 7, y - th - 8), (x + tw + 8, y + 8), (12, 16, 33), -1)
        cv2.addWeighted(overlay, 0.75, image, 0.25, 0, image)
        cv2.putText(image, text, (x, y), font, scale, (10, 214, 255), 1, cv2.LINE_AA)
        return image

    @staticmethod
    def _object_box_color(label, depth=None):
        if isinstance(depth, (int, float)):
            if depth <= 0.25:
                return (85, 45, 255)   # close: red
            if depth <= 0.40:
                return (10, 159, 255)  # approaching: orange
            if depth <= 0.60:
                return (10, 214, 255)  # caution: yellow
        colors = {
            "person": (85, 45, 255),
            "bicycle": (10, 159, 255),
            "motorcycle": (10, 159, 255),
            "car": (0, 229, 160),
            "bus": (48, 209, 88),
            "truck": (48, 209, 88),
            "traffic light": (10, 214, 255),
            "stop sign": (85, 45, 255),
        }
        return colors.get(label, (232, 236, 244))

    def update_video_panels(self, frame, depth_map, alert_res, detections=None):
        detections = detections or []

        # Real detector box used by both standard and AR rendering.
        detector_box = self._primary_detection_box(detections, alert_res)
        threat_box = self._smooth_box(detector_box)

        # ── AR HUD condition: hand off to the AR overlay renderer ──
        if self.condition_flags.ar_overlay_enabled:
            disp_frame = self.ar_overlay.render(frame, depth_map, alert_res, threat_box)
            self._draw_object_boxes(disp_frame, detections, primary_box=threat_box, subtle=True)
            self._draw_detector_status(disp_frame, detections)
            w1, h1 = self.lbl_driver_view.width(), self.lbl_driver_view.height()
            self.lbl_driver_view.setPixmap(self._cv2_to_qpixmap(disp_frame, w1, h1))
            return

        # ── Standard / NO_ALERT mode below ──
        disp_frame = frame.copy()

        show_detector_boxes = bool(detections) and (
            self.condition_flags.threat_box_visible
            or not (self.session_mode and self.condition.name == "NO_ALERT")
        )
        if show_detector_boxes:
            self._draw_object_boxes(disp_frame, detections, primary_box=threat_box)
        elif self.condition_flags.threat_box_visible:
            self._draw_detector_status(disp_frame, detections)

        # ── Peripheral edge glow + dashboard icon ──
        # Non-AR conditions get a real-car-style warning panel and edge cue.
        # Together these give STANDARD a clear visual signal without revealing
        # the depth model's reasoning (no bounding box on the windshield).
        if not self.condition_flags.ar_overlay_enabled and \
           self.condition_flags.alert_bar_visible:
            self._draw_peripheral_glow(disp_frame, threat_box, alert_res)
            self._draw_dashboard_icon(disp_frame, alert_res)

        w1, h1 = self.lbl_driver_view.width(), self.lbl_driver_view.height()
        self.lbl_driver_view.setPixmap(self._cv2_to_qpixmap(disp_frame, w1, h1))

    def _draw_dashboard_icon(self, frame, alert_res):
        """
        Bottom-center dashboard-style warning icon — pulses when there's a
        non-SAFE alert. Inspired by car instrument-cluster warning lights.
        Visual cue for the STANDARD condition that doesn't require a
        bounding box around the threat.
        """
        level = alert_res.get("level", "SAFE")
        if level == "SAFE":
            return

        h, w = frame.shape[:2]
        style = self.ALERT_STYLES.get(level, self.ALERT_STYLES["SAFE"])
        bgr = tuple(int(style["bg"].lstrip('#')[i:i+2], 16) for i in (4, 2, 0))

        # Pulse for CRITICAL — alternates intensity on a ~5 Hz beat
        flash_on = (int(time.time() * 5) % 2 == 0)
        intensity = 1.0 if (level != "CRITICAL" or flash_on) else 0.55

        cx, cy = w // 2, int(h * 0.93)
        size = max(28, h // 18)

        # Background plate (dark rounded panel)
        plate_w, plate_h = size * 4, int(size * 1.4)
        x1, y1 = cx - plate_w // 2, cy - plate_h // 2
        x2, y2 = x1 + plate_w, y1 + plate_h
        overlay = frame.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (12, 16, 33), -1)
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, dst=frame)
        cv2.rectangle(frame, (x1, y1), (x2, y2),
                      tuple(int(c * intensity) for c in bgr), 2)

        # Stylized "car + radar arc" glyph
        scaled = tuple(int(c * intensity) for c in bgr)
        car_x, car_y = cx - int(size * 0.9), cy
        cv2.rectangle(frame, (car_x, car_y - size // 4),
                      (car_x + int(size * 0.7), car_y + size // 4),
                      scaled, -1)
        # arc represents detection beam
        cv2.ellipse(frame, (cx + int(size * 0.4), cy), (size, size // 2),
                    0, -50, 50, scaled, 2)
        cv2.ellipse(frame, (cx + int(size * 0.4), cy),
                    (int(size * 1.4), int(size * 0.7)),
                    0, -50, 50, scaled, 2)

        # Level abbreviation to the right
        text = level[0]  # C, W, A, S
        cv2.putText(frame, text, (cx + int(size * 1.4), cy + size // 3),
                    cv2.FONT_HERSHEY_SIMPLEX, size / 28.0, scaled,
                    max(2, size // 12), cv2.LINE_AA)

    def _draw_peripheral_glow(self, frame, threat_box, alert_res):
        """
        Subtle vertical edge glow when the threat is on the left or right
        third of the frame — no bounding box drawn over the scene, just a
        colored hint in the participant's peripheral vision.
        """
        level = alert_res.get("level", "SAFE")
        if level == "SAFE" or threat_box is None:
            return

        h, w = frame.shape[:2]
        tx1, _, tx2, _ = threat_box
        cx = (tx1 + tx2) / 2

        side = None
        if cx < w * 0.33:
            side = "left"
        elif cx > w * 0.67:
            side = "right"
        if side is None:
            return  # centered — the alert bar / audio handle this

        style = self.ALERT_STYLES.get(level, self.ALERT_STYLES["SAFE"])
        bg_hex = style["bg"]
        bgr_color = tuple(int(bg_hex.lstrip('#')[i:i+2], 16) for i in (4, 2, 0))

        strip_w = max(20, w // 30)
        alpha = 0.35 if level == "CRITICAL" else 0.22

        overlay = frame.copy()
        if side == "left":
            cv2.rectangle(overlay, (0, 0), (strip_w, h), bgr_color, -1)
        else:
            cv2.rectangle(overlay, (w - strip_w, 0), (w, h), bgr_color, -1)
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, dst=frame)

    def _crop_equirectangular_forward(self, frame, fov_deg=90):
        """
        Take a 360° equirectangular frame and crop out the forward-facing
        perspective view at the given horizontal field of view.

        For now this is a simple center crop — a full reprojection would
        require remapping every pixel through a pinhole camera model. The
        forward 90° of an equirectangular video is roughly the center 25%
        horizontally (90° / 360° = 0.25), centered on the front-facing pixel.
        """
        h, w = frame.shape[:2]
        crop_frac = fov_deg / 360.0
        crop_w = int(w * crop_frac)
        cx = w // 2
        x1 = max(0, cx - crop_w // 2)
        x2 = min(w, x1 + crop_w)
        # Keep a 16:9 vertical slice from the equator (middle of the frame)
        target_h = int(crop_w * 9 / 16)
        cy = h // 2
        y1 = max(0, cy - target_h // 2)
        y2 = min(h, y1 + target_h)
        return frame[y1:y2, x1:x2].copy()

    def _cv2_to_qpixmap(self, cv_img, w, h):
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h_img, w_img, ch = rgb_image.shape
        bytes_per_line = ch * w_img
        qimg = QImage(rgb_image.data, w_img, h_img, bytes_per_line, QImage.Format_RGB888)
        transform = Qt.FastTransformation if self.is_playing else Qt.SmoothTransformation
        return QPixmap.fromImage(qimg).scaled(w, h, Qt.KeepAspectRatio, transform)

    # ── Status UI with flash animation ───────────────────────────
    def _apply_status_style(self, level, min_depth, avg_depth):
        fps_val = (
            self.perf_monitor.fps_history[-1]
            if self.perf_monitor.fps_history else 0
        )
        # Hide the alert bar in conditions that don't use it (NO_ALERT, AR_HUD)
        if not self.condition_flags.alert_bar_visible:
            self.lbl_status_box.setText("—")
            self.lbl_status_box.setStyleSheet(
                f"background-color: {C_BORDER}; color: {C_TEXT_MUTED};"
                f" border-radius: 8px; border: none;"
            )
            self.lbl_status_metrics.setText(
                f"CONDITION: {self.condition.value.replace('_', ' ')}"
            )
            self._flash_timer.stop()
            self.lbl_current_fps.setText(f"{fps_val:.0f} FPS")
            return

        style = self.ALERT_STYLES.get(level, self.ALERT_STYLES["SAFE"])

        # Map level to display text
        level_text = {
            "SAFE": "SAFE",
            "CAUTION": "CAUTION",
            "WARNING": "WARNING",
            "CRITICAL": "CRITICAL  —  BRAKE NOW",
        }.get(level, "READY")

        self.lbl_status_box.setText(level_text)
        self._current_alert_bg = style["bg"]
        self._current_alert_text = style["text"]

        self.lbl_status_box.setStyleSheet(
            f"background-color: {style['bg']}; color: {style['text']};"
            f" border-radius: 8px; border: 2px solid {style['border']}40;"
        )

        # Start/stop flash for critical
        if level == "CRITICAL":
            if not self._flash_timer.isActive():
                self._flash_timer.start()
        else:
            self._flash_timer.stop()

        m_str = f"{min_depth:.2f}" if isinstance(min_depth, float) else str(min_depth)
        a_str = f"{avg_depth:.2f}" if isinstance(avg_depth, float) else str(avg_depth)
        self.lbl_status_metrics.setText(f"MIN DEPTH: {m_str}    AVG DEPTH: {a_str}")

        self.lbl_current_fps.setText(f"{fps_val:.0f} FPS")
        fps_color = C_ACCENT if fps_val >= self.target_fps else C_DANGER
        self.lbl_current_fps.setStyleSheet(
            f"color: {fps_color}; font-size: 12px; font-weight: 600;"
            f" background: transparent; border: none;"
        )

    def _toggle_flash(self):
        """Pulse the critical alert bar between two reds."""
        self._alert_flash_on = not self._alert_flash_on
        bg = "#FF4D6F" if self._alert_flash_on else C_DANGER
        self.lbl_status_box.setStyleSheet(
            f"background-color: {bg}; color: #FFFFFF;"
            f" border-radius: 8px; border: 2px solid {C_DANGER}80;"
        )

    def _update_time_label(self):
        curr_sec = int(self.current_frame / self.fps) if self.fps > 0 else 0
        tot_sec = int(self.total_frames / self.fps) if self.fps > 0 else 0
        self.lbl_time.setText(
            f"{curr_sec // 60:02d}:{curr_sec % 60:02d} / {tot_sec // 60:02d}:{tot_sec % 60:02d}"
        )

    # ── Interaction Logic ────────────────────────────────────────
    def record_reaction(self):
        # Allow brake during inter-trial blank too (we just ignore it gracefully)
        if not self.is_playing or self._between_trials:
            return

        remote = getattr(self, "_last_remote_brake", None)
        self.data_logger.log_reaction(
            self.current_frame,
            self.audio_system.current_level,
            trial=self.current_trial,
            trial_start_time=self.trial_start_time,
            condition=self.condition.value,
            response_source=remote.get("source", "desktop") if remote else "desktop",
            network_latency_ms=remote.get("latency_hint_ms", 0) if remote else 0,
        )
        self._last_remote_brake = None

        # Brief visual flash on brake button
        self.btn_brake.setStyleSheet(
            f"background-color: #FF4D6F; color: white; font-size: 18px;"
            f" font-weight: 800; letter-spacing: 1px; border-radius: 10px;"
            f" border: 2px solid #FF4D6F; padding: 14px 24px; min-height: 48px;"
        )
        QTimer.singleShot(200, lambda: self.btn_brake.setStyleSheet(""))

        self.update_analysis_tab()

    def update_monitor_tab(self):
        stats = self.perf_monitor.get_current_stats()
        fps_history, lat_history = self.perf_monitor.get_history()

        # Update metric card values
        fps_val = stats['fps']
        self.lbl_mon_fps.setText(f"{fps_val:.1f}")
        fps_color = C_ACCENT if fps_val >= self.target_fps else C_DANGER
        self.lbl_mon_fps.setStyleSheet(
            f"color: {fps_color}; font-size: 26px; font-weight: 700;"
            f" border: none; background: transparent;"
        )

        self.lbl_mon_latency.setText(f"{stats['latency_ms']:.1f} ms")
        self.lbl_mon_gpu.setText(f"{stats['gpu_memory_used']} / {stats['gpu_memory_total']} MB")
        self.lbl_mon_cpu.setText(f"{stats['cpu_percent']}%")

        # Compatibility badge
        mode = self.cb_mode.currentIndex()
        chk = stats['nano_compatible'] if mode == 1 else stats['xavier_compatible']
        plat_txt = "NANO" if mode == 1 else ("XAVIER" if mode == 2 else "SYSTEM")

        if chk:
            self.lbl_mon_badge.setText(f"  {plat_txt} COMPATIBLE")
            self.lbl_mon_badge.setStyleSheet(
                f"background-color: {C_BG_PANEL}; color: {C_SAFE};"
                f" border: 1px solid {C_SAFE}40; border-radius: 8px;"
                f" font-size: 12px; font-weight: 700; letter-spacing: 1.5px;"
            )
        else:
            self.lbl_mon_badge.setText(f"  {plat_txt} — NOT COMPATIBLE")
            self.lbl_mon_badge.setStyleSheet(
                f"background-color: {C_BG_PANEL}; color: {C_DANGER};"
                f" border: 1px solid {C_DANGER}40; border-radius: 8px;"
                f" font-size: 12px; font-weight: 700; letter-spacing: 1.5px;"
            )

        if fps_history:
            self.fps_curve.setData(fps_history)
        if lat_history:
            self.latency_curve.setData(lat_history)

    def update_analysis_tab(self):
        stats = self.data_logger.get_session_stats()
        self.lbl_stat_hits.setText(str(stats['hits']))
        self.lbl_stat_misses.setText(str(stats['misses']))
        self.lbl_stat_avg.setText(f"{stats['avg_time']} ms")
        self.lbl_stat_detection.setText(f"{stats['detection_rate']}%")
        self.lbl_stat_false.setText(f"{stats['false_alarms']} ({stats['false_alarm_rate']}%)")

        sus = stats["sus_score"]
        sus_text = f"{sus:.1f}" if sus is not None else "pending"
        trust = self.data_logger.participant_data.get("trust_score", "pending")
        self.lbl_questionnaire_status.setText(
            f"NASA-TLX: {stats['tlx_blocks']}/3 blocks  |  SUS: {sus_text}  |  Trust: {trust}"
        )

        self.table_logs.setRowCount(0)
        for row_data in self.data_logger.reaction_data:
            row = self.table_logs.rowCount()
            self.table_logs.insertRow(row)
            timestamp = row_data.get("timestamp", 0)
            ts = time.strftime("%H:%M:%S", time.localtime(timestamp)) if timestamp else ""
            outcome = row_data.get("outcome", "").upper()
            source = self._format_response_source(row_data.get("response_source", ""))
            values = [
                ts,
                source,
                row_data.get("condition", ""),
                str(row_data.get("trial_id", "")),
                row_data.get("event_type", ""),
                row_data.get("expected_level", ""),
                outcome,
                str(row_data.get("reaction_time_ms", "")),
                str(row_data.get("network_latency_ms", "")),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter)
                if col == 1 and value:
                    source_color = C_ACCENT if value != "DESKTOP" else C_TEXT
                    item.setForeground(QColor(source_color))
                elif col == 6:
                    outcome_colors = {
                        "HIT": C_SAFE,
                        "FALSE_ALARM": C_DANGER,
                        "OUT_OF_WINDOW": C_WARN,
                        "MISS": C_DANGER,
                        "DUPLICATE_PRESS": C_TEXT_DIM,
                        "CORRECT_REJECTION": C_SAFE,
                    }
                    item.setForeground(QColor(outcome_colors.get(outcome, C_TEXT)))
                self.table_logs.setItem(row, col, item)
        self.table_logs.scrollToBottom()

    @staticmethod
    def _format_response_source(source: str) -> str:
        if not source:
            return ""
        labels = {
            "desktop": "DESKTOP",
            "click": "WEB BUTTON",
            "keyboard": "KEYBOARD",
            "keyboard_back": "BACK KEY",
            "controller": "VR TRIGGER",
            "controller_panel": "VR PANEL",
            "controller_left_y": "VR Y",
            "controller_back_button": "VR BACK",
        }
        return labels.get(source, source.replace("_", " ").upper())

    def start_session(self):
        """Start a structured HCI session with Latin-square block ordering."""
        from src.core.session_planner import plan_session
        from src.core.experiment import display_name
        from src.core.playlist import PlaylistManager
        from src.ui.block_pause_dialog import BlockPauseDialog

        part_id = self.inp_participant.text().strip()
        if not part_id:
            QMessageBox.warning(
                self, "Participant ID Required",
                "Enter a participant ID (e.g. P01) before starting a session.\n\n"
                "For solo testing without a participant ID, use 'Load Playlist' instead."
            )
            return

        # Need scenarios to plan against — load them once
        try:
            scenarios_pm = PlaylistManager(
                "data/scenarios.csv", base_dir="data/scenarios", shuffle=False
            )
        except Exception as e:
            QMessageBox.critical(self, "Scenario Library Error", str(e))
            return

        plan = plan_session(part_id, scenarios_pm.scenarios)
        self.session_plan = plan
        self.session_block_index = 0  # which block in plan.blocks we're on next
        self.session_mode = True       # vs. solo playlist mode

        self.clear_session()
        self.data_logger.set_participant_id(part_id)
        self.data_logger.session_id = f"{part_id}_{time.strftime('%Y%m%d_%H%M%S')}"
        self.data_logger.log_file = os.path.join(
            self.data_logger.log_dir, f"session_{self.data_logger.session_id}.csv"
        )
        self.data_logger.reaction_file = os.path.join(
            self.data_logger.log_dir, f"reactions_{self.data_logger.session_id}.csv"
        )
        self.data_logger.questionnaire_file = os.path.join(
            self.data_logger.log_dir, f"questionnaires_{self.data_logger.session_id}.csv"
        )
        self.data_logger.participant_file = os.path.join(
            self.data_logger.log_dir, f"participant_{self.data_logger.session_id}.csv"
        )
        self.data_logger.report_file = os.path.join(
            self.data_logger.log_dir, f"report_{self.data_logger.session_id}.txt"
        )

        # Save the plan to disk so it can be audited later
        plan_path = os.path.join(
            self.data_logger.log_dir, f"plan_{self.data_logger.session_id}.txt"
        )
        from src.core.session_planner import plan_summary
        with open(plan_path, "w") as f:
            f.write(plan_summary(plan))

        # Pre-block dialog — confirms participant is ready, shows next condition
        first = plan.blocks[0]
        dlg = BlockPauseDialog(
            completed_block=0, completed_condition="",
            next_block=first.block_num, next_condition=display_name(first.condition),
            parent=self,
        )
        if dlg.exec_() != QDialog.Accepted:
            self.session_mode = False
            self.session_plan = None
            return

        self._start_block(0)
        self.tabs.setCurrentIndex(0)

    def _start_block(self, block_index: int):
        """Activate the condition for a block and queue its trials in the playlist."""
        from src.core.experiment import flags_for
        from src.core.playlist import PlaylistManager

        block = self.session_plan.blocks[block_index]

        # Apply the block's condition (also updates audio + UI gating)
        self.set_condition(block.condition)

        # Build a one-block playlist directly from the plan's trials (no shuffle —
        # the planner already randomized them per-participant)
        self.playlist = PlaylistManager.from_scenarios(
            block.trials, base_dir="data/scenarios"
        )
        self.playlist.shuffle = False
        self.session_block_index = block_index

        # Auto-load the first trial
        self._advance_to_next_trial()

    def save_session(self):
        """Save the session — let the user pick where (Desktop, Downloads, anywhere)."""
        part_id = self.inp_participant.text() or "UNKNOWN"
        self.data_logger.set_participant_id(part_id)

        # Default to the user's Desktop / Downloads, fall back to project logs/
        home = os.path.expanduser("~")
        default_dir = next(
            (d for d in [
                os.path.join(home, "Desktop"),
                os.path.join(home, "Downloads"),
                home,
            ] if os.path.isdir(d)),
            self.data_logger.log_dir,
        )
        suggested = os.path.join(default_dir, f"depthguard_{self.data_logger.session_id}")

        chosen = QFileDialog.getExistingDirectory(
            self, "Choose where to save the session", suggested,
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
        )
        if not chosen:
            return  # user cancelled

        # Create a subfolder named with the participant + session id
        out_dir = os.path.join(chosen, f"depthguard_{self.data_logger.session_id}")
        os.makedirs(out_dir, exist_ok=True)

        # Redirect the logger's output paths into that folder
        self.data_logger.log_dir = out_dir
        self.data_logger.log_file = os.path.join(out_dir, f"session_{self.data_logger.session_id}.csv")
        self.data_logger.reaction_file = os.path.join(out_dir, f"reactions_{self.data_logger.session_id}.csv")
        self.data_logger.questionnaire_file = os.path.join(out_dir, f"questionnaires_{self.data_logger.session_id}.csv")
        self.data_logger.participant_file = os.path.join(out_dir, f"participant_{self.data_logger.session_id}.csv")
        self.data_logger.report_file = os.path.join(out_dir, f"report_{self.data_logger.session_id}.txt")

        self.data_logger.save_session(part_id)

        QMessageBox.information(
            self, "Exported",
            f"Session saved to:\n\n{out_dir}\n\n"
            f"Files:\n"
            f"  • session_{self.data_logger.session_id}.csv (per-frame log)\n"
            f"  • reactions_{self.data_logger.session_id}.csv (trial outcomes)\n"
            f"  • questionnaires_{self.data_logger.session_id}.csv (NASA-TLX per condition)\n"
            f"  • participant_{self.data_logger.session_id}.csv (SUS + demographics)\n"
            f"  • report_{self.data_logger.session_id}.txt (summary)"
        )
        self.update_analysis_tab()

    def clear_session(self):
        self.data_logger = DataLogger()
        self.table_logs.setRowCount(0)
        self.update_analysis_tab()

    def closeEvent(self, event):
        self._closing = True
        self._flash_timer.stop()
        self._tunnel_probe_timer.stop()
        if self.webxr_server is not None:
            try:
                self.webxr_server.stop()
            except Exception:
                pass
        if self._tunnel_process is not None and self._tunnel_process.state() != QProcess.NotRunning:
            self._tunnel_process.terminate()
            if not self._tunnel_process.waitForFinished(750):
                self._tunnel_process.kill()
                self._tunnel_process.waitForFinished(250)
        self.audio_system.cleanup()
        event.accept()

    # ── WebXR companion ──────────────────────────────────────────
    def _start_webxr_stack(self):
        """Bring up the local WebXR server first, then expose it through ngrok."""
        self._start_webxr_server(show_dialog=False)
        self._start_tunnel_if_needed()

    def _start_tunnel_if_needed(self):
        """Start the static ngrok tunnel unless an existing process already serves WebXR."""
        existing_url = self._find_running_tunnel()
        if self._wrong_tunnel_upstream:
            self._show_tunnel_status(
                "TUNNEL USES LOCALHOST - stop old ngrok and restart the app"
            )
            return
        if existing_url:
            self._tunnel_public_url = existing_url
            status = "WEBXR READY" if self.webxr_server is not None and self.webxr_server.is_running() else "TUNNEL ONLINE"
            self._show_tunnel_status(status, existing_url)
            return

        script_path = Path(__file__).resolve().parent.parent.parent / "scripts" / "start_tunnel.sh"
        if not script_path.exists():
            self._show_tunnel_status("TUNNEL SCRIPT NOT FOUND")
            return

        self._tunnel_process = QProcess(self)
        self._tunnel_process.setWorkingDirectory(str(script_path.parent.parent))
        self._tunnel_process.setProcessChannelMode(QProcess.MergedChannels)
        self._tunnel_process.readyReadStandardOutput.connect(self._drain_tunnel_output)
        self._tunnel_process.errorOccurred.connect(self._on_tunnel_error)
        self._tunnel_process.finished.connect(self._on_tunnel_finished)
        self._show_tunnel_status("TUNNEL STARTING...")
        self._tunnel_process.start(str(script_path), [])
        self._tunnel_probe_attempts = 0
        self._tunnel_probe_timer.start()

    def _find_running_tunnel(self):
        """Return an ngrok public URL already forwarding to the WebXR endpoint."""
        self._wrong_tunnel_upstream = None
        try:
            with urlopen(NGROK_API_URL, timeout=0.25) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception:
            return None

        for tunnel in payload.get("tunnels", []):
            public_url = str(tunnel.get("public_url", ""))
            config = tunnel.get("config") or {}
            addr = str(config.get("addr", ""))
            if "localhost:8765" in addr:
                self._wrong_tunnel_upstream = addr
                continue
            if WEBXR_PUBLIC_URL.rstrip("/") in public_url and "127.0.0.1:8765" in addr:
                return public_url.rstrip("/") + "/"
            if "127.0.0.1:8765" in addr and public_url.startswith("https://"):
                return public_url.rstrip("/") + "/"
        return None

    def _probe_tunnel_status(self):
        """Wait for a just-started ngrok child to publish the WebXR URL."""
        public_url = self._find_running_tunnel()
        if public_url:
            self._tunnel_public_url = public_url
            self._tunnel_probe_timer.stop()
            status = "WEBXR READY" if self.webxr_server is not None and self.webxr_server.is_running() else "TUNNEL ONLINE"
            self._show_tunnel_status(status, public_url)
            return

        self._tunnel_probe_attempts += 1
        if self._tunnel_probe_attempts >= 20:
            self._tunnel_probe_timer.stop()
            self._show_tunnel_status("TUNNEL NOT READY - check ngrok authentication")

    def _on_tunnel_error(self, _error):
        if not getattr(self, "_closing", False):
            self._tunnel_probe_timer.stop()
            self._show_tunnel_status("TUNNEL FAILED - run scripts/start_tunnel.sh manually")

    def _drain_tunnel_output(self):
        """Discard ngrok terminal UI output so a long app session stays bounded."""
        if self._tunnel_process is not None:
            self._tunnel_process.readAllStandardOutput()

    def _on_tunnel_finished(self, _exit_code, _exit_status):
        if not getattr(self, "_closing", False) and not self._tunnel_public_url:
            self._tunnel_probe_timer.stop()
            self._show_tunnel_status("TUNNEL STOPPED - check ngrok configuration")

    def _show_tunnel_status(self, status, public_url=None):
        if public_url:
            self.lbl_webxr_url.setText(
                f"{status}: <a href='{public_url}' style='color:{C_ACCENT}; "
                f"text-decoration:underline;'>{public_url}</a>"
            )
            self.lbl_webxr_url.setToolTip("Open the public WebXR URL")
        else:
            self.lbl_webxr_url.setText(status)
            self.lbl_webxr_url.setToolTip("")
        self.lbl_webxr_url.show()

    def _start_webxr_server(self, show_dialog=True):
        """Start the local WebXR HTTP/WebSocket server."""
        if self.webxr_server is not None and self.webxr_server.is_running():
            return True

        try:
            from src.network.webxr_server import WebXRServer
        except ImportError:
            self.btn_webxr.setChecked(False)
            if show_dialog:
                QMessageBox.critical(
                    self, "WebXR - Missing Dependencies",
                    "The WebXR server needs aiohttp + websockets.\n\n"
                    "Install with:\n  pip install aiohttp websockets"
                )
            else:
                self._show_tunnel_status("WEBXR NOT STARTED - missing aiohttp/websockets")
            return False

        self.webxr_server = WebXRServer(
            on_brake=self._handle_remote_brake,
            on_control=self._handle_remote_control,
        )
        try:
            self.webxr_server.start()
        except Exception as e:
            self.btn_webxr.setChecked(False)
            self.webxr_server = None
            if show_dialog:
                QMessageBox.critical(self, "WebXR - Server Error", str(e))
            else:
                self._show_tunnel_status(f"WEBXR NOT STARTED - {e}")
            return False

        local_url = self.webxr_server.public_url_hint()
        url = self._tunnel_public_url or local_url
        port = self.webxr_server.port
        self.btn_webxr.setChecked(True)
        self.btn_webxr.setText("  📡  WebXR: ON")
        self._show_tunnel_status("WEBXR READY", url)

        if show_dialog:
            import webbrowser
            msg = QMessageBox(self)
            msg.setWindowTitle("WebXR Server Started")
            msg.setIcon(QMessageBox.Information)
            msg.setTextFormat(Qt.RichText)
            msg.setTextInteractionFlags(Qt.TextBrowserInteraction)
            msg.setText(
                f"<b>WebXR companion is live.</b><br><br>"
                f"Open on the headset's browser:<br>"
                f"<a href='{url}' style='color:#00E5A0; font-weight:700;'>{url}</a><br><br>"
                f"Local fallback URL: <code>{local_url}</code><br>"
                f"Port: <code>{port}</code><br><br>"
                f"<i>The link will stay visible next to the WebXR button so you can reopen it any time.</i>"
            )
            btn_open = msg.addButton("  Open in Browser  ", QMessageBox.ActionRole)
            msg.addButton("Close", QMessageBox.RejectRole)
            msg.setDefaultButton(btn_open)
            msg.exec_()
            if msg.clickedButton() is btn_open:
                webbrowser.open(url)

        return True

    def toggle_webxr_server(self):
        """Start or stop the WebXR companion server."""
        if self.webxr_server is None or not self.webxr_server.is_running():
            self._start_webxr_server(show_dialog=True)
        else:
            try:
                self.webxr_server.stop()
            except Exception:
                pass
            self.btn_webxr.setText("  📡  WebXR: OFF")
            self.btn_webxr.setChecked(False)
            if self._tunnel_public_url:
                self._show_tunnel_status("TUNNEL ONLINE - WEBXR OFF", self._tunnel_public_url)
            else:
                self.lbl_webxr_url.hide()
                self.lbl_webxr_url.setText("")

    def _handle_remote_brake(self, msg: dict):
        """Marshal a WebXR brake event onto the Qt main thread."""
        self.remote_brake_received.emit(msg)

    @pyqtSlot(dict)
    def _apply_remote_brake(self, msg: dict):
        """Treat a WebXR brake press identically to a local SPACE press."""
        # Stash source + network-latency hint for the next CSV row to pick up
        self._last_remote_brake = {
            "source": msg.get("source", "remote"),
            "latency_hint_ms": msg.get("latency_hint_ms", 0),
        }
        # Reuse the existing brake logic — it handles trial scoring + logging
        self.record_reaction()

    def _handle_remote_control(self, msg: dict):
        """Marshal a WebXR transport command onto the Qt main thread."""
        self.remote_control_received.emit(msg)

    @pyqtSlot(dict)
    def _apply_remote_control(self, msg: dict):
        """Mirror desktop playback and seeking controls for the VR client."""
        action = msg.get("action")
        if action == "toggle_play":
            self.toggle_play()
        elif action == "stop":
            self.stop_video()
        elif action in ("seek_back", "seek_forward"):
            try:
                seconds = float(msg.get("seconds", 5))
            except (TypeError, ValueError):
                seconds = 5.0
            seconds = min(max(seconds, 1.0), 30.0)
            self._seek_relative_seconds(-seconds if action == "seek_back" else seconds)

    def _seek_relative_seconds(self, seconds: float):
        """Seek from WebXR with the same video-position behavior as the desktop slider."""
        if not self.cap or not self.cap.isOpened() or self._between_trials:
            return
        offset = int(round(seconds * self.fps))
        target = max(0, min(max(0, self.total_frames - 1), self.current_frame + offset))
        self.set_frame_position(target)
        self.slider_progress.setValue(target)
        self._render_seek_preview(mirror_to_webxr=True)
