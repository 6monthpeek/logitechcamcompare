import pytest
from PySide6.QtCore import Qt, QPoint, QPointF, QEvent, QCoreApplication
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout
from src.ui.main_window import MainWindow

def simulate_drag_sequence(qtbot, widget, start_local, end_local):
    """
    Simulates a press, move, and release sequence.
    """
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
    qtbot.wait(10)
    
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
    qtbot.wait(10)
    
    release_event = QMouseEvent(
        QEvent.MouseButtonRelease,
        QPointF(end_local),
        QPointF(end_global),
        Qt.LeftButton,
        Qt.NoButton,
        Qt.NoModifier
    )
    QCoreApplication.sendEvent(widget, release_event)
    qtbot.wait(10)

def test_adversarial_drag_negative(qtbot):
    """
    Test dragging with extremely negative coordinates.
    """
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    
    canvas = window.canvas
    camera_a = canvas.camera_a
    
    # Enable interactive layout
    canvas.on_interactive_layout_start()
    camera_a.setGeometry(100, 100, 200, 200)
    
    # Drag camera A to extremely negative coords
    simulate_drag_sequence(qtbot, camera_a, QPoint(100, 100), QPoint(-50000, -50000))
    
    # Should clamp at (0, 0) and preserve size
    assert camera_a.x() == 0
    assert camera_a.y() == 0
    assert camera_a.width() == 200
    assert camera_a.height() == 200

def test_zero_and_negative_resize(qtbot):
    """
    Test resizing to zero or negative width/height from different edges.
    """
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    
    canvas = window.canvas
    camera_a = canvas.camera_a
    
    canvas.on_interactive_layout_start()
    camera_a.setGeometry(100, 100, 200, 200)
    
    # Resize Left edge to the right beyond the right edge (trying to force width <= 0)
    # Left edge is at 100. Right edge is at 300. Drag left edge to x=400 (delta_x = +300).
    simulate_drag_sequence(qtbot, camera_a, QPoint(4, 100), QPoint(304, 100))
    # It must clamp to minimum size 100, keeping right edge at 300, so new x=200, width=100.
    assert camera_a.width() == 100
    assert camera_a.x() == 200
    
    # Resize Right edge to the left beyond the left edge (trying to force width <= 0)
    # Reset geometry
    camera_a.setGeometry(100, 100, 200, 200)
    # Right edge is at 300. Left edge is at 100. Drag right edge (x=196) to x=-50 (delta_x = -250).
    simulate_drag_sequence(qtbot, camera_a, QPoint(196, 100), QPoint(-54, 100))
    # Minimum size 100, left edge fixed at 100, so new right edge = 200, width=100.
    assert camera_a.width() == 100
    assert camera_a.x() == 100

from src.ui.canvas import SceneCanvas

def test_extreme_window_resize(qtbot):
    """
    Test resizing the canvas/window to extreme sizes (0x0, 5x5, 10000x10000) under customized and preset layouts.
    """
    canvas = SceneCanvas()
    qtbot.addWidget(canvas)
    canvas.show()
    
    # Scenario A: Preset layout active
    canvas.set_preset("side-by-side")
    canvas.resize(0, 0)
    QCoreApplication.processEvents()
    # The layout shouldn't crash.
    assert canvas.width() >= 0
    
    canvas.resize(10000, 10000)
    QCoreApplication.processEvents()
    assert canvas.width() > 1000
    
    # Scenario B: Customized layout active
    canvas.on_interactive_layout_start()
    canvas.camera_a.setGeometry(100, 100, 200, 200)
    canvas.camera_b.setGeometry(350, 100, 200, 200)
    
    # Shrink parent to 0x0 (OS/Qt will clamp to a minimum size like 240x62)
    canvas.resize(0, 0)
    QCoreApplication.processEvents()
    # Widgets should be clamped within the actual canvas size without crashing or having negative sizes
    assert canvas.camera_a.width() <= canvas.width()
    assert canvas.camera_a.height() <= canvas.height()
    assert canvas.camera_b.width() <= canvas.width()
    assert canvas.camera_b.height() <= canvas.height()
    
    assert canvas.camera_a.width() >= 0
    assert canvas.camera_b.width() >= 0
    assert canvas.camera_a.height() >= 0
    assert canvas.camera_b.height() >= 0

