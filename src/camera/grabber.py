import time
import cv2
import numpy as np
import threading
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

class CameraGrabber(QThread):
    """
    A multithreaded camera grabber that captures frames using OpenCV in a background thread
    and emits PySide6 signals.
    """
    frame_ready = Signal(object)
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
            
        # Thread-safe render settings store
        self._settings_lock = threading.Lock()
        with self._settings_lock:
            self.target_width = 640
            self.target_height = 480
            self.device_ratio = 1.0
            self.brightness_val = 50.0
            self.contrast_val = 50.0
            self.zoom_val = 1.0
            self.pan_offset_x = 0
            self.pan_offset_y = 0
            
        self.cap = None
        
    def update_render_settings(self, target_w, target_h, device_ratio, brightness, contrast, zoom, pan_x, pan_y):
        with self._settings_lock:
            self.target_width = target_w
            self.target_height = target_h
            self.device_ratio = device_ratio
            self.brightness_val = brightness
            self.contrast_val = contrast
            self.zoom_val = zoom
            self.pan_offset_x = pan_x
            self.pan_offset_y = pan_y
            
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
                self.cap = cv2.VideoCapture(self.index, cv2.CAP_MSMF)
                if not self.cap.isOpened():
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
        reported_fps = self.cap.get(cv2.CAP_PROP_FPS)
        if reported_fps > 0:
            self.fps = reported_fps
        self.current_fps = float(self.fps)
        
        delay = 1.0 / self.fps if self.fps > 0 else 0.033
        
        frame_times = []
        
        while self.running:
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
                
                # Negotiate resolution and fps
                self.active_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH) or self.width)
                self.active_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or self.height)
                reported_fps = self.cap.get(cv2.CAP_PROP_FPS)
                if reported_fps > 0:
                    self.fps = reported_fps
                self.current_fps = float(self.fps)
            
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
                
            # Read settings thread-safely
            with self._settings_lock:
                target_w = self.target_width
                target_h = self.target_height
                device_ratio = self.device_ratio
                brightness = self.brightness_val
                contrast = self.contrast_val
                zoom = self.zoom_val
                pan_x = self.pan_offset_x
                pan_y = self.pan_offset_y
                
            # Perform crop, resize, contrast/brightness scaling, and color conversion in background thread
            try:
                h_orig, w_orig = frame.shape[:2]
                
                # Zoom / Crop
                if zoom > 1.0:
                    crop_w = w_orig / zoom
                    crop_h = h_orig / zoom
                    
                    max_x = (w_orig - crop_w) / 2.0
                    max_y = (h_orig - crop_h) / 2.0
                    px = max(-max_x, min(float(pan_x), max_x))
                    py = max(-max_y, min(float(pan_y), max_y))
                    
                    center_x = w_orig / 2.0 + px
                    center_y = h_orig / 2.0 + py
                    
                    x_start = max(0, int(round(center_x - crop_w / 2.0)))
                    x_end = min(w_orig, int(round(center_x + crop_w / 2.0)))
                    y_start = max(0, int(round(center_y - crop_h / 2.0)))
                    y_end = min(h_orig, int(round(center_y + crop_h / 2.0)))
                    
                    if x_end > x_start and y_end > y_start:
                        frame = frame[y_start:y_end, x_start:x_end]
                        
                # Resize keeping aspect ratio
                if target_w > 0 and target_h > 0:
                    h_current, w_current = frame.shape[:2]
                    if h_current > 0:
                        aspect_ratio = w_current / h_current
                        widget_ratio = target_w / target_h
                        if widget_ratio > aspect_ratio:
                            actual_h = target_h
                            actual_w = int(target_h * aspect_ratio)
                        else:
                            actual_w = target_w
                            actual_h = int(target_w / aspect_ratio)
                        
                        phys_w = max(1, int(actual_w * device_ratio))
                        phys_h = max(1, int(actual_h * device_ratio))
                        
                        if phys_w < w_current:
                            interp = cv2.INTER_LINEAR
                        else:
                            interp = cv2.INTER_CUBIC
                        frame = cv2.resize(frame, (phys_w, phys_h), interpolation=interp)
                    
                # Adjust brightness/contrast only if changed
                if contrast != 50.0 or brightness != 50.0:
                    frame = cv2.convertScaleAbs(
                        frame,
                        alpha=contrast / 50.0,
                        beta=(brightness - 50.0) * 2.0
                    )
                    
                # Convert color space BGR -> RGB
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h_rgb, w_rgb, ch_rgb = rgb_image.shape
                bytes_per_line = ch_rgb * w_rgb
                
                # Construct QImage and copy data safely
                q_image = QImage(rgb_image.data, w_rgb, h_rgb, bytes_per_line, QImage.Format_RGB888).copy()
                q_image.setDevicePixelRatio(device_ratio)
                
                self.frame_ready.emit(q_image)
            except Exception as e:
                # Fallback to emitting raw frame if processing fails
                self.frame_ready.emit(frame)
                
            # Yield control to the OS scheduler is naturally handled by the blocking cap.read() call.
            
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.running = False

