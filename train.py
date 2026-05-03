"""
Self-supervised monocular depth training using DepthPro backbone.

Self-supervised means NO ground truth depth labels are needed.
The model learns depth from video sequences using:
    1. Photometric consistency — if depth is correct, warping frame t to frame t+1
       using the predicted depth + estimated pose should reconstruct frame t+1.
    2. Smoothness — depth should be locally smooth except at edges.

Training data:
    A folder of driving video frames (consecutive frames from dashcam footage).
    The script expects: data/<dataset_name>/frames/*.jpg (or .png)

Usage:
    python train.py --data data/driving --epochs 20 --batch-size 4
    python train.py --data data/driving --resume checkpoints/latest.pt
"""

import argparse
import os
import time
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

from src.models.depth_pro_model import DepthProDepthEstimator


# ── Self-supervised losses ───────────────────────────────────────

class SSIM(nn.Module):
    """Structural Similarity Index — measures perceptual image quality."""

    def __init__(self, window_size=3):
        super().__init__()
        self.mu_pool = nn.AvgPool2d(window_size, 1, window_size // 2)
        self.sig_pool = nn.AvgPool2d(window_size, 1, window_size // 2)
        self.C1 = 0.01 ** 2
        self.C2 = 0.03 ** 2

    def forward(self, x, y):
        mu_x = self.mu_pool(x)
        mu_y = self.mu_pool(y)
        sigma_x = self.sig_pool(x ** 2) - mu_x ** 2
        sigma_y = self.sig_pool(y ** 2) - mu_y ** 2
        sigma_xy = self.sig_pool(x * y) - mu_x * mu_y

        ssim_n = (2 * mu_x * mu_y + self.C1) * (2 * sigma_xy + self.C2)
        ssim_d = (mu_x ** 2 + mu_y ** 2 + self.C1) * (sigma_x + sigma_y + self.C2)

        return torch.clamp((1 - ssim_n / ssim_d) / 2, 0, 1)


def photometric_loss(predicted, target, ssim_fn, alpha=0.85):
    """
    Combined L1 + SSIM photometric reconstruction loss.
    This is the primary self-supervised signal.
    """
    l1 = torch.abs(predicted - target).mean(dim=1, keepdim=True)
    ssim = ssim_fn(predicted, target).mean(dim=1, keepdim=True)
    return alpha * ssim + (1 - alpha) * l1


def smoothness_loss(depth, image):
    """
    Edge-aware depth smoothness — penalizes depth gradients
    except where the image also has strong gradients (edges).
    """
    d_dx = torch.abs(depth[:, :, :, :-1] - depth[:, :, :, 1:])
    d_dy = torch.abs(depth[:, :, :-1, :] - depth[:, :, 1:, :])

    i_dx = torch.mean(torch.abs(image[:, :, :, :-1] - image[:, :, :, 1:]), dim=1, keepdim=True)
    i_dy = torch.mean(torch.abs(image[:, :, :-1, :] - image[:, :, 1:, :]), dim=1, keepdim=True)

    d_dx *= torch.exp(-i_dx)
    d_dy *= torch.exp(-i_dy)

    return d_dx.mean() + d_dy.mean()


# ── Pose network ─────────────────────────────────────────────────

class PoseNet(nn.Module):
    """
    Lightweight CNN that predicts the 6-DOF camera motion between two frames.
    Outputs: (tx, ty, tz, rx, ry, rz) — translation + Euler rotation.

    This is needed for the self-supervised warping: to reconstruct frame B
    from frame A's depth, you need to know how the camera moved.
    """

    def __init__(self):
        super().__init__()
        # Takes 6-channel input (two RGB frames concatenated)
        self.encoder = nn.Sequential(
            nn.Conv2d(6, 16, 7, stride=2, padding=3), nn.ReLU(inplace=True),
            nn.Conv2d(16, 32, 5, stride=2, padding=2), nn.ReLU(inplace=True),
            nn.Conv2d(32, 64, 3, stride=2, padding=1), nn.ReLU(inplace=True),
            nn.Conv2d(64, 128, 3, stride=2, padding=1), nn.ReLU(inplace=True),
            nn.Conv2d(128, 256, 3, stride=2, padding=1), nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d(1),
        )
        self.fc = nn.Linear(256, 6)

        # Initialize near-zero so initial pose ~ identity
        nn.init.zeros_(self.fc.weight)
        nn.init.zeros_(self.fc.bias)

    def forward(self, frame_a, frame_b):
        x = torch.cat([frame_a, frame_b], dim=1)  # (B, 6, H, W)
        x = self.encoder(x).flatten(1)
        pose = self.fc(x) * 0.01  # scale down for stability
        return pose  # (B, 6)


# ── Geometry utils ───────────────────────────────────────────────

def euler_to_matrix(euler):
    """Convert (B, 6) euler pose to (B, 3, 4) transformation matrix."""
    B = euler.shape[0]
    t = euler[:, :3].unsqueeze(-1)  # (B, 3, 1)

    rx, ry, rz = euler[:, 3], euler[:, 4], euler[:, 5]

    cos_x, sin_x = torch.cos(rx), torch.sin(rx)
    cos_y, sin_y = torch.cos(ry), torch.sin(ry)
    cos_z, sin_z = torch.cos(rz), torch.sin(rz)

    zeros = torch.zeros_like(rx)
    ones = torch.ones_like(rx)

    Rx = torch.stack([ones, zeros, zeros, zeros, cos_x, -sin_x, zeros, sin_x, cos_x], dim=1).view(B, 3, 3)
    Ry = torch.stack([cos_y, zeros, sin_y, zeros, ones, zeros, -sin_y, zeros, cos_y], dim=1).view(B, 3, 3)
    Rz = torch.stack([cos_z, -sin_z, zeros, sin_z, cos_z, zeros, zeros, zeros, ones], dim=1).view(B, 3, 3)

    R = Rz @ Ry @ Rx
    return torch.cat([R, t], dim=2)  # (B, 3, 4)


def warp_frame(depth, pose, source_frame, K):
    """
    Inverse-warp source_frame to the target viewpoint using predicted depth and pose.
    This is the core of self-supervised depth: if depth is right, the warp reconstructs the target.

    Args:
        depth: (B, 1, H, W) predicted depth of target frame
        pose: (B, 6) predicted camera motion target → source
        source_frame: (B, 3, H, W) the source RGB frame
        K: (B, 3, 3) camera intrinsics

    Returns:
        warped: (B, 3, H, W) source frame warped to target viewpoint
    """
    B, _, H, W = depth.shape
    device = depth.device

    # Create pixel coordinate grid
    y, x = torch.meshgrid(
        torch.arange(H, device=device, dtype=torch.float32),
        torch.arange(W, device=device, dtype=torch.float32),
        indexing="ij",
    )
    ones = torch.ones_like(x)
    pixel_coords = torch.stack([x, y, ones], dim=0).unsqueeze(0).expand(B, -1, -1, -1)  # (B, 3, H, W)

    # Unproject to 3D: P = depth * K_inv @ pixel
    K_inv = torch.inverse(K)
    flat_pixels = pixel_coords.view(B, 3, -1)  # (B, 3, H*W)
    cam_points = K_inv @ flat_pixels  # (B, 3, H*W)
    cam_points = cam_points * depth.view(B, 1, -1)  # (B, 3, H*W)

    # Transform to source camera frame
    T = euler_to_matrix(pose)  # (B, 3, 4)
    ones_row = torch.ones(B, 1, H * W, device=device)
    cam_points_h = torch.cat([cam_points, ones_row], dim=1)  # (B, 4, H*W)
    src_points = T @ cam_points_h  # (B, 3, H*W)

    # Project back to source image pixels
    src_pixels = K @ src_points  # (B, 3, H*W)
    src_pixels = src_pixels[:, :2] / (src_pixels[:, 2:3] + 1e-7)  # (B, 2, H*W)

    # Normalize to [-1, 1] for grid_sample
    src_pixels = src_pixels.view(B, 2, H, W)
    src_pixels[:, 0] = 2.0 * src_pixels[:, 0] / (W - 1) - 1.0
    src_pixels[:, 1] = 2.0 * src_pixels[:, 1] / (H - 1) - 1.0
    grid = src_pixels.permute(0, 2, 3, 1)  # (B, H, W, 2)

    warped = F.grid_sample(source_frame, grid, mode="bilinear", padding_mode="border", align_corners=True)
    return warped


def make_intrinsics(H, W, device, fov_deg=70.0):
    """Approximate camera intrinsics from assumed horizontal FOV."""
    fx = W / (2.0 * np.tan(np.radians(fov_deg / 2)))
    fy = fx
    cx, cy = W / 2.0, H / 2.0
    K = torch.tensor([[fx, 0, cx], [0, fy, cy], [0, 0, 1]], dtype=torch.float32, device=device)
    return K.unsqueeze(0)  # (1, 3, 3)


# ── Dataset ──────────────────────────────────────────────────────

class FramePairDataset(Dataset):
    """
    Loads consecutive frame pairs from a folder of extracted video frames.
    Assumes frames are named so that sorted order = temporal order.
    """

    def __init__(self, frames_dir, size=(256, 512)):
        self.frames = sorted(Path(frames_dir).glob("*.*"))
        self.frames = [f for f in self.frames if f.suffix.lower() in {".jpg", ".jpeg", ".png"}]
        self.size = size  # (H, W)

        if len(self.frames) < 2:
            raise ValueError(f"Need at least 2 frames in {frames_dir}, found {len(self.frames)}")

    def __len__(self):
        return len(self.frames) - 1

    def __getitem__(self, idx):
        def load(path):
            img = cv2.imread(str(path))
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img = cv2.resize(img, (self.size[1], self.size[0]))
            return torch.from_numpy(img).permute(2, 0, 1).float() / 255.0

        return load(self.frames[idx]), load(self.frames[idx + 1])


# ── Training loop ────────────────────────────────────────────────

def train(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    # Data
    frames_dir = os.path.join(args.data, "frames")
    if not os.path.isdir(frames_dir):
        print(f"Expected frames in: {frames_dir}")
        print("Extract frames from your dashcam video first:")
        print(f"  mkdir -p {frames_dir}")
        print(f"  ffmpeg -i your_video.mp4 -vf fps=10 {frames_dir}/%06d.jpg")
        return

    dataset = FramePairDataset(frames_dir, size=(256, 512))
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True,
                        num_workers=2, pin_memory=True, drop_last=True)
    print(f"Dataset: {len(dataset)} frame pairs")

    # Models
    depth_model = DepthProDepthEstimator(freeze_backbone=True).to(device)
    pose_net = PoseNet().to(device)

    # Only train the refinement head + pose network
    params = list(depth_model.refine_head.parameters()) + \
             [depth_model.residual_alpha] + \
             list(pose_net.parameters())

    optimizer = torch.optim.AdamW(params, lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    ssim_fn = SSIM().to(device)

    os.makedirs(args.checkpoint_dir, exist_ok=True)

    start_epoch = 0
    if args.resume:
        ckpt = torch.load(args.resume, map_location=device, weights_only=True)
        depth_model.load_state_dict(ckpt["model_state_dict"])
        pose_net.load_state_dict(ckpt["pose_state_dict"])
        optimizer.load_state_dict(ckpt["optimizer_state_dict"])
        start_epoch = ckpt["epoch"] + 1
        print(f"Resumed from epoch {start_epoch}")

    # Camera intrinsics (assumed — adjust fov_deg for your dashcam)
    K = make_intrinsics(256, 512, device, fov_deg=args.fov)

    print(f"\nTraining for {args.epochs} epochs...")
    print(f"Trainable params: {sum(p.numel() for p in params):,}")
    print(f"DepthPro backbone: frozen\n")

    for epoch in range(start_epoch, args.epochs):
        depth_model.train()
        pose_net.train()
        epoch_loss = 0.0
        t0 = time.time()

        for batch_idx, (frame_a, frame_b) in enumerate(loader):
            frame_a = frame_a.to(device)
            frame_b = frame_b.to(device)

            # Predict depth for target frame (frame_a)
            # Note: DepthPro expects its own preprocessing, but for training
            # we work at lower resolution with normalized [0,1] RGB directly.
            # The backbone's processor is bypassed — we're training the head.
            depth = depth_model(frame_a)  # (B, 1, H, W)

            # Predict pose: how camera moved from frame_a to frame_b
            pose = pose_net(frame_a, frame_b)  # (B, 6)

            # Warp frame_b back to frame_a's viewpoint using predicted depth + pose
            K_batch = K.expand(frame_a.shape[0], -1, -1)
            warped = warp_frame(depth, pose, frame_b, K_batch)

            # Self-supervised loss: warped frame should match frame_a
            photo_loss = photometric_loss(warped, frame_a, ssim_fn).mean()
            smooth_loss = smoothness_loss(depth / (depth.mean() + 1e-7), frame_a)

            loss = photo_loss + args.smooth_weight * smooth_loss

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            optimizer.step()

            epoch_loss += loss.item()

            if batch_idx % 50 == 0:
                print(f"  [{batch_idx}/{len(loader)}] loss={loss.item():.4f}  "
                      f"photo={photo_loss.item():.4f}  smooth={smooth_loss.item():.4f}")

        scheduler.step()
        avg_loss = epoch_loss / len(loader)
        elapsed = time.time() - t0
        print(f"Epoch {epoch + 1}/{args.epochs}  loss={avg_loss:.4f}  time={elapsed:.1f}s")

        # Save checkpoint
        ckpt_path = os.path.join(args.checkpoint_dir, "latest.pt")
        torch.save({
            "epoch": epoch,
            "model_state_dict": depth_model.state_dict(),
            "pose_state_dict": pose_net.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "loss": avg_loss,
        }, ckpt_path)

        if (epoch + 1) % 5 == 0:
            best_path = os.path.join(args.checkpoint_dir, f"epoch_{epoch + 1}.pt")
            torch.save({
                "epoch": epoch,
                "model_state_dict": depth_model.state_dict(),
                "pose_state_dict": pose_net.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "loss": avg_loss,
            }, best_path)
            print(f"  Saved checkpoint: {best_path}")

    print("\nTraining complete.")
    print(f"Best checkpoint: {args.checkpoint_dir}/latest.pt")
    print(f"\nTo use in DepthGuard:")
    print(f"  Select 'Your Model (DepthPro)' in the MODEL dropdown")
    print(f"  It will load from: {args.checkpoint_dir}/latest.pt")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Self-supervised depth training with DepthPro backbone")
    parser.add_argument("--data", type=str, required=True, help="Path to dataset folder (must contain frames/ subfolder)")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--smooth-weight", type=float, default=0.001)
    parser.add_argument("--fov", type=float, default=70.0, help="Dashcam horizontal FOV in degrees")
    parser.add_argument("--checkpoint-dir", type=str, default="checkpoints")
    parser.add_argument("--resume", type=str, default=None, help="Resume from checkpoint")
    args = parser.parse_args()

    train(args)
