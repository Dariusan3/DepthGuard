# Data folder

Layout:

```
data/
├── scenarios/          # HCI test clips (15 trimmed videos) — committed
├── scenarios.csv       # Trial metadata for the HCI study — committed
├── raw_downloads/      # Full YouTube source videos — gitignored (too large)
├── training/           # Training data (KITTI raw) — gitignored
└── driving/            # ⚠️  STALE — leftover frames from earlier test, can be deleted
```

## scenarios.csv

Source of truth for the HCI study trial list. The 15 rows are templates with placeholder timestamps — replace `event_start_ms` and fill `source` / `license` once each clip is curated.

Required mix (already templated):
- 6 critical-event clips
- 6 warning-event clips
- 3 safe clips (control for false alarms)

## Adding a new scenario

1. Download source video to `raw_downloads/`
2. Trim to a 5–10 s clip with ffmpeg (see `docs/02-technical/real-video-pipeline.md`)
3. Save to `scenarios/<id>_<event>_<level>.mp4`
4. Update the matching row in `scenarios.csv`
