import time
import cv2
import numpy as np
import threading
from PySide6.QtCore import QThread, Signal

class CameraGrabber(QThread):
    """
    A multithreaded camera grabber that captures frames using OpenCV in a background thread
    and emits PySide6 signals.
    """
    frame_ready = Signal(np.ndarray)
    error = Signal(str)
    
    def __init__(self, index=0, width=640, height=480, fps=30, parent=None):
        super().__init__(parent)
        self.index = index
        self.width = width
        self.height = height
        self.fps = fps
        self.running = False
        
        # Diagnostics
        self.active_width = width
        self.active_height = height
        self.current_fps = float(fps)
        
        # Thread-safe property store
        self._properties_lock = threading.Lock()
        with self._properties_lock:
            self._pending_properties = {}
        self.cap = None
        
    def start(self, *args, **kwargs):
        self.running = True
        super().start(*args, **kwargs)

    def start_capture(self, device_idx, width, height, fps, format=None):
        """
        Launches capture thread.
        """
        self.index = device_idx
        self.width = width
        self.height = height
        self.fps = fps
        self.running = True
        self.start()

    def stop_capture(self):
        """
        Sets running to False and joins thread safely.
        """
        self.running = False
        if self.isRunning():
            if not self.wait(1000):
                self.terminate()
                self.wait(500)
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def stop(self):
        """
        Alias for stop_capture to prevent breaking existing code.
        """
        self.stop_capture()

    def set_property(self, prop_id, value):
        """
        Updates camera properties thread-safely by scheduling them.
        """
        with self._properties_lock:
            self._pending_properties[prop_id] = value

    def get_diagnostics(self):
        """
        Returns a tuple of (active_width, active_height, current_fps).
        """
        return (self.active_width, self.active_height, self.current_fps)
        
    def run(self):
        import platform
        try:
            if platform.system() == "Windows":
                self.cap = cv2.VideoCapture(self.index, cv2.CAP_DSHOW)
            else:
                self.cap = cv2.VideoCapture(self.index)
        except TypeError:
            self.cap = cv2.VideoCapture(self.index)
            
        if not self.cap.isOpened():
            # Fallback to default backend
            self.cap = cv2.VideoCapture(self.index)
            
        if not self.cap.isOpened():
            self.error.emit(f"Failed to open camera index {self.index}")
            self.running = False
            return
            
        # Try to negotiate MJPG format to unlock high frame rates and high resolutions
        try:
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        except Exception:
            pass
            
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        try:
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass
        
        # Initialize diagnostics
        self.active_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH) or self.width)
        self.active_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or self.height)
        self.current_fps = float(self.cap.get(cv2.CAP_PROP_FPS) or self.fps)
        
        delay = 1.0 / self.fps if self.fps > 0 else 0.033
        
        frame_times = []
        
        while self.running:
            start_time = time.time()
            
            # Apply any pending properties inside the thread loop
            props_to_apply = {}
            with self._properties_lock:
                if self._pending_properties:
                    props_to_apply = dict(self._pending_properties)
                    self._pending_properties.clear()
            
            if props_to_apply:
                # If changing resolution, make sure FOURCC is MJPG before applying width/height
                if cv2.CAP_PROP_FRAME_WIDTH in props_to_apply or cv2.CAP_PROP_FRAME_HEIGHT in props_to_apply:
                    try:
                        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                    except Exception:
                        pass
                for prop_id, value in props_to_apply.items():
                    self.cap.set(prop_id, value)
                    if prop_id == cv2.CAP_PROP_FRAME_WIDTH:
                        self.width = int(value)
                    elif prop_id == cv2.CAP_PROP_FRAME_HEIGHT:
                        self.height = int(value)
                    elif prop_id == cv2.CAP_PROP_FPS:
                        self.fps = float(value)
                        delay = 1.0 / self.fps if self.fps > 0 else 0.033
                
                # Negotiate resolution and fps
                self.active_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH) or self.width)
                self.active_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or self.height)
                if cv2.CAP_PROP_FPS in props_to_apply:
                    self.current_fps = float(self.cap.get(cv2.CAP_PROP_FPS) or self.fps)
            
            ret, frame = self.cap.read()
            
            # Compute actual rolling FPS for diagnostics
            now = time.time()
            if ret:
                frame_times.append(now)
            frame_times = [t for t in frame_times if now - t <= 1.0]
            if len(frame_times) > 1:
                # rolling FPS over last 1 second
                span = frame_times[-1] - frame_times[0]
                if span > 0:
                    self.current_fps = (len(frame_times) - 1) / span
                else:
                    self.current_fps = 0.0
            else:
                self.current_fps = 0.0
            
            if not ret:
                self.error.emit("Failed to grab frame")
                time.sleep(0.1)
                continue
                
            self.frame_ready.emit(frame)
                
            elapsed = time.time() - start_time
            sleep_time = max(0.001, delay - elapsed)
            time.sleep(sleep_time)
            
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.running = False

