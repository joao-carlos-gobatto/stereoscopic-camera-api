#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
import warnings

from src.state import stop_event
from src.utils import image_folders_setup

from src.sockets.server import (
    start_socket_server,
    stop_socket_server,
)

from src.webSockets.server import (
    start_websocket_server,
    stop_websocket_server,
)


def main():
    warnings.filterwarnings(
        "ignore",
        category=RuntimeWarning,
        module="cv2",
    )

    image_folders_setup()

    start_socket_server()
    start_websocket_server()

    print("Server running.")
    print("\nTo stop the server, press Ctrl+C")

    try:
        while not stop_event.is_set():
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nInterruption via Ctrl+C")

    finally:
        stop_event.set()

        stop_socket_server()
        stop_websocket_server()

        print("Server finished")


if __name__ == "__main__":
    main()
