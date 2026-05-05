# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DepthGuard is a PyQt5 desktop application for driver safety research. It plays back driving videos, runs depth estimation inference on each frame, determines proximity-based alert levels, and records participant brake reactions for analysis. This is a university thesis project (licenta).

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

There are no tests, linting, or build steps configured.

## Architecture

**Entry point:** `main.py` creates a QApplication with Fusion style, shows a `LoginDialog` (`src/auth/login_dialog.py`), and on success launches `MainWindow(user=...)`. The user's role (driver / admin) controls which widgets are visible — see `docs/02-technical/auth-and-roles.md`.

**Core simulation pipeline** (runs per-frame in `MainWindow.process_next_frame`):
1. **Model inference** (`src/models/mock_model.py`) — `MockModel.inference(frame)` returns a 0.0–1.0 depth map. Currently synthetic (gradient + simulated vehicle blob). The UI has model selector dropdowns for MiDaS and custom models but only MockModel is implemented.
2. **Alert classification** (`src/core/alert_system.py`) — `SafetyAlertSystem.process_depth(depth_map)` analyzes a central ROI (40-80% height, 30-70% width) and classifies into SAFE/CAUTION/WARNING/CRITICAL based on min depth thresholds (0.50/0.30/0.15).
3. **Performance tracking** (`src/core/performance_monitor.py`) — records FPS and latency history, checks Jetson Nano/Xavier compatibility thresholds.
4. **Data logging** (`src/core/data_logger.py`) — logs frames every 10th frame, records brake reactions with reaction time calculation, exports CSV + text reports to `logs/`.
5. **Audio alerts** (`src/core/audio_alerts.py`) — generates beep sounds via pygame, plays them on a background thread based on alert level.

**UI** (`src/ui/main_window.py`) — single `MainWindow` class with three tabs:
- **Driving Simulation**: side-by-side driver view + JET-colorized depth map, alert status bar, video controls, BRAKE button, session management
- **Performance Monitor**: live FPS/latency charts (pyqtgraph), system metrics, Jetson compatibility badge
- **Session Analysis**: reaction statistics, log table, CSV export

**Role-based UI:** `MainWindow.__init__(user=...)` accepts the authenticated user. After all widgets are built, `_apply_role_visibility()` hides researcher-only controls (model/mode/condition selectors, session row, Performance + Analysis tabs) when the user is a driver. To hide a new admin-only widget: store it as `self.<name>` (not a local var) and add it to the tuple in `_apply_role_visibility`. Mock users live in `src/auth/users.py` (`_USERS` dict).

## Key Design Details

- Video playback is driven by `QTimer` at `target_fps` interval, not real-time video clock
- Depth maps are float32 arrays [0.0=close, 1.0=far], colorized with OpenCV JET colormap for display
- The model selector (`cb_model`) has three options but only index 0 (MockModel) works — adding real models requires implementing the same `inference(frame) -> depth_map` interface
- Simulation modes adjust `target_fps` and `model.latency` to simulate Jetson hardware constraints
- Session data is per-instance; `clear_session` creates a fresh `DataLogger`
- Audio runs on a daemon thread and must be cleaned up via `closeEvent`
