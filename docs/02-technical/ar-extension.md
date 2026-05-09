# AR Extension — Implementation

Implements the third experimental condition for the HCI study.
Status: **shipped (week 2)**.

---

## What it does

Renders alert visuals as if projected on the windshield:
- Translucent fill on the closest threat object (color-coded by severity)
- HUD-style corner brackets framing the threat
- Bottom-edge red "BRAKE" strip on CRITICAL alerts
- Subtle vignette + scan-line texture for the AR aesthetic (always on in AR mode)

The AR view replaces the standalone alert bar — the AR overlay is the only visual cue in this condition.

---

## Code

| File | Role |
|---|---|
| `src/ui/ar_overlay.py` | `AROverlay.render(frame, depth, alert, threat_box)` returns the composited frame |
| `src/ui/main_window.py` | `update_video_panels` branches on `condition_flags.ar_overlay_enabled` and hands off to `AROverlay` when enabled |

The overlay caches the vignette and scan-line masks per resolution to keep per-frame cost low.

---

## How it's used in the experiment

The 3-way condition selector in the controls bar:

```
[ NO ALERT | STANDARD | AR HUD ]
```

Picking `AR HUD` activates these flags (via `src/core/experiment.py`):

| Flag | Value |
|---|---|
| `audio_enabled` | True (beeps still play) |
| `alert_bar_visible` | False (the standard status bar is hidden) |
| `threat_box_visible` | False (the AR overlay paints its own visuals) |
| `ar_overlay_enabled` | True |

The standard threat-tracking bounding box is computed regardless — the AR renderer uses it as the input for the translucent highlight and corner brackets.

---

## Visual result

```
┌────────────────────────────────────────┐
│ [Driver view from dashcam]             │  ← vignette darkens edges
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │  ← scan lines (subtle)
│      ┏━━━━━━┓                          │
│      ┃░░░░░░┃                          │  ← translucent red fill on threat
│      ┃░[obj]┃                          │  ← thick outline + corner brackets
│      ┃░░░░░░┃                          │
│      ┗━━━━━━┛                          │
│                                        │
│  ▓▓▓▓▓▓▓ BRAKE ▓▓▓▓▓▓▓                 │  ← red strip on CRITICAL only
└────────────────────────────────────────┘
```

---

## Rejected alternative: WebXR demo

Considered exporting depth as WebGL textures and rendering in Three.js for actual phone-AR viewing. Rejected — adds a new tech stack, makes HCI instrumentation harder, and is mostly a wow-factor demo with no research benefit. Could revisit after the thesis.
