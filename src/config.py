# Settings
BROADCAST_MSG = b"ESP_DISCOVERY"
BROADCAST_PORT = 12345
STREAM_PORT_RIGHT = 8080
STREAM_PORT_LEFT = 8081
CAMERAS = {
    STREAM_PORT_RIGHT: {"name": "Right Camera", "side": "right"},
    STREAM_PORT_LEFT: {"name": "Left Camera", "side": "left"}
}
BROADCAST_INTERVAL = 2.0
CAMERA_TIMEOUT = 12.0

FRAME_WIDTH = 240
FRAME_HEIGHT = 240

# Calibration settings
CHESSBOARD_SIZE = (7,10)
MIN_AREA_RATIO = 0.20
AUTO_CAPTURE_DELAY = 2.0
POSE_DUPLICATE_THRESHOLD = 40
MIN_BASELINE = 30
MAX_BASELINE = 350
MAX_TILT_DEG = 15
TARGET_CAPTURE_COUNT = 20


LEFT_CALIBRATION_FOLDER = "images/calibration/left"
RIGHT_CALIBRATION_FOLDER = "images/calibration/right"
LEFT_SAVED_FOLDER = "images/saved/left"
RIGHT_SAVED_FOLDER = "images/saved/right"

# Websocket ports for different services
VIDEO_WEBSOCKET_PORT = 8765  # binary frames stream
CONTROL_WEBSOCKET_PORT = 8766  # JSON system status and command channel

ROVER_WEBSOCKET_URL = "ws://localhost:8767"  # URL for rover control websocket

FRAME_SEND_INTERVAL = 0.033  # ~30 FPS
STATUS_SEND_INTERVAL = 0.1   # how often to push system status (seconds)