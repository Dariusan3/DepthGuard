# Self-Validation Checklist

Run through this before week 3 / before recruiting. Catches bugs in the participant flow that would only show up under real load.

Mark items `[x]` as you complete them. If anything fails, log it as a risk in [`risk-log.md`](../../01-planning/risk-log.md) or fix and re-run.

---

## A. Self-pilot as participant `P00`

The single most valuable test. Run yourself through the full session as if you were a participant.

### Setup
- [ ] Launch `python main.py`
- [ ] Pick **MiDaS Small** in the MODEL dropdown (let it finish loading — wait for the dialog to close)
- [ ] Type `P00` in the participant ID field
- [ ] Click **Start Session**

### Pre-session dialog
- [ ] "READY TO BEGIN" dialog appears
- [ ] Shows the first condition (e.g. "Block 1 will use the No Alert condition")
- [ ] Click **Start Block 1**

### Block 1
- [ ] Trial 1 of 5 starts immediately, video plays
- [ ] Trial counter shows `TRIAL 1 OF 5` (or similar)
- [ ] Press SPACE on at least one clip — feels responsive
- [ ] **Don't** press on at least one safe clip (verify miss/false-alarm logic later)
- [ ] After trial 5, app pauses and shows the between-block dialog

### Between blocks
- [ ] Dialog says "BLOCK 1 COMPLETE" with the just-finished condition
- [ ] Dialog mentions next block + next condition
- [ ] Audio is silent (alert level was reset to SAFE)
- [ ] Click **Start Block 2** — next block begins, condition changes visibly

### Block 2 + Block 3
- [ ] Repeat brake-press behavior
- [ ] Verify each condition looks different:
  - **NO ALERT** — no audio, no status bar color, no threat box, no AR overlay
  - **STANDARD** — status bar shows alerts, threat box appears, audio beeps
  - **AR HUD** — translucent threat highlight + corner brackets + bottom BRAKE strip on critical
- [ ] After block 3, "SESSION COMPLETE" dialog appears

### Save + inspect data
- [ ] Click **Save Session** — file dialog confirms export
- [ ] Open `logs/reactions_P00_<datetime>.csv` — verify:
  - [ ] One row per brake press (plus rows for misses)
  - [ ] `condition` column populated for every row (not blank)
  - [ ] `outcome` column shows hit / miss / false_alarm correctly
  - [ ] `reaction_time_ms` is plausible (200–2000 ms range)
- [ ] Open `logs/plan_P00_<datetime>.txt` — verify:
  - [ ] Latin row index matches expected (`P00` → row 0 → NO_ALERT, STANDARD, AR_HUD)
  - [ ] 3 blocks, 5 trials each, balanced critical/warning/safe

If all of these pass → the participant flow is production-ready.

---

## B. Solo-mode quick-test of each condition

For visual QA of the conditions without the full session machinery.

- [ ] In Solo mode (`Load Playlist`), pick **NO ALERT** — play a critical clip → verify silent + no visual alert
- [ ] Pick **STANDARD** → same clip → verify status bar pulses red + audio beeps + threat box appears
- [ ] Pick **AR HUD** → same clip → verify translucent overlay + bottom BRAKE strip
- [ ] Switch conditions while paused — re-renders the current frame to show the new look

---

## C. Performance baseline — finish the table

```bash
python scripts/profile_performance.py --models mock midas --duration 30
```

- [ ] Mock run completes (already verified, ~64 FPS)
- [ ] MiDaS run completes — note the FPS, latency, peak memory
- [ ] Open [docs/02-technical/jetson-optimization.md](../../02-technical/jetson-optimization.md) and fill in the **Desktop baseline** table MiDaS row
- [ ] Optionally repeat with `--clip data/scenarios/14_city_safe.mp4` to confirm performance is consistent across clip types

If MiDaS hangs at the EfficientNet cache load: kill it with Ctrl+C, retry, and report. The progress prints (every 3s) will tell you if it's actually frozen vs just slow.

---

## D. Edge-case manual tests

Quick failure-mode checks. Don't go deep — just verify these don't crash.

- [ ] In Solo mode, press SPACE before any clip starts → no crash
- [ ] In Solo mode, hit Stop mid-clip → cleanly resets
- [ ] In Session mode, close the between-block dialog without clicking Continue → session aborts cleanly (currently: blocks until you click — that's fine)
- [ ] Toggle conditions rapidly during playback → no flicker / crash
- [ ] Drag the slider during playback → seek + auto-pause works
- [ ] Switch model mid-session → loading dialog appears, session can continue afterward

---

## E. Pre-recruitment readiness

Quick sanity checks before sending recruitment messages.

- [ ] Print the consent form ([`consent-form.md`](../../03-research/participant-materials/consent-form.md)) and fill in your name + email at the top
- [ ] Print the briefing script ([`briefing.md`](../../03-research/participant-materials/briefing.md)) — read it aloud once for timing (~3 min)
- [ ] Print the questionnaires ([`questionnaires.md`](../../03-research/participant-materials/questionnaires.md)) — confirm NASA-TLX × 3 + SUS + demographics
- [ ] Decide on a small incentive (chocolate? coffee voucher?) and budget for ~17 participants

---

## F. Recruitment first message

You can't pilot until you have a participant. **Even one classmate this week** unblocks everything.

- [ ] Draft a short recruitment message (one paragraph)
- [ ] Post in: at least one student WhatsApp group / course mailing list / lab Slack / equivalent
- [ ] Email the supervisor asking if she can share the recruitment message with her students
- [ ] Track who says yes in a spreadsheet — sessions to schedule next week

---

## What to do if something fails

1. **Crash / exception** — copy the traceback into a new section at the bottom of this file, then either fix it yourself or paste it back to the assistant
2. **Behavior that's wrong but not a crash** — write a short bug note here, decide whether to fix now or log as a risk
3. **Question about the protocol** — flag in the next supervisor email, don't guess
