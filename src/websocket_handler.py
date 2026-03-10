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
    CONTROL_WEBSOCKET_PORT,
    ROVER_WEBSOCKET_URL,
    FRAME_SEND_INTERVAL,
    STATUS_SEND_INTERVAL,
)
import src.state
from src.actions import get_handler

rover_ws = None


def process_calibration_frame(frame):
    """Add calibration overlays to the frame."""
    if frame is None:
        return frame
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    ret, corners = cv2.findChessboardCorners(gray, (9, 6), None)
    if ret:
        cv2.drawChessboardCorners(frame, (9, 6), corners, ret)
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

        try:
            left_bytes = encode(left)
            await websocket.send(b"L" + left_bytes)
            right_bytes = encode(right)
            await websocket.send(b"R" + right_bytes)
        except websockets.exceptions.ConnectionClosed:
            break
        await asyncio.sleep(FRAME_SEND_INTERVAL)


async def send_status(websocket):
    """Periodically send current system status as JSON.

    The status dictionary is built from :data:`src.state.systemStatus` so
    that all of the fields requested by the UI are available.  Helper
    functions are used to update FPS and connectivity before each send.
    """
    while not src.state.stop_event.is_set():
        with src.state.frame_lock:
            fps_left = src.state.fps_data[STREAM_PORT_LEFT]["fps"]
            fps_right = src.state.fps_data[STREAM_PORT_RIGHT]["fps"]
        # refresh values that are derived from other globals
        src.state.refresh_fps(fps_right, fps_left)
        src.state.refresh_connection_flags()
        # send a copy so that the lock can be released immediately
        status = src.state.get_status_copy()
        try:
            await websocket.send(json.dumps(status))
        except websockets.exceptions.ConnectionClosed:
            break
        await asyncio.sleep(STATUS_SEND_INTERVAL)


async def connect_rover():
    global rover_ws
    while not src.state.stop_event.is_set():
        if rover_ws is None or rover_ws.closed:
            try:
                rover_ws = await websockets.connect(ROVER_WEBSOCKET_URL)
                print("Connected to rover websocket")
            except Exception as e:
                print(f"Rover connection failed: {e}")
                await asyncio.sleep(5)
        else:
            await asyncio.sleep(1)


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

            # Handle ping messages
            if data.get("type") == "ping":
                try:
                    await websocket.send(json.dumps({"type": "pong"}))
                except Exception as e:
                    print(f"Failed to send pong: {e}")
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

            # If in rover control mode, resend command to rover
            if src.state.get_status_copy()["controlMode"] == 0:
                if rover_ws and not rover_ws.closed:
                    try:
                        await rover_ws.send(message)
                    except Exception as e:
                        print(f"Failed to send to rover: {e}")
                        rover_ws = None

        except websockets.exceptions.ConnectionClosed:
            break
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Unexpected error in receive loop: {e}")
            break


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