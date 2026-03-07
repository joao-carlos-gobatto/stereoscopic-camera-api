import os
import shutil
import cv2
from datetime import datetime
from src.config import LEFT_CALIBRATION_FOLDER, RIGHT_CALIBRATION_FOLDER, STREAM_PORT_LEFT, STREAM_PORT_RIGHT
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

def stereo_calibration_setup():
    os.makedirs(LEFT_CALIBRATION_FOLDER, exist_ok=True)
    os.makedirs(RIGHT_CALIBRATION_FOLDER, exist_ok=True)
    delete_folder_contents(LEFT_CALIBRATION_FOLDER)
    delete_folder_contents(RIGHT_CALIBRATION_FOLDER)
    print("Calibration folders ready")

def save_image_pair(picture_num):
    with frame_lock:
        fl = latest_frames[STREAM_PORT_LEFT]
        fr = latest_frames[STREAM_PORT_RIGHT]
        if fl is not None and fr is not None:
            name_l = f"{LEFT_CALIBRATION_FOLDER}/{picture_num}.jpg"
            name_r = f"{RIGHT_CALIBRATION_FOLDER}/{picture_num}.jpg"
            cv2.imwrite(name_l, fl)
            cv2.imwrite(name_r, fr)
            print("Saved", name_l, name_r)
            return True
    return False

def reset_calibration_folders():
    delete_folder_contents(LEFT_CALIBRATION_FOLDER)
    delete_folder_contents(RIGHT_CALIBRATION_FOLDER)
    print("Calibration folders cleaned")