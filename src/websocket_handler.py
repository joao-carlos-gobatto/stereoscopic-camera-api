import asyncio
import json
import websockets
import cv2
import numpy as np
from src.config import FRAME_WIDTH, FRAME_HEIGHT, STREAM_PORT_LEFT, STREAM_PORT_RIGHT, WEBSOCKET_PORT, FRAME_SEND_INTERVAL
from src.state import frame_lock, latest_frames, fps_data, stop_event, connected_cameras
from src.utils import save_image_pair, reset_calibration_folders
from src.actions import get_handler


async def send_frames(websocket):
    while not stop_event.is_set():
        with frame_lock:
            left = latest_frames[STREAM_PORT_LEFT]
            right = latest_frames[STREAM_PORT_RIGHT]
            fps_left = fps_data[STREAM_PORT_LEFT]["fps"]
            fps_right = fps_data[STREAM_PORT_RIGHT]["fps"]
        if left is None or right is None:
            placeholder = np.zeros((FRAME_HEIGHT, FRAME_WIDTH * 2, 3), dtype=np.uint8)
            msg = f"Waiting cameras ({len(connected_cameras)}/2)"
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
                "LEFT",
                (10, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 100),
                2
            )
            cv2.putText(
                canvas,
                "RIGHT",
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
        try:
            await websocket.send(buffer.tobytes())
        except websockets.exceptions.ConnectionClosed:
            break
        await asyncio.sleep(FRAME_SEND_INTERVAL)

async def receive_commands(websocket):
    while not stop_event.is_set():
        try:
            message = await websocket.recv()
            if not isinstance(message, str):
                print("Received non-text message (binary?) → ignoring")
                continue

            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                print(f"Invalid JSON received: {message}")
                # Optional: await websocket.send(json.dumps({"error": "invalid json"}))
                continue

            action = data.get("action")
            if not action:
                print("Message missing 'action' field")
                continue

            handler = get_handler(action)
            if handler:
                try:
                    await handler(data)  # pass the whole payload
                    # Optional success response
                    # await websocket.send(json.dumps({"status": "ok", "action": action}))
                except Exception as e:
                    print(f"Error in action '{action}': {e}")
                    # Optional: await websocket.send(json.dumps({"error": str(e)}))
            else:
                print(f"Unknown action: {action}")
                # Optional: await websocket.send(json.dumps({"error": f"unknown action: {action}"}))

        except websockets.exceptions.ConnectionClosed:
            break
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Unexpected error in receive loop: {e}")
            break

async def handler(websocket):
    print("Client connected through websocket")
    send_task = asyncio.create_task(send_frames(websocket))
    receive_task = asyncio.create_task(receive_commands(websocket))
    try:
        await asyncio.gather(send_task, receive_task)
    except asyncio.CancelledError:
        pass
    finally:
        send_task.cancel()
        receive_task.cancel()
        print("Client disconnected")

async def server_main():
    async with websockets.serve(handler, "0.0.0.0", WEBSOCKET_PORT):
        print(f"Websocket server started through port: {WEBSOCKET_PORT}")
        await asyncio.Future()  # Run forever until cancelled

def start_websocket_server():
    asyncio.run(server_main())