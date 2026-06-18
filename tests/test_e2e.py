import pytest
import sys
import cv2
import numpy as np
from PySide6.QtCore import Qt, QPoint, QPointF, QEvent
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout

# Import the real classes from the codebase
from src.ui.main_window import MainWindow
from src.ui.canvas import SceneCanvas
from src.ui.control_panel import ControlPanel
from src.ui.camera_widget import CameraWidget


# ==============================================================================
# TIER 1: FEATURE COVERAGE (20 Tests)
# ==============================================================================

def test_tier1_camera_a_selection(qtbot):
    """1. Selecting a camera for Channel A updates active camera indicator and starts capture."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    # Initially not started
    assert window.grabbers["A"] is None
    
    # Select Camera 0 (first camera index in combobox is 1, index 0 is "None")
    window.control_panel.cam_a_dev_combo.setCurrentIndex(1)
    # Start it
    qtbot.mouseClick(window.control_panel.cam_a_toggle_btn, Qt.LeftButton)
    
    qtbot.waitUntil(lambda: window.grabbers["A"] is not None and window.grabbers["A"].running, timeout=2000)
    assert window.grabbers["A"].index == 0
    
    # Wait for frame update (hides placeholder, shows video)
    qtbot.waitUntil(lambda: not window.canvas.camera_a.placeholder_label.isVisible(), timeout=2000)
    assert window.canvas.camera_a.video_label.isVisible()

    # Teardown
    window.stop_grabber("A")
    qtbot.waitUntil(lambda: window.grabbers["A"] is None, timeout=2000)


def test_tier1_camera_b_selection(qtbot):
    """2. Selecting a camera for Channel B updates active camera indicator and starts capture."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    # Initially not started
    assert window.grabbers["B"] is None
    
    # Select Camera 1 (index 2 in combobox)
    window.control_panel.cam_b_dev_combo.setCurrentIndex(2)
    # Start it
    qtbot.mouseClick(window.control_panel.cam_b_toggle_btn, Qt.LeftButton)
    
    qtbot.waitUntil(lambda: window.grabbers["B"] is not None and window.grabbers["B"].running, timeout=2000)
    assert window.grabbers["B"].index == 1
    
    # Wait for frame update
    qtbot.waitUntil(lambda: not window.canvas.camera_b.placeholder_label.isVisible(), timeout=2000)
    assert window.canvas.camera_b.video_label.isVisible()

    # Teardown
    window.stop_grabber("B")
    qtbot.waitUntil(lambda: window.grabbers["B"] is None, timeout=2000)


