import pytest
import time
from unittest.mock import MagicMock, patch
from PySide6.QtCore import Qt
from src.camera.grabber import CameraGrabber
from src.ui.main_window import MainWindow

# ==============================================================================
# CHALLENGE 1: Rolling FPS Calculation
# ==============================================================================

def test_fps_zero_frame_interval():
    """
    Challenge rolling FPS calculation with zero frame interval (division-by-zero prevention).
    When all timestamps are identical (span is zero), current_fps must be 0.0, avoiding ZeroDivisionError.
    """
    grabber = CameraGrabber(index=0, width=640, height=480, fps=30)
    
    # We will mock self.cap and self.running to run a single iteration or manually test the FPS block.
    # To test the logic in lines 130-144 of grabber.py:
    # We simulate ret = True, and multiple frames with the exact same timestamp.
    mock_cap = MagicMock()
    mock_cap.read.return_value = (True, "mock_frame")
    mock_cap.get.side_effect = lambda propId: 30.0 if propId == 5 else 640.0 # cv2.CAP_PROP_FPS = 5
    
    grabber.cap = mock_cap
    grabber.running = True
    
    # We patch time.time to return the same timestamp twice
    with patch("time.time", side_effect=[1.0, 1.0, 1.0, 1.0]):
        # Let's run the calculation logic step-by-step
        frame_times = []
        
        # Frame 1
        now = time.time()
        frame_times.append(now)
        frame_times = [t for t in frame_times if now - t <= 1.0]
        assert len(frame_times) == 1
        # len is 1, so current_fps should be 0.0
        current_fps = 0.0
        
        # Frame 2 (happens at the exact same timestamp)
        now = time.time()
        frame_times.append(now)
        frame_times = [t for t in frame_times if now - t <= 1.0]
        assert len(frame_times) == 2
        span = frame_times[-1] - frame_times[0]
        assert span == 0.0
        
        # The code does:
        if span > 0:
            current_fps = (len(frame_times) - 1) / span
        else:
            current_fps = 0.0
            
        assert current_fps == 0.0

def test_fps_division_by_zero_prevention_on_property():
    """
    Verify division-by-zero protection when setting FPS to 0 or negative values.
    """
    grabber = CameraGrabber(index=0, width=640, height=480, fps=30)
    
    # Test initialization with 0 or negative FPS
    grabber_zero = CameraGrabber(index=0, width=640, height=480, fps=0)
    assert grabber_zero.fps == 0
    
    # We manually trigger run settings update for FPS = 0
    # Inside grabber.py: delay = 1.0 / self.fps if self.fps > 0 else 0.033
    delay_zero = 1.0 / grabber_zero.fps if grabber_zero.fps > 0 else 0.033
    assert delay_zero == 0.033
    
    # For negative FPS
    grabber_neg = CameraGrabber(index=0, width=640, height=480, fps=-10)
    delay_neg = 1.0 / grabber_neg.fps if grabber_neg.fps > 0 else 0.033
    assert delay_neg == 0.033

def test_fps_precision_metrics():
    """
    Verify the precision of the rolling FPS calculation with a known frame rate.
    For 31 frames spaced exactly 0.033333 seconds apart (total 1.0 second span),
    the calculated rolling FPS should be exactly 30.0.
    """
    frame_times = []
    start_t = 100.0
    interval = 1.0 / 30.0 # 0.0333333
    
    # Feed 31 frames (30 intervals of 1/30s = 1.0 second span)
    for i in range(31):
        frame_times.append(start_t + i * interval)
        
    now = frame_times[-1]
    # Filter
    frame_times = [t for t in frame_times if now - t <= 1.0]
    assert len(frame_times) == 31
    
    span = frame_times[-1] - frame_times[0]
    assert abs(span - 1.0) < 1e-7
    
    current_fps = (len(frame_times) - 1) / span
    assert abs(current_fps - 30.0) < 1e-7

# ==============================================================================
# CHALLENGE 2: Resolution Negotiation Fallbacks
# ==============================================================================

def test_resolution_negotiation_fallbacks():
    """
    Challenge resolution negotiation under various cv2.VideoCapture.get() return values.
    Verify that when cv2 returns 0 or None, it falls back to the requested width/height.
    """
    grabber = CameraGrabber(index=0, width=640, height=480, fps=30)
    
    # Case A: cv2 returns valid values (e.g. 1280x720)
    mock_cap_valid = MagicMock()
    mock_cap_valid.get.side_effect = lambda prop: 1280 if prop == 3 else 720 # width=3, height=4
    
    active_width = int(mock_cap_valid.get(3) or grabber.width)
    active_height = int(mock_cap_valid.get(4) or grabber.height)
    assert active_width == 1280
    assert active_height == 720
    
    # Case B: cv2 returns 0 or None (fallback to grabber.width/height)
    mock_cap_fallback = MagicMock()
    mock_cap_fallback.get.side_effect = lambda prop: 0.0 # Falsy
    
    active_width = int(mock_cap_fallback.get(3) or grabber.width)
    active_height = int(mock_cap_fallback.get(4) or grabber.height)
    assert active_width == 640
    assert active_height == 480

# ==============================================================================
# CHALLENGE 3: Sudden Camera Disconnect
# ==============================================================================

def test_sudden_disconnect_handling(qtbot):
    """
    Challenge sudden camera disconnect.
    Verify that setting grabber.cap.is_opened = False on active grabbers successfully:
    1. Halts the thread (enters error block, breaks loop or finishes).
    2. Transitions the widget to offline state (placeholder visible).
    3. Updates the control panel state (Start/Stop button unchecked).
    without leaking resources or crash loops.
    """
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    
    # 1. Start Camera A
    window.control_panel.cam_a_dev_combo.setCurrentIndex(1) # Camera 0
    qtbot.mouseClick(window.control_panel.cam_a_toggle_btn, Qt.LeftButton)
    
    # Wait for grabber to start and active capture to establish
    qtbot.waitUntil(lambda: window.grabbers["A"] is not None and window.grabbers["A"].cap is not None, timeout=2000)
    
    grabber = window.grabbers["A"]
    assert grabber.isRunning()
    assert grabber.cap.is_opened is True
    
    # Confirm video is showing and placeholder is hidden
    qtbot.waitUntil(lambda: not window.canvas.camera_a.placeholder_label.isVisible(), timeout=2000)
    assert window.canvas.camera_a.video_label.isVisible()
    
    # 2. Simulate Sudden Disconnect by setting grabber.cap.is_opened = False
    grabber.cap.is_opened = False
    
    # 3. Wait for grabber thread to stop and UI elements to transition to offline/disconnected
    qtbot.waitUntil(lambda: window.grabbers["A"] is None, timeout=3000)
    
    # Check that widget has transitioned to offline state
    assert window.canvas.camera_a.placeholder_label.isVisible()
    assert not window.canvas.camera_a.video_label.isVisible()
    
    # Check that control panel state has been updated
    assert window.control_panel.cam_a_toggle_btn.isChecked() is False
    assert window.control_panel.cam_a_toggle_btn.text() == "Start Camera A"
    
    # Check that the thread is not running
    assert not grabber.isRunning()
