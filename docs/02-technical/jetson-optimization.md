# Jetson Optimization

Target from the traineeship contract: **≥ 15 FPS, ≤ 4 GB GPU memory** on Jetson Nano (or Xavier).

---

## Reality check

DepthPro is a 1B-parameter ViT-Large model with 1.8 GB of weights. Running it natively on:
- **MacBook Air (CPU only):** ~1 FPS, exhausts RAM under load
- **Jetson Nano (4 GB RAM, Maxwell GPU):** not feasible without aggressive quantization
- **Desktop with discrete NVIDIA GPU:** 0.3 s/frame (~3 FPS) — still below 15 FPS

DepthPro is a **research backbone**, not a deployment model. That's exactly why your thesis trains a smaller distilled model on top of it.

## Decision: MiDaS Small everywhere user-facing

**HCI study on the user's MacBook Air:** MiDaS Small (~30 MB, ~10–15 FPS on CPU). The participant experience needs smooth playback to measure reaction times reliably. DepthPro freezes the laptop and would invalidate timing data.

**Jetson deployment demo:** MiDaS Small. Same model, same code, just runs on the embedded board. Already integrated in `src/models/midas_model.py`.

**Thesis benchmarks comparing models:** All four (Mock / MiDaS Small / DepthPro / your trained model) — but DepthPro and your trained model run on Colab or a borrowed GPU, *not* in DepthGuard live. Benchmark numbers go into a comparison table; live demos use MiDaS.

**Self-supervised training:** Done in your `ml-depth-pro` fork on a server with a real GPU. DepthGuard never trains.

This is consistent with deployment practice in the field: train heavy, deploy light.

---

## Baseline measurements

Captured via `scripts/profile_performance.py`. Re-run any time with:

```bash
python scripts/profile_performance.py --models mock midas depthpro --duration 30
# Output: results/perf/per_frame_<model>.csv  +  results/perf/summary.csv
```

The script measures inference latency, frame time, FPS, and resident memory
for each model on a representative clip (default: `04_brake_lights_critical.mp4`).
First 5 frames are dropped as warm-up.

### Desktop baseline (MacBook Air, Apple M-series CPU only)

Captured 2026-05-03. **Update this table after each profiling run.**

| Model | Frames | Mean FPS | p5 FPS (worst) | Mean latency (ms) | Peak mem (MB) | ≥15 FPS | ≤4 GB |
|---|---|---|---|---|---|---|---|
| MockModel    | 234 | 62.7 | 56.6 | 14.8 | 394 | ✓ | ✓ |
| MiDaS Small  | TBD | TBD  | TBD  | TBD  | TBD | TBD | TBD |
| DepthPro     | TBD | TBD  | TBD  | TBD  | TBD | TBD | TBD |

MockModel doesn't run a real network — its row reports the **pipeline overhead**
(video decode + alert system + logger). Real models add their inference cost on top.

### Jetson Nano simulation

Same models, with playback FPS capped at 15 (Mode dropdown → "Jetson Nano Simulation"):

| Model | Sustained FPS | Latency (ms) | Memory (MB) | Pass |
|---|---|---|---|---|
| MockModel    | TBD | TBD | TBD | TBD |
| MiDaS Small  | TBD | TBD | TBD | TBD |
| DepthPro     | TBD | TBD | TBD | TBD |

### Interpretation

(Fill in once both tables are populated.)

- Which model meets the ≥15 FPS / ≤4 GB target?
- What's the trade-off between accuracy (visual depth quality) and speed?
- Which configuration is recommended for the HCI study? (Already decided: MiDaS Small.)

---

## Jetson access — confirmed: simulate

**Supervisor confirmed (2026-05-01):** no physical Jetson is available through the lab. Simulate the constraints on desktop and document the methodology — this is the agreed-upon path, not a workaround.

How to simulate:
- Cap the playback FPS at 15 in `update_simulation_mode` (already done — pick "Jetson Nano Simulation (15 FPS)" in the Mode dropdown)
- Track resident memory via `psutil.Process().memory_info().rss` — already captured by `scripts/profile_performance.py`
- Run `scripts/profile_performance.py --models mock midas` to produce the baseline numbers for the thesis

The thesis writeup should phrase this as:
> "We evaluated deployment feasibility under simulated Jetson Nano constraints (15 FPS playback cap, 4 GB memory budget) on a MacBook Air baseline. Real hardware was not available; this approach captures the algorithmic constraints (memory + throughput) without conflating them with platform-specific kernel performance, which is left to future work."

---

## Optimization techniques (in order of effort)

### 1. FP16 (half precision) — easy
```python
model = model.half()
input_tensor = input_tensor.half()
```
Roughly 2× speedup, halves memory. Free win if accuracy doesn't degrade.

### 2. ONNX export
```python
torch.onnx.export(model, dummy_input, "depth_pro.onnx", opset_version=17)
```
Lets you switch runtime to ONNX Runtime or TensorRT.

### 3. TensorRT INT8 quantization
- Calibration: feed ~100 representative frames during conversion
- Roughly 4× speedup over FP32 on Jetson
- Some accuracy loss — verify with side-by-side depth maps

### 4. Frame skipping
- Run inference every Nth frame, interpolate alerts in between
- Cheap but visible; document the user-perceptible delay

---

## Deliverable for the thesis

A 1-page section in the thesis with:

1. Table of FPS/latency/memory across {Mock, MiDaS, DepthPro} × {Mac CPU, Mac GPU, Jetson}
2. A line chart: FPS over a 60-s clip for each configuration
3. Discussion: which model meets the 15-FPS target, and what compromises were needed

This satisfies "performance analysis and validation of deployment feasibility" (Learning Outcome 4).