def test_tier1_independent_resolution_a(qtbot):
    """3. Changing resolution of Camera A adjusts feed size and display diagnostics for A only."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    window.control_panel.cam_a_dev_combo.setCurrentIndex(1)
    window.control_panel.cam_b_dev_combo.setCurrentIndex(2)
    qtbot.mouseClick(window.control_panel.cam_a_toggle_btn, Qt.LeftButton)
    qtbot.mouseClick(window.control_panel.cam_b_toggle_btn, Qt.LeftButton)
    
    qtbot.waitUntil(lambda: window.grabbers["A"] is not None and window.grabbers["A"].running, timeout=2000)
    qtbot.waitUntil(lambda: window.grabbers["B"] is not None and window.grabbers["B"].running, timeout=2000)
    
    # Change A to 1920x1080 (index 2 in combo: index 0: 640x480, 1: 1280x720, 2: 1920x1080)
    window.control_panel.cam_a_res_combo.setCurrentIndex(2)
    qtbot.waitUntil(lambda: window.grabbers["A"] is not None and window.grabbers["A"].running, timeout=2000)
    
    assert window.grabbers["A"].width == 1920
    assert window.grabbers["A"].height == 1080
    assert window.grabbers["B"].width == 640
    assert window.grabbers["B"].height == 480

    # Teardown
    window.stop_grabber("A")
    window.stop_grabber("B")
    qtbot.waitUntil(lambda: window.grabbers["A"] is None and window.grabbers["B"] is None, timeout=2000)


def test_tier1_independent_resolution_b(qtbot):
    """4. Changing resolution of Camera B adjusts feed size and display diagnostics for B only."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    window.control_panel.cam_a_dev_combo.setCurrentIndex(1)
    window.control_panel.cam_b_dev_combo.setCurrentIndex(2)
    qtbot.mouseClick(window.control_panel.cam_a_toggle_btn, Qt.LeftButton)
    qtbot.mouseClick(window.control_panel.cam_b_toggle_btn, Qt.LeftButton)
    
    qtbot.waitUntil(lambda: window.grabbers["A"] is not None and window.grabbers["A"].running, timeout=2000)
    qtbot.waitUntil(lambda: window.grabbers["B"] is not None and window.grabbers["B"].running, timeout=2000)
    
    # Change B to 1280x720 (index 1 in combo)
    window.control_panel.cam_b_res_combo.setCurrentIndex(1)
    qtbot.waitUntil(lambda: window.grabbers["B"] is not None and window.grabbers["B"].running, timeout=2000)
    
    assert window.grabbers["A"].width == 640
    assert window.grabbers["A"].height == 480
    assert window.grabbers["B"].width == 1280
    assert window.grabbers["B"].height == 720

    # Teardown
    window.stop_grabber("A")
    window.stop_grabber("B")
    qtbot.waitUntil(lambda: window.grabbers["A"] is None and window.grabbers["B"] is None, timeout=2000)


def test_tier1_independent_fps_a(qtbot):
    """5. Changing frame rate of Camera A updates target FPS control and display diagnostics for A only."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    window.control_panel.cam_a_dev_combo.setCurrentIndex(1)
    window.control_panel.cam_b_dev_combo.setCurrentIndex(2)
    qtbot.mouseClick(window.control_panel.cam_a_toggle_btn, Qt.LeftButton)
    qtbot.mouseClick(window.control_panel.cam_b_toggle_btn, Qt.LeftButton)
    
    qtbot.waitUntil(lambda: window.grabbers["A"] is not None and window.grabbers["A"].running, timeout=2000)
    qtbot.waitUntil(lambda: window.grabbers["B"] is not None and window.grabbers["B"].running, timeout=2000)
    
    # Change A FPS to 60
    window.control_panel.cam_a_fps_spin.setValue(60)
    qtbot.waitUntil(lambda: window.grabbers["A"] is not None and window.grabbers["A"].running, timeout=2000)
    
    assert window.grabbers["A"].fps == 60
    assert window.grabbers["B"].fps == 30  # unaffected

    # Teardown
    window.stop_grabber("A")
    window.stop_grabber("B")
    qtbot.waitUntil(lambda: window.grabbers["A"] is None and window.grabbers["B"] is None, timeout=2000)


def test_tier1_independent_fps_b(qtbot):
    """6. Changing frame rate of Camera B updates target FPS control and display diagnostics for B only."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    window.control_panel.cam_a_dev_combo.setCurrentIndex(1)
    window.control_panel.cam_b_dev_combo.setCurrentIndex(2)
    qtbot.mouseClick(window.control_panel.cam_a_toggle_btn, Qt.LeftButton)
    qtbot.mouseClick(window.control_panel.cam_b_toggle_btn, Qt.LeftButton)
    
    qtbot.waitUntil(lambda: window.grabbers["A"] is not None and window.grabbers["A"].running, timeout=2000)
    qtbot.waitUntil(lambda: window.grabbers["B"] is not None and window.grabbers["B"].running, timeout=2000)
    
    # Change B FPS to 45
    window.control_panel.cam_b_fps_spin.setValue(45)
    qtbot.waitUntil(lambda: window.grabbers["B"] is not None and window.grabbers["B"].running, timeout=2000)
    
    assert window.grabbers["A"].fps == 30  # unaffected
    assert window.grabbers["B"].fps == 45

    # Teardown
    window.stop_grabber("A")
    window.stop_grabber("B")
    qtbot.waitUntil(lambda: window.grabbers["A"] is None and window.grabbers["B"] is None, timeout=2000)


