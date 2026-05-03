# AR Extension

Professor's suggestion: add augmented-reality testing capability.

For a thesis-scale project with 8 weeks and no AR hardware budget, the realistic interpretation is **simulated AR HUD overlay**, not a real headset.

---

## Concept

Render alert visuals as if they were projected on the windshield in front of the driver:
- Semi-transparent depth contours over the live frame
- A "danger zone" outline that highlights the closest object in the ROI
- Distance read-outs floating near detected obstacles

This is what Tesla / Mercedes "augmented reality navigation" looks like — directional cues painted on the driver's view.

---

## Two implementation options

### Option A — Overlay window inside DepthGuard (recommended)
- New PyQt window with `Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint`
- Transparent background (`setAttribute(Qt.WA_TranslucentBackground)`)
- Renders contours from the depth map using `cv2.findContours` on a thresholded depth slice
- Toggleable alongside the standard view

**Pros:** stays in-process, easy to capture for HCI metrics, no new tech stack.
**Cons:** still on the same screen — not "real" AR.

### Option B — WebXR demo (only if Option A is fast)
- Export depth maps as WebGL textures
- Three.js scene that re-projects the frame as a 3D plane with the depth as displacement
- Viewable on iPhone via WebXR

**Pros:** more impressive in supervisor demo.
**Cons:** new tech stack, extra week of work, harder to instrument for HCI metrics.

**Decision:** Implement Option A. Keep Option B as a nice-to-have if time allows after the HCI study.

---

## Visual design (Option A)

```
┌────────────────────────────────────────┐
│ [Driver view from dashcam]             │
│                                        │
│      ┌──────┐                          │  ← yellow outline = WARNING zone
│      │      │                          │
│      │ [obj]│  6.2 m                   │  ← red outline = CRITICAL
│      │      │                          │
│      └──────┘                          │
│                                        │
│  ▓▓▓ DANGER ZONE ▓▓▓                   │  ← bottom-edge HUD strip on critical
└────────────────────────────────────────┘
```

Three layers, blended over the driver frame:
1. **Contour layer** — outlines around any object whose minimum depth crosses the WARNING / CRITICAL threshold.
2. **Distance label layer** — floating text "X.X m" near each contour centroid (uses estimated metric depth from DepthPro).
3. **HUD strip layer** — bottom edge of frame turns red and shows "BRAKE" text when CRITICAL.

Use additive alpha blending so text is readable over dark backgrounds.

---

## Code structure

New file: `src/ui/ar_overlay.py`

```python
class AROverlay:
    def render(self, frame: np.ndarray, depth: np.ndarray, alert: dict) -> np.ndarray:
        """Returns the frame with AR layers blended in."""
```

Wired into `MainWindow.update_video_panels` — when AR mode is on, run frame through `AROverlay.render` before showing.

A toggle button in the controls bar: `[ Standard ] [ AR HUD ]`.

---

## Use in HCI study

The AR mode becomes a **third experimental condition**:
- Condition 1: No alert
- Condition 2: Standard alert (current bar + audio)
- Condition 3: AR HUD overlay

Compare reaction times across all three. This gives the thesis a concrete research question:
**"Does AR-style overlay improve reaction time over a standard alert bar?"**

Even if the answer is "no significant difference", it's a publishable finding.
