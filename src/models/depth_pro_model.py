"""
DepthPro integration for DepthGuard.

Uses the native Apple depth_pro API from:
    https://github.com/Dariusan3/ml-depth-pro

Install:
    git clone https://github.com/Dariusan3/ml-depth-pro.git
    cd ml-depth-pro
    pip install -e .
    source get_pretrained_models.sh

Two modes:
    1. PRETRAINED — use DepthPro as-is (model.infer)
    2. FINETUNED — load your custom trained checkpoint
"""

import cv2
import numpy as np
import torch


class DepthProModel:
    """
    Inference wrapper matching the interface expected by DepthGuard.

    Uses depth_pro.create_model_and_transforms() from your ml-depth-pro repo.

    Usage:
        model = DepthProModel()                                    # pretrained
        model = DepthProModel(checkpoint="checkpoints/best.pt")    # your weights
    """

    def __init__(self, checkpoint=None, device=None):
        import depth_pro

        self.device = device or torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        if checkpoint is not None:
            # Load your custom trained weights
            self.model, self.transform = depth_pro.create_model_and_transforms()
            state = torch.load(checkpoint, map_location=self.device, weights_only=False)
            # Support both full state dict and nested "model_state_dict" key
            if "model_state_dict" in state:
                self.model.load_state_dict(state["model_state_dict"])
            else:
                self.model.load_state_dict(state)
        else:
            # Use pretrained DepthPro as-is
            self.model, self.transform = depth_pro.create_model_and_transforms()

        self.model.to(self.device).eval()

    def inference(self, frame):
        """
        Takes a BGR video frame (H, W, 3 uint8) → returns depth map (H, W)
        float32 normalized to [0.0, 1.0] where 0 = close, 1 = far.
        """
        h, w = frame.shape[:2]

        # depth_pro expects a torch tensor from its transform
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # The transform expects a PIL-like or numpy HWC image
        image_tensor = self.transform(rgb)
        image_tensor = image_tensor.to(self.device)

        with torch.no_grad():
            # model.infer returns {"depth": ..., "focallength_px": ...}
            prediction = self.model.infer(image_tensor)
            depth = prediction["depth"]  # metric depth in meters

        # Resize to original frame size if needed
        if depth.shape[-2:] != (h, w):
            depth = torch.nn.functional.interpolate(
                depth.unsqueeze(0).unsqueeze(0) if depth.dim() == 2 else depth.unsqueeze(0),
                size=(h, w),
                mode="bicubic",
                align_corners=False,
            ).squeeze()

        depth = depth.cpu().numpy()

        # Normalize to [0, 1]: 0 = closest, 1 = farthest
        d_min, d_max = depth.min(), depth.max()
        if d_max - d_min > 1e-6:
            depth = (depth - d_min) / (d_max - d_min)
        else:
            depth = np.zeros_like(depth)

        return depth.astype(np.float32)