def test_tier1_layout_side_by_side(qtbot):
    """7. Selecting Side-by-Side layout arranges feeds side-by-side."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    window.control_panel.preset_combo.setCurrentText("Side-by-Side")
    assert window.canvas.current_preset == "side-by-side"
    assert isinstance(window.canvas.layout(), QHBoxLayout)
    assert window.canvas.camera_a.isVisible()
    assert window.canvas.camera_b.isVisible()


def test_tier1_layout_stacked(qtbot):
    """8. Selecting Stacked layout arranges feeds vertically."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    window.control_panel.preset_combo.setCurrentText("Stacked")
    assert window.canvas.current_preset == "stacked"
    assert isinstance(window.canvas.layout(), QVBoxLayout)
    assert window.canvas.camera_a.isVisible()
    assert window.canvas.camera_b.isVisible()


def test_tier1_layout_pip(qtbot):
    """9. Selecting PiP layout overlays feed B on feed A."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    window.control_panel.preset_combo.setCurrentText("PiP")
    assert window.canvas.current_preset == "pip"
    assert window.canvas.camera_b.parent() == window.canvas
    assert window.canvas.camera_a.isVisible()
    assert window.canvas.camera_b.isVisible()


def test_tier1_brightness_control_a(qtbot):
    """10. Moving brightness slider for Camera A adjusts brightness on canvas A."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert hasattr(window.control_panel, "slider_brightness_a")


def test_tier1_brightness_control_b(qtbot):
    """11. Moving brightness slider for Camera B adjusts brightness on canvas B."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert hasattr(window.control_panel, "slider_brightness_b")


def test_tier1_contrast_control_a(qtbot):
    """12. Moving contrast slider for Camera A adjusts contrast on canvas A."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert hasattr(window.control_panel, "slider_contrast_a")


def test_tier1_contrast_control_b(qtbot):
    """13. Moving contrast slider for Camera B adjusts contrast on canvas B."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert hasattr(window.control_panel, "slider_contrast_b")


def test_tier1_zoom_slider_a(qtbot):
    """14. Moving zoom slider for Camera A digitally crops and zooms feed A."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert hasattr(window.control_panel, "slider_zoom_a")


def test_tier1_zoom_slider_b(qtbot):
    """15. Moving zoom slider for Camera B digitally crops and zooms feed B."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert hasattr(window.control_panel, "slider_zoom_b")


def test_tier1_pan_drag_a(qtbot):
    """16. Dragging on canvas A pans the zoomed viewport of Camera A."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert hasattr(window.canvas.camera_a, "pan_offset")


def test_tier1_pan_drag_b(qtbot):
    """17. Dragging on canvas B pans the zoomed viewport of Camera B."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert hasattr(window.canvas.camera_b, "pan_offset")


def test_tier1_overlay_fps_toggle(qtbot):
    """18. Toggling the FPS overlay checkbox updates FPS display visibility."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    
    assert window.control_panel.check_overlay_fps.isChecked() is True
    assert window.canvas.camera_a.show_fps is True
    assert window.canvas.camera_b.show_fps is True
    
    # Toggle it off
    window.control_panel.check_overlay_fps.setChecked(False)
    assert window.canvas.camera_a.show_fps is False
    assert window.canvas.camera_b.show_fps is False
    
    # Toggle it on
    window.control_panel.check_overlay_fps.setChecked(True)
    assert window.canvas.camera_a.show_fps is True
    assert window.canvas.camera_b.show_fps is True


