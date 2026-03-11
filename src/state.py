import threading
import time
import copy
from src.config import STREAM_PORT_RIGHT, STREAM_PORT_LEFT, CAMERAS

stop_event = threading.Event()
frame_lock = threading.Lock()          # protects frame-related globals
status_lock = threading.Lock()         # protects `systemStatus`

latest_frames = {port: None for port in CAMERAS}
frame_timestamps = {port: 0.0 for port in CAMERAS}
fps_data = {
    port: {"frames": 0, "last_time": time.time(), "fps": 0.0}
    for port in CAMERAS
}
connected_cameras = set()

# consolidated, thread-safe data structure describing system state
systemStatus = {
    "controlMode": 0,  # 0: Rover Control, 1: Calibration, 2: Depth
    "miscellaneousData": {
        "broadcasting": False,
        "calibrating": False,
        "rightCameraConnected": False,
        "leftCameraConnected": False,
        "rightCameraFPS": 0,
        "leftCameraFPS": 0,
        "calibrationImageCounter": 0,
        "stereoBaselineIndicator": 0.0,
        "distanceFeedback": "ok",  # "too far", "too close", "ok"
    },
    "encodersData": {
        "frontRightMotorEncoderReading": 0,
        "frontLeftMotorEncoderReading": 0,
        "rearRightMotorEncoderReading": 0,
        "rearLeftMotorEncoderReading": 0,
    },
    "accelerometerData": {
        "accelerometerXReading": 0,
        "accelerometerYReading": 0,
        "accelerometerZReading": 0,
    },
    "gyroscopeData": {
        "gyroscopeXReading": 0,
        "gyroscopeYReading": 0,
        "gyroscopeZReading": 0,
    },
}


# --- helpers for thread-safe updates -------------------------------------------------------

def get_status_copy():
    """Return a deep copy of :data:`systemStatus`.

    The caller may freely mutate the returned dictionary.
    """
    with status_lock:
        return copy.deepcopy(systemStatus)


def set_control_mode(mode: int):
    """Set the control mode (0: Rover, 1: Calibration, 2: Depth)."""
    with status_lock:
        systemStatus["controlMode"] = mode


def set_miscellaneous_flag(name: str, value):
    if name not in systemStatus["miscellaneousData"]:
        raise KeyError(f"Unknown miscellaneousData field: {name}")
    with status_lock:
        systemStatus["miscellaneousData"][name] = value


def set_encoder_reading(name: str, value):
    if name not in systemStatus["encodersData"]:
        raise KeyError(f"Unknown encoder field: {name}")
    with status_lock:
        systemStatus["encodersData"][name] = value


def set_accelerometer_reading(axis: str, value):
    key = f"accelerometer{axis.capitalize()}Reading"
    if key not in systemStatus["accelerometerData"]:
        raise KeyError(f"Unknown accelerometer axis: {axis}")
    with status_lock:
        systemStatus["accelerometerData"][key] = value


def set_gyroscope_reading(axis: str, value):
    key = f"gyroscope{axis.capitalize()}Reading"
    if key not in systemStatus["gyroscopeData"]:
        raise KeyError(f"Unknown gyroscope axis: {axis}")
    with status_lock:
        systemStatus["gyroscopeData"][key] = value


def refresh_connection_flags():
    """Synchronise the connection booleans from :data:`connected_cameras`."""
    right, left = get_connection_flags()
    with status_lock:
        systemStatus["miscellaneousData"]["rightCameraConnected"] = right
        systemStatus["miscellaneousData"]["leftCameraConnected"] = left


def refresh_fps(right: float, left: float):
    """Store the most recent fps values under ``miscellaneousData``."""
    with status_lock:
        systemStatus["miscellaneousData"]["rightCameraFPS"] = right
        systemStatus["miscellaneousData"]["leftCameraFPS"] = left


def get_connection_flags():
    """Return a pair of booleans mirroring the old helper."""
    return (
        STREAM_PORT_RIGHT in connected_cameras,
        STREAM_PORT_LEFT in connected_cameras,
    )