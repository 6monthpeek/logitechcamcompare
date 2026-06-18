from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                              QFormLayout, QComboBox, QPushButton, QLabel, QSpinBox,
                              QCheckBox, QSlider, QListWidget, QMenu, QScrollArea, QFrame)
from PySide6.QtCore import Signal, Slot, Qt, QPoint

class ControlPanel(QWidget):
    """
    Settings control panel UI for layout presets, sources list, and dynamic camera configurations.
    Exposes static attributes (cam_a_*, cam_b_*) to maintain test compatibility,
    but styles them dynamically inside a clean, modern Next.js dark theme layout.
    """
    # Signals
    preset_changed = Signal(str)
    refresh_requested = Signal()
    reset_layout_requested = Signal()
    
    # Custom camera settings coordination
    source_selected = Signal(str)
    add_camera_requested = Signal(str, int)  # (name, device_idx)
    remove_camera_requested = Signal(str)     # (cam_id)
    camera_settings_changed = Signal(str, int, int, int, int) # (cam_id, device_idx, width, height, fps)
    open_system_settings_requested = Signal(str)
    
    brightness_changed = Signal(str, int)
    contrast_changed = Signal(str, int)
    zoom_changed = Signal(str, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaximumWidth(320)
        
        self.devices_data = []
        self.active_cameras_configs = {}

        # Main Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setSpacing(5)
        
        # Header Widget (Branding)
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(10, 10, 10, 5)
        header_layout.setSpacing(4)
        
        title_label = QLabel("CAMCOMPARE")
        title_label.setStyleSheet("""
            font-family: 'Inter', sans-serif;
            font-size: 16px;
            font-weight: 900;
            color: #ffffff;
            letter-spacing: 2px;
        """)
        
        subtitle_label = QLabel("DUAL WEBCAM ANALYZER")
        subtitle_label.setStyleSheet("""
            font-family: 'Inter', sans-serif;
            font-size: 9px;
            color: #14b8a6;
            font-weight: 700;
            letter-spacing: 1px;
        """)
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        
        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #27272a; max-height: 1px; border: none;")
        header_layout.addWidget(separator)
        
        self.main_layout.addWidget(header_widget)
        
        # Scroll Area for a premium scrollable sidebar layout
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.NoFrame)
        self.scroll_area.setStyleSheet("background-color: transparent;")
        
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(5, 5, 5, 5)
        self.scroll_layout.setSpacing(12)
        
        # 1. General Settings Group
        self.setup_general_group()
        
        # 2. Sources List Group (OBS-style scene sources manager)
        self.setup_sources_group()
        
        # 3. Camera A Settings Card
        self.setup_camera_card("A")
        
        # 4. Camera B Settings Card
        self.setup_camera_card("B")
        
        self.scroll_layout.addStretch()
        self.scroll_area.setWidget(self.scroll_content)
        self.main_layout.addWidget(self.scroll_area)

    def setup_general_group(self):
        group = QGroupBox("Layout & Controls")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        
        # Preset Select
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
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
        
        # Action Buttons
        self.reset_layout_btn = QPushButton("Reset Layout")
        self.reset_layout_btn.setObjectName("reset_layout_btn")
        self.reset_layout_btn.clicked.connect(self.reset_layout_requested.emit)
        layout.addWidget(self.reset_layout_btn)
        
        self.refresh_btn = QPushButton("Scan / Refresh Cameras")
        self.refresh_btn.setObjectName("refresh_btn")
        self.refresh_btn.clicked.connect(self.refresh_requested.emit)
        layout.addWidget(self.refresh_btn)
        
        self.scroll_layout.addWidget(group)

    def setup_sources_group(self):
        group = QGroupBox("Kaynaklar (Sources)")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        
        self.sources_list = QListWidget()
        self.sources_list.itemSelectionChanged.connect(self.on_source_selection_changed)
        layout.addWidget(self.sources_list)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        self.add_source_btn = QPushButton("+ Kamera Ekle")
        self.add_source_btn.clicked.connect(self.show_add_source_menu)
        
        self.remove_source_btn = QPushButton("- Sil")
        self.remove_source_btn.clicked.connect(self.remove_selected_source)
        
        btn_layout.addWidget(self.add_source_btn)
        btn_layout.addWidget(self.remove_source_btn)
        layout.addLayout(btn_layout)
        
        self.scroll_layout.addWidget(group)

    def setup_camera_card(self, cam_id):
        group = QGroupBox(f"Camera {cam_id}")
        group.setObjectName(f"cam_{cam_id.lower()}_group")
        group.setProperty("selected", False)
        
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        
        # Device Combo
        dev_combo = QComboBox()
        dev_combo.addItem("None", -1)
        form.addRow("Aygıt:", dev_combo)
        
        # Resolution Combo
        res_combo = QComboBox()
        form.addRow("Çözünürlük:", res_combo)
        
        # Target FPS
        fps_spin = QSpinBox()
        fps_spin.setRange(1, 120)
        fps_spin.setValue(30)
        form.addRow("Target FPS:", fps_spin)
        
        # Brightness
        slider_brightness = QSlider(Qt.Horizontal)
        slider_brightness.setRange(0, 100)
        slider_brightness.setValue(50)
        brightness_val_label = QLabel("50%")
        brightness_val_label.setFixedWidth(35)
        brightness_layout = QHBoxLayout()
        brightness_layout.setContentsMargins(0, 0, 0, 0)
        brightness_layout.addWidget(slider_brightness)
        brightness_layout.addWidget(brightness_val_label)
        form.addRow("Parlaklık:", brightness_layout)
        
        # Contrast
        slider_contrast = QSlider(Qt.Horizontal)
        slider_contrast.setRange(0, 100)
        slider_contrast.setValue(50)
        contrast_val_label = QLabel("50%")
        contrast_val_label.setFixedWidth(35)
        contrast_layout = QHBoxLayout()
        contrast_layout.setContentsMargins(0, 0, 0, 0)
        contrast_layout.addWidget(slider_contrast)
        contrast_layout.addWidget(contrast_val_label)
        form.addRow("Kontrast:", contrast_layout)
        
        # Zoom
        slider_zoom = QSlider(Qt.Horizontal)
        slider_zoom.setRange(10, 50)
        slider_zoom.setValue(10)
        zoom_val_label = QLabel("1.0x")
        zoom_val_label.setFixedWidth(35)
        zoom_layout = QHBoxLayout()
        zoom_layout.setContentsMargins(0, 0, 0, 0)
        zoom_layout.addWidget(slider_zoom)
        zoom_layout.addWidget(zoom_val_label)
        form.addRow("Zoom:", zoom_layout)
        
        layout.addLayout(form)
        
        # Start/Stop Button
        toggle_btn = QPushButton(f"Start Camera {cam_id}")
        toggle_btn.setProperty("active", False)
        toggle_btn.setCheckable(True)
        toggle_btn.clicked.connect(lambda checked, cid=cam_id: self.on_camera_toggle(cid, checked))
        layout.addWidget(toggle_btn)
        
        # Configure Video (System) Button
        sys_btn = QPushButton("Video Yapılandır (Sistem)")
        sys_btn.setObjectName(f"cam_{cam_id.lower()}_sys_btn")
        sys_btn.setEnabled(False)
        sys_btn.clicked.connect(lambda _, cid=cam_id: self.open_system_settings_requested.emit(f"Camera {cid}"))
        layout.addWidget(sys_btn)
        
        # Save attributes dynamically for test compliance
        setattr(self, f"cam_{cam_id.lower()}_dev_combo", dev_combo)
        setattr(self, f"cam_{cam_id.lower()}_res_combo", res_combo)
        setattr(self, f"cam_{cam_id.lower()}_fps_spin", fps_spin)
        setattr(self, f"cam_{cam_id.lower()}_toggle_btn", toggle_btn)
        setattr(self, f"cam_{cam_id.lower()}_sys_btn", sys_btn)
        
        setattr(self, f"slider_brightness_{cam_id.lower()}", slider_brightness)
        setattr(self, f"slider_contrast_{cam_id.lower()}", slider_contrast)
        setattr(self, f"slider_zoom_{cam_id.lower()}", slider_zoom)
        
        setattr(self, f"cam_{cam_id.lower()}_group", group)
        
        # Sync slider label text
        slider_brightness.valueChanged.connect(lambda val: brightness_val_label.setText(f"{val}%"))
        slider_contrast.valueChanged.connect(lambda val: contrast_val_label.setText(f"{val}%"))
        slider_zoom.valueChanged.connect(lambda val: zoom_val_label.setText(f"{val / 10.0:.1f}x"))
        
        # Connect signals
        dev_combo.currentIndexChanged.connect(lambda _, cid=cam_id: self.on_device_changed(cid))
        res_combo.currentIndexChanged.connect(lambda _, cid=cam_id: self.on_settings_modified(cid))
        fps_spin.valueChanged.connect(lambda _, cid=cam_id: self.on_settings_modified(cid))
        
        slider_brightness.valueChanged.connect(lambda val, cid=cam_id: self.brightness_changed.emit(f"Camera {cid}", val))
        slider_contrast.valueChanged.connect(lambda val, cid=cam_id: self.contrast_changed.emit(f"Camera {cid}", val))
        slider_zoom.valueChanged.connect(lambda val, cid=cam_id: self.zoom_changed.emit(f"Camera {cid}", val / 10.0))
        
        self.scroll_layout.addWidget(group)

    def on_preset_changed(self, text):
        preset_map = {
            "Side-by-Side": "side-by-side",
            "Stacked": "stacked",
            "PiP": "pip"
        }
        self.preset_changed.emit(preset_map.get(text, "side-by-side"))

    def on_camera_toggle(self, cam_id, checked):
        display_name = f"Camera {cam_id}"
        if checked:
            dev_combo = getattr(self, f"cam_{cam_id.lower()}_dev_combo")
            device_idx = dev_combo.currentData()
            if device_idx is None or device_idx == -1:
                # If no device chosen, uncheck toggle and return
                btn = getattr(self, f"cam_{cam_id.lower()}_toggle_btn")
                btn.blockSignals(True)
                btn.setChecked(False)
                btn.blockSignals(False)
                return
            
            res_combo = getattr(self, f"cam_{cam_id.lower()}_res_combo")
            res_data = res_combo.currentData()
            width, height = res_data if res_data else (640, 480)
            fps_spin = getattr(self, f"cam_{cam_id.lower()}_fps_spin")
            fps = fps_spin.value()
            
            self.camera_settings_changed.emit(display_name, device_idx, width, height, fps)
        else:
            self.remove_camera_requested.emit(display_name)

    def on_settings_modified(self, cam_id):
        dev_combo = getattr(self, f"cam_{cam_id.lower()}_dev_combo")
        res_combo = getattr(self, f"cam_{cam_id.lower()}_res_combo")
        fps_spin = getattr(self, f"cam_{cam_id.lower()}_fps_spin")
        
        device_idx = dev_combo.currentData()
        if device_idx is None:
            device_idx = -1
            
        res_data = res_combo.currentData()
        width, height = res_data if res_data else (640, 480)
        fps = fps_spin.value()
        
        self.camera_settings_changed.emit(f"Camera {cam_id}", device_idx, width, height, fps)

    def show_scanning_placeholder(self):
        for cam_id in ["a", "b"]:
            combo = getattr(self, f"cam_{cam_id}_dev_combo")
            combo.clear()
            combo.addItem("Scanning...", -1)
            combo.setCurrentIndex(0)

    @Slot(list)
    def populate_devices(self, devices):
        self.devices_data = devices
        for cam_id in ["a", "b"]:
            combo = getattr(self, f"cam_{cam_id}_dev_combo")
            current_idx = combo.currentData()
            
            combo.blockSignals(True)
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
            combo.blockSignals(False)
            
            self.update_resolution_dropdown(cam_id.upper())

    def on_device_changed(self, cam_id):
        self.update_resolution_dropdown(cam_id)
        self.on_settings_modified(cam_id)

    def update_resolution_dropdown(self, cam_id):
        dev_combo = getattr(self, f"cam_{cam_id.lower()}_dev_combo")
        res_combo = getattr(self, f"cam_{cam_id.lower()}_res_combo")
        
        device_idx = dev_combo.currentData()
        
        device_info = None
        for dev in self.devices_data:
            if dev.get("index") == device_idx:
                device_info = dev
                break
                
        current_res = res_combo.currentData()
        
        res_combo.blockSignals(True)
        res_combo.clear()
        
        supported = []
        if device_info and "supported_resolutions" in device_info:
            supported = device_info["supported_resolutions"]
            
        if not supported or device_idx == -1:
            # Fallback standard resolutions
            supported = [(640, 480), (1280, 720), (1920, 1080), (2560, 1440), (3840, 2160)]
            
        for w, h in supported:
            label = f"{w} x {h}"
            if (w, h) == (1920, 1080):
                label += " (1080p)"
            elif (w, h) == (2560, 1440):
                label += " (2K)"
            elif (w, h) == (3840, 2160):
                label += " (4K)"
            elif (w, h) == (1280, 720):
                label += " (720p)"
            elif (w, h) == (640, 480):
                label += " (480p)"
            res_combo.addItem(label, (w, h))
            
        # Try to restore selection
        found = False
        for idx in range(res_combo.count()):
            if res_combo.itemData(idx) == current_res:
                res_combo.setCurrentIndex(idx)
                found = True
                break
        if not found and res_combo.count() > 0:
            res_combo.setCurrentIndex(0)
            
        res_combo.blockSignals(False)

    @Slot(dict)
    def update_active_cameras(self, configs):
        self.active_cameras_configs = configs
        
        # Sync control status cards
        for cam_id in ["A", "B"]:
            config = configs.get(f"Camera {cam_id}")
            toggle_btn = getattr(self, f"cam_{cam_id.lower()}_toggle_btn")
            sys_btn = getattr(self, f"cam_{cam_id.lower()}_sys_btn")
            dev_combo = getattr(self, f"cam_{cam_id.lower()}_dev_combo")
            res_combo = getattr(self, f"cam_{cam_id.lower()}_res_combo")
            fps_spin = getattr(self, f"cam_{cam_id.lower()}_fps_spin")
            
            if config and config.get("running", False):
                toggle_btn.blockSignals(True)
                toggle_btn.setChecked(True)
                toggle_btn.setText(f"Stop Camera {cam_id}")
                toggle_btn.setProperty("active", True)
                toggle_btn.blockSignals(False)
                
                sys_btn.setEnabled(True)
                
                # Sync device selection
                dev_combo.blockSignals(True)
                for idx in range(dev_combo.count()):
                    if dev_combo.itemData(idx) == config["device_idx"]:
                        dev_combo.setCurrentIndex(idx)
                        break
                dev_combo.blockSignals(False)
                
                # Sync resolution selection
                res_combo.blockSignals(True)
                current_res = (config["width"], config["height"])
                for idx in range(res_combo.count()):
                    if res_combo.itemData(idx) == current_res:
                        res_combo.setCurrentIndex(idx)
                        break
                res_combo.blockSignals(False)
                
                # Sync FPS selection
                fps_spin.blockSignals(True)
                fps_spin.setValue(config["fps"])
                fps_spin.blockSignals(False)
            else:
                toggle_btn.blockSignals(True)
                toggle_btn.setChecked(False)
                toggle_btn.setText(f"Start Camera {cam_id}")
                toggle_btn.setProperty("active", False)
                toggle_btn.blockSignals(False)
                
                sys_btn.setEnabled(False)
                
                dev_combo.blockSignals(True)
                if config and config.get("device_idx", -1) != -1:
                    for idx in range(dev_combo.count()):
                        if dev_combo.itemData(idx) == config["device_idx"]:
                            dev_combo.setCurrentIndex(idx)
                            break
                dev_combo.blockSignals(False)
                
            toggle_btn.style().unpolish(toggle_btn)
            toggle_btn.style().polish(toggle_btn)
            
        # Re-populate the sources list
        self.sources_list.blockSignals(True)
        selected_items = self.sources_list.selectedItems()
        selected_text = selected_items[0].text() if selected_items else None
        
        self.sources_list.clear()
        for cam_id in ["A", "B"]:
            config = configs.get(f"Camera {cam_id}")
            if config and config.get("device_idx", -1) != -1:
                self.sources_list.addItem(f"Camera {cam_id}")
                
        # Restore selection
        if selected_text:
            found = False
            for idx in range(self.sources_list.count()):
                item = self.sources_list.item(idx)
                if item.text() == selected_text:
                    self.sources_list.setCurrentItem(item)
                    found = True
                    break
            if not found and self.sources_list.count() > 0:
                self.sources_list.setCurrentRow(0)
        elif self.sources_list.count() > 0:
            self.sources_list.setCurrentRow(0)
            
        self.sources_list.blockSignals(False)
        self.on_source_selection_changed()

    def on_source_selection_changed(self):
        selected_items = self.sources_list.selectedItems()
        if not selected_items:
            for cid in ["a", "b"]:
                group = getattr(self, f"cam_{cid}_group", None)
                if group:
                    group.setProperty("selected", False)
                    group.style().unpolish(group)
                    group.style().polish(group)
            return
            
        selected_text = selected_items[0].text()
        cam_key = selected_text[-1].lower()
        
        for cid in ["a", "b"]:
            group = getattr(self, f"cam_{cid}_group", None)
            if group:
                is_sel = (cid == cam_key)
                group.setProperty("selected", is_sel)
                group.style().unpolish(group)
                group.style().polish(group)
                
        self.source_selected.emit(selected_text)

    def select_source(self, cam_id):
        self.sources_list.blockSignals(True)
        for idx in range(self.sources_list.count()):
            item = self.sources_list.item(idx)
            if item.text() == cam_id:
                self.sources_list.setCurrentItem(item)
                break
        self.sources_list.blockSignals(False)
        
        cam_key = cam_id[-1].lower() if cam_id else ""
        for cid in ["a", "b"]:
            group = getattr(self, f"cam_{cid}_group", None)
            if group:
                is_sel = (cid == cam_key)
                group.setProperty("selected", is_sel)
                group.style().unpolish(group)
                group.style().polish(group)

    def show_add_source_menu(self, target_widget=None):
        if target_widget is None or isinstance(target_widget, bool):
            target_widget = self.add_source_btn
        menu = QMenu(self)
        
        active_indices = []
        for cid in ["a", "b"]:
            toggle_btn = getattr(self, f"cam_{cid}_toggle_btn")
            if toggle_btn.isChecked():
                dev_combo = getattr(self, f"cam_{cid}_dev_combo")
                idx = dev_combo.currentData()
                if idx is not None and idx != -1:
                    active_indices.append(idx)
                    
        available_devices = []
        for dev in self.devices_data:
            if dev["index"] not in active_indices:
                available_devices.append(dev)
                
        if not available_devices:
            action = menu.addAction("Kullanılabilir kamera yok")
            action.setEnabled(False)
        else:
            for dev in available_devices:
                action = menu.addAction(f"{dev['index']}: {dev['name']}")
                def make_trigger_slot(d=dev):
                    return lambda: self.add_new_camera(d["index"])
                action.triggered.connect(make_trigger_slot(dev))
                
        menu.exec(target_widget.mapToGlobal(QPoint(0, target_widget.height())))

    def add_new_camera(self, device_idx):
        target_slot = None
        for slot in ["a", "b"]:
            toggle_btn = getattr(self, f"cam_{slot}_toggle_btn")
            if not toggle_btn.isChecked():
                target_slot = slot
                break
        
        if target_slot is None:
            target_slot = "a"
            
        dev_combo = getattr(self, f"cam_{target_slot}_dev_combo")
        
        dev_combo.blockSignals(True)
        for idx in range(dev_combo.count()):
            if dev_combo.itemData(idx) == device_idx:
                dev_combo.setCurrentIndex(idx)
                break
        dev_combo.blockSignals(False)
        
        self.update_resolution_dropdown(target_slot.upper())
        
        toggle_btn = getattr(self, f"cam_{target_slot}_toggle_btn")
        toggle_btn.setChecked(True)
        self.on_camera_toggle(target_slot.upper(), True)

    def remove_selected_source(self):
        selected_items = self.sources_list.selectedItems()
        if not selected_items:
            return
        cam_id = selected_items[0].text()
        cam_key = cam_id[-1].lower()
        
        toggle_btn = getattr(self, f"cam_{cam_key}_toggle_btn")
        if toggle_btn.isChecked():
            toggle_btn.setChecked(False)
            self.on_camera_toggle(cam_key.upper(), False)
