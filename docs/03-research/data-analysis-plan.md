# Data Analysis Plan

**Pre-registered analyses** — decided before running the study to avoid p-hacking.

---

## Data preparation

1. Read all session CSVs from `logs/` → master DataFrame.
2. Match each row to scenario metadata (`data/scenarios/scenarios.csv`) by trial ID.
3. Compute reaction time = `(brake_timestamp - event_start_timestamp)` per trial.
4. Tag each trial as `hit`, `miss`, or `false_alarm`.
5. Drop participants with > 50% missing trials or technical errors (note in thesis).

---

## Primary analysis

### H1, H2 — reaction time

For trials where the participant correctly braked on a critical/warning event:

- **Test:** Repeated-measures ANOVA with condition (3 levels) as within-subject factor.
- **Post-hoc:** Bonferroni-corrected pairwise comparisons.
- **Effect size:** Cohen's d for each pair.
- **Plot:** Box plot of RT by condition with individual participant lines overlaid.

Fallback if RT distributions are non-normal (Shapiro-Wilk p < 0.05): Friedman test + Wilcoxon signed-rank post-hocs.

### H3 — workload

NASA-TLX raw score (sum of 6 sub-scales, 0–600):

- **Test:** Same RM-ANOVA / Friedman as above.
- **Plot:** Bar chart with error bars (95% CI).

---

## Secondary analyses

### Detection rate (hits / hits+misses)

- **Test:** McNemar's test pairwise across conditions (binary outcome per trial).
- **Plot:** Stacked bar — hits / misses / false alarms per condition.

### Usability (SUS)

- **Test:** One-sample t-test against the standard SUS benchmark (68 = average).
- **Report:** Mean SUS score with 95% CI; classification per Bangor et al. (acceptable / good / excellent).

### Demographics moderators

- Correlation between driving experience (years) and reaction time
- Independent t-test: prior-dashcam-use (Y/N) on RT

---

## Significance threshold

α = 0.05 for primary analyses. No correction across H1/H2/H3 since each tests a distinct prediction.

---

## Reporting

For the thesis chapter:

- Descriptive stats table: M, SD, N per condition
- ANOVA table: F, df, p, partial η²
- Post-hoc table: pairwise differences with 95% CI
- One figure per primary analysis
- Free-text feedback synthesized into 3–5 themes

---

## Tools

Python with:
- `pandas` for data wrangling
- `scipy.stats` for inferential tests
- `pingouin` for repeated-measures ANOVA (cleaner output than statsmodels)
- `matplotlib` + `seaborn` for plots

Analysis script lives at `analysis/run_analysis.py` (to be created in week 7).

---

## What gets archived

`results/` folder, structure:

```
results/
├── master_data.csv          # All trials, all participants, anonymized
├── tables/
│   ├── descriptives.csv
│   ├── rm_anova_rt.csv
│   └── posthoc_rt.csv
├── figures/
│   ├── fig01_rt_by_condition.png
│   ├── fig02_workload.png
│   ├── fig03_detection_rate.png
│   └── fig04_sus_distribution.png
└── analysis_log.txt         # Decisions, exclusions, deviations from this plan
```
