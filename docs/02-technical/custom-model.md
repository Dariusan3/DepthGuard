# Embedding Your Own Depth Model

DepthGuard can run any depth model you've trained. The app talks to every model
through one tiny interface:

```python
def inference(self, frame: np.ndarray) -> np.ndarray:
    # frame: BGR uint8 (H, W, 3)  — straight from the video
    # returns: float32 (H, W) in [0, 1], where 0 = close, 1 = far
```

You have two paths: the **drop-in checkpoint loader** (no code) or a **custom
wrapper class** (full control).

---

## Path A — Drop-in checkpoint (recommended, no code)

Use the MODEL dropdown → **Load Custom Model…** → pick your checkpoint file.
DepthGuard's `CustomDepthModel` ([src/models/custom_model.py](../../src/models/custom_model.py))
handles loading + pre/post-processing. It accepts three checkpoint formats:

### 1. TorchScript (easiest, most portable)
Export once, no architecture code needed at load time:

```python
import torch
model.eval()
scripted = torch.jit.script(model)         # or torch.jit.trace(model, example_input)
scripted.save("checkpoints/my_model.ts")
```
Then pick `my_model.ts` in the app. Done.

### 2. State-dict + builder
If you only have weights, add a `model_def.py` next to the checkpoint with a
`build_model()` that returns your `nn.Module`:

```python
# checkpoints/model_def.py
def build_model():
    from my_package import MyDepthNet
    return MyDepthNet(backbone="depthpro", ...)
```
Save weights with `torch.save(model.state_dict(), "checkpoints/my_model.pth")`,
then pick `my_model.pth`.

### 3. Full pickled module
```python
torch.save(model, "checkpoints/my_model.pt")   # whole module, not just weights
```
Works as long as the model's class is importable when DepthGuard loads it.

### Tuning the input/output (optional)
Drop a JSON next to the checkpoint (same name, `.json`) to override defaults:

```json
{
  "input_size": [384, 384],
  "mean": [0.485, 0.456, 0.406],
  "std":  [0.229, 0.224, 0.225],
  "invert_output": false,
  "output_is_disparity": false
}
```

| Key | When to change it |
|---|---|
| `input_size` | The `[H, W]` your network expects. Set `null` to feed the native frame size. |
| `mean` / `std` | Per-channel RGB normalization used during your training. |
| `invert_output` | `true` if your model outputs 1 = close, 0 = far (DepthGuard wants the opposite). |
| `output_is_disparity` | `true` if your model predicts disparity (inverse depth) rather than depth. |

The wrapper auto-normalizes the output to `[0, 1]` and resizes back to the frame,
so you mainly need to get `invert_output` right. If the alert fires when objects
are *far* instead of *near*, flip that flag.

---

## Path B — Custom wrapper class (full control)

If your model needs special preprocessing the JSON can't express, write a small
class. Copy [src/models/mock_model.py](../../src/models/mock_model.py) as a
template — the only requirement is the `inference(frame) -> depth_map` method:

```python
# src/models/my_model.py
import cv2, numpy as np, torch

class MyDepthModel:
    def __init__(self, checkpoint):
        self.model = torch.jit.load(checkpoint).eval()

    def inference(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # ... your exact preprocessing ...
        with torch.no_grad():
            depth = self.model(tensor).squeeze().cpu().numpy()
        # normalize to [0,1], 0=close 1=far
        depth = (depth - depth.min()) / (depth.ptp() + 1e-6)
        return depth.astype(np.float32)
```

Then register it in `MainWindow.switch_model` the same way `_load_midas` /
`_load_depthpro` are wired.

---

## Verifying your model works

1. Run `python main.py` → MODEL dropdown → **Load Custom Model…** → pick the file
2. A loading dialog appears (runs on a background thread, UI stays responsive)
3. Load a clip → Play → the right-hand **depth panel** shows your model's output
   colorized with the JET colormap
4. Sanity check: close objects should appear in the warm/red end of the colormap

If the depth panel looks inverted (sky red, road blue), set
`"invert_output": true` in the JSON and reload.

### Quick headless test

```python
import cv2
from src.models.custom_model import CustomDepthModel

m = CustomDepthModel("checkpoints/my_model.ts")
frame = cv2.imread("some_frame.jpg")
depth = m.inference(frame)
print(depth.shape, depth.min(), depth.max())   # (H, W) 0.0 1.0
```

---

## For the thesis

This is the integration point for your self-supervised DepthPro-backbone model.
Once you have a trained checkpoint:

1. Export it as TorchScript (Path A.1)
2. Load it in DepthGuard via **Load Custom Model…**
3. Run the performance profiler against it:
   `python scripts/profile_performance.py --models custom --clip data/scenarios/04_brake_lights_critical.mp4`
   (after adding a `custom` branch pointing at your checkpoint)
4. Compare FPS / latency / depth quality against MiDaS and DepthPro in the
   thesis results section.
