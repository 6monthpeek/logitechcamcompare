import cv2
import datetime
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtGui import QImage, QPixmap, QPainter, QColor, QFont
from PySide6.QtCore import Qt, Slot, QPoint

class CameraWidget(QWidget):
    """
    Widget to display a real-time camera feed.
    Converts incoming BGR frames to RGB QImage and displays them.
    """
    def __init__(self, title="Camera Feed", parent=None):
        super().__init__(parent)
        self.title = title
        self.show_fps = True
        self.show_res = True
        self.show_timestamp = True
        self.grabber = None
        
        # UI elements
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.placeholder_label = QLabel(f"{self.title}\n(Camera Offline)")
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setStyleSheet("background-color: #1e1e24; color: #888888; font-size: 14px; border: 2px dashed #444;")
        self.placeholder_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setVisible(False)
        self.video_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        
        self.layout.addWidget(self.placeholder_label)
        self.layout.addWidget(self.video_label)
        
        self.current_frame = None
        self.brightness_val = 50.0
        self.contrast_val = 50.0
        self.zoom_val = 1.0
        self.pan_offset = QPoint(0, 0)
        self.is_panning = False
        
        # Interaction attributes
        self.setMouseTracking(True)
        self.interaction_direction = None
        self.drag_start_pos = None
        self.drag_start_geometry = None

    def get_interaction_info(self, pos):
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        margin = 8
        
        on_left = x < margin
        on_right = x > w - margin
        on_top = y < margin
        on_bottom = y > h - margin
        
        if on_left and on_top:
            return "TL", Qt.SizeFDiagCursor
        elif on_right and on_bottom:
            return "BR", Qt.SizeFDiagCursor
        elif on_right and on_top:
            return "TR", Qt.SizeBDiagCursor
        elif on_left and on_bottom:
            return "BL", Qt.SizeBDiagCursor
        elif on_left:
            return "L", Qt.SizeHorCursor
        elif on_right:
            return "R", Qt.SizeHorCursor
        elif on_top:
            return "T", Qt.SizeVerCursor
        elif on_bottom:
            return "B", Qt.SizeVerCursor
        else:
            return "drag", Qt.OpenHandCursor

    def set_brightness(self, val):
        self.brightness_val = float(val)
        if self.current_frame is not None:
            self.update_frame(self.current_frame)

    def set_contrast(self, val):
        self.contrast_val = float(val)
        if self.current_frame is not None:
            self.update_frame(self.current_frame)

    def set_zoom(self, val):
        self.zoom_val = float(val)
        if self.current_frame is not None:
            # Clamp pan_offset if zoom changes
            h, w = self.current_frame.shape[:2]
            crop_w = w / self.zoom_val
            crop_h = h / self.zoom_val
            max_x = (w - crop_w) / 2.0
            max_y = (h - crop_h) / 2.0
            px = max(-max_x, min(float(self.pan_offset.x()), max_x))
            py = max(-max_y, min(float(self.pan_offset.y()), max_y))
            self.pan_offset.setX(int(round(px)))
            self.pan_offset.setY(int(round(py)))
            
            self.update_frame(self.current_frame)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            local_pos = event.position().toPoint()
            direction, cursor_shape = self.get_interaction_info(local_pos)
            
            if self.zoom_val > 1.0 and direction == "drag":
                self.is_panning = True
                self.pan_start_pos = event.position()
                self.pan_start_offset = QPoint(self.pan_offset.x(), self.pan_offset.y())
                self.setCursor(Qt.ClosedHandCursor)
                event.accept()
                return
                
            self.is_panning = False
            self.interaction_direction = direction
            self.drag_start_pos = event.globalPosition().toPoint()
            self.drag_start_geometry = self.geometry()
            
            if direction == "drag":
                self.setCursor(Qt.ClosedHandCursor)
            else:
                self.setCursor(cursor_shape)
                
            parent = self.parent()
            if parent and hasattr(parent, "on_interactive_layout_start"):
                parent.on_interactive_layout_start()
                
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if getattr(self, "is_panning", False):
            if self.current_frame is not None:
                delta = event.position() - self.pan_start_pos
                h_img, w_img = self.current_frame.shape[:2]
                crop_w = w_img / self.zoom_val
                crop_h = h_img / self.zoom_val
                
                widget_w = self.width()
                widget_h = self.height()
                
                if widget_w > 0 and widget_h > 0:
                    scale_x = crop_w / float(widget_w)
                    scale_y = crop_h / float(widget_h)
                else:
                    scale_x = 1.0
                    scale_y = 1.0
                
                new_x = self.pan_start_offset.x() - delta.x() * scale_x
                new_y = self.pan_start_offset.y() - delta.y() * scale_y
                
                max_x = (w_img - crop_w) / 2.0
                max_y = (h_img - crop_h) / 2.0
                clamped_x = max(-max_x, min(new_x, max_x))
                clamped_y = max(-max_y, min(new_y, max_y))
                
                self.pan_offset.setX(int(round(clamped_x)))
                self.pan_offset.setY(int(round(clamped_y)))
                
                self.update_frame(self.current_frame)
            event.accept()
            return

        if self.interaction_direction is not None:
            delta = event.globalPosition().toPoint() - self.drag_start_pos
            
            if self.interaction_direction == "drag":
                x0, y0 = self.drag_start_geometry.x(), self.drag_start_geometry.y()
                w0, h0 = self.drag_start_geometry.width(), self.drag_start_geometry.height()
                
                new_x = x0 + delta.x()
                new_y = y0 + delta.y()
                
                parent = self.parent()
                if parent:
                    parent_w = parent.width()
                    parent_h = parent.height()
                else:
                    parent_w = w0
                    parent_h = h0
                    
                new_x = max(0, min(new_x, parent_w - w0))
                new_y = max(0, min(new_y, parent_h - h0))
                
                self.move(new_x, new_y)
            else:
                # Resizing
                x0, y0 = self.drag_start_geometry.x(), self.drag_start_geometry.y()
                w0, h0 = self.drag_start_geometry.width(), self.drag_start_geometry.height()
                r0 = x0 + w0
                b0 = y0 + h0
                
                parent = self.parent()
                parent_w = parent.width() if parent else r0
                parent_h = parent.height() if parent else b0
                
                new_x, new_y, new_w, new_h = x0, y0, w0, h0
                direction = self.interaction_direction
                
                if "L" in direction:
                    requested_x = x0 + delta.x()
                    new_x = max(0, min(requested_x, r0 - 100))
                    new_w = r0 - new_x
                elif "R" in direction:
                    requested_r = r0 + delta.x()
                    new_r = max(x0 + 100, min(requested_r, parent_w))
                    new_w = new_r - x0
                    new_x = x0
                    
                if "T" in direction:
                    requested_y = y0 + delta.y()
                    new_y = max(0, min(requested_y, b0 - 100))
                    new_h = b0 - new_y
                elif "B" in direction:
                    requested_b = b0 + delta.y()
                    new_b = max(y0 + 100, min(requested_b, parent_h))
                    new_h = new_b - y0
                    new_y = y0
                    
                self.setGeometry(new_x, new_y, new_w, new_h)
            event.accept()
        else:
            local_pos = event.position().toPoint()
            _, cursor_shape = self.get_interaction_info(local_pos)
            self.setCursor(cursor_shape)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if getattr(self, "is_panning", False):
                self.is_panning = False
            self.interaction_direction = None
            local_pos = event.position().toPoint()
            _, cursor_shape = self.get_interaction_info(local_pos)
            self.setCursor(cursor_shape)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    @Slot(object)
    def update_frame(self, frame):
        """
        Receives a numpy frame, converts it, and displays it.
        """
        if frame is None:
            self.show_placeholder()
            return
            
        self.current_frame = frame
        
        try:
            h_orig, w_orig = frame.shape[:2]
            
            # Perform zoom cropping (before adjustments) if self.zoom_val > 1.0
            if self.zoom_val > 1.0:
                crop_w = w_orig / self.zoom_val
                crop_h = h_orig / self.zoom_val
                
                # Clamp pan_offset dynamically so the crop box stays within [0, w] and [0, h]
                max_x = (w_orig - crop_w) / 2.0
                max_y = (h_orig - crop_h) / 2.0
                px = max(-max_x, min(float(self.pan_offset.x()), max_x))
                py = max(-max_y, min(float(self.pan_offset.y()), max_y))
                self.pan_offset.setX(int(round(px)))
                self.pan_offset.setY(int(round(py)))
                
                center_x = w_orig / 2.0 + self.pan_offset.x()
                center_y = h_orig / 2.0 + self.pan_offset.y()
                
                x_start = max(0, int(round(center_x - crop_w / 2.0)))
                x_end = min(w_orig, int(round(center_x + crop_w / 2.0)))
                y_start = max(0, int(round(center_y - crop_h / 2.0)))
                y_end = min(h_orig, int(round(center_y + crop_h / 2.0)))
                
                if x_end > x_start and y_end > y_start:
                    frame = frame[y_start:y_end, x_start:x_end]
            
            # Adjust brightness and contrast
            frame = cv2.convertScaleAbs(
                frame, 
                alpha=self.contrast_val / 50.0, 
                beta=(self.brightness_val - 50.0) * 2.0
            )
            
            # Convert BGR to RGB
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            
            # Create QImage and copy to be safe with memory
            q_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
            
            # Create QPixmap and scale it to fit the widget size keeping aspect ratio
            pixmap = QPixmap.fromImage(q_image)
            scaled_pixmap = pixmap.scaled(
                self.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            # Render overlays using QPainter
            painter = QPainter(scaled_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            lines = []
            lines.append(f"{self.title}")
            
            if self.show_res:
                if self.grabber is not None:
                    w_res = self.grabber.active_width
                    h_res = self.grabber.active_height
                else:
                    h_res, w_res = h_orig, w_orig
                lines.append(f"Resolution: {w_res}x{h_res}")
                
            if self.show_fps:
                fps_val = self.grabber.current_fps if self.grabber is not None else 0.0
                lines.append(f"FPS: {fps_val:.1f}")
                
            if self.show_timestamp:
                timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                lines.append(timestamp_str)
                
            font = QFont("Segoe UI", 10, QFont.Bold)
            painter.setFont(font)
            metrics = painter.fontMetrics()
            
            line_height = metrics.height()
            line_spacing = 4
            margin_x = 10
            margin_y = 10
            
            max_w = 0
            for line in lines:
                max_w = max(max_w, metrics.horizontalAdvance(line))
                
            box_w = max_w + (margin_x * 2)
            box_h = (line_height * len(lines)) + (line_spacing * (len(lines) - 1)) + (margin_y * 2)
            
            pos_x = 10
            pos_y = 10
            
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 0, 0, 153))
            painter.drawRoundedRect(pos_x, pos_y, box_w, box_h, 5, 5)
            
            painter.setPen(QColor(255, 255, 255))
            current_y = pos_y + margin_y + metrics.ascent()
            for line in lines:
                painter.drawText(pos_x + margin_x, current_y, line)
                current_y += line_height + line_spacing
                
            painter.end()
            
            if self.placeholder_label.isVisible():
                self.placeholder_label.setVisible(False)
                self.video_label.setVisible(True)
                
            self.video_label.setPixmap(scaled_pixmap)
            
        except Exception as e:
            print(f"Error rendering frame: {e}")
            self.show_placeholder()

    def show_placeholder(self):
        """
        Resets the view to the offline placeholder.
        """
        self.current_frame = None
        self.video_label.setVisible(False)
        self.placeholder_label.setVisible(True)

    def resizeEvent(self, event):
        """
        Ensures that if the widget is resized, the last frame is scaled accordingly.
        """
        super().resizeEvent(event)
        if self.current_frame is not None:
            self.update_frame(self.current_frame)