def test_rapid_preset_switching(qtbot):
    """
    Verify stability and state correctness under rapid preset switching.
    """
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    
    canvas = window.canvas
    
    presets = ["side-by-side", "stacked", "pip"]
    for i in range(60):
        preset = presets[i % len(presets)]
        canvas.set_preset(preset)
        
    # Final state should be "pip"
    assert canvas.current_preset == "pip"
    assert canvas.camera_b.parent() == canvas
    assert canvas.layout_customized is False

def test_switch_preset_mid_drag(qtbot):
    """
    Test switching layout preset while a drag interaction is in progress (mouse button pressed).
    """
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    
    canvas = window.canvas
    camera_a = canvas.camera_a
    
    # Press mouse on camera_a (initiates drag)
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
    
    # Interactive layout should be active
    assert canvas.layout_customized
    assert canvas.layout() is None
    
    # Switch preset mid-drag programmatically
    canvas.set_preset("stacked")
    assert not canvas.layout_customized
    assert isinstance(canvas.layout(), QVBoxLayout)
    
    # Simulate move (user dragging mouse after preset changed)
    move_event = QMouseEvent(
        QEvent.MouseMove,
        QPointF(center + QPoint(50, 50)),
        QPointF(center_global + QPoint(50, 50)),
        Qt.LeftButton,
        Qt.LeftButton,
        Qt.NoModifier
    )
    QCoreApplication.sendEvent(camera_a, move_event)
    
    # Release mouse
    release_event = QMouseEvent(
        QEvent.MouseButtonRelease,
        QPointF(center + QPoint(50, 50)),
        QPointF(center_global + QPoint(50, 50)),
        Qt.LeftButton,
        Qt.NoButton,
        Qt.NoModifier
    )
    QCoreApplication.sendEvent(camera_a, release_event)
    
    # Ensure layout_customized is still False and the layout is active and controls geometry
    assert not canvas.layout_customized
    assert canvas.layout() is not None
    assert isinstance(canvas.layout(), QVBoxLayout)

def test_resize_canvas_while_customized(qtbot):
    """
    Verify that custom layout coordinates are clamped within bounds when canvas size changes.
    """
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    
    canvas = window.canvas
    camera_a = canvas.camera_a
    camera_b = canvas.camera_b
    
    # Set parent canvas size
    canvas.resize(800, 600)
    QCoreApplication.processEvents()
    
    canvas.on_interactive_layout_start()
    camera_a.setGeometry(100, 100, 200, 200)
    camera_b.setGeometry(500, 300, 200, 200)
    
    # Shrink canvas to 400x300
    canvas.resize(400, 300)
    QCoreApplication.processEvents()
    
    # Camera A geometry:
    # w = min(max(100, 200), 400) = 200
    # h = min(max(100, 200), 300) = 200
    # x = max(0, min(100, 400 - 200)) = max(0, 100) = 100
    # y = max(0, min(100, 300 - 200)) = max(0, 100) = 100
    # So Camera A should be at (100, 100) with size 200x200
    assert camera_a.geometry().x() == 100
    assert camera_a.geometry().y() == 100
    assert camera_a.geometry().width() == 200
    assert camera_a.geometry().height() == 200
    
    # Camera B geometry:
    # w = min(max(100, 200), 400) = 200
    # h = min(max(100, 200), 300) = 200
    # x = max(0, min(500, 400 - 200)) = max(0, min(500, 200)) = 200
    # y = max(0, min(300, 300 - 200)) = max(0, min(300, 100)) = 100
    # So Camera B should be at (200, 100) with size 200x200
    assert camera_b.geometry().x() == 200
    assert camera_b.geometry().y() == 100
    assert camera_b.geometry().width() == 200
    assert camera_b.geometry().height() == 200
