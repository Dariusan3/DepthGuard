import time
import cv2
import numpy as np

class MockModel:
    def __init__(self):
        self.latency = 0.033  # Simulate ~30fps 

    def inference(self, frame):
        """
        Takes a BGR video frame and returns a synthetic pseudo-color depth map.
        Simulates inference time delay.
        """
        # Simulate network latency
        time.sleep(self.latency)
        
        h, w = frame.shape[:2]
        
        # Create a gradient background (close at bottom, far at top)
        # Closer objects are darker/warmer in JET usually, but let's make 
        # a 0.0 to 1.0 depth map where 0 is close and 1 is far.
        y_indices = np.linspace(1.0, 0.0, h)
        depth_map = np.tile(y_indices[:, None], (1, w))
        
        # Simulate a vehicle ahead in the center
        center_y, center_x = int(h * 0.6), int(w * 0.5)
        radius_y, radius_x = int(h * 0.15), int(w * 0.15)
        
        y, x = np.ogrid[:h, :w]
        dist_from_center = ((y - center_y) ** 2) / (radius_y ** 2) + ((x - center_x) ** 2) / (radius_x ** 2)
        
        # Make the "vehicle" closer (e.g., depth = 0.2)
        vehicle_mask = dist_from_center <= 1
        
        # Add some noise and movement simulation
        # Using a slight oscillating depth for the vehicle
        oscillation = np.sin(time.time() * 2) * 0.1
        base_vehicle_depth = 0.3 + oscillation
        
        depth_map[vehicle_mask] = base_vehicle_depth
        
        # Add general noise
        noise = np.random.normal(0, 0.02, (h, w))
        depth_map = np.clip(depth_map + noise, 0, 1)
        
        return depth_map
