import asyncio
import json
import websockets
from src.config import (
    ROVER_WEBSOCKET_URL,
    STATUS_SEND_INTERVAL,
    STREAM_PORT_LEFT,
    STREAM_PORT_RIGHT,
)
import src.state
from src.actions import get_handler

rover_ws = None


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

            # Handle mode messages
            if data.get("type") == "mode":
                mode_str = data.get("mode")
                if mode_str == "control":
                    src.state.set_control_mode(0)
                    print("Switched to control mode")
                elif mode_str == "calibration":
                    src.state.set_control_mode(1)
                    print("Switched to calibration mode")
                elif mode_str == "depth":
                    src.state.set_control_mode(2)
                    print("Switched to depth mode")
                else:
                    print(f"Unknown mode: {mode_str}")
                continue

            # Handle command messages (ignored for now)
            if data.get("type") == "command":
                # TODO: implement command handling
                continue

            # Fallback to old action-based messages (for backward compatibility)
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