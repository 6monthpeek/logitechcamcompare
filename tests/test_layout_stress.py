import pytest
from PySide6.QtCore import Qt, QPoint, QPointF, QEvent, QCoreApplication, QSize
from PySide6.QtGui import QMouseEvent, QResizeEvent
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from src.ui.main_window import MainWindow

def simulate_drag(qtbot, widget, start_local, end_local):
    start_global = widget.mapToGlobal(start_local)
    press_event = QMouseEvent(
        QEvent.MouseButtonPress,
        QPointF(start_local),
        QPointF(start_global),
        Qt.LeftButton,
        Qt.LeftButton,
        Qt.NoModifier
    )
    QCoreApplication.sendEvent(widget, press_event)
    qtbot.wait(5)
    
    end_global = widget.mapToGlobal(end_local)
    move_event = QMouseEvent(
        QEvent.MouseMove,
        QPointF(end_local),
        QPointF(end_global),
        Qt.LeftButton,
        Qt.LeftButton,
        Qt.NoModifier
    )
    QCoreApplication.sendEvent(widget, move_event)
    qtbot.wait(5)
    
    release_event = QMouseEvent(
        QEvent.MouseButtonRelease,
        QPointF(end_local),
        QPointF(end_global),
        Qt.LeftButton,
        Qt.NoButton,
        Qt.NoModifier
    )
    QCoreApplication.sendEvent(widget, release_event)
    qtbot.wait(5)

def test_stress_negative_drag_coordinates(qtbot):
    """
    Stress test with negative drag coordinates.
    Asserts that widgets clamp to parent boundaries and do not drift off-canvas.
    """
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    
    canvas = window.canvas
    camera_a = canvas.camera_a
    
    canvas.on_interactive_layout_start()
    camera_a.setGeometry(100, 100, 200, 200)
    
    # Drag far to negative coordinates
    simulate_drag(qtbot, camera_a, QPoint(100, 100), QPoint(-1000, -1000))
    assert camera_a.x() == 0
    assert camera_a.y() == 0
    assert camera_a.width() == 200
    assert camera_a.height() == 200

    # Drag with positive but extreme delta values
    simulate_drag(qtbot, camera_a, QPoint(100, 100), QPoint(10000, 10000))
    parent_w = canvas.width()
    parent_h = canvas.height()
    assert camera_a.x() == parent_w - 200
    assert camera_a.y() == parent_h - 200

def test_stress_zero_width_height_resize(qtbot):
    """
    Stress test resizing to smaller than minimum size, zero-width, or negative dimensions.
    """
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    
    canvas = window.canvas
    camera_a = canvas.camera_a
    
    canvas.on_interactive_layout_start()
    camera_a.setGeometry(100, 100, 200, 200)
    
    # Resize from Left edge to the right beyond limit (should clamp to min 100px width)
    # Right edge is fixed at 300. Drag left edge to 400.
    simulate_drag(qtbot, camera_a, QPoint(4, 100), QPoint(400, 100))
    assert camera_a.width() == 100
    assert camera_a.x() == 200  # 300 - 100 = 200

    # Resize from Right edge to the left beyond limit (should clamp to min 100px width)
    camera_a.setGeometry(100, 100, 200, 200)
    # Left edge is fixed at 100. Drag right edge to 0.
    simulate_drag(qtbot, camera_a, QPoint(196, 100), QPoint(-50, 100))
    assert camera_a.width() == 100
    assert camera_a.x() == 100

