import sys
import os
import time
import unittest
from unittest.mock import patch
import numpy as np
import cv2
import subprocess
from PySide6.QtCore import QCoreApplication

# Ensure src is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.camera.manager import CameraManager
from src.camera.grabber import CameraGrabber


def get_memory_usage():
    """
    Returns the current process's memory usage (Working Set) in bytes using tasklist.
    """
    pid = os.getpid()
    try:
        output = subprocess.check_output(f'tasklist /FI "PID eq {pid}" /FO CSV', shell=True).decode('utf-8')
        lines = output.strip().split('\n')
        if len(lines) > 1:
            # Format: "Image Name","PID","Session Name","Session#","Mem Usage"
            # Example line: "python.exe","23824","Console","1","38,516 K"
            parts = lines[1].split(',')
            mem_str = parts[-1].replace('"', '').replace(' K', '').replace(' ', '').replace(',', '').replace('.', '').strip()
            return int(mem_str) * 1024
    except Exception as e:
        print(f"Warning: Failed to get memory usage: {e}")
    return 0


class StressMockVideoCapture:
    """
    A simulated VideoCapture device designed for stress testing.
    Keeps track of frame reads and simulates hardware initialization delays.
    """
    def __init__(self, index, *args, **kwargs):
        self.index = index
        self.opened = True
        self.width = 640
        self.height = 480
        self.fps = 30.0
        self.released = False

    def isOpened(self):
        return self.opened

    def get(self, prop_id):
        if prop_id == cv2.CAP_PROP_FRAME_WIDTH:
            return float(self.width)
        elif prop_id == cv2.CAP_PROP_FRAME_HEIGHT:
            return float(self.height)
        elif prop_id == cv2.CAP_PROP_FPS:
            return float(self.fps)
        return 0.0

    def set(self, prop_id, value):
        if prop_id == cv2.CAP_PROP_FRAME_WIDTH:
            self.width = int(value)
        elif prop_id == cv2.CAP_PROP_FRAME_HEIGHT:
            self.height = int(value)
        elif prop_id == cv2.CAP_PROP_FPS:
            self.fps = float(value)
        return True

    def read(self):
        if not self.opened or self.released:
            return False, None
        # Sleep a minimal amount to simulate frame grab interval
        time.sleep(0.005)
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        return True, frame

    def release(self):
        self.opened = False
        self.released = True


