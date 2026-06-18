from PySide6.QtWidgets import QMainWindow, QSplitter, QWidget, QHBoxLayout
from PySide6.QtCore import Qt, Slot, QThread, Signal
from src.ui.canvas import SceneCanvas
from src.ui.control_panel import ControlPanel
from src.camera.manager import CameraManager, CameraBackend
from src.camera.grabber import CameraGrabber

class CameraDiscoveryWorker(QThread):
    finished = Signal(list)
    
    def run(self):
        try:
            devices = CameraManager.list_devices()
            result = []
            for dev in devices:
                result.append({
                    "index": dev["index"],
                    "name": dev["name"],
                    "id": str(dev["index"])
                })
            self.finished.emit(result)
        except Exception:
            self.finished.emit([])

class MainWindow(QMainWindow):
    """
    Main application window. Hosts the canvas and control panel inside a horizontal splitter.
    Coordinates device settings, starting/stopping threads, and signal connections.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Webcam Comparison App")
        self.resize(1100, 700)
        
        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Splitter to separate Canvas and Control Panel
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Canvas
        self.canvas = SceneCanvas(self)
        splitter.addWidget(self.canvas)
        
        # Control Panel
        self.control_panel = ControlPanel(self)
        splitter.addWidget(self.control_panel)
        
        # Set splitter ratios (800px for canvas, 300px for control panel)
        splitter.setSizes([800, 300])
        
        # Active camera grabbers
        self.grabbers = {
            "A": None,
            "B": None
        }
        
        # Camera configurations (default settings)
        self.camera_configs = {
            "A": {"device_idx": -1, "width": 640, "height": 480, "fps": 30},
            "B": {"device_idx": -1, "width": 640, "height": 480, "fps": 30}
        }
        
        # Connect signals
        self.control_panel.preset_changed.connect(self.canvas.set_preset)
        self.control_panel.refresh_requested.connect(self.refresh_cameras)
        self.control_panel.camera_toggle_requested.connect(self.toggle_camera)
        self.control_panel.camera_settings_changed.connect(self.update_camera_settings)
        self.control_panel.reset_layout_requested.connect(self.canvas.reset_layout)
        
        # Connect overlay checkbox signals
        self.control_panel.check_overlay_fps.toggled.connect(self.update_overlays)
        self.control_panel.check_overlay_res.toggled.connect(self.update_overlays)
        self.control_panel.check_overlay_timestamp.toggled.connect(self.update_overlays)
        
        # Connect slider signals to camera widgets
        self.control_panel.brightness_changed.connect(self.on_brightness_changed)
        self.control_panel.contrast_changed.connect(self.on_contrast_changed)
        self.control_panel.zoom_changed.connect(self.on_zoom_changed)
        
        # Initial camera scan
        self.refresh_cameras()
        
    def refresh_cameras(self):
        self.control_panel.show_scanning_placeholder()
        
        try:
            from PySide6.QtMultimedia import QMediaDevices
            video_inputs = QMediaDevices.videoInputs()
            if video_inputs:
                devices = []
                for i, device in enumerate(video_inputs):
                    devices.append({
                        "index": i,
                        "name": device.description() or f"Camera {i}",
                        "id": str(i)
                    })
                self.control_panel.populate_devices(devices)
                return
        except Exception:
            pass
            
        self._discovery_worker = CameraDiscoveryWorker(self)
        self._discovery_worker.finished.connect(self.on_discovery_finished)
        self._discovery_worker.start()

    def on_discovery_finished(self, devices):
        self.control_panel.populate_devices(devices)

    @Slot(str, int)
    def on_brightness_changed(self, cam_id, val):
        cam_widget = self.canvas.camera_a if cam_id == "A" else self.canvas.camera_b
        cam_widget.set_brightness(val)

    @Slot(str, int)
    def on_contrast_changed(self, cam_id, val):
        cam_widget = self.canvas.camera_a if cam_id == "A" else self.canvas.camera_b
        cam_widget.set_contrast(val)

    @Slot(str, float)
    def on_zoom_changed(self, cam_id, val):
        cam_widget = self.canvas.camera_a if cam_id == "A" else self.canvas.camera_b
        cam_widget.set_zoom(val)

    @Slot(str, int, int, int, int)
    def update_camera_settings(self, cam_id, device_idx, width, height, fps):
        self.camera_configs[cam_id] = {
            "device_idx": device_idx,
            "width": width,
            "height": height,
            "fps": fps
        }
        
        # If camera is currently active, restart it with new settings
        if self.grabbers[cam_id] is not None:
            self.stop_grabber(cam_id)
            self.start_grabber(cam_id)

    @Slot(str, bool)
    def toggle_camera(self, cam_id, active):
        if active:
            self.start_grabber(cam_id)
        else:
            self.stop_grabber(cam_id)

    @Slot()
    def update_overlays(self):
        fps_checked = self.control_panel.check_overlay_fps.isChecked()
        res_checked = self.control_panel.check_overlay_res.isChecked()
        time_checked = self.control_panel.check_overlay_timestamp.isChecked()
        
        for cam_widget in [self.canvas.camera_a, self.canvas.camera_b]:
            cam_widget.show_fps = fps_checked
            cam_widget.show_res = res_checked
            cam_widget.show_timestamp = time_checked
            if cam_widget.current_frame is not None:
                cam_widget.update_frame(cam_widget.current_frame)

    def start_grabber(self, cam_id):
        config = self.camera_configs[cam_id]
        if config["device_idx"] == -1:
            # No device selected, turn off the check status of the toggle button
            btn = getattr(self.control_panel, f"cam_{cam_id.lower()}_toggle_btn")
            btn.setChecked(False)
            btn.setText(f"Start Camera {cam_id}")
            btn.setProperty("active", False)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            return
            
        self.stop_grabber(cam_id) # Ensure clean state
        
        # Create new grabber thread
        grabber = CameraGrabber(
            index=config["device_idx"],
            width=config["width"],
            height=config["height"],
            fps=config["fps"],
            parent=self
        )
        
        # Connect frame ready signal to corresponding camera widget on canvas
        cam_widget = self.canvas.camera_a if cam_id == "A" else self.canvas.camera_b
        cam_widget.grabber = grabber
        
        dev_combo = getattr(self.control_panel, f"cam_{cam_id.lower()}_dev_combo")
        cam_widget.title = dev_combo.currentText()
        
        grabber.frame_ready.connect(cam_widget.update_frame)
        
        def handle_error(msg, cid=cam_id, widget=cam_widget):
            widget.show_placeholder()
            self.stop_grabber(cid)
            btn = getattr(self.control_panel, f"cam_{cid.lower()}_toggle_btn")
            btn.setChecked(False)
            btn.setText(f"Start Camera {cid}")
            btn.setProperty("active", False)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            
        grabber.error.connect(handle_error)
        
        self.grabbers[cam_id] = grabber
        grabber.start()

    def stop_grabber(self, cam_id):
        grabber = self.grabbers[cam_id]
        cam_widget = self.canvas.camera_a if cam_id == "A" else self.canvas.camera_b
        
        if grabber is not None:
            try:
                grabber.frame_ready.disconnect(cam_widget.update_frame)
            except (TypeError, RuntimeError):
                pass
            try:
                grabber.error.disconnect()
            except (TypeError, RuntimeError):
                pass
            grabber.stop()
            self.grabbers[cam_id] = None
            
        cam_widget.grabber = None
        cam_widget.show_placeholder()

    def closeEvent(self, event):
        # Ensure all grabbers are stopped before application exits
        for cam_id in list(self.grabbers.keys()):
            self.stop_grabber(cam_id)
        super().closeEvent(event)
