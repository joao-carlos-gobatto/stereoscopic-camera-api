import socket
import time
from src.config import (
    CAMERAS_BROADCAST_MSG,
    CAMERAS_BROADCAST_PORT,
    BROADCAST_INTERVAL,
    CAMERAS,
)
from src.state import (
    stop_event,
    connected_cameras,
    get_camera_broadcasting,
    set_camera_broadcasting,
)
from src.utils import get_broadcast_addr


def cameras_send_broadcast():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    print(f"Cameras UDP Broadcast started in port: {CAMERAS_BROADCAST_PORT}")

    broadcast_addr = get_broadcast_addr()

    try:
        while not stop_event.is_set():
            connected = len(connected_cameras)
            broadcasting = get_camera_broadcasting()

            should_broadcast = connected < len(CAMERAS)

            if should_broadcast:
                if not broadcasting:
                    set_camera_broadcasting(True)

                try:
                    sock.sendto(
                        CAMERAS_BROADCAST_MSG,
                        (broadcast_addr, CAMERAS_BROADCAST_PORT),
                    )

                    print(
                        f"Sending broadcast message ({connected}/{len(CAMERAS)} connected)"
                    )

                except Exception as e:
                    print("Cameras Broadcast error:", e)

            else:
                if broadcasting:
                    set_camera_broadcasting(False)
                    print("Stopping broadcast: cameras connected")

            time.sleep(BROADCAST_INTERVAL)

    finally:
        sock.close()
        set_camera_broadcasting(False)
