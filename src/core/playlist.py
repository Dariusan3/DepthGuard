"""
Playlist manager for HCI study sessions.

Reads data/scenarios.csv, optionally shuffles trial order, and yields
one scenario at a time. Each scenario carries the metadata needed to
score reaction times (event_start_ms, expected_alert_level).
"""

import random
from pathlib import Path

import pandas as pd


class PlaylistManager:
    """Walks through trial scenarios in order or shuffled."""

    def __init__(self, csv_path: str | None = None, base_dir: str = "data/scenarios",
                 shuffle: bool = True, seed: int | None = None,
                 scenarios: list[dict] | None = None):
        """
        Either pass csv_path (read from file) OR scenarios (pre-built list).
        """
        if scenarios is not None:
            self.scenarios = [dict(s) for s in scenarios]
        elif csv_path is not None:
            df = pd.read_csv(csv_path)
            self.scenarios = df.to_dict("records")
        else:
            raise ValueError("Provide csv_path or scenarios=")

        # Resolve full file paths if not already set, and default the projection
        # column for legacy CSVs that don't have one yet.
        base = Path(base_dir)
        for s in self.scenarios:
            if "full_path" not in s or not s["full_path"]:
                s["full_path"] = str(base / s["filename"])
            # projection: "flat" (default) or "equirectangular" (360°)
            proj = s.get("projection")
            if not proj or (isinstance(proj, float) and proj != proj):  # NaN check
                s["projection"] = "flat"

        if shuffle:
            rng = random.Random(seed)
            rng.shuffle(self.scenarios)

        self.current_idx = -1

    @classmethod
    def from_scenarios(cls, scenarios: list[dict], base_dir: str = "data/scenarios"):
        """Build a playlist from a pre-selected scenario list (e.g. one block of a session plan)."""
        return cls(csv_path=None, base_dir=base_dir, shuffle=False, scenarios=scenarios)

    @property
    def total(self) -> int:
        return len(self.scenarios)

    @property
    def trial_num(self) -> int:
        """1-based; 0 if not started."""
        return self.current_idx + 1 if self.current_idx >= 0 else 0

    @property
    def current(self) -> dict | None:
        if 0 <= self.current_idx < len(self.scenarios):
            return self.scenarios[self.current_idx]
        return None

    def has_next(self) -> bool:
        return self.current_idx + 1 < len(self.scenarios)

    def next(self) -> dict | None:
        if not self.has_next():
            return None
        self.current_idx += 1
        return self.scenarios[self.current_idx]

    def reset(self):
        self.current_idx = -1
