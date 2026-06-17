from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout
from PySide6.QtCore import Qt
from src.ui.camera_widget import CameraWidget

class SceneCanvas(QWidget):
    """
    Main canvas viewport area where the dual camera feeds are displayed.
    Supports presets: Side-by-Side, Stacked, and Picture-in-Picture (PiP).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #0d0d0f; border: 1px solid #2d2d30; border-radius: 4px;")
        
        # Dual camera widgets
        self.camera_a = CameraWidget(title="Camera A", parent=self)
        self.camera_b = CameraWidget(title="Camera B", parent=self)
        
        # Default layout is Side-by-Side
        self.current_preset = "side-by-side"
        self.layout_customized = False
        self.setup_layout()
        
    def setup_layout(self):
        # Clear existing layout
        if self.layout() is not None:
            old_layout = self.layout()
            old_layout.removeWidget(self.camera_a)
            old_layout.removeWidget(self.camera_b)
            # Re-parent to self just in case they were unparented
            self.camera_a.setParent(self)
            self.camera_b.setParent(self)
            # Safely delete the old layout
            QWidget().setLayout(old_layout) 
            
        if self.current_preset == "side-by-side":
            layout = QHBoxLayout(self)
            layout.setContentsMargins(10, 10, 10, 10)
            layout.setSpacing(10)
            layout.addWidget(self.camera_a)
            layout.addWidget(self.camera_b)
            self.camera_b.show()
            
        elif self.current_preset == "stacked":
            layout = QVBoxLayout(self)
            layout.setContentsMargins(10, 10, 10, 10)
            layout.setSpacing(10)
            layout.addWidget(self.camera_a)
            layout.addWidget(self.camera_b)
            self.camera_b.show()
            
        elif self.current_preset == "pip":
            # Camera A is full size (layout-managed), Camera B is floating
            layout = QHBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(self.camera_a)
            
            # Position Camera B floatingly
            self.camera_b.setParent(self)
            self.camera_b.raise_()
            self.update_pip_geometry()
            
        self.update()

    def on_interactive_layout_start(self):
        if not self.layout_customized:
            # Snapshot geometries
            geom_a = self.camera_a.geometry()
            geom_b = self.camera_b.geometry()
            
            # Disable/remove/delete the active layout manager
            if self.layout() is not None:
                old_layout = self.layout()
                old_layout.removeWidget(self.camera_a)
                old_layout.removeWidget(self.camera_b)
                self.camera_a.setParent(self)
                self.camera_b.setParent(self)
                QWidget().setLayout(old_layout)
            
            # Re-apply the geometries using absolute coordinates
            self.camera_a.setGeometry(geom_a)
            self.camera_b.setGeometry(geom_b)
            
            self.layout_customized = True

    def reset_layout(self):
        self.layout_customized = False
        self.setup_layout()

    def set_preset(self, preset):
        if preset in ["side-by-side", "stacked", "pip"]:
            self.layout_customized = False
            self.current_preset = preset
            self.setup_layout()

    def set_side_by_side(self):
        self.set_preset("side-by-side")

    def set_stacked(self):
        self.set_preset("stacked")

    def set_pip(self):
        self.set_preset("pip")

    def update_pip_geometry(self):
        if self.current_preset == "pip":
            # Position Camera B in the bottom-right corner, 1/4 of size
            w = max(160, self.width() // 4)
            h = max(120, self.height() // 4)
            x = self.width() - w - 15
            y = self.height() - h - 15
            x = max(0, min(x, self.width() - w))
            y = max(0, min(y, self.height() - h))
            self.camera_b.setGeometry(x, y, w, h)
            self.camera_b.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.layout_customized:
            parent_w = self.width()
            parent_h = self.height()
            for camera in [self.camera_a, self.camera_b]:
                geom = camera.geometry()
                x, y, w, h = geom.x(), geom.y(), geom.width(), geom.height()
                w = max(100, w)
                h = max(100, h)
                w = min(w, parent_w)
                h = min(h, parent_h)
                x = max(0, min(x, parent_w - w))
                y = max(0, min(y, parent_h - h))
                camera.setGeometry(x, y, w, h)
        else:
            if self.current_preset == "pip":
                self.update_pip_geometry()
