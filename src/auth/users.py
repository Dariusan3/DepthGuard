"""
Mock user store for DepthGuard.

The thesis study has two roles with very different needs:

- DRIVER  — the participant in the HCI experiment. Sees a stripped-down
            cockpit-style view: video, alert status, BRAKE button. No
            researcher controls (no model selector, no condition switcher,
            no performance/analysis tabs).
- ADMIN   — the researcher running the session. Sees the full UI including
            model/condition/mode selectors, session controls, and the
            Performance and Analysis tabs.

This is a *mock* authentication layer suitable for a closed lab study —
credentials live in-process, passwords are hashed only with SHA-256 (no
salt, no key-stretching). Do not reuse this for any deployment outside the
controlled study environment.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Role(str, Enum):
    DRIVER = "driver"
    ADMIN = "admin"


@dataclass(frozen=True)
class User:
    username: str
    role: Role
    display_name: str

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    @property
    def is_driver(self) -> bool:
        return self.role == Role.DRIVER


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# username -> (password_hash, role, display_name)
# Demo accounts for the thesis study. Add more participant logins here as
# needed; the username doubles as the participant ID for driver accounts.
_USERS: dict[str, tuple[str, Role, str]] = {
    "admin":    (_hash("admin123"),    Role.ADMIN,  "Researcher"),
    "supervisor": (_hash("super123"),  Role.ADMIN,  "Supervisor"),
    "driver":   (_hash("driver123"),   Role.DRIVER, "Demo Driver"),
    "p01":      (_hash("p01"),         Role.DRIVER, "Participant 01"),
    "p02":      (_hash("p02"),         Role.DRIVER, "Participant 02"),
    "p03":      (_hash("p03"),         Role.DRIVER, "Participant 03"),
}


def authenticate(username: str, password: str) -> Optional[User]:
    """Return a User on success, None on failure. Username is case-insensitive."""
    if not username or not password:
        return None
    key = username.strip().lower()
    record = _USERS.get(key)
    if record is None:
        return None
    pw_hash, role, display = record
    if _hash(password) != pw_hash:
        return None
    return User(username=key, role=role, display_name=display)


def list_demo_credentials() -> list[tuple[str, str, Role]]:
    """For the login screen's 'demo accounts' hint panel only.

    Returns (username, password, role) tuples. Passwords are surfaced here
    *only* because this is a mock store for a thesis demo — never do this
    in production code.
    """
    return [
        ("admin",    "admin123",  Role.ADMIN),
        ("driver",   "driver123", Role.DRIVER),
        ("p01",      "p01",       Role.DRIVER),
    ]
