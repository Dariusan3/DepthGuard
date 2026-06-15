"""
Optional YOLO object detection for ADAS-style overlays.

The desktop app can run without this module's optional dependencies. When
Ultralytics is available, detections provide realistic object boxes for people,
vehicles, cyclists, and traffic signs; otherwise callers simply receive [].
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import os
from typing import Iterable

import numpy as np


ADAS_CLASS_IDS = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
    9: "traffic light",
    11: "stop sign",
}

CLASS_WEIGHTS = {
    "person": 1.35,
    "bicycle": 1.25,
    "motorcycle": 1.25,
    "car": 1.00,
    "bus": 1.10,
    "truck": 1.15,
    "traffic light": 0.70,
    "stop sign": 0.75,
}


@dataclass(frozen=True)
class DetectedObject:
    label: str
    class_id: int
    confidence: float
    bbox: tuple[int, int, int, int]
    center: tuple[int, int]
    depth: float | None
    importance: float

    def to_payload(self) -> dict:
        return asdict(self)


class YOLOObjectDetector:
    """
    Lazy Ultralytics YOLO wrapper.

    Set DEPTHGUARD_YOLO=0 to disable. Set DEPTHGUARD_YOLO_MODEL to a local
    weights path or an Ultralytics model name such as yolov8n.pt.
    """

    def __init__(
        self,
        model_name: str | None = None,
        conf: float = 0.30,
        imgsz: int = 640,
        class_ids: Iterable[int] | None = None,
        max_detections: int = 12,
    ):
        self.enabled = os.environ.get("DEPTHGUARD_YOLO", "1").lower() not in {
            "0",
            "false",
            "off",
            "no",
        }
        self.model_name = model_name or os.environ.get("DEPTHGUARD_YOLO_MODEL", "yolov8n.pt")
        self.conf = conf
        self.imgsz = imgsz
        self.class_ids = tuple(class_ids or ADAS_CLASS_IDS.keys())
        self.max_detections = max_detections

        self._model = None
        self._device = None
        self._names = {}
        self.error: str | None = None
        self.last_count = 0

    @property
    def available(self) -> bool:
        return self.enabled and self.error is None

    def detect(self, frame: np.ndarray, depth_map: np.ndarray | None = None) -> list[DetectedObject]:
        if not self.enabled:
            self.last_count = 0
            return []
        if not self._ensure_model():
            self.last_count = 0
            return []

        try:
            results = self._model.predict(
                frame,
                conf=self.conf,
                imgsz=self.imgsz,
                classes=list(self.class_ids),
                device=self._device,
                verbose=False,
            )
        except Exception as exc:
            self.error = str(exc)
            self.last_count = 0
            return []

        if not results:
            self.last_count = 0
            return []

        boxes = getattr(results[0], "boxes", None)
        if boxes is None or boxes.xyxy is None:
            self.last_count = 0
            return []

        xyxy = boxes.xyxy.detach().cpu().numpy()
        confs = boxes.conf.detach().cpu().numpy()
        classes = boxes.cls.detach().cpu().numpy().astype(int)

        h, w = frame.shape[:2]
        detections: list[DetectedObject] = []
        for coords, score, class_id in zip(xyxy, confs, classes):
            x1, y1, x2, y2 = self._clamp_box(coords, w, h)
            if x2 <= x1 or y2 <= y1:
                continue
            label = self._class_label(class_id)
            # Skip the ego-vehicle: the driver's own hood / dashboard / A-pillars
            # show up as a huge, bottom-anchored, centered "car" or "truck" box.
            # Detecting it as a threat makes no sense, so drop it.
            if self._is_ego_vehicle(label, (x1, y1, x2, y2), (h, w)):
                continue
            center = ((x1 + x2) // 2, (y1 + y2) // 2)
            depth = self._box_depth(depth_map, (x1, y1, x2, y2))
            importance = self._importance(
                label=label,
                confidence=float(score),
                bbox=(x1, y1, x2, y2),
                center=center,
                depth=depth,
                frame_shape=(h, w),
            )
            detections.append(
                DetectedObject(
                    label=label,
                    class_id=int(class_id),
                    confidence=float(score),
                    bbox=(x1, y1, x2, y2),
                    center=center,
                    depth=depth,
                    importance=importance,
                )
            )

        detections.sort(key=lambda d: d.importance, reverse=True)
        detections = detections[: self.max_detections]
        self.last_count = len(detections)
        return detections

    def _ensure_model(self) -> bool:
        if self._model is not None:
            return True
        if self.error is not None:
            return False
        try:
            import torch
            from ultralytics import YOLO

            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            self._model = YOLO(self.model_name)
            self._names = getattr(self._model, "names", {}) or {}
            return True
        except Exception as exc:
            self.error = str(exc)
            self._model = None
            return False

    def _class_label(self, class_id: int) -> str:
        name = self._names.get(class_id) if isinstance(self._names, dict) else None
        return str(name or ADAS_CLASS_IDS.get(class_id, f"class_{class_id}"))

    @staticmethod
    def _is_ego_vehicle(label: str, bbox: tuple[int, int, int, int],
                        frame_shape: tuple[int, int]) -> bool:
        """
        Heuristic: a detection is the participant's OWN car (not a real threat)
        when it is a vehicle that is large, anchored to the very bottom of the
        frame, and roughly centered. Dashcams capture the hood / dashboard /
        A-pillars which YOLO often labels 'car' or 'truck'.
        """
        if label not in {"car", "truck", "bus"}:
            return False
        h, w = frame_shape
        x1, y1, x2, y2 = bbox
        bw, bh = (x2 - x1), (y2 - y1)
        if bw <= 0 or bh <= 0:
            return False

        # Bottom-anchored: box bottom edge sits in the lowest 8% of the frame
        bottom_anchored = y2 >= h * 0.92
        # Large: covers a big slice of the frame width and a chunk of its height
        wide = bw >= w * 0.45
        tall_enough = bh >= h * 0.18
        # Centered horizontally: box center within the middle third
        cx = (x1 + x2) / 2.0
        centered = (w * 0.30) <= cx <= (w * 0.70)

        return bottom_anchored and wide and tall_enough and centered

    @staticmethod
    def _clamp_box(coords, width: int, height: int) -> tuple[int, int, int, int]:
        x1, y1, x2, y2 = [int(round(float(v))) for v in coords]
        x1 = max(0, min(width - 1, x1))
        x2 = max(0, min(width - 1, x2))
        y1 = max(0, min(height - 1, y1))
        y2 = max(0, min(height - 1, y2))
        return x1, y1, x2, y2

    @staticmethod
    def _box_depth(depth_map: np.ndarray | None, bbox: tuple[int, int, int, int]) -> float | None:
        if depth_map is None:
            return None
        x1, y1, x2, y2 = bbox
        roi = depth_map[y1:y2, x1:x2]
        if roi.size == 0:
            return None
        finite = roi[np.isfinite(roi)]
        if finite.size == 0:
            return None
        return float(np.percentile(finite, 25))

    @staticmethod
    def _importance(
        label: str,
        confidence: float,
        bbox: tuple[int, int, int, int],
        center: tuple[int, int],
        depth: float | None,
        frame_shape: tuple[int, int],
    ) -> float:
        h, w = frame_shape
        x1, y1, x2, y2 = bbox
        cx, cy = center
        depth_score = 0.5 if depth is None else 1.0 - float(np.clip(depth, 0.0, 1.0))
        center_score = 1.0 - min(1.0, abs((cx / max(w, 1)) - 0.5) / 0.5)
        lower_score = cy / max(h, 1)
        area_score = np.sqrt(((x2 - x1) * (y2 - y1)) / max(w * h, 1))
        class_weight = CLASS_WEIGHTS.get(label, 0.85)
        score = (
            0.45 * depth_score
            + 0.25 * center_score
            + 0.20 * lower_score
            + 0.10 * float(area_score)
        )
        return float(score * class_weight * confidence)
