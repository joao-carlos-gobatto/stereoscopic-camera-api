import time

from src.state import (
    stop_event,
    get_connected_cameras,
    get_frame_timestamp,
    disconnect_camera,
    set_latest_frame,
)
from src.config import CAMERA_TIMEOUT


def watchdog():
    print("Cameras Watchdog started")
    while not stop_event.is_set():
        time.sleep(5)

        now = time.time()

        for port in get_connected_cameras():
            last_frame_time = get_frame_timestamp(port)

            if now - last_frame_time > CAMERA_TIMEOUT:
                print(f"Camera disconnected at port {port}")

                disconnect_camera(port)
                set_latest_frame(port, None)
