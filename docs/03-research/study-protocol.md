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

---

## Implementation status

The protocol above is implemented in code (week 2 — pulled forward from week 4):

| Protocol element | Implementation |
|---|---|
| 3 conditions (NO_ALERT / STANDARD / AR_HUD) | `src/core/experiment.py` — `ExperimentCondition` enum + `flags_for()` returns 4 pipeline flags (audio / alert bar / threat box / AR overlay) |
| Latin-square block ordering | `src/core/session_planner.py` — `LATIN_SQUARE` constant, `plan_session(participant_id, scenarios)` returns a 3-block plan |
| Balanced trial selection (2 critical + 2 warning + 1 safe per block) | `plan_session` + bucketing by `expected_alert_level` |
| Per-participant trial randomization | `random.Random(_participant_seed(participant_id))` — reproducible per ID |
| Pre-session + between-block + end-of-session pause dialogs | `src/ui/block_pause_dialog.py` — modal with researcher prompt to administer NASA-TLX |
| `condition` column in reaction CSV | `src/core/data_logger.py` — `log_reaction(condition=...)` and `log_miss(condition=...)` |
| Plan audit log | `logs/plan_<participant>_<datetime>.txt` — written by `start_session` |

### How to run a participant session

1. Enter participant ID (e.g. `P01`) in the controls bar
2. Click **Start Session** (not "Load Playlist", which is solo mode)
3. Pre-session dialog confirms readiness, shows first condition
4. App runs Block 1 (5 trials). Participant presses SPACE on hazards.
5. Between-block dialog appears → researcher administers NASA-TLX → click Continue
6. Block 2 runs.
7. Between-block dialog → NASA-TLX → Continue.
8. Block 3 runs.
9. End-of-session dialog → researcher administers SUS + demographics.
10. Click **Save Session** to export CSVs + report to `logs/`.

### Solo-test mode (no participant)

For self-testing or quick demos without a participant ID, use **Load Playlist** instead. This walks through all 16 trials in the currently-selected condition, no Latin-square logic. Data is still logged but counts as N=1 for analysis.