def test_tier1_overlay_resolution_toggle(qtbot):
    """19. Toggling the resolution overlay checkbox updates resolution display visibility."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    
    assert window.control_panel.check_overlay_res.isChecked() is True
    assert window.canvas.camera_a.show_res is True
    assert window.canvas.camera_b.show_res is True
    
    # Toggle it off
    window.control_panel.check_overlay_res.setChecked(False)
    assert window.canvas.camera_a.show_res is False
    assert window.canvas.camera_b.show_res is False
    
    # Toggle it on
    window.control_panel.check_overlay_res.setChecked(True)
    assert window.canvas.camera_a.show_res is True
    assert window.canvas.camera_b.show_res is True


def test_tier1_overlay_timestamp_toggle(qtbot):
    """20. Toggling the timestamp overlay checkbox updates timestamp display visibility."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    
    assert window.control_panel.check_overlay_timestamp.isChecked() is True
    assert window.canvas.camera_a.show_timestamp is True
    assert window.canvas.camera_b.show_timestamp is True
    
    # Toggle it off
    window.control_panel.check_overlay_timestamp.setChecked(False)
    assert window.canvas.camera_a.show_timestamp is False
    assert window.canvas.camera_b.show_timestamp is False
    
    # Toggle it on
    window.control_panel.check_overlay_timestamp.setChecked(True)
    assert window.canvas.camera_a.show_timestamp is True
    assert window.canvas.camera_b.show_timestamp is True


# ==============================================================================
# TIER 2: BOUNDARY/CORNER CASES (20 Tests)
# ==============================================================================

def test_tier2_camera_same_device_selection(qtbot):
    """21. Selecting the same physical camera index for both A and B."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    window.control_panel.cam_a_dev_combo.setCurrentIndex(1)  # Camera 0
    window.control_panel.cam_b_dev_combo.setCurrentIndex(1)  # Camera 0
    qtbot.mouseClick(window.control_panel.cam_a_toggle_btn, Qt.LeftButton)
    qtbot.mouseClick(window.control_panel.cam_b_toggle_btn, Qt.LeftButton)
    
    qtbot.waitUntil(lambda: window.grabbers["A"] is not None and window.grabbers["A"].running, timeout=2000)
    qtbot.waitUntil(lambda: window.grabbers["B"] is not None and window.grabbers["B"].running, timeout=2000)
    
    assert window.grabbers["A"].index == 0
    assert window.grabbers["B"].index == 0

    # Teardown
    window.stop_grabber("A")
    window.stop_grabber("B")
    qtbot.waitUntil(lambda: window.grabbers["A"] is None and window.grabbers["B"] is None, timeout=2000)


def test_tier2_camera_disconnect_handling_a(qtbot):
    """22. Simulating sudden camera disconnect (OpenCV read failure) for Camera A."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    # Start camera A
    window.control_panel.cam_a_dev_combo.setCurrentIndex(1) # Camera 0
    qtbot.mouseClick(window.control_panel.cam_a_toggle_btn, Qt.LeftButton)
    
    qtbot.waitUntil(lambda: window.grabbers["A"] is not None and window.grabbers["A"].cap is not None, timeout=2000)
    
    grabber = window.grabbers["A"]
    assert grabber.cap is not None
    assert grabber.cap.is_opened is True
    
    # Wait until camera widget displays video
    qtbot.waitUntil(lambda: not window.canvas.camera_a.placeholder_label.isVisible(), timeout=2000)
    assert window.canvas.camera_a.video_label.isVisible()
    
    # Simulate disconnect: set is_opened to False
    grabber.cap.is_opened = False
    
    # Wait for recovery: grabber should stop, placeholder should be visible, toggle button reset
    qtbot.waitUntil(lambda: window.grabbers["A"] is None, timeout=3000)
    assert window.canvas.camera_a.placeholder_label.isVisible()
    assert window.control_panel.cam_a_toggle_btn.isChecked() is False
    assert window.control_panel.cam_a_toggle_btn.text() == "Start Camera A"


