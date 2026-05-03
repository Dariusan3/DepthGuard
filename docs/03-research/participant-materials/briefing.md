# Participant Briefing Script

Read this aloud to each participant before they start. Don't paraphrase — keep it consistent across participants to reduce researcher-induced variance.

---

## Briefing

> "Thank you for agreeing to participate. This study takes about 30 minutes.
>
> You'll watch short driving videos — about 5 to 10 seconds each — recorded from a dashcam mounted on a car's dashboard. These are real driving situations.
>
> Your task is simple: imagine you are the driver. Watch the video, and **press the SPACEBAR as quickly as you can whenever you see a hazard** — anything you'd want to brake for. That could be a pedestrian, another car braking suddenly, a cyclist appearing, or anything that looks dangerous.
>
> Some videos will have hazards. Some will not. **Don't press the spacebar if there's no hazard.** If you press it during a safe video, that counts as a false alarm.
>
> You'll watch the videos in three blocks. In some blocks, the system will give you visual or audio alerts when it detects a hazard. In other blocks, you'll see only the raw video — no alerts. We're studying how alerts affect your reaction time.
>
> Between blocks, I'll ask you to fill out a short questionnaire about how the experience felt.
>
> Two practice trials first, then the real session begins. Any questions?"

---

## Practice trials

Run two practice trials. The first should have a clear pedestrian (CRITICAL); the second should be a SAFE clip.

After each practice trial, ask: *"Did you understand what to do? Did the system feel responsive?"*

If the participant did not press for the pedestrian or pressed for the safe trial, **repeat practice once more**. Do not move on until they have correctly responded to one of each.

---

## During trials

- Sit slightly behind and to the side, out of the participant's peripheral vision.
- Do not give feedback on individual trials ("good job", "you missed that one").
- Do not answer questions about specific videos. If asked: "I'll explain everything at the end."
- Note any anomalies in `data/sessions/notes.txt`: e.g. "P07 sneezed during trial 4", "P09 reported screen glare".

---

## After all blocks

> "Great, that's the last block. Three quick questionnaires now."

Hand over:
1. NASA-TLX (one per condition — three total, but they fill them as you go between blocks)
2. SUS (10 items)
3. Demographics + free-text feedback (one form, end of session)

---

## Debrief

> "We're done — thank you. To explain what we were measuring: we have a system called DepthGuard that uses an AI model to estimate how far away things are in a video, and triggers an alert when something gets too close. We're comparing three versions: no alert, a standard alert bar at the bottom, and an augmented-reality-style overlay with depth contours.
>
> We're measuring whether the alerts help people react faster, and whether the AR overlay is better than the standard one. Your data will be combined with about 15 other participants for a Bachelor's thesis at UPM.
>
> Do you have any questions about the study or what the system does?"

If the participant asks how their personal results compared: explain that we don't analyze individual data — only the group average matters for the research question.
