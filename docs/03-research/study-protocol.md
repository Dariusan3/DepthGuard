# HCI Study Protocol

**Status:** Draft v0.1 — needs supervisor approval before pilot.
**Target N:** 15+ participants
**Session length:** ~30 minutes

---

## Research question

> Does a depth-based driver alert system (visual + audio + AR HUD overlay) reduce reaction time to critical road hazards compared to no alert?

Secondary questions:
- Does the AR HUD overlay outperform a standard alert bar?
- Does the alert system increase or decrease perceived workload (NASA-TLX)?
- How do participants rate usability (SUS)?

---

## Hypotheses

- **H1:** Mean reaction time in the AR-alert condition is significantly shorter than in the no-alert condition.
- **H2:** Mean reaction time in the standard-alert condition is significantly shorter than in the no-alert condition.
- **H3:** Perceived workload (NASA-TLX) is no higher in alert conditions than in no-alert (i.e. alerts don't add cognitive load).

---

## Design

**Within-subjects, counterbalanced.** Each participant experiences all three conditions:

| Condition | Alert UI |
|---|---|
| C1 — No alert | Just the dashcam playback, no DepthGuard overlay |
| C2 — Standard | Bottom alert bar + audio beep on CRITICAL/WARNING |
| C3 — AR HUD | Contour overlay on driver view + distance labels + bottom strip on CRITICAL |

Order is counterbalanced across participants (Latin-square 3×3, 6 orderings; cycle through).

---

## Trial structure

Each participant sees **15 trials**: 5 trials × 3 conditions.

Trials are drawn from `data/scenarios/`:
- 6 critical events (pedestrian / brake / cyclist / lane intrusion)
- 6 warning-level events
- 3 safe (no event — control to detect false alarms)

Counterbalancing: within a condition block, trial order is randomized per participant.

Inter-trial blank: 2 seconds, gray screen, "Trial X complete. Get ready..." text.

---

## Procedure

1. **Welcome (2 min)** — Greet, hand consent form. Wait for signature.
2. **Briefing (3 min)** — Read the briefing script (see participant-materials/briefing.md). Demo one practice trial.
3. **Practice (2 min)** — Two practice trials, no data recorded. Confirm spacebar = brake.
4. **Block 1 (5 min)** — 5 trials of condition assigned via Latin square.
5. **Mid-block questionnaire (1 min)** — NASA-TLX for the just-finished condition.
6. **Block 2 (5 min)** — 5 trials of next condition.
7. **Mid-block questionnaire (1 min)** — NASA-TLX.
8. **Block 3 (5 min)** — 5 trials of last condition.
9. **Final questionnaires (5 min)** — SUS, demographics, free-text feedback.
10. **Debrief (2 min)** — Thank, explain study purpose, answer questions.

Total: ~31 min.

---

## Independent variables

| Variable | Levels |
|---|---|
| Alert condition | No-alert / Standard / AR HUD |
| Trial type (within-condition) | Critical / Warning / Safe |

---

## Dependent variables

Captured automatically by DepthGuard:

| Variable | Source | Notes |
|---|---|---|
| Reaction time (ms) | `data_logger.log_reaction()` | Time from event_start_ms to brake press |
| Correct response | `data_logger.log_reaction()` | Brake press within ±3000 ms of critical/warning event |
| False alarm | `data_logger.log_reaction()` | Brake press during a safe trial |
| Miss | Computed post-hoc | Critical/warning event with no brake press in window |

Captured via questionnaire:

| Variable | Instrument |
|---|---|
| Perceived workload | NASA-TLX (6 sub-scales) |
| Usability | SUS (10 items) |
| Trust in system | 5-point Likert (custom): "I trusted the alert system" |
| Demographics | Age, driving experience (years), prior dashcam use (Y/N) |

---

## Inclusion / exclusion criteria

**Include:**
- Adult (≥ 18)
- Comfortable with computer keyboards
- Normal or corrected-to-normal vision

**Exclude:**
- Active driving instructors (likely outliers in reaction time)
- Researchers who saw the alert thresholds (anyone who has used DepthGuard outside of this session)

---

## Sample size justification

Target: N = 15.

Rationale: For a within-subjects design with 3 conditions and an expected medium effect size (Cohen's d ≈ 0.5) on reaction time, N = 15 gives ~70% power at α = 0.05. The traineeship contract specifies "15+ participants" as the deliverable. Aim for 17 to account for dropouts/data loss.

---

## Ethics

This is a low-risk study (passive video viewing + keyboard responses). No deception, no physical intervention.

- Consent form signed before each session
- Right to withdraw at any time, no questions asked
- All data stored as anonymized participant IDs (P01, P02, ...) — no names in CSVs
- Identifying info (consent forms) stored separately, in a locked folder
- Aggregated results only — no individual-level data published

**Supervisor confirmed (2026-05-01):** academic studies at UPM do not require ethics committee approval. Informed consent (signed) is sufficient. Treat the consent form in `participant-materials/consent-form.md` as the formal requirement.

---

## Counterbalancing schedule

Use this ordering across participants (cycle every 6):

| Participant | Block 1 | Block 2 | Block 3 |
|---|---|---|---|
| P01 | No-alert | Standard | AR HUD |
| P02 | No-alert | AR HUD | Standard |
| P03 | Standard | No-alert | AR HUD |
| P04 | Standard | AR HUD | No-alert |
| P05 | AR HUD | No-alert | Standard |
| P06 | AR HUD | Standard | No-alert |
| P07 | No-alert | Standard | AR HUD |
| ... | ... | ... | ... |
