"""
Headless smoke test for the DepthGuard data pipeline.

Walks the playlist, runs MockModel inference on each clip, simulates a few
brake presses, and verifies the CSV/report files get written correctly.

Run:
    python scripts/smoke_test.py
"""

import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np

# Make src importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.alert_system import SafetyAlertSystem
from src.core.data_logger import DataLogger
from src.core.playlist import PlaylistManager
from src.models.mock_model import MockModel


def main():
    repo_root = Path(__file__).resolve().parent.parent
    os.chdir(repo_root)

    csv_path = "data/scenarios.csv"
    if not os.path.exists(csv_path):
        print(f"FAIL: {csv_path} not found")
        return 1

    print(f"Loading playlist from {csv_path}")
    playlist = PlaylistManager(csv_path, base_dir="data/scenarios", shuffle=False)
    print(f"  {playlist.total} scenarios")

    model = MockModel()
    model.latency = 0.001  # speed up the test (skip the 33ms sleep)
    alert_system = SafetyAlertSystem()
    logger = DataLogger(log_dir="logs")

    # Override session_id so we can find the test run easily
    logger.session_id = "smoke_test_" + time.strftime("%Y%m%d_%H%M%S")
    logger.log_file = os.path.join(logger.log_dir, f"session_{logger.session_id}.csv")
    logger.reaction_file = os.path.join(logger.log_dir, f"reactions_{logger.session_id}.csv")
    logger.report_file = os.path.join(logger.log_dir, f"report_{logger.session_id}.txt")

    issues = []
    total_frames_processed = 0
    total_alerts = {"SAFE": 0, "CAUTION": 0, "WARNING": 0, "CRITICAL": 0}

    print("\nWalking through scenarios...")
    while playlist.has_next():
        scenario = playlist.next()
        path = scenario["full_path"]
        if not os.path.exists(path):
            issues.append(f"missing file: {path}")
            continue

        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            issues.append(f"cannot open: {path}")
            continue

        trial_start = time.time()
        n_frames = 0
        # Sample one frame in 5 to keep this test fast (~200 ms per clip on Mock)
        skip = 5

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            n_frames += 1
            if n_frames % skip != 0:
                continue
            depth = model.inference(frame)
            alert = alert_system.process_depth(depth)
            total_alerts[alert["level"]] += 1

            if n_frames % 10 == 0:
                logger.log_frame(n_frames, alert["level"], alert["min_depth"])

        cap.release()
        total_frames_processed += n_frames

        # Simulate one brake press near the expected event for non-SAFE trials
        if scenario["expected_alert_level"] != "SAFE":
            # Simulate a 600ms reaction
            simulated_press_time = trial_start + (
                int(scenario["event_start_ms"]) / 1000.0
            ) + 0.6
            # Pretend it's "now" by pinning trial_start_time slightly in the past
            fake_trial_start = simulated_press_time - (
                int(scenario["event_start_ms"]) / 1000.0
            ) - 0.6
            logger.log_reaction(
                frame_num=n_frames - 1,
                alert_level="CRITICAL",
                trial=scenario,
                trial_start_time=fake_trial_start,
            )
        else:
            # No press on safe trial — that's a TN (true negative), no log entry
            pass

        print(
            f"  trial {playlist.trial_num:2d}/{playlist.total}: "
            f"{scenario['filename']:32s}  {n_frames} frames"
        )

    print("\nWriting session files...")
    logger.save_session(participant_id="SMOKE_TEST")

    # Verify outputs
    print("\nVerifying outputs:")
    for f in [logger.log_file, logger.reaction_file, logger.report_file]:
        if os.path.exists(f):
            size = os.path.getsize(f)
            print(f"  ✓ {f}  ({size} bytes)")
        else:
            issues.append(f"missing output: {f}")

    print(f"\nFrames processed: {total_frames_processed}")
    print(f"Alert distribution: {total_alerts}")
    print(f"Reactions logged: {logger.total_reactions}")
    print(f"Hits: {logger.correct_reactions}")
    print(f"False alarms: {logger.false_alarms}")
    print(f"Mean RT: {sum(logger.reaction_times) / len(logger.reaction_times):.0f} ms"
          if logger.reaction_times else "Mean RT: n/a (no hits)")

    if issues:
        print("\nISSUES:")
        for i in issues:
            print(f"  - {i}")
        return 1

    print("\n✓ Smoke test passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
