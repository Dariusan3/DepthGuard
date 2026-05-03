import time
from collections import deque
import psutil
try:
    import GPUtil
    HAS_GPUTIL = True
except ImportError:
    HAS_GPUTIL = False

class PerformanceMonitor:
    def __init__(self, history_size=100):
        self.fps_history = deque(maxlen=history_size)
        self.latency_history = deque(maxlen=history_size)
        self.last_frame_time = time.time()
        
    def record_frame(self, latency_ms):
        """Record a frame processing event with its latency"""
        current_time = time.time()
        time_diff = current_time - self.last_frame_time
        
        # Avoid division by zero
        fps = 1.0 / time_diff if time_diff > 0 else 0
        
        self.fps_history.append(fps)
        self.latency_history.append(latency_ms)
        self.last_frame_time = current_time
        
    def get_current_stats(self):
        """Returns the latest performance metrics"""
        current_fps = self.fps_history[-1] if self.fps_history else 0
        current_latency = self.latency_history[-1] if self.latency_history else 0
        
        # CPU Usage
        cpu_percent = psutil.cpu_percent()
        
        # GPU Memory (if available)
        gpu_memory_used = 0
        gpu_memory_total = 4096 # default assumption if no GPU
        if HAS_GPUTIL:
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu_memory_used = gpus[0].memoryUsed
                gpu_memory_total = gpus[0].memoryTotal
                
        # Check compatibility with targets
        nano_compatible = current_fps >= 15 and gpu_memory_used <= 4096
        xavier_compatible = current_fps >= 30 and gpu_memory_used <= 8192
        
        return {
            "fps": current_fps,
            "latency_ms": current_latency,
            "cpu_percent": cpu_percent,
            "gpu_memory_used": gpu_memory_used,
            "gpu_memory_total": gpu_memory_total,
            "nano_compatible": nano_compatible,
            "xavier_compatible": xavier_compatible
        }
        
    def get_history(self):
        """Returns lists suitable for plotting"""
        return list(self.fps_history), list(self.latency_history)
