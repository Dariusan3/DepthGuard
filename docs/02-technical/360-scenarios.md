# 360-degree scenarios

DepthGuard now supports equirectangular (360°) clips as trial stimuli alongside the standard flat dashcam clips.

---

## Adding a 360° clip

### 1. Acquire the source video

Look for 360° dashcam compilations on YouTube tagged "360 dashcam" or "VR driving":

```bash
yt-dlp -f "best[height<=2160]" -o "data/raw_downloads/source_%(id)s.%(ext)s" "<youtube-url>"
```

360° YouTube videos are typically uploaded as 4K equirectangular (3840×1920 or 4096×2048).

### 2. Trim with ffmpeg as usual

```bash
ffmpeg -ss 02:14 -i data/raw_downloads/source_XYZ.mp4 -t 8 \
       -c:v libx264 -preset fast -crf 23 -an \
       data/scenarios/17_pedestrian_critical_360.mp4
```

### 3. Add a row to `scenarios.csv` with the `projection` column

If your CSV doesn't have a `projection` column yet, add it. Existing rows default to `flat`.

```csv
id,filename,event_type,expected_alert_level,event_start_ms,duration_ms,source,license,notes,projection
17,17_pedestrian_critical_360.mp4,pedestrian,CRITICAL,3000,8000,<url>,fair-use,,equirectangular
```

Valid values:

| Value | Behavior |
|---|---|
| `flat` (or empty) | Default — treated as a normal forward-facing dashcam clip |
| `equirectangular` | 360° video. The pipeline crops the forward 90° FOV for depth + alert processing |

---

## What happens at runtime

When the playlist loader sees `projection: equirectangular`, the per-frame pipeline crops out the forward-view portion of the frame before sending it to the depth model. This means:

- The depth model + alert ROI work on a normal-looking rectangle
- Reaction times remain comparable to the flat clips
- The participant sees the forward view only

The crop is currently a **center-rectangle slice** that takes the middle 25% of the frame width (≈ 90° horizontal FOV) at the equator. A full pinhole reprojection is documented as future work in [planned-enhancements.md](planned-enhancements.md).

---

## In VR (WebXR companion)

For an immersive 360° experience in the headset, the next step is to render the equirectangular frame onto a sphere geometry around the user. Implementation deferred — see [planned-enhancements.md](planned-enhancements.md). For now the WebXR client receives the same forward-cropped frame and displays it on the virtual windshield.

---

## Verifying it works

After adding a 360° clip:

```bash
python scripts/smoke_test.py
```

The clip should run without errors. Visually inspect the cropped frame in the driver view — it should look like a normal forward-facing dashcam shot, not a fisheye distortion. If the crop is too narrow or too wide, adjust `fov_deg` in `MainWindow._crop_equirectangular_forward`.
