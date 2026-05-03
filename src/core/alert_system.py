import numpy as np

class SafetyAlertSystem:
    # Alert levels mapping to string and color codes
    LEVELS = {
        "SAFE": {"text": "✅ SAFE", "color": "#00AA00", "bg": "#00AA00"},
        "CAUTION": {"text": "⚠ CAUTION", "color": "#CCAA00", "bg": "#CCAA00"},
        "WARNING": {"text": "⚠️ WARNING", "color": "#FF8C00", "bg": "#FF8C00"},
        "CRITICAL": {"text": "🚨 CRITICAL - BRAKE NOW!", "color": "#FFFFFF", "bg": "#CC0000"}
    }

    def __init__(self):
        # ROI definition: 40%-80% height, 30%-70% width
        self.roi_ymin = 0.4
        self.roi_ymax = 0.8
        self.roi_xmin = 0.3
        self.roi_xmax = 0.7

    def process_depth(self, depth_map):
        """
        Analyzes the central ROI of the depth map to determine safety alert level.
        Expects depth_map with values between 0.0 (closest) and 1.0 (farthest).
        """
        h, w = depth_map.shape[:2]
        
        # Calculate pixel coordinates for ROI
        y1, y2 = int(h * self.roi_ymin), int(h * self.roi_ymax)
        x1, x2 = int(w * self.roi_xmin), int(w * self.roi_xmax)
        
        # Extract ROI
        roi = depth_map[y1:y2, x1:x2]
        
        # Calculate heuristics
        min_depth = np.min(roi)
        avg_depth = np.mean(roi)
        
        # Determine alert level
        level = self.get_alert_level(min_depth)
        
        return {
            "level": level,
            "min_depth": float(min_depth),
            "avg_depth": float(avg_depth),
            "roi_coords": (x1, y1, x2, y2),
            "ui_data": self.LEVELS[level]
        }

    def get_alert_level(self, min_depth):
        if min_depth < 0.15:
            return "CRITICAL"
        elif min_depth < 0.30:
            return "WARNING"
        elif min_depth < 0.50:
            return "CAUTION"
        else:
            return "SAFE"
