import pytest
from PySide6.QtCore import Qt, QPoint, QPointF, QEvent, QCoreApplication
from PySide6.QtGui import QMouseEvent
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

def test_preset_layout_creation(qtbot):
    """1. Test preset layout creation (QHBoxLayout/QVBoxLayout/QHBoxLayout for PiP)."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    
    canvas = window.canvas
    
    # Default is side-by-side
    assert canvas.current_preset == "side-by-side"
    assert isinstance(canvas.layout(), QHBoxLayout)
    assert canvas.camera_a.isVisible()
    assert canvas.camera_b.isVisible()
    
    # Switch to stacked
    canvas.set_preset("stacked")
    assert canvas.current_preset == "stacked"
    assert isinstance(canvas.layout(), QVBoxLayout)
    assert canvas.camera_a.isVisible()
    assert canvas.camera_b.isVisible()
    
    # Switch to PiP
    canvas.set_preset("pip")
    assert canvas.current_preset == "pip"
    assert isinstance(canvas.layout(), QHBoxLayout)
    # Camera A should be managed, Camera B should be floating (not in layout)
    assert canvas.layout().indexOf(canvas.camera_b) == -1
    assert canvas.camera_b.parent() == canvas
    assert canvas.camera_a.isVisible()
    assert canvas.camera_b.isVisible()

def test_interactive_drag_transition(qtbot):
    """2. Test interactive drag transition (starting drag destroys layout manager, marks customized)."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    
    canvas = window.canvas
    camera_a = canvas.camera_a
    
    assert not canvas.layout_customized
    assert canvas.layout() is not None
    
    # Press mouse in the center of camera_a to start dragging
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
    
    # Layout should now be customized and layout manager destroyed
    assert canvas.layout_customized
    assert canvas.layout() is None
    assert camera_a.interaction_direction == "drag"
    assert camera_a.cursor().shape() == Qt.ClosedHandCursor
    
    # Release mouse
    release_event = QMouseEvent(
        QEvent.MouseButtonRelease,
        QPointF(center),
        QPointF(center_global),
        Qt.LeftButton,
        Qt.NoButton,
        Qt.NoModifier
    )
    QCoreApplication.sendEvent(camera_a, release_event)
    
    assert camera_a.interaction_direction is None

def test_drag_boundaries(qtbot):
    """3. Test drag boundaries (clamps normal drag, clamps out of bounds left/top, clamps out of bounds right/bottom)."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    
    canvas = window.canvas
    camera_a = canvas.camera_a
    
    # Force layout customization to enable drag/resize and decouple from layout
    canvas.on_interactive_layout_start()
    
    # Set initial geometry of camera_a to a known size and position
    camera_a.setGeometry(50, 50, 200, 200)
    
    # 3.1 Clamps out of bounds left/top (drag far top-left)
    simulate_drag(qtbot, camera_a, QPoint(100, 100), QPoint(-500, -500))
    assert camera_a.x() == 0
    assert camera_a.y() == 0
    assert camera_a.width() == 200
    assert camera_a.height() == 200
    
    # 3.2 Clamps out of bounds right/bottom (drag far bottom-right)
    simulate_drag(qtbot, camera_a, QPoint(100, 100), QPoint(1500, 1500))
    parent = canvas
    assert camera_a.x() == parent.width() - 200
    assert camera_a.y() == parent.height() - 200
    assert camera_a.width() == 200
    assert camera_a.height() == 200

def test_resize_and_minimum_size(qtbot):
    """4. Test resize and minimum size constraints (clamps shrinking below 100x100, clamps growing out of canvas boundaries)."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    
    canvas = window.canvas
    camera_a = canvas.camera_a
    
    # Force customized layout
    canvas.on_interactive_layout_start()
    
    # Set initial position and size
    camera_a.setGeometry(100, 100, 200, 200)
    
    # 4.1 Test resizing from Left edge (shrinking)
    # Drag Left edge (x=4) to the right by 50 pixels (new x should be 150, width 150)
    simulate_drag(qtbot, camera_a, QPoint(4, 100), QPoint(54, 100))
    assert camera_a.x() == 150
    assert camera_a.width() == 150
    # Right edge is fixed at 100 + 200 = 300
    assert camera_a.x() + camera_a.width() == 300
    
    # 4.2 Test shrinking below 100x100 limit from Left edge
    # Drag Left edge further to the right by 100 pixels (attempt to make width 50)
    simulate_drag(qtbot, camera_a, QPoint(4, 100), QPoint(104, 100))
    # It must clamp to minimum width of 100, meaning left edge is fixed at 300 - 100 = 200
    assert camera_a.width() == 100
    assert camera_a.x() == 200
    
    # 4.3 Test resizing growing out of canvas boundaries (bottom-right edge)
    # Set geometry close to bottom right
    pw, ph = canvas.width(), canvas.height()
    camera_a.setGeometry(pw - 200, ph - 200, 150, 150)
    
    # Drag Bottom-Right corner (x=146, y=146) far past parent boundaries
    simulate_drag(qtbot, camera_a, QPoint(146, 146), QPoint(800, 800))
    # The right and bottom edges must clamp to parent width/height
    assert camera_a.x() == pw - 200
    assert camera_a.y() == ph - 200
    assert camera_a.x() + camera_a.width() == pw
    assert camera_a.y() + camera_a.height() == ph

def test_reset_layout(qtbot):
    """5. Test reset layout (restores layout manager and resets customized flag)."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    
    canvas = window.canvas
    
    # Start a drag to customize layout
    canvas.on_interactive_layout_start()
    assert canvas.layout_customized
    assert canvas.layout() is None
    
    # Click reset layout button
    qtbot.mouseClick(window.control_panel.reset_layout_btn, Qt.LeftButton)
    
    # Verify customized is false and layout manager is restored
    assert not canvas.layout_customized
    assert canvas.layout() is not None
    assert isinstance(canvas.layout(), QHBoxLayout)  # default side-by-side


def test_explicit_helper_methods_and_pip_clamping(qtbot):
    """6. Test explicit layout preset helper methods and coordinate clamping under extreme window shrinkage."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    
    canvas = window.canvas
    
    # 6.1 Test set_stacked() helper
    canvas.set_stacked()
    assert canvas.current_preset == "stacked"
    assert isinstance(canvas.layout(), QVBoxLayout)
    
    # 6.2 Test set_pip() helper
    canvas.set_pip()
    assert canvas.current_preset == "pip"
    
    # 6.3 Test set_side_by_side() helper
    canvas.set_side_by_side()
    assert canvas.current_preset == "side-by-side"
    assert isinstance(canvas.layout(), QHBoxLayout)
    
    # 6.4 Test PiP coordinate clamping under extreme window shrinkage
    canvas.set_pip()
    # Force the canvas to a tiny size (e.g. 50x50) where default w=160, h=120 would exceed parent boundaries
    canvas.resize(50, 50)
    canvas.update_pip_geometry()
    
    # Check that x and y of camera_b are clamped properly
    geom = canvas.camera_b.geometry()
    # The clamp is max(0, min(x, self.width() - w))
    # w = max(160, self.width() // 4) => w = max(160, 12) = 160
    # h = max(120, self.height() // 4) => h = max(120, 12) = 120
    # Since self.width() - w = 50 - 160 = -110, clamping max(0, -110) must yield 0
    # Since self.height() - h = 50 - 120 = -70, clamping max(0, -70) must yield 0
    assert geom.x() == 0
    assert geom.y() == 0

