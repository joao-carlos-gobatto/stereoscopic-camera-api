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