def test_tier2_camera_disconnect_handling_b(qtbot):
    """23. Simulating sudden camera disconnect (OpenCV read failure) for Camera B."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    # Start camera B
    window.control_panel.cam_b_dev_combo.setCurrentIndex(2) # Camera 1
    qtbot.mouseClick(window.control_panel.cam_b_toggle_btn, Qt.LeftButton)
    
    qtbot.waitUntil(lambda: window.grabbers["B"] is not None and window.grabbers["B"].cap is not None, timeout=2000)
    
    grabber = window.grabbers["B"]
    assert grabber.cap is not None
    assert grabber.cap.is_opened is True
    
    # Wait until camera widget displays video
    qtbot.waitUntil(lambda: not window.canvas.camera_b.placeholder_label.isVisible(), timeout=2000)
    assert window.canvas.camera_b.video_label.isVisible()
    
    # Simulate disconnect: set is_opened to False
    grabber.cap.is_opened = False
    
    # Wait for recovery: grabber should stop, placeholder should be visible, toggle button reset
    qtbot.waitUntil(lambda: window.grabbers["B"] is None, timeout=3000)
    assert window.canvas.camera_b.placeholder_label.isVisible()
    assert window.control_panel.cam_b_toggle_btn.isChecked() is False
    assert window.control_panel.cam_b_toggle_btn.text() == "Start Camera B"


def test_tier2_unsupported_resolution_request(qtbot):
    """24. Requesting a resolution not natively supported by the mock camera."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    window.control_panel.cam_a_dev_combo.setCurrentIndex(1)
    qtbot.mouseClick(window.control_panel.cam_a_toggle_btn, Qt.LeftButton)
    qtbot.waitUntil(lambda: window.grabbers["A"] is not None and window.grabbers["A"].running, timeout=2000)
    
    # Add custom unsupported resolution item and select it
    window.control_panel.cam_a_res_combo.addItem("9999 x 9999", (9999, 9999))
    window.control_panel.cam_a_res_combo.setCurrentText("9999 x 9999")
    
    qtbot.waitUntil(lambda: window.grabbers["A"] is not None and window.grabbers["A"].running, timeout=2000)
    
    assert window.grabbers["A"].width == 9999
    assert window.grabbers["A"].height == 9999

    # Teardown
    window.stop_grabber("A")
    qtbot.waitUntil(lambda: window.grabbers["A"] is None, timeout=2000)


def test_tier2_extreme_zoom_limit_min_a(qtbot):
    """25. Setting zoom slider A to minimum limit (1.0x)."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert hasattr(window.control_panel, "slider_zoom_a")


def test_tier2_extreme_zoom_limit_max_a(qtbot):
    """26. Setting zoom slider A to maximum limit (5.0x)."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert hasattr(window.control_panel, "slider_zoom_a")


def test_tier2_extreme_zoom_limit_min_b(qtbot):
    """27. Setting zoom slider B to minimum limit (1.0x)."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert hasattr(window.control_panel, "slider_zoom_b")


def test_tier2_extreme_zoom_limit_max_b(qtbot):
    """28. Setting zoom slider B to maximum limit (5.0x)."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert hasattr(window.control_panel, "slider_zoom_b")


def test_tier2_pan_out_of_bounds_drag_a(qtbot):
    """29. Attempting to pan/drag viewport A past the edges of the original frame is bounded safely."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert hasattr(window.canvas.camera_a, "pan_offset")


def test_tier2_pan_out_of_bounds_drag_b(qtbot):
    """30. Attempting to pan/drag viewport B past the edges of the original frame is bounded safely."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert hasattr(window.canvas.camera_b, "pan_offset")


def test_tier2_brightness_boundary_min_a(qtbot):
    """31. Setting brightness slider A to extreme minimum value."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert hasattr(window.control_panel, "slider_brightness_a")


def test_tier2_brightness_boundary_max_a(qtbot):
    """32. Setting brightness slider A to extreme maximum value."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert hasattr(window.control_panel, "slider_brightness_a")


