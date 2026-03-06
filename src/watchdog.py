import time
from src.config import CAMERA_TIMEOUT
from src.state import stop_event, frame_lock, connected_cameras, frame_timestamps, latest_frames

def watchdog():
    while not stop_event.is_set():
        time.sleep(5)
        now = time.time()
        with frame_lock:
            for port in list(connected_cameras):
                if now - frame_timestamps[port] > CAMERA_TIMEOUT:
                    print("Camera disconnected at port", port)
                    connected_cameras.remove(port)
                    latest_frames[port] = None