# Hardware

`AndroidMotionSensorSource` uses accelerometer windows and optional gyroscope input. `CameraPpgCaptureSource` uses CameraX RGBA frames, rear camera, and torch for a bounded capture session. Capability detection is explicit; absent sensors are displayed as unavailable. ECG is not provided by phone camera PPG and requires an external ECG sensor integration.

