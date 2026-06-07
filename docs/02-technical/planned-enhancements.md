# Planned Enhancements

Backlog of features discussed but deferred to keep the working pipeline stable.
Each item lists scope, value to the thesis, and rough effort.

---

## 360-degree dataset support

**Status: partial — desktop crop shipped, full VR sphere deferred.**

**Shipped (see [360-scenarios.md](360-scenarios.md))**
- `scenarios.csv`: optional `projection` column (`flat` | `equirectangular`); legacy CSVs default to `flat`
- Loader detects projection per clip
- Per-frame pipeline crops the forward 90° FOV from equirectangular frames before the depth model runs

**Still deferred**
- Full pinhole reprojection (current crop is a flat center slice — fine for forward driving)
- WebXR sphere rendering — show the equirectangular frame on a `SphereGeometry` BackSide around the user in VR
- HCI study protocol section explaining 360° as an additional independent variable

**Decision.** Half the value (the dataset infrastructure) is shipped. The other half (VR immersive 360°) is gated on actually having 360° dashcam clips to use — defer until at least one is acquired and tested with the new crop.

---

## Per-condition audio palette

**Status: shipped.**

- `audio_alerts.py` now exposes a `set_condition(condition_name)` API + per-condition sound palettes
- STANDARD condition uses classic harsh dashboard-style beeps (1000 Hz modulated for CRITICAL, 800 Hz pure tone for WARNING)
- AR_HUD condition uses softer two-tone pitch-sweep chirps (more like a phone notification)
- `MainWindow.set_condition` now calls `audio_system.set_condition(condition.value)` so the palette tracks the experiment

**Still deferred: per-event-type tones (pedestrian vs vehicle).** Not on the critical path. Would only add ~1 layer of differentiation that's unlikely to surface in a small-N study.

---

## Spatial / stereo audio for VR

**Scope.** Currently alerts play through laptop speakers in mono. In VR, route them through the Quest's audio with positional 3D — beep comes from the direction of the threat.

**What needs to change**
- WebXR client uses Web Audio API + `PannerNode` to spatially position the alert
- Server sends threat position with each alert (already available in `threat_box`)

**Value.** Genuinely VR-specific feature — makes the AR HUD condition feel more 3D. Visible win for the thesis figure of "what the user sees vs hears".

**Effort.** 1 day.

**Decision.** Worth doing if WebXR/Quest is going to be a real research thread, not just demo.

---

## Better danger evaluation (multi-ROI + time-to-collision)

**Scope.** Replace the single central-ROI min-depth heuristic with a richer signal:
- 3 sub-ROIs (left / center / right) — alert separately
- Track depth across frames → estimate time-to-collision (TTC) for the closest object
- Use TTC + position to set alert level

**What needs to change**
- `alert_system.py`: from single-shot to stateful, accumulates per-frame history
- New module `tracker.py` to identify object continuity across frames
- Alert thresholds become TTC-based (seconds) instead of depth-based (normalized)

**Value.** Big improvement in "alert quality" — fewer false positives on slow-moving distant objects, more responsive on rapidly-approaching close ones. Thesis can claim a real research contribution beyond "use existing model".

**Effort.** 2–3 days (the right way).

**Decision.** Worth considering for the model evaluation section. Could be a thesis discussion point.

---

## Already shipped (for reference)

These were in the original wishlist and are now in production:

- ✅ Hide bounding box on the participant's driver view (STANDARD condition; researcher still sees it on depth panel)
- ✅ Lateral peripheral edge-glow indicators when threat is on left/right side of frame
- ✅ Minimum-size filter on threats (don't alert on super-far objects)
- ✅ Enhanced reaction logs: `response_source` (keyboard / controller / click), `min_depth_at_press`, `threat_box_at_press`, `threat_position` columns in `reactions_*.csv`
- ✅ Dashboard-style warning icon for STANDARD condition (bottom-center, pulses on CRITICAL)
- ✅ Per-condition audio palette: harsh beep (STANDARD) vs softer chirp (AR_HUD)
- ✅ 360° scenario infrastructure (forward-FOV crop in the pipeline; full VR sphere deferred)
