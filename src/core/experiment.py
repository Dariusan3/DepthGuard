"""
HCI experiment conditions for the DepthGuard study.

Three within-subject conditions (see docs/03-research/study-protocol.md):
    1. NO_ALERT  — raw video only; no audio, no visual alert, no AR overlay.
    2. STANDARD  — alert status bar + audio beeps + threat bounding box.
    3. AR_HUD    — AR overlay (translucent threat highlight, BRAKE strip)
                   + audio beeps. The standard alert bar is hidden in this
                   condition; the AR view is the only visual cue.

Each condition exposes flags consumed by the rest of the pipeline.
"""

from dataclasses import dataclass
from enum import Enum


class ExperimentCondition(str, Enum):
    NO_ALERT = "NO_ALERT"
    STANDARD = "STANDARD"
    AR_HUD = "AR_HUD"


@dataclass(frozen=True)
class ConditionFlags:
    """Pipeline flags derived from the active condition."""
    audio_enabled: bool
    alert_bar_visible: bool       # the big "CRITICAL — BRAKE NOW" status bar
    threat_box_visible: bool      # color-coded box on driver view
    ar_overlay_enabled: bool      # AR HUD compositing


def flags_for(condition: ExperimentCondition) -> ConditionFlags:
    if condition == ExperimentCondition.NO_ALERT:
        return ConditionFlags(
            audio_enabled=False,
            alert_bar_visible=False,
            threat_box_visible=False,
            ar_overlay_enabled=False,
        )
    if condition == ExperimentCondition.STANDARD:
        return ConditionFlags(
            audio_enabled=True,
            alert_bar_visible=True,
            threat_box_visible=True,
            ar_overlay_enabled=False,
        )
    if condition == ExperimentCondition.AR_HUD:
        return ConditionFlags(
            audio_enabled=True,
            alert_bar_visible=False,    # AR view replaces the standalone bar
            threat_box_visible=False,   # AR overlay paints its own
            ar_overlay_enabled=True,
        )
    raise ValueError(f"Unknown condition: {condition}")


def display_name(condition: ExperimentCondition) -> str:
    return {
        ExperimentCondition.NO_ALERT: "No Alert",
        ExperimentCondition.STANDARD: "Standard",
        ExperimentCondition.AR_HUD: "AR HUD",
    }[condition]
