import socket
import cv2
import numpy as np
import time
from src.state import stop_event, frame_lock, latest_frames, frame_timestamps, fps_data, connected_cameras

def stream_receiver(port, camera_name, side):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", port))
    sock.settimeout(1.0)
    print(f"[STREAM {side.upper()}] waiting for port {port}")
    while not stop_event.is_set():
        try:
            data, addr = sock.recvfrom(65535)
            frame = cv2.imdecode(
                np.frombuffer(data, np.uint8),
                cv2.IMREAD_COLOR
            )
            if frame is None:
                continue
            now = time.time()
            with frame_lock:
                latest_frames[port] = frame.copy()
                frame_timestamps[port] = now
                fps_data[port]["frames"] += 1
                dt = now - fps_data[port]["last_time"]
                if dt >= 1.0:
                    fps_data[port]["fps"] = fps_data[port]["frames"] / dt
                    fps_data[port]["frames"] = 0
                    fps_data[port]["last_time"] = now
                if port not in connected_cameras:
                    print(f"{camera_name} connected {addr[0]}")
                    connected_cameras.add(port)
        except socket.timeout:
            continue
        except Exception as e:
            print("Stream Error:", e)
    sock.close()