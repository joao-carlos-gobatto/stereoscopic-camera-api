import os
import socket
import shutil
import cv2
from datetime import datetime
from src.config import (
    STREAM_PORT_LEFT,
    STREAM_PORT_RIGHT,
    LEFT_IMAGE_FOLDER,
    RIGHT_IMAGE_FOLDER,
)
from src.state import frame_lock, latest_frames


def format_timestamp(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y%m%d_%H%M%S_%f")[:-3]


def delete_folder_contents(folder):
    if not os.path.isdir(folder):
        return
    for filename in os.listdir(folder):
        path = os.path.join(folder, filename)
        try:
            if os.path.isfile(path) or os.path.islink(path):
                os.unlink(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
        except Exception as e:
            print("failed to delete", path, e)


def image_folders_setup():
    os.makedirs(LEFT_IMAGE_FOLDER, exist_ok=True)
    os.makedirs(RIGHT_IMAGE_FOLDER, exist_ok=True)
    delete_folder_contents(LEFT_IMAGE_FOLDER)
    delete_folder_contents(RIGHT_IMAGE_FOLDER)
    print("Calibration folders ready")


def save_image_pair(picture_num):
    with frame_lock:
        fl = latest_frames[STREAM_PORT_LEFT]
        fr = latest_frames[STREAM_PORT_RIGHT]
        if fl is not None and fr is not None:
            name_l = f"{LEFT_IMAGE_FOLDER}/{picture_num}.jpg"
            name_r = f"{RIGHT_IMAGE_FOLDER}/{picture_num}.jpg"
            cv2.imwrite(name_l, fl)
            cv2.imwrite(name_r, fr)
            print("Saved", name_l, name_r)
            return True
    return False


def reset_calibration_folders():
    delete_folder_contents(LEFT_IMAGE_FOLDER)
    delete_folder_contents(RIGHT_IMAGE_FOLDER)
    print("Calibration folders cleaned")


def get_broadcast_addr():
    """Get the broadcast address for the local subnet."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        ip_parts = local_ip.split(".")
        ip_parts[3] = "255"
        return ".".join(ip_parts)
    except Exception:
        return "192.168.15.255"  # Fallback
