import os
import shutil
from datetime import datetime
from src.config import LEFT_CALIBRATION_FOLDER, RIGHT_CALIBRATION_FOLDER

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
            print("Failed to delete", path, e)

def stereo_calibration_setup():
    os.makedirs(LEFT_CALIBRATION_FOLDER, exist_ok=True)
    os.makedirs(RIGHT_CALIBRATION_FOLDER, exist_ok=True)
    delete_folder_contents(LEFT_CALIBRATION_FOLDER)
    delete_folder_contents(RIGHT_CALIBRATION_FOLDER)
    print("Folders for saving calibration images ready")