import pytest
from PySide6.QtCore import Qt, QCoreApplication, QSize
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout
from src.ui.main_window import MainWindow

def test_styling_aspect_ratios_and_breakage(qtbot):
    """
    Stress test styling and layout integrity under different viewport aspect ratios.
    Checks for overlapping elements, invalid sizes, and layout constraints.
    """
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    
    canvas = window.canvas
    panel = window.control_panel
    
    # List of aspect ratios and sizes to test:
    # (width, height, description)
    viewport_scenarios = [
        (1280, 720, "16:9 Landscape"),
        (1024, 768, "4:3 Standard"),
        (800, 800, "1:1 Square"),
        (1600, 600, "21:9 Ultra-Wide"),
        (450, 800, "Portrait 9:16"),
        (200, 800, "Extremely Narrow Portrait"),
        (1000, 200, "Extremely Flat Landscape"),
        (50, 50, "Microscopic"),
    ]
    
    presets = ["side-by-side", "stacked", "pip"]
    
    for w, h, desc in viewport_scenarios:
        print(f"\nTesting viewport size {w}x{h} ({desc})...")
        window.resize(w, h)
        QCoreApplication.processEvents()
        
        # Verify the central splitter constraints
        assert window.width() >= 0
        assert window.height() >= 0
        
        # Check Control Panel dimensions
        # ControlPanel has a maximum width of 320, but it should scale smaller if needed
        # and its components must not collapse to 0 height
        panel_w = panel.width()
        panel_h = panel.height()
        assert panel_w >= 0
        assert panel_h >= 0
        
        # Verify that controls inside Control Panel have valid sizes
        # (they should not have 0 width or height unless the whole panel is collapsed to 0)
        if panel_w > 50:
            assert panel.preset_combo.width() > 0
            assert panel.preset_combo.height() > 0
            assert panel.reset_layout_btn.width() > 0
            assert panel.reset_layout_btn.height() > 0
            
            # Check slider geometries
            assert panel.slider_brightness_a.width() > 0
            assert panel.slider_brightness_a.height() > 0
            assert panel.slider_contrast_a.width() > 0
            assert panel.slider_contrast_a.height() > 0
            assert panel.slider_zoom_a.width() > 0
            assert panel.slider_zoom_a.height() > 0
            
        # Test each layout preset under this viewport size
        for preset in presets:
            canvas.set_preset(preset)
            QCoreApplication.processEvents()
            
            # Ensure canvas layout does not crash and updates correctly
            geom_a = canvas.camera_a.geometry()
            geom_b = canvas.camera_b.geometry()
            
            assert geom_a.width() >= 0
            assert geom_a.height() >= 0
            assert geom_b.width() >= 0
            assert geom_b.height() >= 0
            
            if preset == "side-by-side":
                # Camera A should be to the left of Camera B, with no overlapping
                # Unless the size is too small for margins/spacing
                if canvas.width() > 50:
                    assert geom_a.x() + geom_a.width() <= geom_b.x()
            elif preset == "stacked":
                # Camera A should be above Camera B, with no overlapping
                if canvas.height() > 50:
                    assert geom_a.y() + geom_a.height() <= geom_b.y()
            elif preset == "pip":
                # Camera B should be floating inside the bounds of the canvas
                # (allowing overlapping but ensuring Camera B stays within canvas bounds)
                assert geom_b.x() >= 0
                assert geom_b.y() >= 0
                assert geom_b.x() + geom_b.width() <= canvas.width()
                assert geom_b.y() + geom_b.height() <= canvas.height()

def test_customized_layout_resizing_constraints(qtbot):
    """
    Test customized layout behavior under extreme aspect ratio resizes.
    """
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    
    canvas = window.canvas
    camera_a = canvas.camera_a
    camera_b = canvas.camera_b
    
    # Put some camera sizes
    canvas.on_interactive_layout_start()
    camera_a.setGeometry(10, 10, 150, 150)
    camera_b.setGeometry(200, 10, 150, 150)
    
    # Resize canvas to extremely wide
    canvas.resize(2000, 200)
    QCoreApplication.processEvents()
    
    # Verify that geometries are clamped within canvas bounds and have min size 100x100
    for cam in [camera_a, camera_b]:
        geom = cam.geometry()
        assert geom.width() >= 100
        assert geom.height() >= 100
        assert geom.x() >= 0
        assert geom.y() >= 0
        assert geom.x() + geom.width() <= canvas.width()
        assert geom.y() + geom.height() <= canvas.height()

    # Resize canvas to extremely narrow
    canvas.resize(150, 1000)
    QCoreApplication.processEvents()
    
    for cam in [camera_a, camera_b]:
        geom = cam.geometry()
        assert geom.width() >= 100
        assert geom.height() >= 100
        assert geom.x() >= 0
        assert geom.y() >= 0
        assert geom.x() + geom.width() <= canvas.width()
        assert geom.y() + geom.height() <= canvas.height()
