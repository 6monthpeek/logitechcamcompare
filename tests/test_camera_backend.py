import unittest
from unittest.mock import patch
import numpy as np
import cv2
import time
from src.camera.manager import CameraManager

class MockVideoCapture:
    """
    A simulated OpenCV VideoCapture device.
    Allows testing camera backend functionality without physical camera hardware.
    """
    def __init__(self, index, supported_resolutions=None, default_fps=30.0, active_indices=None):
        self.index = index
        self.active_indices = active_indices if active_indices is not None else [0, 1]
        self.opened = index in self.active_indices
        
        # Default supported resolutions
        self.supported_resolutions = supported_resolutions if supported_resolutions is not None else [
            (640, 480),
            (1280, 720)
        ]
        
        # Initial properties
        self.properties = {
            cv2.CAP_PROP_FRAME_WIDTH: 640.0,
            cv2.CAP_PROP_FRAME_HEIGHT: 480.0,
            cv2.CAP_PROP_FPS: default_fps,
        }

    def isOpened(self):
        return self.opened

    def get(self, prop_id):
        if not self.opened:
            return 0.0
        return float(self.properties.get(prop_id, 0.0))

    def set(self, prop_id, value):
        if not self.opened:
            return False
            
        if prop_id == cv2.CAP_PROP_FRAME_WIDTH:
            self._temp_width = value
            self.properties[cv2.CAP_PROP_FRAME_WIDTH] = float(value)
            return True
            
        elif prop_id == cv2.CAP_PROP_FRAME_HEIGHT:
            self.properties[cv2.CAP_PROP_FRAME_HEIGHT] = float(value)
            # Validate resolution pair
            w = self.properties.get(cv2.CAP_PROP_FRAME_WIDTH, 0)
            h = value
            if (int(w), int(h)) in self.supported_resolutions:
                return True
            else:
                # Revert to default resolution if not supported
                self.properties[cv2.CAP_PROP_FRAME_WIDTH] = 640.0
                self.properties[cv2.CAP_PROP_FRAME_HEIGHT] = 480.0
                return True
                
        elif prop_id in self.properties:
            self.properties[prop_id] = float(value)
            return True
            
        return False

    def read(self):
        if not self.opened:
            return False, None
        w = int(self.properties[cv2.CAP_PROP_FRAME_WIDTH])
        h = int(self.properties[cv2.CAP_PROP_FRAME_HEIGHT])
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        return True, frame

    def release(self):
        self.opened = False


class TestCameraManager(unittest.TestCase):
    
    @patch('cv2.VideoCapture')
    def test_list_devices_success(self, mock_video_capture):
        """
        Verify that list_devices returns discovered cameras with the correct format.
        """
        mock_video_capture.side_effect = lambda idx: MockVideoCapture(idx, active_indices=[0, 1])
        
        devices = CameraManager.list_devices()
        
        discovered_indices = [dev["index"] for dev in devices]
        self.assertEqual(discovered_indices, [0, 1])
        for dev in devices:
            self.assertIn("index", dev)
            self.assertIn("name", dev)
            self.assertIn("supported_resolutions", dev)
            self.assertIsInstance(dev["supported_resolutions"], list)

    @patch('cv2.VideoCapture')
    def test_check_capabilities_valid(self, mock_video_capture):
        """
        Verify that check_capabilities correctly identifies supported resolutions and FPS.
        """
        supported = [(640, 480), (1280, 720)]
        mock_video_capture.return_value = MockVideoCapture(
            index=0, 
            supported_resolutions=supported, 
            default_fps=60.0
        )
        
        caps = CameraManager.check_capabilities(device_index=0)
        
        self.assertIn((640, 480), caps["resolutions"])
        self.assertIn((1280, 720), caps["resolutions"])
        self.assertNotIn((1920, 1080), caps["resolutions"])
        self.assertEqual(caps["fps"], 60.0)

    @patch('cv2.VideoCapture')
    def test_check_capabilities_closed(self, mock_video_capture):
        """
        Verify that querying an offline/closed camera returns empty capabilities.
        """
        mock_video_capture.return_value = MockVideoCapture(index=9, active_indices=[])
        
        caps = CameraManager.check_capabilities(device_index=9)
        
        self.assertEqual(caps["resolutions"], [])
        self.assertEqual(caps["fps"], 0.0)


class TestCameraGrabber(unittest.TestCase):
    
    @patch('cv2.VideoCapture')
    def test_grabber_start_stop_diagnostics(self, mock_video_capture):
        """
        Verify that CameraGrabber start_capture, stop_capture, and get_diagnostics operate correctly.
        """
        from src.camera.grabber import CameraGrabber
        mock_cap = MockVideoCapture(index=0)
        mock_video_capture.return_value = mock_cap
        
        grabber = CameraGrabber(index=0, width=640, height=480, fps=30)
        grabber.start_capture(device_idx=0, width=1280, height=720, fps=60)
        
        # Give thread a brief moment to initialize
        time.sleep(0.1)
        
        w, h, fps = grabber.get_diagnostics()
        self.assertEqual(w, 1280)
        self.assertEqual(h, 720)
        
        grabber.set_property(cv2.CAP_PROP_FRAME_WIDTH, 640)
        grabber.set_property(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Give thread a brief moment to process the queue
        time.sleep(0.1)
        
        w, h, fps = grabber.get_diagnostics()
        self.assertEqual(w, 640)
        self.assertEqual(h, 480)
        
        grabber.stop_capture()
        self.assertFalse(grabber.isRunning())

if __name__ == '__main__':
    unittest.main()

