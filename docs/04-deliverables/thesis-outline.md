# Thesis Chapter Outline

Target length: **8–12 pages** (single chapter inside the larger thesis document).

Style: scientific report — past tense for completed work, third person.

---

## 1. Introduction (~1 page)

- Motivation: distracted/fatigued driving as a global safety issue
- Existing solutions (forward collision warning systems): cost, hardware barriers
- Research gap: lightweight, monocular-camera-only systems using self-supervised depth learning
- Project contribution: DepthGuard — desktop simulator + AR overlay + HCI evaluation
- Research questions (mirror `study-protocol.md`)

## 2. Background (~1 page)

- Monocular depth estimation: brief history (MiDaS → DPT → DepthPro)
- Self-supervised learning for depth: photometric loss, pose networks
- HCI for safety-critical systems: reaction time as a measure, NASA-TLX, SUS
- AR HUDs in modern vehicles: short survey

## 3. System Design (~2 pages)

- Architecture diagram (from `02-technical/architecture.md`)
- Pipeline: per-frame processing, alert classification, logging
- Three model paths: Mock / MiDaS / DepthPro — interface contract
- UI: three tabs, transport controls, AR overlay
- Data captured per session

## 4. Implementation (~1 page)

- Tech stack: PyQt5, OpenCV, PyTorch, pygame, pyqtgraph
- DepthPro integration via Apple's reference repo (forked at github.com/Dariusan3/ml-depth-pro)
- Alert system: ROI-based thresholding (justify the chosen 0.50 / 0.30 / 0.15 cutoffs)
- AR overlay: contour rendering with cv2.findContours
- Performance instrumentation: deque-based history with 100-sample window

## 5. Performance Evaluation (~1.5 pages)

- Methodology: 60-s benchmark clip, three runs averaged
- Hardware tested: Mac (CPU + GPU), Jetson (if available)
- Results table: FPS / latency / memory across {Mock, MiDaS, DepthPro} × {Mac, Jetson}
- Plot: FPS over time for each configuration
- Discussion: which models meet the 15 FPS / 4 GB target; trade-offs

## 6. HCI User Study (~3 pages)

- Method: design, participants, materials, procedure (compress study-protocol.md)
- Quantitative results:
  - RT by condition (table + box plot)
  - ANOVA + post-hocs
  - Detection rate / false-alarm rate
  - NASA-TLX scores
  - SUS scores
- Qualitative results: themes from free-text feedback
- Discussion of hypotheses: H1, H2, H3 — supported / not supported

## 7. Discussion (~1 page)

- Interpretation: do the results support the use of monocular depth estimation for driver alerts?
- Comparison to commercial systems (Mobileye, Tesla AP) — DepthGuard is a research prototype, not a competitor
- Limitations:
  - N = 15 (small sample)
  - Desktop simulation (no real-driving validity)
  - Daylight only
  - No Jetson hardware (if applicable)
- Threats to validity: reaction time as a proxy for safety improvement

## 8. Conclusion + Future Work (~0.5 page)

- Recap of contributions
- Future work:
  - Train custom self-supervised model on KITTI (the original thesis ambition)
  - Real driving simulator integration (CARLA / AirSim)
  - Real Jetson deployment + on-road test
  - Larger HCI sample with diverse demographics

## References

15–25 entries. Must include:
- DepthPro paper (arxiv 2410.02073)
- MiDaS paper (Ranftl et al.)
- BDD100K / KITTI dataset papers (whichever is used)
- NASA-TLX (Hart & Staveland 1988)
- SUS (Brooke 1996)
- Self-supervised depth: Monodepth2 (Godard et al.)

---

## Writing schedule

| Week | Section | Status |
|---|---|---|
| 7 | §3, §4, §5 | Empty |
| 7 | §6 (after analysis) | Empty |
| 8 | §1, §2, §7, §8, refs | Empty |
| 8 | Polish + supervisor feedback | Empty |
