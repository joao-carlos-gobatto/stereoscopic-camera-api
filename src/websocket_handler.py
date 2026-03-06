import asyncio
import websockets
import cv2
import numpy as np
from src.config import FRAME_WIDTH, FRAME_HEIGHT, STREAM_PORT_LEFT, STREAM_PORT_RIGHT, WEBSOCKET_PORT, FRAME_SEND_INTERVAL
from src.state import frame_lock, latest_frames, fps_data, stop_event, connected_cameras

async def handler(websocket):
    print("Client connected through websocket")
    try:
        while not stop_event.is_set():
            with frame_lock:
                left = latest_frames[STREAM_PORT_LEFT]
                right = latest_frames[STREAM_PORT_RIGHT]
                fps_left = fps_data[STREAM_PORT_LEFT]["fps"]
                fps_right = fps_data[STREAM_PORT_RIGHT]["fps"]
            if left is None or right is None:
                placeholder = np.zeros((FRAME_HEIGHT, FRAME_WIDTH * 2, 3), dtype=np.uint8)
                msg = f"Waiting for cameras ({len(connected_cameras)}/2)"
                cv2.putText(
                    placeholder,
                    msg,
                    (200, FRAME_HEIGHT // 2),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 180, 255),
                    2
                )
                _, buffer = cv2.imencode('.jpg', placeholder)
            else:
                canvas = np.hstack([left, right])
                cv2.line(
                    canvas,
                    (FRAME_WIDTH, 0),
                    (FRAME_WIDTH, FRAME_HEIGHT),
                    (200, 200, 200),
                    2
                )
                cv2.putText(
                    canvas,
                    "Left",
                    (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 100),
                    2
                )
                cv2.putText(
                    canvas,
                    "Right",
                    (FRAME_WIDTH + 10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 100),
                    2
                )
                cv2.putText(
                    canvas,
                    f"FPS: {fps_left:.1f}",
                    (10, FRAME_HEIGHT - 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 255),
                    2
                )
                cv2.putText(
                    canvas,
                    f"FPS: {fps_right:.1f}",
                    (FRAME_WIDTH + 10, FRAME_HEIGHT - 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 255),
                    2
                )
                _, buffer = cv2.imencode('.jpg', canvas)
            await websocket.send(buffer.tobytes())
            await asyncio.sleep(FRAME_SEND_INTERVAL)
    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected")

async def server_main():
    async with websockets.serve(handler, "0.0.0.0", WEBSOCKET_PORT):
        print(f"Websocket server running in port: {WEBSOCKET_PORT}")
        await asyncio.Future()

def start_websocket_server():
    asyncio.run(server_main())