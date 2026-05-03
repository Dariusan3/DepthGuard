# Deliverables Checklist

Everything that must be ready by **2026-06-23**.

---

## Technical (60% of grade)

- [ ] **Functional application** with all three model paths (Mock / MiDaS / DepthPro)
- [ ] Real driving footage in `data/scenarios/` (≥ 15 clips)
- [ ] Visual + audio alerts firing correctly on real footage
- [ ] AR HUD overlay implemented as third experimental condition
- [ ] Performance metrics page with FPS, latency, CPU/GPU memory
- [ ] **Jetson compatibility report** (≥ 15 FPS, ≤ 4 GB) — pass OR documented why not
- [ ] **Code quality:** type hints on public APIs, docstrings on classes, no dead code
- [ ] `requirements.txt` pinned + tested fresh install
- [ ] `README.md` with install + run instructions
- [ ] 3-min demo video showing the full pipeline

## Research (30% of grade)

- [ ] HCI study protocol approved by supervisor
- [ ] **≥ 15 participants** completed the full session
- [ ] Anonymized dataset in `results/master_data.csv`
- [ ] Statistical analysis: ANOVA / Friedman + post-hocs
- [ ] Figures: RT distribution, workload, detection rate, SUS
- [ ] **Thesis chapter** (≥ 8–10 pages: intro, method, results, discussion)

## Professional (10% of grade)

- [ ] Weekly emails to supervisor (8 total expected)
- [ ] Self-assessment report (1–2 pages)
- [ ] Activity log showing weekly hours
- [ ] Showed up to milestone meetings prepared

---

## Final submission package

Folder `submission/`:

```
submission/
├── thesis-chapter.pdf
├── self-assessment.pdf
├── demo-video.mp4
├── code/                  # Cleaned DepthGuard repo zip
├── data/
│   ├── scenarios.csv      # Trial metadata
│   └── master_data.csv    # Anonymized participant data
├── results/
│   ├── tables/
│   └── figures/
└── README.md              # What's in this folder
```

---

## Hard "do not break" items

If any one of these fails, the project fails:

1. App must run without errors on a fresh laptop (no `~/.cache` magic)
2. ≥ 15 participants — no exceptions
3. Statistical analysis must be reproducible from `master_data.csv`
4. Thesis chapter must be in supervisor's hands ≥ 5 days before submission
