# Weekly Supervisor Updates

Running log of Friday emails to Prof. Angélica de Antonio. Newest first.

---

## Week 1 — Apr 27 to May 3, 2026

Subject: DepthGuard - Week 1 update

Dear Professor de Antonio,

Quick update before the weekend.

Following up on what we discussed, I replaced the placeholder video with 16 real dashcam clips from public YouTube compilations (7 critical, 6 warning, 3 safe), each 5 to 10 seconds with the event timestamp noted. I also reworked the interface, added keyboard shortcuts for participants, and built a Playlist mode that walks through all 16 clips automatically.

On the model side I have three options wired in (mock, MiDaS Small, and DepthPro from the Apple repo I forked). DepthPro is too heavy to run in real time on my laptop, so my plan is to use MiDaS Small for the participant sessions and keep DepthPro for the research and training side in the ml-depth-pro fork.

For next week I'd like to start on the AR HUD overlay you mentioned and get a performance baseline.

Two things I'd appreciate your input on at our next meeting: first, whether the HCI study needs formal ethics approval at UPM or just your sign-off; second, whether the lab has a Jetson I could borrow, or if I should plan to simulate the constraints on desktop.

Have a good weekend.

Best,
Andrei

---

## Week 2 — May 4 to May 10, 2026

Subject: DepthGuard - Week 2 update

Dear Professor de Antonio,

Quick update on this week's progress.

The AR HUD overlay is now built and working as the third experimental condition. The interface has a 3-way condition selector (No Alert / Standard / AR HUD) that switches the pipeline live: audio, the alert status bar, the threat bounding box, and the AR overlay all turn on or off depending on the active condition. The AR view paints a translucent highlight on the closest threat, corner brackets, a vignette, and a red BRAKE strip at the bottom on critical alerts.

I also pulled forward most of the participant-flow infrastructure from later weeks. There's now a session planner that takes a participant ID, builds a 3-block plan with Latin-square counterbalancing, and selects 5 balanced trials per block (2 critical + 2 warning + 1 safe). Between blocks the app shows a pause dialog so I can administer the NASA-TLX before the next block starts. Each reaction is tagged with the active condition in the CSV output, ready for analysis.

I built two run modes that share the same logging pipeline: a solo mode for quick self-testing across all 16 clips, and the multi-participant mode with Latin square. Either way the data structure is identical.

I also added a performance profiler script that captures FPS, latency and memory per model. The mock baseline runs at ~63 FPS on my laptop (so the non-model overhead of decode + alerts + logging is ~16 ms). I'll run MiDaS through it next and put the numbers in the thesis.

For week 3 I want to nail down the MiDaS performance numbers, finalize the participant materials, and start on the analysis pipeline.

One thing I'd appreciate your input on: would you be able to share the recruitment ad with your students, or do you have suggestions for where to post it within UPM? The study itself takes about 30 minutes per person.

Best,
Andrei

---

<!-- Future updates go above this line, newest first -->
