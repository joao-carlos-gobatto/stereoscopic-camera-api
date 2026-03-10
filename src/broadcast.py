import socket
import time
from src.config import BROADCAST_MSG, BROADCAST_ADDR, BROADCAST_PORT, BROADCAST_INTERVAL
import src.state

def send_broadcast():

    src.state.broadcasting = True
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    print("Broadcast started")
    while not src.state.stop_event.is_set():
        if len(src.state.connected_cameras) < 2:
            try:
                sock.sendto(BROADCAST_MSG, (BROADCAST_ADDR, BROADCAST_PORT))
                print(f"Sending broadcast message ({len(src.state.connected_cameras)}/2 connected)")
            except Exception as e:
                print("Broadcast error:", e)
        else:
            if src.state.broadcasting:
                src.state.broadcasting = False
                print("Stopping broadcast: cameras connected")
        time.sleep(BROADCAST_INTERVAL)
    sock.close()
    src.state.broadcasting = False