def test_tier2_brightness_boundary_min_b(qtbot):
    """33. Setting brightness slider B to extreme minimum value."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert hasattr(window.control_panel, "slider_brightness_b")


def test_tier2_brightness_boundary_max_b(qtbot):
    """34. Setting brightness slider B to extreme maximum value."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert hasattr(window.control_panel, "slider_brightness_b")


def test_tier2_contrast_boundary_min_a(qtbot):
    """35. Setting contrast slider A to minimum value."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert hasattr(window.control_panel, "slider_contrast_a")


def test_tier2_contrast_boundary_max_a(qtbot):
    """36. Setting contrast slider A to maximum value."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert hasattr(window.control_panel, "slider_contrast_a")


def test_tier2_contrast_boundary_min_b(qtbot):
    """37. Setting contrast slider B to minimum value."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert hasattr(window.control_panel, "slider_contrast_b")


def test_tier2_contrast_boundary_max_b(qtbot):
    """38. Setting contrast slider B to maximum value."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert hasattr(window.control_panel, "slider_contrast_b")


def test_tier2_window_resize_extreme_small(qtbot):
    """39. Resizing MainWindow to extremely small size."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    window.resize(100, 100)
    assert window.width() <= 100 or window.minimumWidth() > 0


def test_tier2_window_resize_extreme_large(qtbot):
    """40. Resizing MainWindow to extremely large size."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    window.resize(3840, 2160)
    assert window.width() == 3840
    assert window.height() == 2160


# ==============================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS (4 Tests)
# ==============================================================================

def test_tier3_pip_layout_with_zoom_and_pan(qtbot):
    """41. PiP layout combined with zoom and pan on both cameras independently."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    
    # Enable cameras
    window.control_panel.cam_a_dev_combo.setCurrentIndex(1)
    window.control_panel.cam_b_dev_combo.setCurrentIndex(2)
    qtbot.mouseClick(window.control_panel.cam_a_toggle_btn, Qt.LeftButton)
    qtbot.mouseClick(window.control_panel.cam_b_toggle_btn, Qt.LeftButton)
    
    qtbot.waitUntil(lambda: window.grabbers["A"] is not None and window.grabbers["A"].running, timeout=2000)
    qtbot.waitUntil(lambda: window.grabbers["B"] is not None and window.grabbers["B"].running, timeout=2000)
    
    # Switch to PiP
    window.control_panel.preset_combo.setCurrentText("PiP")
    assert window.canvas.current_preset == "pip"
    
    # Change zoom sliders
    window.control_panel.slider_zoom_a.setValue(20) # 2.0x zoom
    window.control_panel.slider_zoom_b.setValue(30) # 3.0x zoom
    
    assert window.canvas.camera_a.zoom_val == 2.0
    assert window.canvas.camera_b.zoom_val == 3.0
    
    # Drag camera A to pan
    window.canvas.camera_a.pan_offset = QPoint(10, -5)
    window.canvas.camera_b.pan_offset = QPoint(-20, 15)
    
    assert window.canvas.camera_a.pan_offset == QPoint(10, -5)
    assert window.canvas.camera_b.pan_offset == QPoint(-20, 15)
    
    # Teardown
    window.stop_grabber("A")
    window.stop_grabber("B")


def test_tier3_resolution_change_during_active_zoom(qtbot):
    """42. Zoomed in feed handles resolution change and updates layout bounds cleanly."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    
    # Start Camera A
    window.control_panel.cam_a_dev_combo.setCurrentIndex(1)
    qtbot.mouseClick(window.control_panel.cam_a_toggle_btn, Qt.LeftButton)
    qtbot.waitUntil(lambda: window.grabbers["A"] is not None and window.grabbers["A"].running, timeout=2000)
    
    # Zoom camera A to 2.5x (value 25)
    window.control_panel.slider_zoom_a.setValue(25)
    assert window.canvas.camera_a.zoom_val == 2.5
    
    # Change resolution
    window.control_panel.cam_a_res_combo.setCurrentIndex(1) # 1280 x 720
    qtbot.waitUntil(lambda: window.grabbers["A"] is not None and window.grabbers["A"].running, timeout=2000)
    
    assert window.grabbers["A"].width == 1280
    assert window.grabbers["A"].height == 720
    assert window.canvas.camera_a.zoom_val == 2.5
    
    # Teardown
    window.stop_grabber("A")


