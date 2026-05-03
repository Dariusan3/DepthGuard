# Risk Log

Living document. Add new risks as they appear; mark mitigated ones.

---

| # | Risk | Likelihood | Impact | Mitigation | Status |
|---|---|---|---|---|---|
| R1 | DepthPro too heavy for Jetson Nano (≥15 FPS unreachable) | High | Medium | Fall back to MiDaS Small (already integrated). Document trade-off in thesis. | Open |
| R2 | **Recruitment may not reach 15 participants** | **High** | **High** | **Critical to 30% grade.** Mitigations: ask supervisor for recruitment help in next email; tap student WhatsApp/course mailing lists; family + friends remote; if N<15 frame as pilot study and document limitations honestly. **Build infrastructure for both solo + multi-participant flows so no work is wasted.** | **Open — top priority** |
| R3 | No physical Jetson available for testing | — | — | **Confirmed by supervisor (2026-05-01): simulate constraints on desktop**, document as a methodology choice not a limitation | Resolved |
| R4 | DepthPro repo install fails on macOS | Medium | Low | Use Hugging Face DepthPro-hf as backup; or fall back to MiDaS for the demo | Open |
| R5 | AR overlay slows pipeline below acceptable FPS | Medium | Low | Make AR overlay optional; render at lower resolution | Open |
| R6 | Statistical analysis shows no significant effect | Medium | High (research grade) | Frame the thesis around methodology + tooling; preregister hypotheses; even null results are publishable | Open |
| R7 | Last-week thesis writing crunch | High | Medium | Start chapter draft in week 6 after first 8 participants; outline sections in week 4 | Open |
| R8 | Supervisor unavailable during exam period | Low | Medium | Confirm her availability for weeks 7–8 in week 4 meeting; agree on email turnaround | Open |
| R9 | Threat bounding box jitters / doesn't lock onto pedestrian/vehicle reliably | Low | Low | Cosmetic for HCI study (alert level + audio is what's measured). Revisit week 2 — try semantic segmentation (YOLOv8 person/car) overlaid with depth, or median-depth tracking with IoU stability | Open |
