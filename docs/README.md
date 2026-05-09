# DepthGuard — Thesis Documentation

Research Internship in Self-Supervised Monocular Depth Estimation for Driver Safety Applications.

**Supervisor:** Prof. Angélica de Antonio (UPM)
**Deadline:** 2026-06-23

---

## Index

### 01 — Planning
- [Thesis Requirements](01-planning/thesis-requirements.md) — Original traineeship plan (source of truth)
- [Roadmap](01-planning/roadmap.md) — 8-week plan from now to deadline
- [Weekly Milestones](01-planning/weekly-milestones.md) — Week-by-week tasks
- [Risk Log](01-planning/risk-log.md) — Known risks and mitigations

### 02 — Technical
- [Architecture](02-technical/architecture.md) — System overview
- [Real Video Pipeline](02-technical/real-video-pipeline.md) — Replacing mock with real dashcam footage
- [UI Redesign](02-technical/ui-redesign.md) — Frontend improvements (done + planned)
- [AR Extension](02-technical/ar-extension.md) — Augmented reality testing capability
- [Jetson Optimization](02-technical/jetson-optimization.md) — Embedded deployment plan

### 03 — Research (HCI Study)
- [Study Protocol](03-research/study-protocol.md) — Methodology, hypotheses, metrics
- [Data Analysis Plan](03-research/data-analysis-plan.md) — Statistical methods
- [Participant Materials](03-research/participant-materials/) — Consent, briefing, debrief

### 04 — Deliverables
- [Deliverables Checklist](04-deliverables/checklist.md) — What must be turned in
- [Thesis Outline](04-deliverables/thesis-outline.md) — Chapter structure

### 05 — Weekly Progress (retrospectives)
- [Index](05-progress/) — what was actually done each week
- [Week 01](05-progress/week-01/) — Apr 27 to May 3 — Real videos + UI polish
- [Week 02](05-progress/week-02/) — May 4 to May 10 — AR HUD + experimental conditions

---

## Quick status

| Area | Status |
|---|---|
| PyQt5 application | ✓ shipped — HUD theme |
| Depth models (Mock / MiDaS / DepthPro) | ✓ all three wired in |
| Real video integration | ✓ 16 dashcam scenarios |
| AR HUD overlay | ✓ shipped (week 2) |
| 3 experimental conditions + Latin square | ✓ shipped (week 2, pulled from W4) |
| Multi-participant flow + block dialogs | ✓ shipped (week 2, pulled from W4) |
| Solo-test mode | ✓ shipped |
| Performance baseline (Mock) | ✓ — MiDaS row pending |
| Jetson simulation plan | ✓ documented (no hardware available) |
| HCI study design | ✓ protocol drafted |
| HCI study recruitment | Open — top risk |
| HCI study execution | Pending (weeks 5–6) |
| Thesis chapter | Pending (weeks 7–8) |

Last updated: 2026-05-03