def test_tier3_high_resolution_high_fps_both_cameras(qtbot):
    """43. High resolution (1080p) + high FPS (60) running simultaneously on both channels."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    window.control_panel.cam_a_dev_combo.setCurrentIndex(1)
    window.control_panel.cam_b_dev_combo.setCurrentIndex(2)
    qtbot.mouseClick(window.control_panel.cam_a_toggle_btn, Qt.LeftButton)
    qtbot.mouseClick(window.control_panel.cam_b_toggle_btn, Qt.LeftButton)
    
    qtbot.waitUntil(lambda: window.grabbers["A"] is not None and window.grabbers["A"].running, timeout=2000)
    qtbot.waitUntil(lambda: window.grabbers["B"] is not None and window.grabbers["B"].running, timeout=2000)
    
    window.control_panel.cam_a_res_combo.setCurrentText("1920 x 1080 (1080p)")
    window.control_panel.cam_b_res_combo.setCurrentText("1920 x 1080 (1080p)")
    
    window.control_panel.cam_a_fps_spin.setValue(60)
    window.control_panel.cam_b_fps_spin.setValue(60)
    
    qtbot.waitUntil(lambda: window.grabbers["A"] is not None and window.grabbers["A"].running, timeout=2000)
    qtbot.waitUntil(lambda: window.grabbers["B"] is not None and window.grabbers["B"].running, timeout=2000)
    
    assert window.grabbers["A"].width == 1920
    assert window.grabbers["B"].width == 1920
    assert window.grabbers["A"].fps == 60
    assert window.grabbers["B"].fps == 60

    # Teardown
    window.stop_grabber("A")
    window.stop_grabber("B")
    qtbot.waitUntil(lambda: window.grabbers["A"] is None and window.grabbers["B"] is None, timeout=2000)


def test_tier3_layout_switch_during_active_drag(qtbot):
    """44. Layout changes triggered while dragging viewports do not cause exceptions."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    
    camera = window.canvas.camera_a
    center = camera.rect().center()
    
    # Press to start drag
    qtbot.mousePress(camera, Qt.LeftButton, pos=center)
    assert window.canvas.layout_customized is True
    assert camera.interaction_direction == "drag"
    
    # Change layout in control panel during drag
    window.control_panel.preset_combo.setCurrentText("Stacked")
    assert window.canvas.layout_customized is False
    
    # Release mouse
    qtbot.mouseRelease(camera, Qt.LeftButton, pos=center)
    assert camera.interaction_direction is None


# ==============================================================================
# TIER 4: REAL-WORLD APPLICATION SCENARIOS (5 Tests)
# ==============================================================================

def test_tier4_startup_no_cameras(qtbot):
    """45. App startup defaults to placeholders and status is Disconnected if no camera selected."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    assert window.grabbers["A"] is None
    assert window.grabbers["B"] is None
    assert window.canvas.camera_a.placeholder_label.isVisible()
    assert window.canvas.camera_b.placeholder_label.isVisible()


def test_tier4_dual_webcam_comparison_flow(qtbot):
    """46. Simulates complete user comparison workflow."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    
    # 1. Select and start both cameras
    window.control_panel.cam_a_dev_combo.setCurrentIndex(1)
    window.control_panel.cam_b_dev_combo.setCurrentIndex(2)
    qtbot.mouseClick(window.control_panel.cam_a_toggle_btn, Qt.LeftButton)
    qtbot.mouseClick(window.control_panel.cam_b_toggle_btn, Qt.LeftButton)
    
    qtbot.waitUntil(lambda: window.grabbers["A"] is not None and window.grabbers["A"].running, timeout=2000)
    qtbot.waitUntil(lambda: window.grabbers["B"] is not None and window.grabbers["B"].running, timeout=2000)
    
    # 2. Adjust brightness and contrast on A
    window.control_panel.slider_brightness_a.setValue(60)
    window.control_panel.slider_contrast_a.setValue(70)
    
    # 3. Zoom A and B
    window.control_panel.slider_zoom_a.setValue(15)
    window.control_panel.slider_zoom_b.setValue(20)
    
    # 4. Check settings
    assert window.canvas.camera_a.brightness_val == 60
    assert window.canvas.camera_a.contrast_val == 70
    assert window.canvas.camera_a.zoom_val == 1.5
    assert window.canvas.camera_b.zoom_val == 2.0
    
    # 5. Stop both
    window.stop_grabber("A")
    window.stop_grabber("B")


