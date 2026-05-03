# Roadmap — 8 Weeks to Deadline

**Today:** 2026-04-27 (Monday)
**Deadline:** 2026-06-23 (Tuesday) — **57 days, ~8 weeks**

---

## Strategic Principle

The 30% research grade requires **HCI study with 15+ participants + statistical analysis + thesis chapter**. That work cannot be parallelized or rushed at the end — recruitment alone takes 1–2 weeks. Therefore:

> **The HCI study must start by week 5 (May 25) at the latest.**
> All technical work must be "good enough" by then. No new technical features after week 5.

---

## Phases

### Phase 1 — Real Videos + UI Polish (Week 1: Apr 27 – May 3)
**Goal:** Replace mock content with real driving footage; polish UI for participants.

- Acquire dashcam footage (BDD100K, KITTI raw, or curated YouTube clips)
- Curate 15–20 short scenarios (5–10 s each) covering: pedestrian crossing, sudden brake-light ahead, cyclist, lane intrusion, stop sign approach
- UI polish: keyboard shortcuts (spacebar = brake, escape = pause), fullscreen mode, larger BRAKE target for participants
- Document video sources + licenses

### Phase 2 — AR Extension + Jetson Profiling (Week 2: May 4 – May 10)
**Goal:** Implement AR-style overlay; baseline performance numbers.

- AR HUD overlay: semi-transparent depth contours rendered over driver view, simulating windshield projection
- Optionally: WebXR demo for handover scenarios
- Profile current pipeline: FPS, latency, memory on Mac (CPU baseline)
- Document limits: what would need to change for Jetson Nano (≥15 FPS, ≤4 GB)

### Phase 3 — Jetson Optimization (Week 3: May 11 – May 17)
**Goal:** Hit the ≥15 FPS / ≤4 GB target (or document why not feasible).

- Export DepthPro to ONNX
- Quantize INT8 (or FP16) — pick MiDaS small as a fallback if DepthPro is too heavy
- Validate on Jetson hardware OR simulate via constrained desktop mode
- Performance report (table of FPS, memory, accuracy trade-offs)

### Phase 4 — HCI Study Design + Pilot (Week 4: May 18 – May 24)
**Goal:** Study protocol approved by supervisor; pilot with 2–3 friends/labmates.

- Finalize study design (between-subjects: alert ON vs alert OFF)
- Consent form, participant briefing, debrief script
- Pilot 2–3 runs; iterate on issues found
- **Milestone review with supervisor (week 4 in original plan)**

### Phase 5 — Formal HCI Study (Week 5–6: May 25 – Jun 7)
**Goal:** 15+ participants run through the full protocol; data captured.

- Recruit participants (peers, university student pool)
- Schedule 30 min slots; aim for 3–4 sessions/day
- Each session: consent → briefing → 8 trials → questionnaires (NASA-TLX, SUS) → debrief
- Daily backup of CSV data

### Phase 6 — Analysis + Thesis Writing (Week 7: Jun 8 – Jun 14)
**Goal:** Statistical results computed; thesis chapter drafted.

- Statistical analysis: paired t-tests on reaction times, ANOVA, false-alarm rates
- Plots: reaction-time distributions, FPS vs latency, alert-level confusion matrix
- Thesis chapter draft: methodology, results, discussion

### Phase 7 — Polish + Submission (Week 8: Jun 15 – Jun 22)
**Goal:** Everything ready before deadline.

- Self-assessment report
- Code cleanup, README, demo video
- Final supervisor review
- **Submission day: Jun 23**

---

## Critical Path

```
Real video (W1)
    ↓
HCI Pilot (W4) ────────── HCI Study (W5–6) ───── Analysis (W7) ───── Submit (W8)
    ↑                                                  ↑
UI / AR (W1–2)                                  Thesis chapter (W7–8)
    ↑
Jetson optimization (W2–3) → can be partial if HCI is at risk
```

If anything slips, **cut Jetson optimization first**, then AR. Never cut HCI.

---

## Buffer Strategy

Each phase has 1–2 days of slack built in. Use them for:
- Re-recruiting participants who no-show
- Re-running pilot if first protocol has issues
- Last-minute thesis revisions
