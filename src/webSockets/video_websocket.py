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
    FRAME_SEND_INTERVAL,
    CHESSBOARD_SIZE
)
import src.state

# build a helper to encode a single frame
def encode(frame):
    if frame is None:
        placeholder = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)
        _, buf = cv2.imencode('.jpg', placeholder)
    else:
        canvas = frame.copy()
        # Add overlays based on mode
        mode = src.state.get_status_copy()["controlMode"]
        if mode == 1:  # Calibration mode
            canvas = process_calibration_frame(canvas)
        _, buf = cv2.imencode('.jpg', canvas)
    return buf.tobytes()


def process_calibration_frame(frame):
    """Add calibration overlays to the frame."""
    if frame is None:
        return frame
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    ret, corners = cv2.findChessboardCorners(gray, CHESSBOARD_SIZE, None)
    if ret:
        cv2.drawChessboardCorners(frame, CHESSBOARD_SIZE, corners, ret)
    return frame


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
            
        try:
            left_bytes = encode(left)
            await websocket.send(b"L" + left_bytes)
            right_bytes = encode(right)
            await websocket.send(b"R" + right_bytes)
        except websockets.exceptions.ConnectionClosed:
            break
        await asyncio.sleep(FRAME_SEND_INTERVAL)


async def receive_ping(websocket):
    """Receive and handle ping messages for video websocket."""
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

            # Handle ping messages
            if data.get("type") == "ping":
                try:
                    await websocket.send(json.dumps({"type": "pong"}))
                except Exception as e:
                    print(f"Failed to send pong: {e}")
                continue
            else:
                print(f"Unexpected message on video websocket: {data}")

        except websockets.exceptions.ConnectionClosed:
            break
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Unexpected error in video receive loop: {e}")
            break


async def video_handler(websocket):
    # simple stream, every cycle sends left then right frame with prefix
    print("Client connected to video stream (split frames)")
    send_task = asyncio.create_task(send_frames(websocket))
    receive_task = asyncio.create_task(receive_ping(websocket))
    try:
        await asyncio.gather(send_task, receive_task)
    except asyncio.CancelledError:
        pass
    finally:
        send_task.cancel()
        receive_task.cancel()
        print("Video client disconnected")