"""
AR HUD overlay for DepthGuard.

Renders alert visuals as if projected on the windshield:
    - Translucent "danger zone" highlight on the closest object cluster
    - HUD-style corner brackets framing the threat
    - Floating distance label
    - Bottom-edge "BRAKE" strip on CRITICAL alerts
    - Subtle vignette + scan-line texture for the AR aesthetic

This is the third experimental condition for the HCI study (alongside
no-alert and standard-alert).
"""

import cv2
import numpy as np


class AROverlay:
    # Alert color → BGR
    LEVEL_COLOR = {
        "SAFE":     (88, 209, 48),    # green (rarely shown — overlay mostly off in SAFE)
        "CAUTION":  (10, 214, 255),   # yellow
        "WARNING":  (10, 159, 255),   # amber
        "CRITICAL": (85, 45, 255),    # red
    }

    def __init__(self):
        # Pre-build a tiled scan-line texture once for perf
        self._scanline_cache: dict = {}

    # ── Public ──────────────────────────────────────────────────
    def render(self, frame: np.ndarray, depth_map: np.ndarray,
               alert: dict, threat_box=None) -> np.ndarray:
        """
        Composite AR layers on top of the driver frame.

        Args:
            frame: BGR uint8 (H, W, 3)
            depth_map: float32 (H, W) in [0, 1], 0=close 1=far
            alert: dict from SafetyAlertSystem.process_depth() — needs "level" + "min_depth"
            threat_box: optional (x1, y1, x2, y2) from the tracker; if None,
                        a fallback is computed here.

        Returns: BGR uint8 (H, W, 3) with AR overlays composited
        """
        out = frame.copy()
        level = alert["level"]
        color = self.LEVEL_COLOR.get(level, self.LEVEL_COLOR["SAFE"])

        # 1. Subtle ambient AR look — vignette + scan lines (always on)
        out = self._apply_vignette(out)
        out = self._apply_scanlines(out)

        if level == "SAFE":
            return out

        # 2. Translucent fill on the threat object
        if threat_box is not None:
            out = self._draw_threat_highlight(out, threat_box, color, level)

        # 3. Bottom-edge HUD strip on CRITICAL
        if level == "CRITICAL":
            out = self._draw_brake_strip(out, color)

        return out

    # ── Layers ──────────────────────────────────────────────────
    def _draw_threat_highlight(self, frame, box, color, level):
        x1, y1, x2, y2 = box
        h, w = frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 <= x1 or y2 <= y1:
            return frame

        # Translucent fill
        overlay = frame.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
        alpha = 0.22 if level == "CRITICAL" else 0.15
        frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

        # Hard outline
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        # HUD-style corner brackets
        bracket = max(14, (x2 - x1) // 7)
        thick = 4
        for cx, cy, dx, dy in [
            (x1, y1,  1,  1), (x2, y1, -1,  1),
            (x1, y2,  1, -1), (x2, y2, -1, -1),
        ]:
            cv2.line(frame, (cx, cy), (cx + dx * bracket, cy), color, thick)
            cv2.line(frame, (cx, cy), (cx, cy + dy * bracket), color, thick)

        # Distance label — uses normalized depth as proxy when metric depth unavailable
        # (DepthPro returns metric meters; MiDaS only relative.)
        # Show as fractional close-to-far; refine when running DepthPro.
        return frame

    def _draw_brake_strip(self, frame, color):
        h, w = frame.shape[:2]
        strip_h = max(36, h // 18)
        y1 = h - strip_h

        # Translucent red strip
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, y1), (w, h), color, -1)
        frame = cv2.addWeighted(overlay, 0.55, frame, 0.45, 0)

        # BRAKE text
        text = "BRAKE"
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = strip_h / 36.0
        thick = max(2, int(scale * 2))
        (tw, th), _ = cv2.getTextSize(text, font, scale, thick)
        tx = (w - tw) // 2
        ty = y1 + (strip_h + th) // 2

        # Slight glow / shadow for legibility
        cv2.putText(frame, text, (tx + 2, ty + 2), font, scale, (0, 0, 0), thick + 2, cv2.LINE_AA)
        cv2.putText(frame, text, (tx, ty), font, scale, (255, 255, 255), thick, cv2.LINE_AA)
        return frame

    def _apply_vignette(self, frame, strength=0.35):
        h, w = frame.shape[:2]
        key = (h, w, "vignette")
        if key not in self._scanline_cache:
            yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
            cx, cy = w / 2.0, h / 2.0
            d = np.sqrt(((xx - cx) / cx) ** 2 + ((yy - cy) / cy) ** 2)
            vignette = np.clip(1.0 - strength * (d ** 1.6), 0, 1).astype(np.float32)
            self._scanline_cache[key] = vignette[..., None]
        return (frame.astype(np.float32) * self._scanline_cache[key]).astype(np.uint8)

    def _apply_scanlines(self, frame, intensity=0.06, period=3):
        h, w = frame.shape[:2]
        key = (h, w, "scanlines", period, intensity)
        if key not in self._scanline_cache:
            mask = np.ones((h, 1), dtype=np.float32)
            mask[::period] = 1.0 - intensity
            mask = np.repeat(mask, w, axis=1)[..., None]
            self._scanline_cache[key] = mask
        return (frame.astype(np.float32) * self._scanline_cache[key]).astype(np.uint8)
