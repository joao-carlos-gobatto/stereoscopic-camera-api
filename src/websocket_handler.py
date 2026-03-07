import asyncio
import json
import websockets
import cv2
import numpy as np
from src.config import (
    FRAME_WIDTH,
    FRAME_HEIGHT,
    STREAM_PORT_LEFT,
    STREAM_PORT_RIGHT,
    VIDEO_WEBSOCKET_PORT,
    STATUS_WEBSOCKET_PORT,
    FRAME_SEND_INTERVAL,
    STATUS_SEND_INTERVAL,
)
import src.state
from src.actions import get_handler


async def send_frames(websocket):
    """Send individual frames for left and right cameras.
    Each message is prefixed with a single ASCII byte:
      'L' for left, 'R' for right.

    Clients can inspect the first byte to decide which <img> to update.
    """
    while not src.state.stop_event.is_set():
        with src.state.frame_lock:
            left = src.state.latest_frames[STREAM_PORT_LEFT]
            right = src.state.latest_frames[STREAM_PORT_RIGHT]
            fps_left = src.state.fps_data[STREAM_PORT_LEFT]["fps"]
            fps_right = src.state.fps_data[STREAM_PORT_RIGHT]["fps"]
        # build a helper to encode a single frame
        def encode(frame):
            if frame is None:
                placeholder = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)
                _, buf = cv2.imencode('.jpg', placeholder)
            else:
                canvas = frame.copy()
                _, buf = cv2.imencode('.jpg', canvas)
            return buf.tobytes()

        try:
            left_bytes = encode(left)
            await websocket.send(b"L" + left_bytes)
            right_bytes = encode(right)
            await websocket.send(b"R" + right_bytes)
        except websockets.exceptions.ConnectionClosed:
            break
        await asyncio.sleep(FRAME_SEND_INTERVAL)


async def send_status(websocket):
    """Periodically send current system status as JSON."""
    while not src.state.stop_event.is_set():
        with src.state.frame_lock:
            fps_left = src.state.fps_data[STREAM_PORT_LEFT]["fps"]
            fps_right = src.state.fps_data[STREAM_PORT_RIGHT]["fps"]
        # build status dictionary
        status = {
            "broadcasting": src.state.broadcasting,
            "calibrating": src.state.calibrating,
            "rightCameraFPS": fps_right,
            "leftCameraFPS": fps_left,
        }
        # merge connection flags computed from state
        status.update(src.state.get_connection_flags())
        try:
            await websocket.send(json.dumps(status))
        except websockets.exceptions.ConnectionClosed:
            break
        await asyncio.sleep(STATUS_SEND_INTERVAL)


async def receive_commands(websocket):
    while not src.state.stop_event.is_set():
        try:
            message = await websocket.recv()
            if not isinstance(message, str):
                print("Received non-text message (binary?) → ignoring")
                continue

            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                print(f"Invalid JSON received: {message}")
                continue

            action = data.get("action")
            if not action:
                print("Message missing 'action' field")
                continue

            handler = get_handler(action)
            if handler:
                try:
                    await handler(data)  # pass the whole payload
                except Exception as e:
                    print(f"Error in action '{action}': {e}")
            else:
                print(f"Unknown action: {action}")

        except websockets.exceptions.ConnectionClosed:
            break
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Unexpected error in receive loop: {e}")
            break


async def video_handler(websocket):
    # simple stream, every cycle sends left then right frame with prefix
    print("Client connected to video stream (split frames)")
    try:
        await send_frames(websocket)
    finally:
        print("Video client disconnected")


async def status_handler(websocket):
    # 'path' argument dropped for compatibility with current websockets library
    print("Client connected to system status")
    send_task = asyncio.create_task(send_status(websocket))
    receive_task = asyncio.create_task(receive_commands(websocket))
    try:
        await asyncio.gather(send_task, receive_task)
    except asyncio.CancelledError:
        pass
    finally:
        send_task.cancel()
        receive_task.cancel()
        print("Status client disconnected")


async def server_main():
    # run both video and status servers concurrently
    async with websockets.serve(video_handler, "0.0.0.0", VIDEO_WEBSOCKET_PORT), \
               websockets.serve(status_handler, "0.0.0.0", STATUS_WEBSOCKET_PORT):
        print(f"Websocket video server started on port: {VIDEO_WEBSOCKET_PORT}")
        print(f"Websocket status server started on port: {STATUS_WEBSOCKET_PORT}")
        await asyncio.Future()  # Run forever until cancelled

def start_websocket_server():
    asyncio.run(server_main())