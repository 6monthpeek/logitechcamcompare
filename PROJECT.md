# Project: webcam-comparison-app

## Architecture
This is an Electron-based desktop application. 
- **Main Process (`src/main/main.js` or `index.js`)**: Manages the application window, lifecycle, and system integration.
- **Renderer Process (`src/renderer/`)**: Contains the frontend interface.
  - `index.html`: The markup containing the OBS-like canvas, viewport area, and control panel.
  - `styles.css`: Styles for modern OBS-like UI, responsive canvas, and diagnostics.
  - `renderer.js`: Manages video streams, diagnostic counters, and control panel controls.
  - `layout.js`: Layout math, coordinate checking, drag-and-resize handlers, presets.
- **Shared Interfaces / Contracts**:
  - The communication between Main and Renderer is kept to standard Electron IPC if needed (e.g., config save/load, window resizing).
  - Renderer uses standard HTML5 `navigator.mediaDevices` to access cameras.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Core Boilerplate & Dev Environment | Setup Electron main/renderer processes, npm scripts, launch verify | None | IN_PROGRESS (sub_orch_m1: 49833384-91a6-482d-b347-d60973610111) |
| 2 | Interactive Scene Canvas & Layout | Canvas layout engine, drag/resize mechanics, presets (Side-by-Side, Stacked, PiP), unit tests | M1 | PLANNED |
| 3 | Dual Camera Capture Integration | Access mediaDevices, populate dropdowns, implement dual stream capture, constraints config, mock tests | M2 | PLANNED |
| 4 | Diagnostic & Metadata Overlay | Active resolution reader, real-time FPS counter (requestVideoFrameCallback), overlay UI | M3 | PLANNED |
| 5 | Control Panel & Settings UI | Toggle UI panel, adjust camera settings (resolution, frame rate, active state) | M4 | PLANNED |
| 6 | Integration & Verification | E2E suite validation, Challenger coverage hardening, final builds | M5, E2E | PLANNED |

## Interface Contracts
### Renderer Layout Engine ↔ Canvas DOM
- `layout.js` exports:
  - `updatePresets(presetName, containerWidth, containerHeight, videoContainerA, videoContainerB)`: returns bounds/positions.
  - `applyDrag(element, deltaX, deltaY, boundaryWidth, boundaryHeight)`: updates layout bounds.
  - `applyResize(element, deltaWidth, deltaHeight, direction, boundaryWidth, boundaryHeight)`: updates dimensions.

### Video Diagnostics ↔ Overlay
- `diagnostics.js` or renderer helper:
  - `startFPSCounter(videoElement, callback)`: uses requestVideoFrameCallback or requestAnimationFrame to calculate and output current FPS.

## Code Layout
- `package.json` - configuration and dependencies.
- `src/main/main.js` - Electron main entry point.
- `src/renderer/index.html` - UI layout.
- `src/renderer/styles.css` - Styles.
- `src/renderer/renderer.js` - Renderer orchestration.
- `src/renderer/layout.js` - Layout presets and canvas math.
- `tests/layout.test.js` - Unit tests for the layout logic.
- `tests/mock_devices.test.js` - Test script verifying HTML5 constraints and device queries.
- `tests/e2e/` - E2E test suite directory.