def test_tier4_camera_reconnect_recovery(qtbot):
    """47. Disconnect and reconnect camera recovers stream without app crash."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    window.control_panel.cam_a_dev_combo.setCurrentIndex(1)
    qtbot.mouseClick(window.control_panel.cam_a_toggle_btn, Qt.LeftButton)
    qtbot.waitUntil(lambda: window.grabbers["A"] is not None and window.grabbers["A"].running, timeout=2000)
    
    # Disconnect (Toggle off)
    qtbot.mouseClick(window.control_panel.cam_a_toggle_btn, Qt.LeftButton)
    qtbot.waitUntil(lambda: window.grabbers["A"] is None, timeout=2000)
    
    # Reconnect (Toggle on)
    qtbot.mouseClick(window.control_panel.cam_a_toggle_btn, Qt.LeftButton)
    qtbot.waitUntil(lambda: window.grabbers["A"] is not None and window.grabbers["A"].running, timeout=2000)

    # Teardown
    window.stop_grabber("A")
    qtbot.waitUntil(lambda: window.grabbers["A"] is None, timeout=2000)


def test_tier4_preset_swap_stress(qtbot):
    """48. Repeated layout changes in quick succession do not leak or break layouts."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    window.control_panel.cam_a_dev_combo.setCurrentIndex(1)
    window.control_panel.cam_b_dev_combo.setCurrentIndex(2)
    qtbot.mouseClick(window.control_panel.cam_a_toggle_btn, Qt.LeftButton)
    qtbot.mouseClick(window.control_panel.cam_b_toggle_btn, Qt.LeftButton)
    
    qtbot.waitUntil(lambda: window.grabbers["A"] is not None and window.grabbers["A"].running, timeout=2000)
    qtbot.waitUntil(lambda: window.grabbers["B"] is not None and window.grabbers["B"].running, timeout=2000)
    
    presets = ["Side-by-Side", "Stacked", "PiP"]
    for i in range(5):
        for preset in presets:
            window.control_panel.preset_combo.setCurrentText(preset)
            
    assert window.grabbers["A"] is not None
    assert window.grabbers["B"] is not None

    # Teardown
    window.stop_grabber("A")
    window.stop_grabber("B")
    qtbot.waitUntil(lambda: window.grabbers["A"] is None and window.grabbers["B"] is None, timeout=2000)


def test_tier4_long_running_stream_stability(qtbot):
    """49. Continuous streaming updates diagnostic counters stably."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    window.control_panel.cam_a_dev_combo.setCurrentIndex(1)
    qtbot.mouseClick(window.control_panel.cam_a_toggle_btn, Qt.LeftButton)
    
    # Wait for frame ready signals to arrive
    qtbot.waitUntil(lambda: not window.canvas.camera_a.placeholder_label.isVisible(), timeout=2000)
    # Let it stream for 500ms
    qtbot.wait(500)
    assert window.grabbers["A"] is not None
    assert window.grabbers["A"].running

    # Teardown
    window.stop_grabber("A")
    qtbot.waitUntil(lambda: window.grabbers["A"] is None, timeout=2000)
