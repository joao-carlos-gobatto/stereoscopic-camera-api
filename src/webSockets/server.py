import asyncio
import threading

import websockets

from src.config import (
    VIDEO_WEBSOCKET_PORT,
    CONTROL_WEBSOCKET_PORT,
)

from src.state import stop_event
from src.webSockets.control import status_handler
from src.webSockets.video import video_handler


_thread = None


async def server_main():
    """Run websocket servers."""

    async with (
        websockets.serve(
            video_handler,
            "0.0.0.0",
            VIDEO_WEBSOCKET_PORT,
        ),
        websockets.serve(
            status_handler,
            "0.0.0.0",
            CONTROL_WEBSOCKET_PORT,
        ),
    ):
        print(f"Websocket video server started on port {VIDEO_WEBSOCKET_PORT}")

        print(f"Websocket status server started on port {CONTROL_WEBSOCKET_PORT}")

        while not stop_event.is_set():
            await asyncio.sleep(1)


def _run_async_server():
    asyncio.run(server_main())


def start_websocket_server():
    """Start websocket server thread."""

    global _thread

    print("[WEBSOCKET] Starting...")

    _thread = threading.Thread(
        target=_run_async_server,
        daemon=True,
        name="websocket-server",
    )

    _thread.start()

    print("[WEBSOCKET] Running")


def stop_websocket_server(timeout=2):
    """Wait websocket thread to finish."""

    if _thread is None:
        return

    print("[WEBSOCKET] Stopping")

    _thread.join(timeout=timeout)
