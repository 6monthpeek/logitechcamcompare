# E2E Test Infrastructure for Webcam Comparison Desktop Application

This document outlines the testing methodology, mock strategies, test execution instructions, and verification results for the E2E Testing Track.

## 1. Test Methodology
The E2E test suite utilizes **pytest** as the primary test runner and **pytest-qt** (with the `qtbot` fixture) to drive interface interactions and assertions directly against the real application codebase.

The test cases verify application functionality end-to-end:
- **Widget Manipulation**: Simulated user actions on the actual comboboxes (`preset_combo`, `cam_a_dev_combo`, `cam_b_dev_combo`, `cam_a_res_combo`, `cam_b_res_combo`), the target FPS spinboxes (`cam_a_fps_spin`, `cam_b_fps_spin`), and the camera toggle buttons (`cam_a_toggle_btn`, `cam_b_toggle_btn`).
- **Layout Math & Geometry**: Verifying canvas alignments and parenting behavior in Stacked, Side-by-Side, and Picture-in-Picture layouts.
- **Asynchronous Grabber Threads**: Verifying that starting the cameras launches real multithreaded `CameraGrabber` background threads that communicate with the GUI thread.
- **Thread Lifecycle & Teardown**: Ensuring started threads are explicitly stopped and joined at the end of each test to avoid background thread leaks or interpreter teardown deadlocks/segfaults.

---

## 2. Mocking Strategy

### A. OpenCV Capture Mock (`MockVideoCapture`)
To bypass hardware camera dependency, `tests/conftest.py` implements a `MockVideoCapture` class that mirrors the behavior of `cv2.VideoCapture`. 
- Returns synthetic numpy images generated in real-time.
- Embeds stateful textual overlays (Camera Index, Frame Count, Resolution).
- Reacts to `set()` and `get()` calls for width, height, brightness, contrast, and FPS properties.

### B. Early Module-Level Monkeypatching
To ensure `MockVideoCapture` intercepts all camera captures (both during test discovery and execution), monkeypatching of `cv2.VideoCapture` is performed at the **module level** of `tests/conftest.py`. This guarantees it is evaluated before any other application modules (such as `src.camera.grabber` or `src.camera.manager`) are imported, avoiding issues with real hardware camera access.

### C. Fallback Removal
All dynamic import intercepts, fallback stubs (`MainWindowStub`, `CameraCanvasStub`), and `sys.modules` monkeypatching have been removed. The tests import the real widget classes from `src` and run assertions against the actual application.

---

## 3. Test Runner Commands
To run the E2E tests:

```bash
# Activate or target the virtual environment and run the test suite
.venv\Scripts\python.exe -m pytest tests/test_e2e.py -v
```

---

## 4. Verification Results
- **Date Verified**: 2026-06-17
- **Test Discoverability**: 49 test cases found across 4 distinct testing tiers.
- **Execution Log Output**:
  ```text
  tests/test_e2e.py::test_tier1_camera_a_selection PASSED                  [  2%]
  tests/test_e2e.py::test_tier1_camera_b_selection PASSED                  [  4%]
  tests/test_e2e.py::test_tier1_independent_resolution_a PASSED            [  6%]
  tests/test_e2e.py::test_tier1_independent_resolution_b PASSED            [  8%]
  tests/test_e2e.py::test_tier1_independent_fps_a PASSED                   [ 10%]
  tests/test_e2e.py::test_tier1_independent_fps_b PASSED                   [ 12%]
  tests/test_e2e.py::test_tier1_layout_side_by_side PASSED                 [ 14%]
  tests/test_e2e.py::test_tier1_layout_stacked PASSED                      [ 16%]
  tests/test_e2e.py::test_tier1_layout_pip PASSED                          [ 18%]
  tests/test_e2e.py::test_tier1_brightness_control_a XFAIL (Feature no...) [ 20%]
  ...
  ======================= 18 passed, 31 xfailed in 5.79s ========================
  ```
- **Stability**: Explicit teardown is implemented for all tests starting a background thread, ensuring clean test isolation and preventing Qt crashes during test suite tear-down.
