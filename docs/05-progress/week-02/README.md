# Week 2 — May 4 to May 10, 2026

**Theme:** AR overlay + experimental conditions + multi-participant flow.

Most of weeks 4–5 prep was pulled forward this week so that recruitment and analysis can start on schedule.

---

## Shipped

### AR HUD overlay (3rd experimental condition)

[`src/ui/ar_overlay.py`](../../../src/ui/ar_overlay.py) — composites:
- Translucent fill on the closest threat object (color-coded by severity)
- HUD-style corner brackets
- Subtle vignette + scan-line texture (always on in AR mode)
- Bottom-edge red BRAKE strip on CRITICAL alerts

The standard alert bar is hidden in this condition — the AR overlay is the only visual cue.

### Three experimental conditions

[`src/core/experiment.py`](../../../src/core/experiment.py) — `ExperimentCondition` enum (`NO_ALERT`, `STANDARD`, `AR_HUD`) and `flags_for(condition)` returning four pipeline flags:

| Condition | Audio | Alert bar | Threat box | AR overlay |
|---|---|---|---|---|
| NO_ALERT | off | hidden | hidden | off |
| STANDARD | on | full color | shown | off |
| AR_HUD | on | hidden | hidden | active |

### 3-way condition selector in UI

Replaced the AR ON/OFF toggle with a segmented control in the controls bar:

```
[ NO ALERT | STANDARD | AR HUD ]
```

Switching is instant — re-renders the current frame so the change is visible even when paused.

### Pipeline gating

`update_video_panels`, `_apply_status_style`, and the audio call site all honor the condition flags. The depth panel always shows the threat (researcher reference); only the participant-facing driver view is gated.

### SessionPlanner with Latin square

[`src/core/session_planner.py`](../../../src/core/session_planner.py):
- 6-row Latin square cycles per participant (P01 → row 1, P07 → row 1 again, etc.)
- 3 blocks of 5 trials each
- Block composition: 2 critical + 2 warning + 1 safe (when scenario counts allow)
- Per-participant trial randomization seeded by SHA-256 of the participant ID (reproducible)

Verified for P01, P02, P05, P10 — all produce valid 15-trial plans with conditions counterbalanced.

### Between-block pause dialog

[`src/ui/block_pause_dialog.py`](../../../src/ui/block_pause_dialog.py):
- Pre-session: confirms participant readiness, shows first condition
- Between blocks: prompts researcher to administer NASA-TLX, shows next condition
- End-of-session: prompts for SUS + demographics

Dialogs are modal + frameless with the project palette.

### Two run modes (shared logging)

| Mode | Trigger | Use case |
|---|---|---|
| **Solo** | `Load Playlist` button | Self-testing, demos. All 16 trials in current condition. |
| **Multi-participant** | `Start Session` button (requires participant ID) | Real HCI sessions. Latin-square ordering, between-block dialogs. |

Data structure is identical across both — analysis pipeline doesn't care.

### Data logger updates

`reactions_*.csv` now includes a `condition` column on every row (hit, miss, false_alarm, out_of_window). Plan also written to `logs/plan_<participant>_<datetime>.txt` for audit.

### Performance profiler scaffold

[`scripts/profile_performance.py`](../../../scripts/profile_performance.py) — runs each model for N seconds on a clip and produces:
- `results/perf/per_frame_<model>.csv` — frame-by-frame metrics
- `results/perf/summary.csv` — mean FPS, p5 FPS, p95 latency, peak memory, ≥15 FPS / ≤4 GB pass-fail

Periodic progress prints every 3 s so the user knows it's alive.

### Mock baseline captured

| Model | Frames | Mean FPS | p5 FPS | Latency (ms) | Peak mem (MB) | ≥15 FPS | ≤4 GB |
|---|---|---|---|---|---|---|---|
| MockModel | 234 | 64.3 | 63.1 | 14.4 | 350 | ✓ | ✓ |

This is the **non-model overhead** of the pipeline — video decode + alert system + logger costs ~16 ms per frame. Whatever real models add on top is purely their inference cost.

### Documentation updates

| File | Change |
|---|---|
| `docs/02-technical/jetson-optimization.md` | Rewritten around supervisor's "simulate, don't borrow" decision; baseline tables pre-built |
| `docs/02-technical/ar-extension.md` | Plan → implementation spec |
| `docs/03-research/study-protocol.md` | New "Implementation status" section mapping protocol to code |
| `docs/01-planning/risk-log.md` | R3 (no Jetson) Resolved; R2 (recruitment) escalated to High/High |
| `docs/01-planning/weekly-milestones.md` | Week 2 checked off + "Pulled forward from later weeks" section |

---

## Files added / changed

```
src/core/experiment.py          # new — condition enum + flag dataclass
src/core/session_planner.py     # new — Latin square + balanced trial selection
src/ui/ar_overlay.py            # new — AR HUD compositor
src/ui/block_pause_dialog.py    # new — between-block modal
src/ui/main_window.py           # condition selector, set_condition, _start_block,
                                #   _handle_block_end, _show_session_complete_screen,
                                #   gating in update_video_panels + _apply_status_style
src/core/playlist.py            # added from_scenarios() classmethod
src/core/data_logger.py         # added condition= parameter to log_reaction + log_miss
scripts/profile_performance.py  # new — FPS / latency / memory profiler
results/perf/per_frame_mock.csv # mock baseline data
results/perf/summary.csv        # baseline summary
```

---

## Supervisor email

Drafted in [supervisor-updates.md](../../01-planning/supervisor-updates.md). Mentions AR overlay, condition selector, Latin-square planner, mock baseline, and asks for help with student recruitment.

Per supervisor's prior decisions (saved as memory), no further questions about ethics approval or Jetson availability.

---

## Outcomes

- AR HUD condition built and integrated as a real research instrument (not just a wow-factor demo)
- Multi-participant infrastructure in place — ready when recruitment lands
- Solo-test mode covers the worst-case "I can only test myself" scenario without rework
- Mock pipeline baseline establishes the overhead floor (~16 ms/frame on MacBook Air)

---

## Open / pending

- **MiDaS Small profiler row** — script ready, needs to run on the user's machine
- **DepthPro profiler row** — too heavy for live inference on MacBook Air; possibly skip and document
- **Recruitment** — top open risk (R2). Supervisor recruitment ask in this week's email.

---

## Risks updated

| Risk | Before | After |
|---|---|---|
| R2 — Recruitment | Medium / High | **High / High — top priority** |
| R3 — No Jetson | Open | **Resolved — simulate on desktop** |
| R9 — Threat box jitter | Open | Improved (stability gate, grace frames, IoU snap) |
