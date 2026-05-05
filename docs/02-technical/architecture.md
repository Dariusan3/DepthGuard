# System Architecture

## High-level

```
┌─────────────────────────────────────────────────────────────────┐
│                     DepthGuard PyQt5 App                        │
│                                                                 │
│  ┌──────────────┐   ┌─────────────┐   ┌────────────────────┐   │
│  │ Video loader │──▶│ Per-frame   │──▶│ UI: dual viewports │   │
│  │ (cv2)        │   │ pipeline    │   │ + alert bar        │   │
│  └──────────────┘   └─────┬───────┘   └────────────────────┘   │
│                           │                                     │
│                           ▼                                     │
│        ┌──────────────────────────────────────┐                 │
│        │ 1. Depth model.inference(frame)      │                 │
│        │ 2. SafetyAlertSystem.process_depth() │                 │
│        │ 3. PerformanceMonitor.record()       │                 │
│        │ 4. DataLogger.log_frame()            │                 │
│        │ 5. AudioAlertSystem.set_level()      │                 │
│        │ 6. Update UI (driver + depth panels) │                 │
│        └──────────────────────────────────────┘                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
                ┌──────────────────────┐
                │  logs/ — CSV + TXT   │
                │  reports per session │
                └──────────────────────┘
```

## Key files

| File | Role |
|---|---|
| `main.py` | Entry point — login dialog → main window loop |
| `src/auth/login_dialog.py` | Sign-in screen shown before the main window |
| `src/auth/users.py` | Mock user store + `authenticate()` (driver / admin roles) — see [auth-and-roles.md](auth-and-roles.md) |
| `src/ui/main_window.py` | Three-tab main window (Simulation / Performance / Analysis); driver role hides researcher-only widgets |
| `src/models/mock_model.py` | Synthetic depth (fallback for UI testing) |
| `src/models/midas_model.py` | MiDaS via torch.hub (fallback for Jetson) |
| `src/models/depth_pro_model.py` | DepthPro via local fork (primary thesis model) |
| `src/core/alert_system.py` | ROI-based alert classification (4 levels) |
| `src/core/performance_monitor.py` | FPS, latency, GPU/CPU tracking |
| `src/core/data_logger.py` | Frame logs + reaction logs + report generation |
| `src/core/audio_alerts.py` | pygame-driven beep loop |

## Model interface contract

Any model class must implement:

```python
def inference(self, frame: np.ndarray) -> np.ndarray:
    """
    frame: BGR uint8 (H, W, 3) — straight from cv2.VideoCapture
    returns: float32 (H, W) in [0.0, 1.0] where 0=close, 1=far
    """
```

This is the contract that lets us swap MockModel ↔ MiDaS ↔ DepthPro ↔ user's trained model without touching the rest of the pipeline.

## Alert thresholds

Defined in `src/core/alert_system.py`:

| Level | Min depth in ROI | Color |
|---|---|---|
| SAFE | ≥ 0.50 | green |
| CAUTION | 0.30 – 0.50 | yellow |
| WARNING | 0.15 – 0.30 | amber |
| CRITICAL | < 0.15 | red (pulsing) |

ROI = central rectangle (40–80% height, 30–70% width) — approximates the road ahead.

## Data captured per session

`logs/session_<id>.csv` — per-frame log (every 10th frame): timestamp, frame, alert level, min depth.
`logs/reactions_<id>.csv` — per-brake-press: timestamp, frame, alert level at press, reaction time (ms), is_correct.
`logs/report_<id>.txt` — human-readable session summary.
