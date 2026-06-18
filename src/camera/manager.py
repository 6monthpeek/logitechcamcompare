import cv2
try:
    from PySide6.QtMultimedia import QMediaDevices
    PYSIDE_MULTIMEDIA_AVAILABLE = True
except ImportError:
    PYSIDE_MULTIMEDIA_AVAILABLE = False

class CameraManager:
    """
    Handles camera discovery, listing, and capability checks using OpenCV and QMediaDevices.
    """
    
    @staticmethod
    def list_devices():
        """
        Lists available camera devices.
        Returns:
            list of dict: [{"index": int, "name": str, "supported_resolutions": [(w, h), ...]}]
        """
        devices = []
        if PYSIDE_MULTIMEDIA_AVAILABLE:
            video_inputs = QMediaDevices.videoInputs()
            if video_inputs:
                for i, device in enumerate(video_inputs):
                    caps = CameraManager.check_capabilities(i)
                    devices.append({
                        "index": i,
                        "name": device.description() or f"Camera {i}",
                        "supported_resolutions": caps["resolutions"]
                    })
                return devices
        
        # Fallback to cv2 VideoCapture discovery
        import platform
        for index in range(10):
            try:
                if platform.system() == "Windows":
                    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
                else:
                    cap = cv2.VideoCapture(index)
            except TypeError:
                cap = cv2.VideoCapture(index)
            if not cap.isOpened() and platform.system() == "Windows":
                try:
                    cap = cv2.VideoCapture(index) # Fallback to default
                except TypeError:
                    pass
            if cap.isOpened():
                cap.release()
                caps = CameraManager.check_capabilities(index)
                devices.append({
                    "index": index,
                    "name": f"Camera {index}",
                    "supported_resolutions": caps["resolutions"]
                })
        return devices

    @staticmethod
    def check_capabilities(device_index):
        """
        Probes the camera at the given index to find supported resolutions and FPS.
        Returns:
            dict: {
                "resolutions": list of tuples (width, height),
                "fps": float
            }
        """
        capabilities = {
            "resolutions": [],
            "fps": 0.0
        }
        
        if not isinstance(device_index, int) or isinstance(device_index, bool):
            return capabilities
            
        if not (-2**31 <= device_index < 2**31):
            return capabilities
                
        import platform
        try:
            try:
                if platform.system() == "Windows":
                    cap = cv2.VideoCapture(device_index, cv2.CAP_DSHOW)
                else:
                    cap = cv2.VideoCapture(device_index)
            except TypeError:
                cap = cv2.VideoCapture(device_index)
            if not cap.isOpened() and platform.system() == "Windows":
                try:
                    cap = cv2.VideoCapture(device_index)
                except TypeError:
                    pass
        except (cv2.error, TypeError, OverflowError, ValueError, Exception):
            return capabilities
            
        if not cap.isOpened():
            return capabilities
            
        common_resolutions = [
            (640, 480),
            (1280, 720),
            (1920, 1080),
            (2560, 1440),
            (3840, 2160)
        ]
        
        for w, h in common_resolutions:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
            
            actual_w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            
            if int(actual_w) == w and int(actual_h) == h:
                capabilities["resolutions"].append((w, h))
                
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps > 0:
            capabilities["fps"] = float(fps)
            
        cap.release()
        return capabilities


class CameraBackend:
    """
    Deprecated: Handles camera discovery and capability checks using OpenCV and QMediaDevices.
    Please use CameraManager instead.
    """
    
    @staticmethod
    def discover_cameras(max_indices=10):
        discovered = []
        for index in range(max_indices):
            cap = cv2.VideoCapture(index)
            if cap.isOpened():
                discovered.append(index)
                cap.release()
        return discovered

    @staticmethod
    def get_camera_devices():
        devices = []
        if PYSIDE_MULTIMEDIA_AVAILABLE:
            video_inputs = QMediaDevices.videoInputs()
            for i, device in enumerate(video_inputs):
                devices.append({
                    "index": i,
                    "name": device.description(),
                    "id": device.id().data().decode(errors="replace") if hasattr(device.id(), 'data') else str(device.id())
                })
        return devices

    @staticmethod
    def get_camera_capabilities(index, common_resolutions=None):
        return CameraManager.check_capabilities(index)

