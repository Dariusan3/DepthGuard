# Test Video Sources

Curated list of dashcam / driving-hazard footage for building HCI study stimuli.
Use `scripts/download_clips.sh <url>` then trim with `scripts/trim_scenario.sh`.

---

## Best option for the thesis: research datasets (clean license)

These avoid the fair-use ambiguity of YouTube compilation channels and are
citable in your methods section.

| Dataset | What | Link |
|---|---|---|
| **BDD100K** | 100k driving clips, ~40s each, 720p/30fps, front-facing, mostly daytime, 85k+ pedestrian instances. Free for academic use after registration. **Recommended primary source.** | http://bdd-data.berkeley.edu/ |
| BDD100K (Kaggle mirror) | Easier-to-download subset | https://www.kaggle.com/datasets/solesensei/solesensei_bdd100k |
| DR(eye)VE | 555k frames, real driving + eye-tracking, attention-validated critical scenes | https://arxiv.org/abs/1705.03854 |
| KITTI | Front-facing, free, but low hazard density | http://www.cvlibs.net/datasets/kitti/ |
| UK DVSA Hazard Perception clips | Purpose-built "developing hazard" driver-POV clips (pedestrian steps out, cyclist enters lane) | https://hazardperceptiontest.net/ |

---

## YouTube dashcam compilations (secondary — scrub for timestamps)

Front-facing, daytime, many discrete events per video. Note: monetized
compilation channels aggregate third-party footage, so lead with the datasets
above in your write-up and treat these as supplementary.

| URL | Content |
|---|---|
| https://www.youtube.com/watch?v=2m_hudctGBw | **Pedestrian near-misses** — best match for the pedestrian category (zebra-crossing conflicts, jaywalkers) |
| https://www.youtube.com/watch?v=cesm33VJSNM | **Brake-checks / sudden braking ahead** — best match for the brake-lights category |
| https://www.youtube.com/watch?v=GrAqVdW9yHQ | Mixed: intersection collisions, merging near-misses, sudden stops |
| https://www.youtube.com/watch?v=N23jLNPRGtk | Pedestrian/vehicle conflicts, intersection events |
| https://www.youtube.com/watch?v=XcLJaO2L4Sk | Sudden braking, cut-ins, collisions ahead |
| https://www.youtube.com/@MegaDrivingSchool | Channel — highest events-per-video yield for batch clipping |

---

## 360° hazard videos (for the WebXR / VR arm)

True equirectangular, purpose-built for VR hazard perception. The JAF set is
already in use (`scenarios_360.csv`).

| URL | Content |
|---|---|
| https://www.youtube.com/watch?v=Re6GEscZY1I | **JAF — blind-spot pedestrian reveal** (currently used) |
| https://www.youtube.com/watch?v=VydKGOQ1mxI | JAF — collision scene, 55 km/h impact |
| https://www.youtube.com/watch?v=n8EdUPTiwKo | JAF — expressway high-speed hazard |
| https://english.jaf.or.jp/safe-driving/360video | JAF landing index (all scenes described) |

---

## Workflow

```bash
# 1. Download a source video
./scripts/download_clips.sh "https://www.youtube.com/watch?v=2m_hudctGBw"

# 2. Find the real filename
ls data/raw_downloads/

# 3. Trim an event into a scenario clip
./scripts/trim_scenario.sh data/raw_downloads/<file>.mp4 02:14 8 17 pedestrian critical

# 4. Add a row to the matching CSV (scenarios.csv or a per-type file)
```

For 360° clips, use `./scripts/download_360_samples.sh` instead and tag the CSV
row `projection=equirectangular`.

---

## Recommendation

1. **Primary:** BDD100K — clean academic license, reproducible, satisfies the
   supervisor's "real videos" priority and is defensible in the thesis.
2. **Supplement:** the two best YouTube clips (`2m_hudctGBw` pedestrians,
   `cesm33VJSNM` braking) for any hazard type BDD100K underrepresents.
3. **VR arm:** the JAF 360° set.
