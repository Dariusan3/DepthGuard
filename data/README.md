# Data folder

Layout:

```
data/
├── scenarios/                      # 16 HCI test clips (mp4) — committed
├── scenarios.csv                   # FULL trial set (all 16 clips) — used by Start Session
├── scenarios_pedestrian.csv        # 5 pedestrian-only clips — load via Load Playlist
├── scenarios_brake_lights.csv      # 8 brake-lights-only clips
├── scenarios_safe.csv              # 3 safe baseline clips
├── scenarios_360.csv               # 360° template — placeholder rows to fill in
├── raw_downloads/                  # Full YouTube source videos — gitignored
├── training/                       # Training data (KITTI raw) — gitignored
└── driving/                        # ⚠️  STALE — old frames, can be deleted
```

---

## scenarios.csv (master)

The full set of 16 curated clips. **This is the file Start Session uses** — the session planner picks a balanced subset from here per participant (Latin square).

Distribution:
- 7 critical events (pedestrian + brake_lights)
- 6 warning events (pedestrian + brake_lights)
- 3 safe baseline clips
- All `projection: flat` (forward-facing dashcam)

## Per-event-type CSVs

For solo testing / quick demos when you only want one type of stimulus:

| File | Count | What's in it |
|---|---|---|
| `scenarios_pedestrian.csv` | 5 | All pedestrian clips (3 CRITICAL + 2 WARNING) |
| `scenarios_brake_lights.csv` | 8 | All brake-light clips (4 CRITICAL + 4 WARNING) |
| `scenarios_safe.csv` | 3 | All safe baselines |

To use one, click **Load Playlist** in DepthGuard and pick the file you want. The clip itself is the same — these are just curated subsets pulled from the master CSV.

## scenarios_360.csv

Template for 360° equirectangular clips. The five rows are **placeholders** — the filenames don't exist yet. To make this CSV usable:

1. Acquire a 360° dashcam video (see [docs/02-technical/360-scenarios.md](../docs/02-technical/360-scenarios.md))
2. Trim with ffmpeg and save the file as `scenarios/360_01_pedestrian_critical.mp4` (etc.)
3. Replace `REPLACE_WITH_YOUR_URL@MM:SS` with the real source URL
4. Set the correct `event_start_ms` based on when the event happens

When loaded, the per-frame pipeline detects `projection: equirectangular` and crops the forward 90° FOV automatically.

---

## CSV schema

All scenario CSVs share the same columns:

| Column | Type | Example | Notes |
|---|---|---|---|
| `id` | string | `01`, `360_01` | Unique identifier |
| `filename` | string | `01_pedestrian_critical.mp4` | Must exist in `scenarios/` folder |
| `event_type` | enum | `pedestrian` / `brake_lights` / `cyclist` / `lane_intrusion` / `safe` | What kind of hazard |
| `expected_alert_level` | enum | `CRITICAL` / `WARNING` / `CAUTION` / `SAFE` | Used to score reactions |
| `event_start_ms` | int | `1500` | When the hazard becomes visible (0 for SAFE clips) |
| `duration_ms` | int | `7000` | Clip length |
| `source` | string | YouTube URL @ timestamp | Provenance |
| `license` | string | `fair-use` | Always fair-use for the current set |
| `notes` | string | free text | Anything worth flagging |
| `projection` | enum | `flat` (default) / `equirectangular` | Frame projection |

---

## Adding a new scenario

1. Download source to `raw_downloads/`
2. Trim with ffmpeg → save to `scenarios/<id>_<event>_<level>.mp4`
3. Add a row to the appropriate CSV (master + per-type if it fits a category)
4. Verify the smoke test passes: `python scripts/smoke_test.py`
