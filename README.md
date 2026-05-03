# DepthGuard

Driver safety alert system for HCI research — desktop simulator that plays dashcam footage, runs monocular depth estimation per frame, classifies proximity into alert levels, and records driver brake reactions.

University thesis project (UPM). Self-supervised monocular depth estimation for driver safety applications.

## Features

- **Three depth-estimation backends:** Mock (testing), MiDaS Small (lightweight, real-time), DepthPro (research backbone via [forked Apple repo](https://github.com/Dariusan3/ml-depth-pro))
- **HUD-style alert UI:** color-coded status, threat-tracking bounding box, audio beeps
- **AR HUD overlay condition:** translucent threat highlight + on-screen BRAKE strip
- **Three experimental conditions** for HCI study: NO_ALERT / STANDARD / AR_HUD
- **Latin-square multi-participant flow** with between-block pause dialogs
- **Solo-test mode** for self-evaluation and quick demos
- **Full session logging:** CSV export of frame-level alerts + reaction events

## Install

```bash
pip install -r requirements.txt

# Optional — for real depth estimation:
git clone https://github.com/Dariusan3/ml-depth-pro.git ../ml-depth-pro
cd ../ml-depth-pro && pip install -e . && source get_pretrained_models.sh
```

## Run

```bash
python main.py
```

Default path:
1. Pick **MiDaS Small** in the MODEL dropdown (first load downloads weights via torch.hub)
2. Pick a CONDITION: **NO ALERT** / **STANDARD** / **AR HUD**
3. Click **Load Playlist** (solo mode) or enter a participant ID and click **Start Session** (multi-participant Latin-square mode)
4. Press **SPACE** when you see a hazard

## Architecture

| Module | Role |
|---|---|
| `src/ui/main_window.py` | PyQt5 main window: video panels, controls, three tabs |
| `src/models/` | `mock_model.py`, `midas_model.py`, `depth_pro_model.py` — share `inference(frame) → depth` interface |
| `src/core/alert_system.py` | ROI-based depth → alert level (SAFE/CAUTION/WARNING/CRITICAL) |
| `src/core/experiment.py` | Three HCI conditions + flag-based pipeline gating |
| `src/core/session_planner.py` | Latin-square block ordering, balanced trial selection |
| `src/core/playlist.py` | Per-trial playback manager |
| `src/core/data_logger.py` | Frame logs + reaction logs + report generation |
| `src/ui/ar_overlay.py` | AR HUD compositing |

## Data layout

```
data/
├── scenarios/          # 16 trimmed dashcam clips for the HCI trials
├── scenarios.csv       # Trial metadata (event timestamps, expected alerts)
├── raw_downloads/      # Source YouTube downloads (gitignored — too large)
└── training/           # KITTI raw sequences for self-supervised training (later)
```

## Tooling scripts

| Script | Purpose |
|---|---|
| `scripts/profile_performance.py` | Benchmark FPS / latency / memory across models |
| `scripts/smoke_test.py` | Headless integration test of the playlist + logger |
| `scripts/trim_scenario.sh` | ffmpeg helper to trim a clip from a raw download |

## Documentation

Full thesis-level documentation in [docs/](docs/) — roadmap, weekly milestones, technical specs, HCI study protocol, participant materials, deliverables checklist.

## License

Thesis research code. Source video clips are derived from public YouTube dashcam compilations under fair-use academic terms.
