# Weekly Milestones

Concrete, checkable tasks per week. Mark `[x]` as completed.

---

## Week 1 — Apr 27 → May 3 (this week)
**Theme:** Real videos + participant-ready UI.

- [ ] Download 1 GB subset of BDD100K (or 5 KITTI raw clips, or curated YouTube)
- [ ] Curate 15–20 driving scenarios (5–10 s each, varied risk levels)
- [ ] Save scenarios to `data/scenarios/` with naming convention `<id>_<event_type>_<risk>.mp4`
- [ ] Build a scenario-loader screen in DepthGuard (replaces single-video mode)
- [ ] Add keyboard shortcuts: SPACE = brake, ESC = pause, ENTER = next scenario
- [ ] Fullscreen mode toggle (F11)
- [ ] Test full session end-to-end with at least one real video
- [ ] Email supervisor with first weekly update

**Deliverables at week end:**
- `data/scenarios/` populated with curated clips
- DepthGuard runs a participant-ready playlist of real footage
- Updated `docs/02-technical/real-video-pipeline.md`

---

## Week 2 — May 4 → May 10
**Theme:** AR overlay + baseline performance.

- [ ] Design AR overlay: depth contours / "danger zone" rendering on top of driver view
- [ ] Implement AR overlay as a separate PyQt window with WindowStaysOnTopHint
- [ ] Add toggle: "Standard view" vs "AR HUD view"
- [ ] Profile current pipeline: capture FPS, latency, memory for 1-min clip × 3 runs
- [ ] Document baseline numbers (Mac/CPU vs target Jetson Nano)
- [ ] Email supervisor with week 2 update

**Deliverables:**
- AR overlay working with toggle
- `docs/02-technical/jetson-optimization.md` baseline section filled
- 1-page performance report

---

## Week 3 — May 11 → May 17
**Theme:** Jetson optimization OR fallback to a lighter model.

- [ ] Try ONNX export of DepthPro
- [ ] If DepthPro too heavy: switch primary model to MiDaS Small (already integrated)
- [ ] Run on Jetson Nano (if available) OR simulate constraints on Mac
- [ ] Measure: FPS, memory, accuracy proxy (visual inspection)
- [ ] Update performance report

**Deliverables:**
- Final answer: "Yes" or "No" on Jetson ≥15 FPS / ≤4 GB
- If No: documented reason + which model would work
- Demo video showing performance on target hardware

---

## Week 4 — May 18 → May 24 (Milestone review)
**Theme:** HCI study protocol locked.

- [ ] Finalize study protocol (independent variables, hypotheses, dependent measures)
- [ ] Write consent form (Spanish + English)
- [ ] Write participant brief script
- [ ] Build debrief questionnaire (NASA-TLX, custom usability)
- [ ] Pilot with 2–3 people (friends/labmates, NOT counted toward 15)
- [ ] Iterate based on pilot feedback
- [ ] **Milestone meeting with supervisor — present prototype + protocol**

**Deliverables:**
- `docs/03-research/study-protocol.md` complete
- `docs/03-research/participant-materials/` complete
- Pilot data showing the pipeline captures everything correctly

---

## Week 5 — May 25 → May 31
**Theme:** Run participants 1–8.

- [ ] Open recruiting (peers, posters, course mailing lists)
- [ ] Schedule 8 sessions (target: 2/day, 4 days)
- [ ] Run sessions (consent → brief → trials → questionnaire → debrief)
- [ ] Daily CSV backup to `data/sessions/`
- [ ] Note any protocol drift in a log

**Deliverables:**
- 8 participants done, data archived

---

## Week 6 — Jun 1 → Jun 7
**Theme:** Run participants 9–15+, plus 2 buffer.

- [ ] Run remaining sessions (target ≥15 total, aim for 17 in case of dropouts)
- [ ] Preliminary look at data quality (no broken CSVs, reaction times reasonable)
- [ ] Email supervisor: "data collection complete, starting analysis"

**Deliverables:**
- ≥15 participants done
- All session CSVs archived

---

## Week 7 — Jun 8 → Jun 14
**Theme:** Analysis + thesis chapter draft.

- [ ] Aggregate session data into one master DataFrame
- [ ] Compute: mean reaction time, false-alarm rate, NASA-TLX scores by condition
- [ ] Run statistical tests (paired t-tests or Mann-Whitney; pick based on normality)
- [ ] Generate plots (PNG): RT distribution, alert-vs-no-alert comparison, FPS-latency
- [ ] Draft thesis chapter: Introduction (½ p), Method (2–3 p), Results (3–4 p), Discussion (2 p)
- [ ] Send draft to supervisor

**Deliverables:**
- `results/` folder with figures and stats
- Thesis chapter v1 (sent to supervisor)

---

## Week 8 — Jun 15 → Jun 22
**Theme:** Polish + submit.

- [ ] Address supervisor feedback on chapter
- [ ] Self-assessment report
- [ ] Code cleanup: type hints, docstrings, README, requirements pinned
- [ ] Record 3-min demo video
- [ ] Final submission package
- [ ] **Submit Jun 23**

---

## Habit checklist (every week)

- [ ] Email supervisor with progress + blockers
- [ ] Update `docs/01-planning/risk-log.md` if anything shifts
- [ ] Commit code at least every 2 days
