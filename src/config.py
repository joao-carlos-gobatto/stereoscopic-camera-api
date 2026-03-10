# Settings
BROADCAST_MSG = b"ESP_DISCOVERY"
BROADCAST_ADDR = "192.168.15.255"
BROADCAST_PORT = 12345
STREAM_PORT_RIGHT = 8080
STREAM_PORT_LEFT = 8081
CAMERAS = {
    STREAM_PORT_RIGHT: {"name": "Right Camera", "side": "right"},
    STREAM_PORT_LEFT: {"name": "Left Camera", "side": "left"}
}
BROADCAST_INTERVAL = 2.0
CAMERA_TIMEOUT = 12.0

# VGA
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
DISPLAY_SIZE = (FRAME_WIDTH * 2, FRAME_HEIGHT)
LEFT_CALIBRATION_FOLDER = "images/stereoCalibrationLeft"
RIGHT_CALIBRATION_FOLDER = "images/stereoCalibrationRight"

# Websocket ports for different services
VIDEO_WEBSOCKET_PORT = 8765  # binary frames stream
CONTROL_WEBSOCKET_PORT = 8766  # JSON system status and command channel

ROVER_WEBSOCKET_URL = "ws://localhost:8767"  # URL for rover control websocket

FRAME_SEND_INTERVAL = 0.033  # ~30 FPS
STATUS_SEND_INTERVAL = 0.1   # how often to push system status (seconds)