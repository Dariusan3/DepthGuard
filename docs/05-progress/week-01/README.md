# Week 1 — Apr 27 to May 3, 2026

**Theme:** Real videos + participant-ready UI.

---

## Shipped

### Real video pipeline (replacing the placeholder mock video)

Acquired 16 dashcam scenarios from public YouTube compilations:
- 7 critical events (pedestrian crossings, sudden brake-light situations)
- 6 warning-level events
- 3 truly safe baseline clips (control trials for false-alarm rate)

All clips are 5–10 s, with the critical-event timestamp noted in `data/scenarios.csv`.

**Source videos** (in `data/raw_downloads/`, gitignored):
- `MKPkT2TuZhs` — 20 min compilation
- `EqiHzik7-fY` — 10 min compilation
- `dR2h8xD6dPI` — 10 min compilation
- `Q84JXbuD3Is` — 15 min for safe-driving stretches

Decision: KITTI for training the depth model later, BDD100K/YouTube for HCI stimuli (separation rationale documented in [02-technical/real-video-pipeline.md](../../02-technical/real-video-pipeline.md)).

### UI redesign (HUD/cockpit theme)

- Deep blue-black background (`#06080F`) with electric mint accent (`#00E5A0`)
- Branded header bar with glowing logo + live FPS
- Three-tab structure: Simulation / Performance / Analysis
- Pulsing status bar on CRITICAL alerts
- BRAKE button with red glow + flash feedback on press

### Scenario loader (Playlist mode)

Replaced the single-video `Load Video` button with `Load Playlist` that walks through all 16 trials with a 2-second blank between them. Trial counter visible during playback.

### Threat-tracking bounding box

Box that follows the closest object using percentile-based depth thresholding, aspect-ratio + size filters, center bias, plus temporal stability gate (3-frame minimum) and IoU-based snap detection. Hold-for-grace-frames when the threat momentarily disappears.

### Slider scrubbing

Press → pauses playback. Drag → seeks live with debounced (80 ms) frame render to keep the UI responsive even with MiDaS. Release → resumes if was playing.

### Loading dialog + QThread

Modal dialog with animated dots when switching depth models. Loading happens on a `QThread` so the UI stays responsive even when MiDaS or DepthPro is downloading weights.

### Three depth backends wired in

| Backend | File | Status |
|---|---|---|
| MockModel | `src/models/mock_model.py` | working |
| MiDaS Small / Hybrid / Large | `src/models/midas_model.py` | working |
| DepthPro pretrained | `src/models/depth_pro_model.py` | working (1.8 GB weights downloaded + symlinked) |

### Headless smoke test

`scripts/smoke_test.py` walks all 16 scenarios with the alert system + data logger and verifies CSV/report output. Passes cleanly.

### Documentation buildout

Built `docs/` folder with:
- 01-planning: thesis-requirements, roadmap, weekly-milestones, risk-log, supervisor-updates
- 02-technical: architecture, real-video-pipeline, ui-redesign, ar-extension (plan), jetson-optimization (plan)
- 03-research: study-protocol, data-analysis-plan, participant-materials (consent, briefing, questionnaires)
- 04-deliverables: checklist, thesis-outline

---

## Files added / changed

```
docs/                           # entire folder created
data/scenarios/                 # 16 trimmed mp4 clips
data/scenarios.csv              # trial metadata
data/scenario_picks.txt         # working notes — timestamps for trim_scenario.sh
scripts/smoke_test.py
scripts/trim_scenario.sh
src/ui/main_window.py           # major rewrite — HUD theme + playlist mode + threat box
src/ui/loading_dialog.py        # new
src/core/playlist.py            # new
src/core/data_logger.py         # added per-trial scoring (hit / miss / false_alarm / out_of_window)
src/models/midas_model.py       # new
src/models/depth_pro_model.py   # new
.gitignore                      # new
checkpoints/depth_pro.pt        # symlink to ../../ml-depth-pro/checkpoints/depth_pro.pt
```

---

## Supervisor email

Sent Friday May 1. See [supervisor-updates.md](../../01-planning/supervisor-updates.md) for the text.

### Supervisor's reply

Decisions received the same day:
1. **No formal ethics approval needed** at UPM for academic studies — informed consent is sufficient.
2. **No Jetson available** through the lab — simulate the constraints on desktop.

Both saved as project-memory and propagated through the docs (risk-log R3 marked Resolved, study-protocol notes ethics confirmation, jetson-optimization rewritten around simulate-on-desktop).

---

## Outcomes

- 16 real scenarios curated and ready for the HCI study
- App runs end-to-end on real footage (verified via smoke test)
- All major risks from R1–R8 either mitigated or resolved
- Foundation in place for week 2's AR work + multi-participant flow

---

## What's left for week 2

- Build AR HUD overlay (3rd experimental condition)
- Performance profiler — capture real numbers
- (Pulled forward in practice: condition selector + session planner + multi-participant flow)
