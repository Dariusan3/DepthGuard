"""
Generic loader for YOUR OWN trained depth model.

This wraps any PyTorch checkpoint and exposes the standard DepthGuard model
interface:

    def inference(self, frame: np.ndarray) -> np.ndarray
        # frame: BGR uint8 (H, W, 3)
        # returns: float32 (H, W) in [0,1], 0 = close, 1 = far

Three ways to plug in your model, tried in order:

1. SCRIPTED / TRACED  (easiest — recommended)
   Export your model with torch.jit and point DepthGuard at the .pt/.ts file.
       scripted = torch.jit.script(model)   # or torch.jit.trace(model, example)
       scripted.save("checkpoints/my_model.ts")
   No architecture code needed at load time.

2. STATE-DICT + BUILDER
   Put a build_model() function in checkpoints/model_def.py that returns your
   nn.Module, then save the weights with torch.save(model.state_dict(), ...).
   DepthGuard imports build_model(), constructs the net, and loads the weights.

3. FULL PICKLED MODULE
   torch.save(model, "checkpoints/my_model.pt")  # whole module, not just weights
   Works if the class definition is importable at load time.

Set the input normalization / resize via the optional companion JSON
(my_model.json next to the checkpoint) — see DEFAULTS below.
"""

from __future__ import annotations

import json
import os

import cv2
import numpy as np


DEFAULTS = {
    "input_size": [384, 384],        # [H, W] the network expects; null = keep frame size
    "mean": [0.485, 0.456, 0.406],   # per-channel RGB normalization
    "std": [0.229, 0.224, 0.225],
    "invert_output": False,          # set True if your model outputs 1=close, 0=far
    "output_is_disparity": False,    # set True if output is disparity (inverse depth)
}


class CustomDepthModel:
    """Loads and runs a user-supplied depth model checkpoint."""

    def __init__(self, checkpoint: str, device: str | None = None):
        import torch

        self.torch = torch
        self.device = torch.device(
            device or ("cuda" if torch.cuda.is_available() else "cpu")
        )
        self.checkpoint = checkpoint
        self.cfg = self._load_config(checkpoint)
        self.model = self._load_model(checkpoint)
        self.model.to(self.device).eval()

    # ── Loading ──────────────────────────────────────────────────
    def _load_config(self, checkpoint: str) -> dict:
        cfg = dict(DEFAULTS)
        side = os.path.splitext(checkpoint)[0] + ".json"
        if os.path.exists(side):
            try:
                with open(side) as f:
                    cfg.update(json.load(f))
            except Exception:
                pass
        return cfg

    def _load_model(self, checkpoint: str):
        torch = self.torch
        ext = os.path.splitext(checkpoint)[1].lower()

        # 1. TorchScript (.ts or .pt saved via jit) — try this first
        try:
            return torch.jit.load(checkpoint, map_location=self.device)
        except Exception:
            pass

        obj = torch.load(checkpoint, map_location=self.device, weights_only=False)

        # 3. Full pickled nn.Module
        if hasattr(obj, "eval") and hasattr(obj, "forward"):
            return obj

        # 2. State dict (+ optional builder in checkpoints/model_def.py)
        state = obj
        if isinstance(obj, dict):
            for key in ("model_state_dict", "state_dict", "model", "weights"):
                if key in obj and isinstance(obj[key], dict):
                    state = obj[key]
                    break

        builder = self._import_builder(checkpoint)
        if builder is None:
            raise RuntimeError(
                "Checkpoint is a state-dict but no builder was found.\n"
                "Either export with torch.jit.save (recommended), save the whole\n"
                "module with torch.save(model, ...), OR add a build_model() function\n"
                "in a model_def.py next to the checkpoint."
            )
        model = builder()
        model.load_state_dict(state, strict=False)
        return model

    @staticmethod
    def _import_builder(checkpoint: str):
        """Look for build_model() in <checkpoint_dir>/model_def.py."""
        import importlib.util

        mod_path = os.path.join(os.path.dirname(checkpoint), "model_def.py")
        if not os.path.exists(mod_path):
            return None
        spec = importlib.util.spec_from_file_location("dg_custom_model_def", mod_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return getattr(module, "build_model", None)

    # ── Inference ────────────────────────────────────────────────
    def inference(self, frame: np.ndarray) -> np.ndarray:
        torch = self.torch
        h, w = frame.shape[:2]

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0

        size = self.cfg.get("input_size")
        if size:
            net_in = cv2.resize(rgb, (int(size[1]), int(size[0])),
                                interpolation=cv2.INTER_AREA)
        else:
            net_in = rgb

        mean = np.array(self.cfg["mean"], dtype=np.float32)
        std = np.array(self.cfg["std"], dtype=np.float32)
        net_in = (net_in - mean) / std

        tensor = torch.from_numpy(net_in.transpose(2, 0, 1)).unsqueeze(0).to(self.device)

        with torch.no_grad():
            out = self.model(tensor)

        # Models may return a tensor, a tuple, or a dict
        if isinstance(out, (tuple, list)):
            out = out[0]
        elif isinstance(out, dict):
            for key in ("depth", "pred", "out", "prediction"):
                if key in out:
                    out = out[key]
                    break

        depth = out.squeeze().detach().cpu().numpy().astype(np.float32)

        # Resize back to the frame resolution
        if depth.shape[:2] != (h, w):
            depth = cv2.resize(depth, (w, h), interpolation=cv2.INTER_LINEAR)

        # Disparity → depth if needed
        if self.cfg.get("output_is_disparity"):
            depth = 1.0 / np.clip(depth, 1e-6, None)

        # Normalize to [0, 1]
        d_min, d_max = float(depth.min()), float(depth.max())
        if d_max - d_min > 1e-6:
            depth = (depth - d_min) / (d_max - d_min)
        else:
            depth = np.zeros_like(depth)

        # Convention: 0 = close, 1 = far. Invert if the model is the other way.
        if self.cfg.get("invert_output"):
            depth = 1.0 - depth

        return depth
