from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                             QFormLayout, QComboBox, QPushButton, QLabel, QSpinBox,
                             QCheckBox, QSlider)
from PySide6.QtCore import Signal, Slot, Qt

class ControlPanel(QWidget):
    """
    Settings control panel UI for preset selection, camera selection, and resolution/FPS settings.
    """
    # Signals
    preset_changed = Signal(str)
    refresh_requested = Signal()
    camera_toggle_requested = Signal(str, bool)  # (cam_id: "A"|"B", active: bool)
    camera_settings_changed = Signal(str, int, int, int, int) # (cam_id, device_idx, width, height, fps)
    reset_layout_requested = Signal()
    brightness_changed = Signal(str, int)
    contrast_changed = Signal(str, int)
    zoom_changed = Signal(str, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.slider_brightness_a = None
        self.slider_brightness_b = None
        self.slider_contrast_a = None
        self.slider_contrast_b = None
        self.slider_zoom_a = None
        self.slider_zoom_b = None
        self.setMaximumWidth(320)
        self.setStyleSheet("""
            QWidget {
                background-color: #1a1a1e;
                color: #e0e0e0;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QGroupBox {
                border: 1px solid #3d3d42;
                border-radius: 6px;
                margin-top: 12px;
                font-weight: bold;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }
            QComboBox, QSpinBox {
                background-color: #2b2b30;
                border: 1px solid #4d4d54;
                border-radius: 4px;
                padding: 4px;
                color: #e0e0e0;
            }
            QComboBox::drop-down {
                border: none;
            }
            QPushButton {
                background-color: #007acc;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1a8ad6;
            }
            QPushButton:pressed {
                background-color: #005999;
            }
            QPushButton#refresh_btn {
                background-color: #3a3a3f;
            }
            QPushButton#refresh_btn:hover {
                background-color: #4a4a4f;
            }
            QCheckBox {
                color: #e0e0e0;
                spacing: 8px;
                padding-top: 4px;
                padding-bottom: 4px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid #4d4d54;
                border-radius: 3px;
                background-color: #2b2b30;
            }
            QCheckBox::indicator:hover {
                border-color: #007acc;
            }
            QCheckBox::indicator:checked {
                background-color: #007acc;
                border-color: #007acc;
            }
        """)

        # Main Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)
        
        # General Settings Group
        self.setup_general_group()
        
        # Camera A Group
        self.setup_camera_group("A")
        
        # Camera B Group
        self.setup_camera_group("B")
        
        # Spacer
        self.main_layout.addStretch()

    def setup_general_group(self):
        group = QGroupBox("Layout & Controls")
        layout = QVBoxLayout(group)
        
        # Preset Select
        form = QFormLayout()
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["Side-by-Side", "Stacked", "PiP"])
        self.preset_combo.currentTextChanged.connect(self.on_preset_changed)
        form.addRow("Preset:", self.preset_combo)
        layout.addLayout(form)
        
        # Overlays
        self.check_overlay_fps = QCheckBox("Show FPS")
        self.check_overlay_fps.setChecked(True)
        self.check_overlay_res = QCheckBox("Show Resolution")
        self.check_overlay_res.setChecked(True)
        self.check_overlay_timestamp = QCheckBox("Show Timestamp")
        self.check_overlay_timestamp.setChecked(True)
        
        layout.addWidget(self.check_overlay_fps)
        layout.addWidget(self.check_overlay_res)
        layout.addWidget(self.check_overlay_timestamp)
        
        # Refresh Button
        self.refresh_btn = QPushButton("Scan / Refresh Cameras")
        self.refresh_btn.setObjectName("refresh_btn")
        self.refresh_btn.clicked.connect(self.refresh_requested.emit)
        layout.addWidget(self.refresh_btn)
        
        # Reset Layout Button
        self.reset_layout_btn = QPushButton("Reset Layout")
        self.reset_layout_btn.setObjectName("reset_layout_btn")
        self.reset_layout_btn.clicked.connect(self.reset_layout_requested.emit)
        layout.addWidget(self.reset_layout_btn)
        
        self.main_layout.addWidget(group)

    def setup_camera_group(self, cam_id):
        group = QGroupBox(f"Camera {cam_id}")
        layout = QVBoxLayout(group)
        form = QFormLayout()
        
        # Device Selection
        dev_combo = QComboBox()
        dev_combo.addItem("None", -1)
        form.addRow("Device:", dev_combo)
        
        # Resolution Selection
        res_combo = QComboBox()
        res_combo.addItem("640 x 480", (640, 480))
        res_combo.addItem("1280 x 720", (1280, 720))
        res_combo.addItem("1920 x 1080", (1920, 1080))
        form.addRow("Resolution:", res_combo)
        
        # FPS Selection
        fps_spin = QSpinBox()
        fps_spin.setRange(1, 120)
        fps_spin.setValue(30)
        form.addRow("Target FPS:", fps_spin)
        
        # Brightness Slider (brightness: range 0-100, default 50)
        slider_brightness = QSlider(Qt.Horizontal)
        slider_brightness.setRange(0, 100)
        slider_brightness.setValue(50)
        form.addRow("Brightness:", slider_brightness)
        
        # Contrast Slider (contrast: range 0-100, default 50)
        slider_contrast = QSlider(Qt.Horizontal)
        slider_contrast.setRange(0, 100)
        slider_contrast.setValue(50)
        form.addRow("Contrast:", slider_contrast)
        
        # Zoom Slider (zoom: range 10-50, default 10 representing 1.0x to 5.0x zoom)
        slider_zoom = QSlider(Qt.Horizontal)
        slider_zoom.setRange(10, 50)
        slider_zoom.setValue(10)
        form.addRow("Zoom:", slider_zoom)
        
        layout.addLayout(form)
        
        # Start/Stop Button
        toggle_btn = QPushButton(f"Start Camera {cam_id}")
        toggle_btn.setCheckable(True)
        toggle_btn.clicked.connect(lambda checked: self.on_camera_toggle(cam_id, checked))
        layout.addWidget(toggle_btn)
        
        # Save attributes dynamically
        setattr(self, f"cam_{cam_id.lower()}_dev_combo", dev_combo)
        setattr(self, f"cam_{cam_id.lower()}_res_combo", res_combo)
        setattr(self, f"cam_{cam_id.lower()}_fps_spin", fps_spin)
        setattr(self, f"cam_{cam_id.lower()}_toggle_btn", toggle_btn)
        
        setattr(self, f"slider_brightness_{cam_id.lower()}", slider_brightness)
        setattr(self, f"slider_contrast_{cam_id.lower()}", slider_contrast)
        setattr(self, f"slider_zoom_{cam_id.lower()}", slider_zoom)
        
        # Connect change signals
        dev_combo.currentIndexChanged.connect(lambda: self.on_settings_modified(cam_id))
        res_combo.currentIndexChanged.connect(lambda: self.on_settings_modified(cam_id))
        fps_spin.valueChanged.connect(lambda: self.on_settings_modified(cam_id))
        
        slider_brightness.valueChanged.connect(lambda val, cid=cam_id: self.brightness_changed.emit(cid, val))
        slider_contrast.valueChanged.connect(lambda val, cid=cam_id: self.contrast_changed.emit(cid, val))
        slider_zoom.valueChanged.connect(lambda val, cid=cam_id: self.zoom_changed.emit(cid, val / 10.0))
        
        self.main_layout.addWidget(group)

    def on_preset_changed(self, text):
        preset_map = {
            "Side-by-Side": "side-by-side",
            "Stacked": "stacked",
            "PiP": "pip"
        }
        self.preset_changed.emit(preset_map.get(text, "side-by-side"))

    def on_camera_toggle(self, cam_id, checked):
        btn = getattr(self, f"cam_{cam_id.lower()}_toggle_btn")
        if checked:
            btn.setText(f"Stop Camera {cam_id}")
            btn.setStyleSheet("background-color: #d9534f;")
            self.camera_toggle_requested.emit(cam_id, True)
        else:
            btn.setText(f"Start Camera {cam_id}")
            btn.setStyleSheet("background-color: #007acc;")
            self.camera_toggle_requested.emit(cam_id, False)

    def on_settings_modified(self, cam_id):
        # Only emit settings change if the camera is not active or needs updates
        dev_combo = getattr(self, f"cam_{cam_id.lower()}_dev_combo")
        res_combo = getattr(self, f"cam_{cam_id.lower()}_res_combo")
        fps_spin = getattr(self, f"cam_{cam_id.lower()}_fps_spin")
        
        device_idx = dev_combo.currentData()
        if device_idx is None:
            device_idx = -1
            
        res_data = res_combo.currentData()
        width, height = res_data if res_data else (640, 480)
        fps = fps_spin.value()
        
        self.camera_settings_changed.emit(cam_id, device_idx, width, height, fps)

    def show_scanning_placeholder(self):
        """
        Displays a placeholder 'Scanning...' in the device dropdowns.
        """
        for cam_id in ["a", "b"]:
            combo = getattr(self, f"cam_{cam_id}_dev_combo")
            combo.clear()
            combo.addItem("Scanning...", -1)
            combo.setCurrentIndex(0)

    @Slot(list)
    def populate_devices(self, devices):
        """
        Populates the device dropdowns with available devices.
        devices: list of dicts: [{'index': int, 'name': str, 'id': str}]
        """
        for cam_id in ["a", "b"]:
            combo = getattr(self, f"cam_{cam_id}_dev_combo")
            current_idx = combo.currentData()
            
            combo.clear()
            combo.addItem("None", -1)
            
            for dev in devices:
                combo.addItem(f"{dev['index']}: {dev['name']}", dev['index'])
                
            # Try to restore selection
            found = False
            for idx in range(combo.count()):
                if combo.itemData(idx) == current_idx:
                    combo.setCurrentIndex(idx)
                    found = True
                    break
            if not found:
                combo.setCurrentIndex(0)

