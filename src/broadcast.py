import socket
import time
from src.config import BROADCAST_MSG, BROADCAST_ADDR, BROADCAST_PORT, BROADCAST_INTERVAL
from src.state import stop_event, connected_cameras

def send_broadcast():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    print("Broadcast started")
    while not stop_event.is_set() and len(connected_cameras) < 2:
        try:
            sock.sendto(BROADCAST_MSG, (BROADCAST_ADDR, BROADCAST_PORT))
            print(f"Sending broadcast message ({len(connected_cameras)}/2 connected)")
        except Exception as e:
            print("Broadcast error:", e)
        time.sleep(BROADCAST_INTERVAL)
    sock.close()