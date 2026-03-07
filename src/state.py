import threading
import time
from src.config import STREAM_PORT_RIGHT, STREAM_PORT_LEFT, CAMERAS

stop_event = threading.Event()
frame_lock = threading.Lock()
latest_frames = {port: None for port in CAMERAS}
frame_timestamps = {port: 0.0 for port in CAMERAS}
fps_data = {
    port: {"frames": 0, "last_time": time.time(), "fps": 0.0}
    for port in CAMERAS
}
connected_cameras = set()

# additional boolean statuses tracked by the server
broadcasting = False        # True while discovery broadcasts are being sent
calibrating = False         # allow UI to inform that calibration is in progress


def get_connection_flags():
    """Return booleans indicating which cameras are connected."""
    return {
        "rightCameraConnected": STREAM_PORT_RIGHT in connected_cameras,
        "leftCameraConnected": STREAM_PORT_LEFT in connected_cameras,
    }