import cv2
import numpy as np
import torch


class MiDaSModel:
    """
    Real monocular depth estimation using MiDaS v2.1 (small).
    Downloads the model on first use (~30 MB).

    Returns a 0.0–1.0 depth map where 0 = close, 1 = far,
    matching the interface expected by SafetyAlertSystem.
    """

    # Available MiDaS variants (torch.hub)
    VARIANTS = {
        "small": ("MiDaS_small", "MiDaS_small"),      # fast, ~30 MB
        "hybrid": ("DPT_Hybrid", "DPT_Hybrid"),        # balanced
        "large": ("DPT_Large", "DPT_Large"),            # most accurate
    }

    def __init__(self, variant="small"):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        model_name, transform_name = self.VARIANTS[variant]

        # Load model from Intel's torch.hub repo (auto-downloads weights)
        self.model = torch.hub.load(
            "isl-org/MiDaS", model_name, trust_repo=True
        )
        self.model.to(self.device).eval()

        # Load the matching input transform
        midas_transforms = torch.hub.load(
            "isl-org/MiDaS", "transforms", trust_repo=True
        )
        if variant == "small":
            self.transform = midas_transforms.small_transform
        elif variant == "hybrid":
            self.transform = midas_transforms.dpt_transform
        else:
            self.transform = midas_transforms.dpt_transform

    def inference(self, frame):
        """
        Takes a BGR video frame (numpy H×W×3) and returns a float32
        depth map (H×W) normalized to [0.0, 1.0] where 0 = close, 1 = far.
        """
        # MiDaS expects RGB input
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        input_batch = self.transform(rgb).to(self.device)

        with torch.no_grad():
            prediction = self.model(input_batch)

            # Resize back to original frame dimensions
            prediction = torch.nn.functional.interpolate(
                prediction.unsqueeze(1),
                size=frame.shape[:2],
                mode="bicubic",
                align_corners=False,
            ).squeeze()

        depth = prediction.cpu().numpy()

        # MiDaS outputs *inverse* depth (higher = closer).
        # Normalize to [0, 1] and invert so 0 = close, 1 = far.
        d_min, d_max = depth.min(), depth.max()
        if d_max - d_min > 0:
            depth = (depth - d_min) / (d_max - d_min)  # now 0=far, 1=close
            depth = 1.0 - depth                          # invert: 0=close, 1=far
        else:
            depth = np.zeros_like(depth, dtype=np.float32)

        return depth.astype(np.float32)