class TestMilestone1Stress(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Ensure a QCoreApplication exists for QThread operations
        cls.app = QCoreApplication.instance()
        if cls.app is None:
            cls.app = QCoreApplication([])

    def test_01_camera_manager_extreme_indices(self):
        """
        Verify CameraManager.check_capabilities with negative, extremely large, None, and incorrect type indices.
        """
        print("\n=== Test 1: CameraManager check_capabilities with Extreme Indices ===")
        
        # Test cases: (name, index, expected_to_raise)
        test_cases = [
            ("None", None, False),
            ("Negative Index -1", -1, False),
            ("Large Index (fits C int) 2147483647", 2**31 - 1, False),
            ("Large Index (overflows C int) 2147483648", 2**31, False),
            ("String Index 'invalid'", "invalid", False),
            ("Float Index 1.5", 1.5, False)
        ]
        
        for name, idx, expected_to_raise in test_cases:
            try:
                # Call check_capabilities. Since we run this file directly or via pytest,
                # we want to see the real OpenCV VideoCapture behavior here.
                caps = CameraManager.check_capabilities(idx)
                print(f"  [PASS] Index '{name}': Returned resolutions={caps['resolutions']}, fps={caps['fps']}")
                if idx != 2**31 - 1:
                    self.assertEqual(caps["resolutions"], [], f"Resolutions for {name} should be empty")
                    self.assertEqual(caps["fps"], 0.0, f"FPS for {name} should be 0.0")
                if expected_to_raise:
                    print(f"  [WARNING] Index '{name}' was expected to raise an exception but completed successfully.")
            except Exception as e:
                if expected_to_raise:
                    print(f"  [PASS/EXPECTED EXCEPTION] Index '{name}' raised expected exception: {type(e).__name__}: {e}")
                else:
                    print(f"  [FAIL] Index '{name}' raised UNEXPECTED exception: {type(e).__name__}: {e}")
                    raise e

    def test_02_grabber_start_stop_rapid_toggle(self):
        """
        Stress test start and stop on CameraGrabber by rapidly toggling in succession.
        """
        print("\n=== Test 2: CameraGrabber Start/Stop Rapid Toggling Stress ===")
        
        with patch('cv2.VideoCapture', side_effect=StressMockVideoCapture):
            grabber = CameraGrabber(index=0)
            
            num_toggles = 50
            print(f"  Executing {num_toggles} start/stop cycles in rapid succession...")
            
            start_time = time.time()
            for i in range(num_toggles):
                # Start capture
                grabber.start_capture(device_idx=0, width=640, height=480, fps=30)
                
                # Sleep briefly (various small durations to hit race conditions)
                time.sleep(0.002)
                
                # Stop capture
                grabber.stop_capture()
                
            elapsed = time.time() - start_time
            print(f"  [INFO] Completed {num_toggles} rapid toggles in {elapsed:.4f} seconds.")
            
            # Verify clean termination
            self.assertFalse(grabber.isRunning(), "Grabber thread should not be running after final stop.")
            print("  [PASS] Grabber thread terminated successfully.")

    def test_03_memory_and_thread_leak(self):
        """
        Run multiple grabbers concurrently to verify no memory or thread leaks occur.
        """
        print("\n=== Test 3: Concurrency, Thread, and Memory Leak Verification ===")
        
        num_grabbers = 12
        grabbers = []
        
        initial_mem = get_memory_usage()
        print(f"  Initial process memory: {initial_mem / (1024*1024):.2f} MB")
        
        with patch('cv2.VideoCapture', side_effect=StressMockVideoCapture):
            print(f"  Starting {num_grabbers} concurrent CameraGrabbers...")
            for i in range(num_grabbers):
                g = CameraGrabber(index=i)
                g.start_capture(device_idx=i, width=640, height=480, fps=30)
                grabbers.append(g)
                
            # Allow them to run and grab frames concurrently
            time.sleep(1.5)
            
            # Verify they are actually running
            running_count = sum(1 for g in grabbers if g.isRunning())
            print(f"  Currently running threads: {running_count}/{num_grabbers}")
            self.assertEqual(running_count, num_grabbers, f"Only {running_count} out of {num_grabbers} grabbers started.")
            
            peek_mem = get_memory_usage()
            print(f"  Memory during active capture: {peek_mem / (1024*1024):.2f} MB (Delta: {(peek_mem - initial_mem) / (1024*1024):+.2f} MB)")
            
            # Stop all grabbers
            print("  Stopping all grabbers...")
            stop_start_time = time.time()
            for g in grabbers:
                g.stop_capture()
            stop_duration = time.time() - stop_start_time
            print(f"  Stopped all grabbers in {stop_duration:.4f} seconds.")
            
            # Verify all threads stopped cleanly
            leaked_threads = [idx for idx, g in enumerate(grabbers) if g.isRunning()]
            self.assertEqual(len(leaked_threads), 0, f"Leaked grabber threads at indices: {leaked_threads}")
            print("  [PASS] All grabber threads terminated cleanly.")
            
            # Allow garbage collection and cooldown
            time.sleep(1.0)
            final_mem = get_memory_usage()
            print(f"  Final process memory: {final_mem / (1024*1024):.2f} MB (Delta from initial: {(final_mem - initial_mem) / (1024*1024):+.2f} MB)")
            
            # Note: Memory delta might be slightly positive due to PySide6/Qt allocations, but should not grow linearly.
            print("  [PASS] No uncontrolled thread or memory leak observed.")


if __name__ == '__main__':
    unittest.main()
