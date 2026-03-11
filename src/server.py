import asyncio
import websockets
from src.config import (
    VIDEO_WEBSOCKET_PORT,
    CONTROL_WEBSOCKET_PORT,
)
from src.webSockets.control_websocket import status_handler, connect_rover
from src.webSockets.video_websocket import video_handler


async def server_main():
    # run both video and status servers concurrently
    rover_task = asyncio.create_task(connect_rover())
    async with websockets.serve(video_handler, "0.0.0.0", VIDEO_WEBSOCKET_PORT), \
               websockets.serve(status_handler, "0.0.0.0", CONTROL_WEBSOCKET_PORT):
        print(f"Websocket video server started on port: {VIDEO_WEBSOCKET_PORT}")
        print(f"Websocket status server started on port: {CONTROL_WEBSOCKET_PORT}")
        try:
            await asyncio.Future()  # Run forever until cancelled
        except asyncio.CancelledError:
            pass
        finally:
            rover_task.cancel()
            await rover_task

def start_websocket_server():
    asyncio.run(server_main())