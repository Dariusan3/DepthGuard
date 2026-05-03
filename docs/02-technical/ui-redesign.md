# UI Redesign

## Done (2026-04-27)

Applied the [Frontend Design](.claude/frontend/Frontend%20design.md) principles:

- HUD/cockpit dark theme: deep blue-black (`#06080F`) + electric mint accent (`#00E5A0`)
- Branded header bar with glowing logo + live FPS
- Refined typography: uppercase tab navigation, letterspaced labels, font hierarchy
- Three-tab structure: Simulation / Performance / Analysis
- Status bar with pulsing flash on CRITICAL alerts
- BRAKE button with red glow + flash feedback on press
- Metric cards (replaces stacked labels) on Performance + Analysis tabs

Files: `src/ui/main_window.py` (single file, ~950 lines).

---

## Planned (Week 1–2)

For participant readiness:

### Keyboard shortcuts (essential for HCI study)
- `SPACE` → BRAKE press (don't make participants click — they'll hesitate)
- `ESC` → Pause
- `ENTER` → Next scenario (during playlist mode)
- `F11` → Fullscreen toggle

Implementation: `QShortcut` or `keyPressEvent` override in `MainWindow`.

### Scenario playlist mode
- Replace single-video `Load Video` button with `Load Playlist` (loads `scenarios.csv`)
- Shows "Trial X of Y" counter
- Auto-advance with 2-s blank screen between trials
- Disables manual scrubbing during a trial (can't bias reaction times)

### Participant mode
- Hide the developer chrome (model selector, mode dropdown, performance tab) when running a participant
- One toggle: `Researcher / Participant` mode
- In Participant mode: only the simulation tab visible, fullscreen by default

### Larger BRAKE target
- Currently a button in the controls bar
- For real participants: full-bottom strip across the screen, easier to hit when stressed

---

## Why these matter for the HCI study

| Change | Why |
|---|---|
| Spacebar = brake | Mouse clicks add latency variance unrelated to perception. Keyboard is what driving sims use. |
| Auto-advance | Removes researcher bias (clicking "next" too soon/late) |
| Scenario playlist | Counterbalancing requires a reproducible trial order |
| Participant mode | Researcher-visible info (FPS, model name) might bias the participant |

---

## Out of scope (do NOT do)

- Custom font installation (uses system fonts only; participants have whatever is on the lab Mac)
- Animations beyond the existing flash (CPU budget needs to go to depth inference)
- Theming options (one polished theme is better than three half-baked ones)
