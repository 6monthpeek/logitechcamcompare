import sys
import types
import pytest
import numpy as np
import cv2

# Define the MockVideoCapture class mimicking cv2.VideoCapture
class MockVideoCapture:
    def __init__(self, index_or_path=0):
        self.index = index_or_path
        self.width = 640
        self.height = 480
        self.fps = 30.0
        self.brightness = 50.0
        self.contrast = 50.0
        self.is_opened = True
        self.frame_count = 0
        if isinstance(index_or_path, int) and index_or_path < 0:
            self.is_opened = False

    def isOpened(self):
        return self.is_opened

    def read(self):
        if not self.is_opened:
            return False, None
        
        self.frame_count += 1
        # Generate synthetic frame: a grey background with text and grid
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        if self.index == 0:
            frame[:, :] = [50, 50, 50]  # Dark grey for A
        else:
            frame[:, :] = [70, 50, 50]  # Dark blue-grey for B

        # Draw text overlay representing camera state
        text = f"Cam {self.index} | Frame {self.frame_count} | {self.width}x{self.height}"
        cv2.putText(frame, text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # Apply scaling according to contrast and brightness
        c_scale = self.contrast / 50.0
        b_offset = (self.brightness - 50.0) * 2.0
        frame = cv2.convertScaleAbs(frame, alpha=c_scale, beta=b_offset)

        return True, frame

    def get(self, propId):
        if propId == cv2.CAP_PROP_FRAME_WIDTH:
            return self.width
        elif propId == cv2.CAP_PROP_FRAME_HEIGHT:
            return self.height
        elif propId == cv2.CAP_PROP_FPS:
            return self.fps
        elif propId == cv2.CAP_PROP_BRIGHTNESS:
            return self.brightness
        elif propId == cv2.CAP_PROP_CONTRAST:
            return self.contrast
        return 0.0

    def set(self, propId, value):
        if propId == cv2.CAP_PROP_FRAME_WIDTH:
            self.width = int(value)
            return True
        elif propId == cv2.CAP_PROP_FRAME_HEIGHT:
            self.height = int(value)
            return True
        elif propId == cv2.CAP_PROP_FPS:
            self.fps = float(value)
            return True
        elif propId == cv2.CAP_PROP_BRIGHTNESS:
            self.brightness = float(value)
            return True
        elif propId == cv2.CAP_PROP_CONTRAST:
            self.contrast = float(value)
            return True
        return False

    def release(self):
        self.is_opened = False

# Monkeypatch cv2.VideoCapture globally during test session
cv2.VideoCapture = MockVideoCapture

@pytest.fixture(autouse=True, scope="session")
def monkeypatch_cv2_video_capture():
    # Keep the fixture as autouse to ensure compatibility with pytest's fixture graph
    pass


@pytest.fixture(autouse=True)
def cleanup_mainwindow_threads():
    from src.ui.main_window import MainWindow

    created_instances = []
    original_init = MainWindow.__init__

    def patched_init(self, *args, **kwargs):
        created_instances.append(self)
        original_init(self, *args, **kwargs)

    MainWindow.__init__ = patched_init
    try:
        yield
    finally:
        MainWindow.__init__ = original_init
        for window in created_instances:
            try:
                window.stop_grabber("A")
            except Exception:
                pass
            try:
                window.stop_grabber("B")
            except Exception:
                pass



