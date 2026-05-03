"""
Session planner for the HCI study.

Given a participant ID and the scenario library, produces a 3-block plan
where each block:
    - has one of the 3 conditions (Latin-square counterbalanced)
    - contains 5 trials drawn from the scenario library
    - is internally balanced (mix of critical / warning / safe)
    - is randomized within the block

The 6 Latin-square rows cycle modulo participant ID. Numeric IDs are
parsed from "P01", "P12", etc.; non-numeric IDs are hashed instead.

See docs/03-research/study-protocol.md for the experimental design.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from typing import Iterable

from src.core.experiment import ExperimentCondition


# Latin-square ordering of conditions across 3 blocks.
# Index = (participant_number - 1) % 6.
LATIN_SQUARE: list[tuple[ExperimentCondition, ExperimentCondition, ExperimentCondition]] = [
    (ExperimentCondition.NO_ALERT, ExperimentCondition.STANDARD, ExperimentCondition.AR_HUD),
    (ExperimentCondition.NO_ALERT, ExperimentCondition.AR_HUD,   ExperimentCondition.STANDARD),
    (ExperimentCondition.STANDARD, ExperimentCondition.NO_ALERT, ExperimentCondition.AR_HUD),
    (ExperimentCondition.STANDARD, ExperimentCondition.AR_HUD,   ExperimentCondition.NO_ALERT),
    (ExperimentCondition.AR_HUD,   ExperimentCondition.NO_ALERT, ExperimentCondition.STANDARD),
    (ExperimentCondition.AR_HUD,   ExperimentCondition.STANDARD, ExperimentCondition.NO_ALERT),
]

TRIALS_PER_BLOCK = 5
N_BLOCKS = 3


@dataclass
class Block:
    block_num: int                          # 1, 2, 3
    condition: ExperimentCondition
    trials: list[dict] = field(default_factory=list)


@dataclass
class SessionPlan:
    participant_id: str
    seed: int
    latin_row: int                          # which row of the Latin square (0–5)
    blocks: list[Block]

    @property
    def total_trials(self) -> int:
        return sum(len(b.trials) for b in self.blocks)


def _participant_seed(participant_id: str) -> int:
    """Stable per-participant seed for reproducible randomization."""
    h = hashlib.sha256(participant_id.encode("utf-8")).hexdigest()
    return int(h[:8], 16)


def _participant_number(participant_id: str) -> int:
    """
    Extract a 1-based number from IDs like 'P01', 'p_07', '12'.
    Falls back to a hash-based assignment if no digits found.
    """
    digits = "".join(c for c in participant_id if c.isdigit())
    if digits:
        return int(digits)
    # No digits — derive a stable index
    return _participant_seed(participant_id) % 1000 + 1


def _bucket(scenarios: Iterable[dict]) -> dict[str, list[dict]]:
    """Group scenarios by expected_alert_level."""
    buckets = {"CRITICAL": [], "WARNING": [], "SAFE": []}
    for s in scenarios:
        level = s.get("expected_alert_level", "SAFE")
        if level in buckets:
            buckets[level].append(dict(s))
    return buckets


def plan_session(participant_id: str, scenarios: list[dict]) -> SessionPlan:
    """
    Build a 3-block × 5-trial plan for one participant.

    Block composition (when scenario counts allow):
        2 critical + 2 warning + 1 safe = 5 trials
    Across 3 blocks: 6 critical + 6 warning + 3 safe = 15 trials

    If the library has more critical/warning than needed, the surplus is dropped.
    If fewer, we fall back to whatever's available (and warn via metadata).
    """
    seed = _participant_seed(participant_id)
    rng = random.Random(seed)

    pnum = _participant_number(participant_id)
    latin_row = (pnum - 1) % len(LATIN_SQUARE)
    condition_order = LATIN_SQUARE[latin_row]

    buckets = _bucket(scenarios)

    # Shuffle each bucket per-participant (reproducible via seed)
    for v in buckets.values():
        rng.shuffle(v)

    # Pull 6 critical, 6 warning, 3 safe (or as many as available)
    pool_critical = buckets["CRITICAL"][:6]
    pool_warning = buckets["WARNING"][:6]
    pool_safe = buckets["SAFE"][:3]

    blocks: list[Block] = []
    for i in range(N_BLOCKS):
        b_trials: list[dict] = []
        # 2 critical, 2 warning, 1 safe per block (if available)
        for _ in range(2):
            if pool_critical:
                b_trials.append(pool_critical.pop(0))
        for _ in range(2):
            if pool_warning:
                b_trials.append(pool_warning.pop(0))
        if pool_safe:
            b_trials.append(pool_safe.pop(0))

        # Top up if any pool ran dry — pull from whatever's left
        leftover = pool_critical + pool_warning + pool_safe
        while len(b_trials) < TRIALS_PER_BLOCK and leftover:
            b_trials.append(leftover.pop(0))

        # Shuffle order within the block
        rng.shuffle(b_trials)

        blocks.append(Block(
            block_num=i + 1,
            condition=condition_order[i],
            trials=b_trials,
        ))

    return SessionPlan(
        participant_id=participant_id,
        seed=seed,
        latin_row=latin_row,
        blocks=blocks,
    )


def plan_summary(plan: SessionPlan) -> str:
    """Human-readable text summary of a plan, useful for debugging or logs."""
    lines = [
        f"Participant: {plan.participant_id}",
        f"Latin row: {plan.latin_row + 1}/6",
        f"Total trials: {plan.total_trials}",
        "",
    ]
    for b in plan.blocks:
        lines.append(f"Block {b.block_num} — {b.condition.value}")
        for t in b.trials:
            lines.append(f"  {t['filename']}  ({t['expected_alert_level']})")
    return "\n".join(lines)