def test_stress_extreme_window_sizes(qtbot):
    """
    Stress test layout scaling when the window/canvas is resized to extreme proportions.
    """
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    
    canvas = window.canvas
    
    # 1. Extremely small size (1x1)
    canvas.resize(1, 1)
    # Force layout update
    QCoreApplication.processEvents()
    
    # Side-by-side layout should adjust sizes without crashing
    canvas.set_preset("side-by-side")
    QCoreApplication.processEvents()
    
    # PiP layout with 1x1 size
    canvas.set_preset("pip")
    QCoreApplication.processEvents()
    geom_b = canvas.camera_b.geometry()
    expected_w = max(160, canvas.width() // 4)
    expected_h = max(120, canvas.height() // 4)
    assert geom_b.width() == expected_w
    assert geom_b.height() == expected_h
    expected_x = max(0, min(canvas.width() - expected_w - 15, canvas.width() - expected_w))
    expected_y = max(0, min(canvas.height() - expected_h - 15, canvas.height() - expected_h))
    assert geom_b.x() == expected_x
    assert geom_b.y() == expected_y

    # 2. Extremely large size (10000x10000)
    canvas.resize(10000, 10000)
    QCoreApplication.processEvents()
    
    canvas.set_preset("pip")
    QCoreApplication.processEvents()
    geom_b = canvas.camera_b.geometry()
    expected_w_large = max(160, canvas.width() // 4)
    expected_h_large = max(120, canvas.height() // 4)
    assert geom_b.width() == expected_w_large
    assert geom_b.height() == expected_h_large
    
    expected_x_large = max(0, min(canvas.width() - expected_w_large - 15, canvas.width() - expected_w_large))
    expected_y_large = max(0, min(canvas.height() - expected_h_large - 15, canvas.height() - expected_h_large))
    assert geom_b.x() == expected_x_large
    assert geom_b.y() == expected_y_large

    # Reset to normal size
    canvas.resize(800, 600)
    QCoreApplication.processEvents()

def test_stress_rapid_preset_switching(qtbot):
    """
    Rapidly toggle presets in succession to verify stability, no crashes, and correct restoration.
    """
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    
    canvas = window.canvas
    
    presets = ["side-by-side", "stacked", "pip"]
    for i in range(30):  # 30 switches
        preset = presets[i % 3]
        canvas.set_preset(preset)
        QCoreApplication.processEvents()
        
        # Verify basic preset state
        assert canvas.current_preset == preset
        if preset == "side-by-side":
            assert isinstance(canvas.layout(), QHBoxLayout)
        elif preset == "stacked":
            assert isinstance(canvas.layout(), QVBoxLayout)
        elif preset == "pip":
            assert isinstance(canvas.layout(), QHBoxLayout)
            assert canvas.layout().indexOf(canvas.camera_b) == -1

def test_stress_switch_presets_mid_drag(qtbot):
    """
    Test switching layout presets while dragging is actively happening (mid-drag).
    """
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    
    canvas = window.canvas
    camera_a = canvas.camera_a
    
    # 1. Trigger drag press on Camera A
    center = camera_a.rect().center()
    center_global = camera_a.mapToGlobal(center)
    press_event = QMouseEvent(
        QEvent.MouseButtonPress,
        QPointF(center),
        QPointF(center_global),
        Qt.LeftButton,
        Qt.LeftButton,
        Qt.NoModifier
    )
    QCoreApplication.sendEvent(camera_a, press_event)
    
    # Verify customized drag layout is started
    assert canvas.layout_customized
    assert canvas.layout() is None
    assert camera_a.interaction_direction == "drag"
    
    # 2. Switch preset while mouse is still down (simulating mid-drag preset change)
    canvas.set_preset("side-by-side")
    
    # Verify layout is reset but Camera A still has active interaction direction
    assert not canvas.layout_customized
    assert canvas.layout() is not None
    assert isinstance(canvas.layout(), QHBoxLayout)
    assert camera_a.interaction_direction == "drag"
    
    # 3. Send a MouseMove event on Camera A (simulating continuing the drag)
    # The drag starts from `drag_start_pos`, which was `center_global`.
    # Let's move by 50, 50
    moved_global = center_global + QPoint(50, 50)
    moved_local = center + QPoint(50, 50)
    move_event = QMouseEvent(
        QEvent.MouseMove,
        QPointF(moved_local),
        QPointF(moved_global),
        Qt.LeftButton,
        Qt.LeftButton,
        Qt.NoModifier
    )
    QCoreApplication.sendEvent(camera_a, move_event)
    
    # Verify that geometry of camera_a might change temporarily, but layout remains active.
    # Note that Qt layout managers lay out children on resize or show events.
    # Let's see if it causes any crash or exception.
    QCoreApplication.processEvents()
    
    # 4. Release mouse button to clean up
    release_event = QMouseEvent(
        QEvent.MouseButtonRelease,
        QPointF(moved_local),
        QPointF(moved_global),
        Qt.LeftButton,
        Qt.NoButton,
        Qt.NoModifier
    )
    QCoreApplication.sendEvent(camera_a, release_event)
    
    assert camera_a.interaction_direction is None
    assert not canvas.layout_customized
    assert canvas.layout() is not None
