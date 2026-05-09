"""
Performance profiler for the depth-estimation pipeline.

Runs each available model over a representative clip (or all scenarios) and
measures FPS, inference latency, and memory usage. Writes a per-frame CSV plus
a summary table to results/.

Use this to:
    - Benchmark Mock vs MiDaS Small vs DepthPro
    - Document the desktop baseline for the thesis
    - Validate the "≥15 FPS / ≤4 GB" target by simulating Jetson constraints

Usage:
    python scripts/profile_performance.py                    # all available models, default clip
    python scripts/profile_performance.py --models mock midas
    python scripts/profile_performance.py --clip data/scenarios/04_brake_lights_critical.mp4
    python scripts/profile_performance.py --duration 30      # cap measurement window in seconds
"""

import argparse
import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import psutil

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.alert_system import SafetyAlertSystem
from src.models.mock_model import MockModel


def load_model(name):
    """Lazy-load a model by name. Returns the model or None if unavailable."""
    name = name.lower()
    if name == "mock":
        m = MockModel()
        m.latency = 0.0  # skip the simulated delay for honest profiling
        return m
    if name == "midas":
        try:
            from src.models.midas_model import MiDaSModel
            return MiDaSModel(variant="small")
        except Exception as e:
            print(f"  [skip] midas: {e}")
            return None
    if name == "depthpro":
        try:
            from src.models.depth_pro_model import DepthProModel
            return DepthProModel()
        except Exception as e:
            print(f"  [skip] depthpro: {e}")
            return None
    print(f"  [skip] unknown model: {name}")
    return None


def profile_model(model_name, model, clip_path, max_duration_s):
    """Run the model over a clip and collect per-frame metrics."""
    cap = cv2.VideoCapture(clip_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open clip: {clip_path}")

    alert_system = SafetyAlertSystem()
    proc = psutil.Process()

    rows = []
    t_session_start = time.time()
    frame_idx = 0
    last_t = time.time()
    last_progress_t = t_session_start

    while True:
        if time.time() - t_session_start > max_duration_s:
            break
        ret, frame = cap.read()
        if not ret:
            break
        frame_idx += 1

        # Inference latency (model only)
        t0 = time.time()
        depth = model.inference(frame)
        infer_ms = (time.time() - t0) * 1000

        # Alert classification
        alert = alert_system.process_depth(depth)

        # End-to-end frame time + FPS
        now = time.time()
        frame_ms = (now - last_t) * 1000
        last_t = now
        fps = 1000.0 / frame_ms if frame_ms > 0 else 0

        # Memory (resident set size in MB)
        mem_mb = proc.memory_info().rss / (1024 * 1024)

        rows.append({
            "frame": frame_idx,
            "inference_ms": round(infer_ms, 2),
            "frame_ms": round(frame_ms, 2),
            "fps": round(fps, 2),
            "memory_mb": round(mem_mb, 1),
            "alert_level": alert["level"],
        })

        # Periodic progress so the user knows it's alive
        if now - last_progress_t >= 3.0:
            elapsed = now - t_session_start
            avg_fps = frame_idx / elapsed if elapsed > 0 else 0
            print(f"    ...{frame_idx} frames, {elapsed:.0f}s elapsed, "
                  f"{avg_fps:.1f} FPS, {mem_mb:.0f} MB", flush=True)
            last_progress_t = now

    cap.release()
    return pd.DataFrame(rows)


def summarize(df, model_name):
    """Compute summary stats — drop the first 5 frames (warm-up)."""
    if len(df) <= 5:
        return None
    warm = df.iloc[5:]
    return {
        "model": model_name,
        "frames": len(warm),
        "mean_fps": round(warm["fps"].mean(), 2),
        "p95_fps": round(warm["fps"].quantile(0.05), 2),  # 5th pct of fps = worst case
        "mean_latency_ms": round(warm["inference_ms"].mean(), 2),
        "p95_latency_ms": round(warm["inference_ms"].quantile(0.95), 2),
        "peak_memory_mb": round(warm["memory_mb"].max(), 1),
        "delta_memory_mb": round(warm["memory_mb"].max() - warm["memory_mb"].iloc[0], 1),
        "meets_15fps": warm["fps"].mean() >= 15.0,
        "meets_4gb": warm["memory_mb"].max() <= 4096,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", default=["mock", "midas", "depthpro"],
                        help="Models to profile")
    parser.add_argument("--clip", default="data/scenarios/04_brake_lights_critical.mp4",
                        help="Path to video clip")
    parser.add_argument("--duration", type=float, default=20.0,
                        help="Max profiling duration per model (seconds)")
    parser.add_argument("--output", default="results/perf",
                        help="Output directory for CSVs + summary")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    os.chdir(repo_root)

    if not os.path.exists(args.clip):
        print(f"Clip not found: {args.clip}")
        sys.exit(1)

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Profiling on: {args.clip}")
    print(f"Max duration per model: {args.duration} s\n")

    summaries = []
    for name in args.models:
        print(f"── {name} ──")
        model = load_model(name)
        if model is None:
            continue
        df = profile_model(name, model, args.clip, args.duration)
        per_frame_path = out_dir / f"per_frame_{name}.csv"
        df.to_csv(per_frame_path, index=False)
        summary = summarize(df, name)
        if summary:
            summaries.append(summary)
            print(f"  frames: {summary['frames']}  "
                  f"FPS: {summary['mean_fps']} (p5={summary['p95_fps']})  "
                  f"latency: {summary['mean_latency_ms']} ms  "
                  f"mem: {summary['peak_memory_mb']} MB")
            print(f"  ≥15 FPS: {'✓' if summary['meets_15fps'] else '✗'}  "
                  f"≤4 GB: {'✓' if summary['meets_4gb'] else '✗'}")
        print(f"  saved {per_frame_path}\n")

        # Free memory before next model
        del model

    if summaries:
        summary_df = pd.DataFrame(summaries)
        summary_path = out_dir / "summary.csv"
        summary_df.to_csv(summary_path, index=False)
        print(f"\n=== Summary ({summary_path}) ===")
        print(summary_df.to_string(index=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())
