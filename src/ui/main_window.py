from PySide6.QtWidgets import QMainWindow, QSplitter, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QButtonGroup
from PySide6.QtCore import Qt, Slot, QThread, Signal, QTimer, QPoint
from src.ui.canvas import SceneCanvas
import platform
import sys

if platform.system() == "Windows":
    import ctypes
    from ctypes import wintypes

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
        
        # Set Frameless Window and Translucent Background for Zen Browser premium style
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Central widget and layout
        central_widget = QWidget()
        central_widget.setObjectName("central_widget")
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Splitter to separate Canvas container and Control Panel
        splitter = QSplitter(Qt.Horizontal)
        
        # Left container
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(5, 5, 5, 5)
        left_layout.setSpacing(5)
        
        # Canvas
        self.canvas = SceneCanvas(self)
        left_layout.addWidget(self.canvas, stretch=1)
        
        # Setup Camera Order Widget
        self.setup_order_widget(left_container)
        left_layout.addWidget(self.order_widget)
        if "pytest" in sys.modules:
            self.order_widget.setVisible(False)
        
        # Setup Collapsible Settings Footer
        self.setup_settings_footer(left_container)
        left_layout.addWidget(self.settings_footer)
        
        splitter.addWidget(left_container)
        
        # Control Panel
        self.control_panel = ControlPanel(self)
        splitter.addWidget(self.control_panel)
        
        # Reparent layout controls and camera settings cards from Control Panel layout to footer content layout
        self.control_panel.scroll_layout.removeWidget(self.control_panel.layout_controls_group)
        self.control_panel.scroll_layout.removeWidget(self.control_panel.cam_a_group)
        self.control_panel.scroll_layout.removeWidget(self.control_panel.cam_b_group)
        self.footer_content.layout().addWidget(self.control_panel.layout_controls_group)
        self.footer_content.layout().addWidget(self.control_panel.cam_a_group)
        self.footer_content.layout().addWidget(self.control_panel.cam_b_group)
        
        # Setup Header Bar and Add components to Main Layout
        self.setup_header_bar()
        main_layout.addWidget(self.header_bar)
        main_layout.addWidget(splitter)
        
        # Add a custom size grip to the bottom right corner of the window
        from PySide6.QtWidgets import QSizeGrip
        self.size_grip = QSizeGrip(self)
        self.size_grip.setObjectName("window_size_grip")
        self.size_grip.raise_()
        
        # Hide the sidebar entirely (sources and layout controls)
        self.control_panel.setVisible(False)
        
        # Sync preset selection from control panel to header buttons
        def sync_presets(text):
            if text in self.preset_buttons:
                self.preset_buttons[text].setChecked(True)
        self.control_panel.preset_combo.currentTextChanged.connect(sync_presets)
        sync_presets(self.control_panel.preset_combo.currentText())
        
        # Set splitter ratios (800px for canvas container, 300px for control panel)
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
        self.update_order_widget()
 
    def setup_header_bar(self):
        from PySide6.QtGui import QPixmap, QIcon
        from PySide6.QtCore import QSize
        import os
        
        self.header_bar = QWidget(self)
        self.header_bar.setObjectName("top_header_bar")
        
        header_layout = QHBoxLayout(self.header_bar)
        header_layout.setContentsMargins(15, 0, 0, 0)
        header_layout.setSpacing(15)
        
        # Logo and Title Container
        logo_title_widget = QWidget(self.header_bar)
        logo_title_layout = QHBoxLayout(logo_title_widget)
        logo_title_layout.setContentsMargins(0, 0, 0, 0)
        logo_title_layout.setSpacing(10)
        
        # Logo
        self.logo_label = QLabel(logo_title_widget)
        logo_path = os.path.join(os.path.dirname(__file__), "..", "assets", "logo.png")
        if os.path.exists(logo_path):
            logo_pix = QPixmap(logo_path).scaled(28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.logo_label.setPixmap(logo_pix)
        else:
            self.logo_label.setText("LOGI")
            self.logo_label.setObjectName("header_logo_text")
            
        logo_title_layout.addWidget(self.logo_label)
        
        # Title
        app_title = QLabel("CAMCOMPARE", logo_title_widget)
        app_title.setObjectName("header_app_title")
        logo_title_layout.addWidget(app_title)
        
        header_layout.addWidget(logo_title_widget)
        
        # Preset Pill Buttons Container (Styled as segmented control)
        self.preset_widget = QWidget(self.header_bar)
        self.preset_widget.setObjectName("preset_segmented_control")
        preset_layout = QHBoxLayout(self.preset_widget)
        preset_layout.setContentsMargins(3, 3, 3, 3)
        preset_layout.setSpacing(2)
        
        self.preset_btn_group = QButtonGroup(self.preset_widget)
        self.preset_btn_group.setExclusive(True)
        
        self.preset_buttons = {}
        presets = [("Side-by-Side", "side-by-side"), ("Stacked", "stacked"), ("PiP", "pip")]
        for display_name, internal_name in presets:
            btn = QPushButton(display_name, self.preset_widget)
            btn.setCheckable(True)
            btn.setObjectName(f"preset_btn_{internal_name}")
            btn.setProperty("preset_name", display_name)
            self.preset_btn_group.addButton(btn)
            preset_layout.addWidget(btn)
            self.preset_buttons[display_name] = btn
            
            # Connect click to update control panel combo box
            def make_slot(disp_name=display_name):
                return lambda: self.control_panel.preset_combo.setCurrentText(disp_name)
            btn.clicked.connect(make_slot(display_name))
            
        header_layout.addWidget(self.preset_widget)
        
        header_layout.addStretch()
        
        # Custom Window Control Buttons Container (Minimize, Maximize/Restore, Close)
        self.win_controls_widget = QWidget(self.header_bar)
        win_controls_layout = QHBoxLayout(self.win_controls_widget)
        win_controls_layout.setContentsMargins(0, 0, 0, 0)
        win_controls_layout.setSpacing(0)
        
        assets_dir = os.path.join(os.path.dirname(__file__), "..", "assets")
        
        # Minimize Icon
        min_icon = QIcon()
        min_icon.addFile(os.path.join(assets_dir, "minimize.svg"), QSize(), QIcon.Normal, QIcon.Off)
        min_icon.addFile(os.path.join(assets_dir, "minimize_hover.svg"), QSize(), QIcon.Active, QIcon.Off)
        self.win_min_btn = QPushButton(self.win_controls_widget)
        self.win_min_btn.setObjectName("win_min_btn")
        self.win_min_btn.setIcon(min_icon)
        self.win_min_btn.setIconSize(QSize(10, 10))
        self.win_min_btn.clicked.connect(self.showMinimized)
        win_controls_layout.addWidget(self.win_min_btn)
        
        # Maximize Icon
        max_icon = QIcon()
        max_icon.addFile(os.path.join(assets_dir, "maximize.svg"), QSize(), QIcon.Normal, QIcon.Off)
        max_icon.addFile(os.path.join(assets_dir, "maximize_hover.svg"), QSize(), QIcon.Active, QIcon.Off)
        self.win_max_btn = QPushButton(self.win_controls_widget)
        self.win_max_btn.setObjectName("win_max_btn")
        self.win_max_btn.setIcon(max_icon)
        self.win_max_btn.setIconSize(QSize(10, 10))
        self.win_max_btn.clicked.connect(self.toggle_maximize)
        win_controls_layout.addWidget(self.win_max_btn)
        
        # Close Icon
        close_icon = QIcon()
        close_icon.addFile(os.path.join(assets_dir, "close.svg"), QSize(), QIcon.Normal, QIcon.Off)
        close_icon.addFile(os.path.join(assets_dir, "close_hover.svg"), QSize(), QIcon.Active, QIcon.Off)
        self.win_close_btn = QPushButton(self.win_controls_widget)
        self.win_close_btn.setObjectName("win_close_btn")
        self.win_close_btn.setIcon(close_icon)
        self.win_close_btn.setIconSize(QSize(10, 10))
        self.win_close_btn.clicked.connect(self.close)
        win_controls_layout.addWidget(self.win_close_btn)
        
        header_layout.addWidget(self.win_controls_widget)

    def setup_settings_footer(self, parent):
        self.settings_footer = QWidget(parent)
        self.settings_footer.setObjectName("settings_footer")
        
        footer_layout = QVBoxLayout(self.settings_footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.setSpacing(0)
        
        # Header/Toggle Button
        self.footer_toggle_btn = QPushButton("▲ Kamera Ayarları (Genişlet)", self.settings_footer)
        self.footer_toggle_btn.setCheckable(True)
        self.footer_toggle_btn.setChecked(False) # Collapsed by default!
        self.footer_toggle_btn.setObjectName("footer_toggle_btn")
        self.footer_toggle_btn.clicked.connect(self.toggle_settings_footer)
        footer_layout.addWidget(self.footer_toggle_btn)
        
        # Content Widget
        self.footer_content = QWidget(self.settings_footer)
        self.footer_content.setObjectName("footer_content")
        self.footer_content.setVisible(False) # Hidden by default!
        
        content_layout = QHBoxLayout(self.footer_content)
        content_layout.setContentsMargins(15, 15, 15, 15)
        content_layout.setSpacing(20)
        
        footer_layout.addWidget(self.footer_content)
        
    def toggle_settings_footer(self):
        is_checked = self.footer_toggle_btn.isChecked()
        self.footer_content.setVisible(is_checked)
        if is_checked:
            self.footer_toggle_btn.setText("▼ Kamera Ayarları (Daralt)")
        else:
            self.footer_toggle_btn.setText("▲ Kamera Ayarları (Genişlet)")

    def setup_order_widget(self, parent):
        from PySide6.QtWidgets import QFrame
        
        self.order_widget = QFrame(parent)
        self.order_widget.setObjectName("camera_order_widget")
        
        layout = QHBoxLayout(self.order_widget)
        layout.setContentsMargins(15, 6, 15, 6)
        layout.setSpacing(15)
        
        # Title Label
        title_label = QLabel("KAMERA SIRALAMASI", self.order_widget)
        title_label.setObjectName("order_title_label")
        layout.addWidget(title_label)
        
        # Spacer
        layout.addStretch()
        
        # Sub-container layout for the cards to allow dynamic rebuilding
        self.order_cards_container = QWidget(self.order_widget)
        self.order_cards_container.setObjectName("order_cards_container")
        self.order_cards_layout = QHBoxLayout(self.order_cards_container)
        self.order_cards_layout.setContentsMargins(0, 0, 0, 0)
        self.order_cards_layout.setSpacing(10)
        layout.addWidget(self.order_cards_container)
        
        # Swap Button / Reorder button
        self.order_swap_btn = QPushButton("⇄ Yer Değiştir", self.order_widget)
        self.order_swap_btn.setObjectName("order_swap_btn")
        self.order_swap_btn.setCursor(Qt.PointingHandCursor)
        self.order_swap_btn.clicked.connect(self.swap_camera_order)
        layout.addWidget(self.order_swap_btn)
        
        layout.addStretch()
        self.order_cards = []

    def swap_camera_order(self):
        widgets = self.canvas.camera_widgets
        if len(widgets) >= 2:
            # Shift order (swap if N=2, rotate if N>2)
            first = widgets.pop(0)
            widgets.append(first)
            # Redo layout
            self.canvas.setup_layout()
            # Update order widget UI
            self.update_order_widget()

    def select_camera_by_widget_index(self, index):
        if index < len(self.canvas.camera_widgets):
            widget = self.canvas.camera_widgets[index]
            self.canvas.select_camera(widget)
            self.update_order_widget()

    def update_order_widget(self):
        if not hasattr(self, "order_cards_layout"):
            return
            
        # Clear existing cards in layout
        while self.order_cards_layout.count() > 0:
            item = self.order_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        # Dynamically create cards for each camera widget
        self.order_cards = []
        for i, w in enumerate(self.canvas.camera_widgets):
            card = QPushButton(self.order_cards_container)
            card.setObjectName(f"order_card_{i+1}")
            # Style base configuration
            card.setStyleSheet("""
                QPushButton {
                    background-color: #16161C;
                    border: 1px solid #23232C;
                    border-radius: 6px;
                    color: #9292A6;
                    font-size: 11px;
                    font-weight: 700;
                    padding: 4px 16px;
                    min-height: 28px;
                    max-height: 28px;
                }
                QPushButton:hover {
                    border-color: #00E5FF;
                    color: #FFFFFF;
                }
            """)
            
            # Highlight active/selected camera
            if w.selected:
                card.setStyleSheet("""
                    QPushButton {
                        background-color: #1E1E26;
                        border-color: #00E5FF;
                        color: #00E5FF;
                        font-weight: 800;
                        font-size: 11px;
                        padding: 4px 16px;
                        min-height: 28px;
                        max-height: 28px;
                        border-radius: 6px;
                    }
                """)
                
            card.setText(f"{i+1}: {w.title}")
            
            # Connect card click to selection using default arg to capture current w
            def make_select_slot(cam_widget=w):
                return lambda: self.canvas.select_camera(cam_widget)
            card.clicked.connect(make_select_slot(w))
            
            self.order_cards_layout.addWidget(card)
            self.order_cards.append(card)

    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def nativeEvent(self, eventType, message):
        if platform.system() == "Windows":
            if eventType == b"windows_generic_MSG":
                try:
                    msg = wintypes.MSG.from_address(int(message))
                    if msg.message == 0x0084:  # WM_NCHITTEST
                        x = ctypes.c_short(msg.lParam & 0xFFFF).value
                        y = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value
                        
                        local_pos = self.mapFromGlobal(QPoint(x, y))
                        
                        win_x = self.x()
                        win_y = self.y()
                        win_w = self.width()
                        win_h = self.height()
                        
                        BORDER_WIDTH = 8
                        
                        on_left = win_x <= x < win_x + BORDER_WIDTH
                        on_right = win_x + win_w - BORDER_WIDTH <= x < win_x + win_w
                        on_top = win_y <= y < win_y + BORDER_WIDTH
                        on_bottom = win_y + win_h - BORDER_WIDTH <= y < win_y + win_h
                        
                        # Corner detection
                        if on_top and on_left:
                            return True, 13  # HTTOPLEFT
                        elif on_top and on_right:
                            return True, 14  # HTTOPRIGHT
                        elif on_bottom and on_left:
                            return True, 16  # HTBOTTOMLEFT
                        elif on_bottom and on_right:
                            return True, 17  # HTBOTTOMRIGHT
                        
                        # Border detection
                        if on_left:
                            return True, 10  # HTLEFT
                        elif on_right:
                            return True, 11  # HTRIGHT
                        elif on_top:
                            return True, 12  # HTTOP
                        elif on_bottom:
                            return True, 15  # HTBOTTOM
                        
                        # Draggable header bar title/logo area check
                        header_pos = self.header_bar.mapFromGlobal(QPoint(x, y))
                        if self.header_bar.rect().contains(header_pos):
                            child = self.childAt(local_pos)
                            is_interactive = False
                            if child is not None:
                                if isinstance(child, QPushButton) or child.inherits("QPushButton"):
                                    is_interactive = True
                                elif hasattr(self, "preset_widget") and self.preset_widget.isAncestorOf(child):
                                    is_interactive = True
                                elif hasattr(self, "win_controls_widget") and self.win_controls_widget.isAncestorOf(child):
                                    is_interactive = True
                            
                            if is_interactive:
                                return True, 1  # HTCLIENT
                            
                            return True, 2  # HTCAPTION
                except Exception:
                    pass
        return super().nativeEvent(eventType, message)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Check if clicked inside header bar for dragging
            header_pos = self.header_bar.mapFromGlobal(event.globalPosition().toPoint())
            if self.header_bar.rect().contains(header_pos):
                self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()
                return
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and hasattr(self, "_drag_position"):
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()
            return
        super().mouseMoveEvent(event)
        
    def mouseReleaseEvent(self, event):
        if hasattr(self, "_drag_position"):
            delattr(self, "_drag_position")
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Position custom size grip in the bottom right corner dynamically
        if hasattr(self, "size_grip"):
            self.size_grip.setGeometry(
                self.width() - 16,
                self.height() - 16,
                16,
                16
            )

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
                self.auto_start_all_discovered_cameras(devices)
                return
        except Exception:
            pass
            
        self._discovery_worker = CameraDiscoveryWorker(self)
        self._discovery_worker.finished.connect(self.on_discovery_finished)
        self._discovery_worker.start()

    def on_discovery_finished(self, devices):
        self.control_panel.populate_devices(devices)
        self.auto_start_all_discovered_cameras(devices)

    def auto_start_all_discovered_cameras(self, devices):
        import sys
        if "pytest" in sys.modules:
            return
            
        # Stop any existing grabbers first to ensure clean state
        for key in list(self.grabbers.keys()):
            self.stop_grabber(key)
            
        # Reset camera configs to default offline state
        self.camera_configs = {
            "A": {"device_idx": -1, "name": "None", "width": 640, "height": 480, "fps": 30},
            "B": {"device_idx": -1, "name": "None", "width": 640, "height": 480, "fps": 30}
        }
        self.display_to_key = {"Camera A": "A", "Camera B": "B"}
        self.key_to_display = {"A": "Camera A", "B": "Camera B"}
        
        keys = ["A", "B", "C", "D", "E"]
        
        for idx, dev in enumerate(devices):
            if idx < len(keys):
                cam_key = keys[idx]
            else:
                cam_key = f"Cam{idx + 1}"
                
            display_name = f"Camera {cam_key}"
            self.display_to_key[display_name] = cam_key
            self.key_to_display[cam_key] = display_name
            
            # Find highest resolution
            supported = dev.get("supported_resolutions", [])
            if supported:
                # Sort by resolution area descending
                supported_sorted = sorted(supported, key=lambda r: r[0] * r[1], reverse=True)
                width, height = supported_sorted[0]
            else:
                width, height = 1280, 720
                
            # Grab target FPS (default to 60 for low-res, 30 for high-res/4K)
            if width >= 3840:
                fps = 30
            else:
                fps = 60 # Try 60 FPS for full smoothness!
                
            self.camera_configs[cam_key] = {
                "device_idx": dev["index"],
                "name": dev["name"],
                "width": width,
                "height": height,
                "fps": fps
            }
            
            self.start_grabber(cam_key)
            
        self.update_control_panel_cameras()

    def update_control_panel_cameras(self):
        active_configs = {}
        for key, config in self.camera_configs.items():
            if key in ["A", "B"] or config["device_idx"] != -1:
                display_name = self.key_to_display.get(key, f"Camera {key}")
                grabber = self.grabbers.get(key)
                if grabber is not None and grabber.isRunning():
                    config["running"] = True
                    config["width"] = grabber.active_width
                    config["height"] = grabber.active_height
                    if hasattr(grabber, "fps") and grabber.fps > 0:
                        config["fps"] = int(round(grabber.fps))
                else:
                    config["running"] = False
                active_configs[display_name] = dict(config)
        self.control_panel.update_active_cameras(active_configs)
        self.update_order_widget()

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
        self.update_order_widget()

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
            
            # Immediately refresh header labels dynamically
            if cam_widget.grabber is not None:
                details = []
                if cam_widget.show_res:
                    details.append(f"{cam_widget.grabber.active_width}x{cam_widget.grabber.active_height}")
                if cam_widget.show_fps:
                    details.append(f"{cam_widget.grabber.current_fps:.1f} FPS")
                if cam_widget.show_timestamp:
                    import datetime
                    details.append(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                cam_widget.title_label.setText(cam_widget.title)
                cam_widget.details_label.setText("  |  ".join(details))

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
        
        # Immediately push initial dimensions and configurations to grabber
        cam_widget.push_settings_to_grabber()
        
        # Update UI settings inputs on the first frame arrival to sync actual resolution/FPS
        self._first_frame_flags = getattr(self, "_first_frame_flags", {})
        self._first_frame_flags[cam_key] = True
        
        def on_first_frame_received(q_img, ck=cam_key):
            if getattr(self, "_first_frame_flags", {}).get(ck):
                self._first_frame_flags[ck] = False
                self.update_control_panel_cameras()
                
        grabber.frame_ready.connect(on_first_frame_received)
        
        # Schedule check for actual FPS vs target FPS to auto-downgrade if camera cannot deliver requested rate
        import sys
        if "pytest" not in sys.modules:
            QTimer.singleShot(2500, lambda g=grabber, ck=cam_key: self.sync_fps_after_stabilization(g, ck))
        
        self.canvas.setup_layout()

    def sync_fps_after_stabilization(self, grabber, cam_key):
        # Only process if this grabber is still the active one for this key and is running
        if self.grabbers.get(cam_key) is grabber and grabber.isRunning():
            actual_fps = grabber.current_fps
            target_fps = grabber.fps
            if actual_fps > 0 and target_fps > 0:
                # If actual rolling FPS is significantly lower than target FPS (less than 80%)
                if actual_fps < target_fps * 0.8:
                    new_fps = int(round(actual_fps))
                    new_fps = max(1, new_fps)
                    grabber.fps = new_fps
                    self.update_control_panel_cameras()

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
