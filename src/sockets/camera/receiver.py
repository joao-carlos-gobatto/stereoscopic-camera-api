import socket

import cv2
import numpy as np

from src.state import (
    stop_event,
    is_camera_connected,
    set_latest_frame,
    update_fps,
    connect_camera,
)


def stream_receiver(port, camera_name, side):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", port))
    sock.settimeout(1.0)

    print(f"[{side.upper()} CAMERA STREAM] waiting for port {port}")

    try:
        while not stop_event.is_set():
            try:
                data, addr = sock.recvfrom(65535)

                frame = cv2.imdecode(
                    np.frombuffer(data, np.uint8),
                    cv2.IMREAD_COLOR,
                )

                if frame is None:
                    continue

                set_latest_frame(port, frame)

                update_fps(port)

                if not is_camera_connected(port):
                    print(f"{camera_name} connected {addr[0]}")
                    connect_camera(port)

            except socket.timeout:
                continue

            except Exception as e:
                print(f"[{side.upper()} CAMERA STREAM] Error:", e)

    finally:
        sock.close()
