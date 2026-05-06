#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import threading
import warnings
import time
from src.config import CAMERAS
from src.state import stop_event
from src.utils import stereo_calibration_setup
from src.broadcast import send_broadcast
from src.receiver import stream_receiver
from src.watchdog import watchdog
from src.server import start_websocket_server

def main():
    warnings.filterwarnings("ignore", category=RuntimeWarning, module="cv2")
    stereo_calibration_setup()
    threads = []
    # Broadcast message for cameras to connect
    t = threading.Thread(target=send_broadcast, daemon=True)
    t.start()
    threads.append(t)
    # Receivers
    for port, info in CAMERAS.items():
        t = threading.Thread(
            target=stream_receiver,
            args=(port, info["name"], info["side"]),
            daemon=True
        )
        t.start()
        threads.append(t)
    # Watchdog
    t = threading.Thread(target=watchdog, daemon=True)
    t.start()
    threads.append(t)
    # Websocket server
    t = threading.Thread(target=start_websocket_server, daemon=True)
    t.start()
    threads.append(t)
    print("Server running.")
    print("\n\nTo stop the server, press Ctrl+C")
    try:
        # Just wait forever until someone sets stop_event (via web or Ctrl+C)
        while not stop_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nInterruption via Ctrl+C")
    
    stop_event.set()
    
    # Cleanup
    for t in threads:
        t.join(timeout=2)
    print("Server finished")

if __name__ == "__main__":
    main()