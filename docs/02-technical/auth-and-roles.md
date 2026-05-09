# Authentication & User Roles

## Why two roles

The thesis study has two completely different user types in front of the
DepthGuard app:

- **Driver** — the *participant* in the HCI experiment. Their job is to
  watch the dashcam footage and press BRAKE when they perceive a hazard.
  Every additional widget on screen is a distraction that risks polluting
  the reaction-time data, so the driver UI is intentionally stripped down.
- **Admin** — the *researcher* (me / supervisor) running the session.
  Needs the full UI: model selector, condition switcher, simulation-mode
  selector, session controls, performance dashboard, and reaction-log
  analysis.

Splitting the two roles also gives us a clean place to talk about *who
sees what* in the thesis chapter when describing the system design.

## Files

| File | Purpose |
|---|---|
| [`src/auth/users.py`](../../src/auth/users.py) | `User` / `Role` types, mock user store, `authenticate()` |
| [`src/auth/login_dialog.py`](../../src/auth/login_dialog.py) | `LoginDialog` — Qt sign-in screen |
| [`main.py`](../../main.py) | Login → MainWindow loop (re-shows login on log-out) |
| [`src/ui/main_window.py`](../../src/ui/main_window.py) | `MainWindow(user=...)` — applies role-based visibility |

## Mock accounts (thesis lab only)

Defined in [`src/auth/users.py`](../../src/auth/users.py). These are
**mock** credentials — passwords are SHA-256 hashed but unsalted, and the
list is in-process. Suitable for a closed lab demo, **not** for any
deployment outside the controlled study environment.

| Username | Password | Role | Notes |
|---|---|---|---|
| `admin` | `admin123` | Admin | Default researcher login |
| `supervisor` | `super123` | Admin | For the supervisor's walkthrough |
| `driver` | `driver123` | Driver | Generic demo driver (use for screencasts) |
| `p01` | `p01` | Driver | Participant 01 — extend pattern for new participants |
| `p02` | `p02` | Driver | Participant 02 |
| `p03` | `p03` | Driver | Participant 03 |

Adding a new participant: edit the `_USERS` dict in
[`src/auth/users.py`](../../src/auth/users.py) and add a row keyed by the
participant ID (e.g. `"p04": (_hash("p04"), Role.DRIVER, "Participant 04")`).

The login screen also surfaces three of these credentials in a "Demo
accounts" panel so anyone running the app for the first time can sign in
without consulting the docs.

## What each role sees

### Driver UI (minimal — participant-facing)

```
┌──────────────────────────────────────────────────────────┐
│ DEPTHGUARD · DRIVER SAFETY SYSTEM     [DRIVER · P01] [LOG OUT] │
├──────────────────────────────────────────────────────────┤
│ ┌──────────────┐  ┌──────────────┐                       │
│ │ Driver view  │  │ Depth map    │                       │
│ └──────────────┘  └──────────────┘                       │
│ ┌──────────────────────────────────────────────────────┐ │
│ │                  ALERT STATUS BAR                    │ │
│ └──────────────────────────────────────────────────────┘ │
│ [── progress slider ──]                  00:00 / 01:23   │
│ [Load Video] [Play] [Stop] [Loop]              [BRAKE ⎵] │
└──────────────────────────────────────────────────────────┘
```

**Visible:** video panels, alert strip, progress bar, transport buttons,
BRAKE button, header with logout.

**Hidden:** model selector, simulation-mode selector, condition selector
(NO ALERT / STANDARD / AR HUD), participant-ID input, Start Session
button, Load Playlist button, Save Session button, the Performance tab,
and the Analysis tab.

### Admin UI (full — researcher-facing)

Identical to the pre-login UI: three tabs (Simulation / Performance /
Analysis) with all session-management and research controls visible. The
header gains an `[ADMIN · Researcher] [LOG OUT]` pill.

## How role-gating is implemented

`MainWindow.__init__(user=...)` accepts the authenticated `User`. After
`setup_ui()` runs and creates *all* widgets, `_apply_role_visibility()`
hides the admin-only ones when the role is `DRIVER`:

```python
# src/ui/main_window.py
def _apply_role_visibility(self):
    if self.user.is_admin:
        return
    for w in (self.condition_frame, self._sim_vsep,
              self.lbl_model, self.cb_model,
              self.lbl_mode, self.cb_mode,
              self._session_row):
        w.setVisible(False)
    # Drop researcher-only tabs (highest index first)
    self.tabs.removeTab(2)  # ANALYSIS
    self.tabs.removeTab(1)  # PERFORMANCE
    self.monitor_timer.stop()
```

This "build everything, then hide" approach keeps the production code
path identical — no `if admin:` branches scattered across UI setup, no
risk of a driver's data logger being a different object than an admin's.

## Login → MainWindow → logout loop

[`main.py`](../../main.py):

```python
while True:
    login = LoginDialog()
    if login.exec_() != QDialog.Accepted:
        return 0                          # user cancelled
    window = MainWindow(user=login.user)
    window.show()
    app.exec_()
    if not window._logout_requested:
        return 0                          # window closed = exit
    # otherwise loop back to the login screen
```

The "log out" button in the header sets `_logout_requested = True` and
closes the window, which drops out of `app.exec_()` and re-shows the
login dialog. Closing the window via the OS chrome (X button) exits the
app normally.

## Threat model

This auth layer is **mock by design**. It exists so that:

1. The thesis demo can show two distinct user experiences without two
   separate launchers.
2. Reviewers can grasp at a glance who sees what in the system.
3. Participants can be given a simple `pXX / pXX` credential card with no
   risk of stumbling into the researcher dashboard mid-experiment.

It does **not** defend against:

- An adversary with code access — the mock user list is right there in
  the source tree.
- Password cracking — SHA-256 with no salt is fast to brute-force.
- Credential reuse — passwords are stored only once in the source dict,
  but anyone reading the repo learns them all.

If DepthGuard ever leaves the lab, replace the mock store with a real
identity provider (or at minimum: bcrypt/argon2 + per-user salt + a
credential file outside the repo).

## Extending the system

- **Add a participant:** add a row to `_USERS` in
  [`src/auth/users.py`](../../src/auth/users.py).
- **Add a new role:** extend the `Role` enum, then update
  `_apply_role_visibility` with whatever widgets that role should hide.
- **Hide a new widget per role:** make sure it's a `self.<attr>` (not a
  local variable) inside `setup_sim_tab` / `setup_monitor_tab` /
  `setup_analysis_tab`, then add it to the tuple in
  `_apply_role_visibility`.

## Related thesis content

For the *Implementation* chapter, the relevant sub-section is
"User-facing modes". Two screenshots — one of the driver UI, one of the
admin UI — make the role split immediately legible. Capture them with
the `driver` and `admin` demo accounts respectively.
