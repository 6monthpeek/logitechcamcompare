from PySide6.QtWidgets import QMainWindow, QSplitter, QWidget, QHBoxLayout
from PySide6.QtCore import Qt, Slot, QThread, Signal
from src.ui.canvas import SceneCanvas
from src.ui.control_panel import ControlPanel
from src.camera.manager import CameraManager
from src.camera.grabber import CameraGrabber
from src.ui.camera_widget import CameraWidget

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
                    "id": str(dev["index"]),
                    "supported_resolutions": dev.get("supported_resolutions", [])
                })
            self.finished.emit(result)
        except Exception:
            self.finished.emit([])

class MainWindow(QMainWindow):
    """
    Main application window. Hosts the canvas and control panel inside a horizontal splitter.
    Coordinates device settings, dynamic camera addition/removal/selection, and signal connections.
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
        
        # Dynamic Camera Key mappings
        self.display_to_key = {"Camera A": "A", "Camera B": "B"}
        self.key_to_display = {"A": "Camera A", "B": "Camera B"}
        
        # Active camera grabber threads
        self.grabbers = {
            "A": None,
            "B": None
        }
        
        # Camera configurations (default settings)
        self.camera_configs = {
            "A": {"device_idx": -1, "name": "None", "width": 640, "height": 480, "fps": 30},
            "B": {"device_idx": -1, "name": "None", "width": 640, "height": 480, "fps": 30}
        }
        
        # Connect signals
        self.control_panel.preset_changed.connect(self.canvas.set_preset)
        self.control_panel.refresh_requested.connect(self.refresh_cameras)
        self.control_panel.reset_layout_requested.connect(self.canvas.reset_layout)
        
        # Connect overlay checkbox signals
        self.control_panel.check_overlay_fps.toggled.connect(self.update_overlays)
        self.control_panel.check_overlay_res.toggled.connect(self.update_overlays)
        self.control_panel.check_overlay_timestamp.toggled.connect(self.update_overlays)
        
        # Connect dynamic sources signals
        self.control_panel.add_camera_requested.connect(self.add_camera_source)
        self.control_panel.remove_camera_requested.connect(self.remove_camera_source)
        self.control_panel.camera_settings_changed.connect(self.update_camera_settings)
        self.control_panel.open_system_settings_requested.connect(self.open_system_settings)
        self.control_panel.source_selected.connect(self.on_source_selected_from_panel)
        
        self.control_panel.brightness_changed.connect(self.on_brightness_changed)
        self.control_panel.contrast_changed.connect(self.on_contrast_changed)
        self.control_panel.zoom_changed.connect(self.on_zoom_changed)
        
        # Initial camera scan
        self.refresh_cameras()
        self.update_control_panel_cameras()

    def refresh_cameras(self):
        self.control_panel.show_scanning_placeholder()
        
        try:
            from PySide6.QtMultimedia import QMediaDevices
            video_inputs = QMediaDevices.videoInputs()
            if video_inputs:
                devices = []
                for i, device in enumerate(video_inputs):
                    caps = CameraManager.check_capabilities(i)
                    devices.append({
                        "index": i,
                        "name": device.description() or f"Camera {i}",
                        "id": str(i),
                        "supported_resolutions": caps["resolutions"]
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

    def update_control_panel_cameras(self):
        active_configs = {}
        for key, config in self.camera_configs.items():
            if key in ["A", "B"] or config["device_idx"] != -1:
                display_name = self.key_to_display.get(key, f"Camera {key}")
                config_copy = dict(config)
                config_copy["running"] = (self.grabbers.get(key) is not None and self.grabbers[key].isRunning())
                active_configs[display_name] = config_copy
        self.control_panel.update_active_cameras(active_configs)

    @Slot(str)
    def on_source_selected_from_panel(self, display_name):
        for w in self.canvas.camera_widgets:
            if w.title == display_name:
                self.canvas.select_camera(w)
                break

    def on_camera_selected(self, widget):
        if widget:
            self.control_panel.select_source(widget.title)
        else:
            self.control_panel.sources_list.clearSelection()

    def get_camera_state(self, display_name):
        cam_key = self.display_to_key.get(display_name)
        if not cam_key:
            return {}
        cam_widget = self.get_camera_widget(cam_key)
        if cam_widget:
            return {
                "brightness": cam_widget.brightness_val,
                "contrast": cam_widget.contrast_val,
                "zoom": cam_widget.zoom_val
            }
        return {}

    def get_camera_widget(self, cam_key):
        if cam_key == "A":
            return self.canvas.camera_a
        elif cam_key == "B":
            return self.canvas.camera_b
        else:
            display_name = self.key_to_display.get(cam_key)
            for w in self.canvas.camera_widgets:
                if w.title == display_name:
                    return w
        return None

    @Slot(str, int)
    def add_camera_source(self, name, device_idx):
        # Find available slot key
        for key in ["A", "B", "C", "D", "E"]:
            if key not in self.camera_configs or self.camera_configs[key]["device_idx"] == -1:
                cam_key = key
                break
        else:
            cam_key = f"Cam{len(self.camera_configs) + 1}"
            
        display_name = f"Camera {cam_key}"
        if cam_key in ["A", "B"]:
            display_name = f"Camera {cam_key}"
        self.display_to_key[display_name] = cam_key
        self.key_to_display[cam_key] = display_name
        
        self.camera_configs[cam_key] = {
            "device_idx": device_idx,
            "name": name,
            "width": 640,
            "height": 480,
            "fps": 30
        }
        
        self.start_grabber(cam_key)
        self.update_control_panel_cameras()
        self.control_panel.select_source(display_name)

    @Slot(str)
    def remove_camera_source(self, display_name):
        cam_key = self.display_to_key.get(display_name)
        if not cam_key:
            return
            
        self.stop_grabber(cam_key)
        
        if cam_key in ["A", "B"]:
            self.camera_configs[cam_key] = {"device_idx": -1, "name": "None", "width": 640, "height": 480, "fps": 30}
        else:
            if cam_key in self.camera_configs:
                del self.camera_configs[cam_key]
            if cam_key in self.grabbers:
                del self.grabbers[cam_key]
                
        self.update_control_panel_cameras()

    @Slot(str, int)
    def on_brightness_changed(self, display_name, val):
        cam_key = self.display_to_key.get(display_name)
        if not cam_key:
            return
        cam_widget = self.get_camera_widget(cam_key)
        if cam_widget:
            cam_widget.set_brightness(val)

    @Slot(str, int)
    def on_contrast_changed(self, display_name, val):
        cam_key = self.display_to_key.get(display_name)
        if not cam_key:
            return
        cam_widget = self.get_camera_widget(cam_key)
        if cam_widget:
            cam_widget.set_contrast(val)

    @Slot(str, float)
    def on_zoom_changed(self, display_name, val):
        cam_key = self.display_to_key.get(display_name)
        if not cam_key:
            return
        cam_widget = self.get_camera_widget(cam_key)
        if cam_widget:
            cam_widget.set_zoom(val)

    @Slot(str, int, int, int, int)
    def update_camera_settings(self, display_name, device_idx, width, height, fps):
        cam_key = self.display_to_key.get(display_name)
        if not cam_key:
            return
            
        config = self.camera_configs[cam_key]
        
        self.camera_configs[cam_key] = {
            "device_idx": device_idx,
            "name": config.get("name", "Camera"),
            "width": width,
            "height": height,
            "fps": fps
        }
        
        toggle_btn = getattr(self.control_panel, f"cam_{cam_key.lower()}_toggle_btn", None)
        should_run = toggle_btn.isChecked() if toggle_btn else False
        
        if should_run:
            if device_idx == -1:
                self.stop_grabber(cam_key)
            else:
                self.start_grabber(cam_key)
        else:
            self.stop_grabber(cam_key)
            
        self.update_control_panel_cameras()

    @Slot(str)
    def open_system_settings(self, display_name):
        cam_key = self.display_to_key.get(display_name)
        if not cam_key:
            return
        grabber = self.grabbers.get(cam_key)
        if grabber is not None and grabber.isRunning():
            import cv2
            grabber.set_property(cv2.CAP_PROP_SETTINGS, 1)

    @Slot()
    def update_overlays(self):
        fps_checked = self.control_panel.check_overlay_fps.isChecked()
        res_checked = self.control_panel.check_overlay_res.isChecked()
        time_checked = self.control_panel.check_overlay_timestamp.isChecked()
        
        for cam_widget in self.canvas.camera_widgets:
            cam_widget.show_fps = fps_checked
            cam_widget.show_res = res_checked
            cam_widget.show_timestamp = time_checked
            if cam_widget.current_frame is not None:
                cam_widget.update_frame(cam_widget.current_frame)

    def start_grabber(self, cam_key):
        config = self.camera_configs[cam_key]
        if config["device_idx"] == -1:
            return
            
        self.stop_grabber(cam_key)
        
        grabber = CameraGrabber(
            index=config["device_idx"],
            width=config["width"],
            height=config["height"],
            fps=config["fps"],
            parent=self
        )
        
        cam_widget = self.get_camera_widget(cam_key)
        if not cam_widget:
            display_name = self.key_to_display.get(cam_key, f"Camera {cam_key}")
            cam_widget = CameraWidget(title=display_name, parent=self.canvas)
            self.canvas.add_camera_widget(cam_widget)
            
        cam_widget.grabber = grabber
        cam_widget.title = self.key_to_display.get(cam_key, f"Camera {cam_key}")
        
        grabber.frame_ready.connect(cam_widget.update_frame)
        
        def handle_error(msg, ck=cam_key, widget=cam_widget):
            widget.show_placeholder()
            self.stop_grabber(ck)
            if ck in self.camera_configs:
                self.camera_configs[ck]["device_idx"] = -1
            self.update_control_panel_cameras()
            
        grabber.error.connect(handle_error)
        
        self.grabbers[cam_key] = grabber
        grabber.start()
        
        self.canvas.setup_layout()

    def stop_grabber(self, cam_key):
        grabber = self.grabbers.get(cam_key)
        cam_widget = self.get_camera_widget(cam_key)
        
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
            self.grabbers[cam_key] = None
            
        if cam_widget:
            cam_widget.grabber = None
            cam_widget.show_placeholder()
            
        if cam_key not in ["A", "B"] and cam_widget:
            self.canvas.remove_camera_widget(cam_widget)
            
        self.canvas.setup_layout()

    def closeEvent(self, event):
        for cam_key in list(self.grabbers.keys()):
            self.stop_grabber(cam_key)
        super().closeEvent(event)
