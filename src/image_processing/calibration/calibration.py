import cv2
import numpy as np
import time
import src.state as state
import src.image_processing.calibration.calibration_utils as calibration_utils
from src.config import (
    CHESSBOARD_SIZE,
    MIN_AREA_RATIO,
    AUTO_CAPTURE_DELAY,
    POSE_DUPLICATE_THRESHOLD,
    MIN_BASELINE,
    MAX_BASELINE,
    MAX_TILT_DEG,
    TARGET_CAPTURE_COUNT,
    FRAME_WIDTH,
    FRAME_HEIGHT,
    STREAM_PORT_LEFT,
    STREAM_PORT_RIGHT,
    LEFT_CALIBRATION_FOLDER,
    RIGHT_CALIBRATION_FOLDER
)

coverage_map = np.zeros((FRAME_HEIGHT,FRAME_WIDTH),dtype=np.float32)
pose_history=[]
pose_vectors=[]

last_capture_time=0

objpoints=[]
imgpoints_l=[]
imgpoints_r=[]

state.reproject_error_left=None
state.reproject_error_right=None

objp = np.zeros((CHESSBOARD_SIZE[0]*CHESSBOARD_SIZE[1],3), np.float32)
objp[:,:2] = np.mgrid[0:CHESSBOARD_SIZE[0],0:CHESSBOARD_SIZE[1]].T.reshape(-1,2)

def reset_stereo_calibration_data():
    coverage_map = np.zeros((FRAME_HEIGHT,FRAME_WIDTH),dtype=np.float32)
    pose_history=[]
    pose_vectors=[]

    last_capture_time=0

    objpoints=[]
    imgpoints_l=[]
    imgpoints_r=[]

    state.reproject_error_left=None
    state.reproject_error_right=None

    objp = np.zeros((CHESSBOARD_SIZE[0]*CHESSBOARD_SIZE[1],3), np.float32)
    objp[:,:2] = np.mgrid[0:CHESSBOARD_SIZE[0],0:CHESSBOARD_SIZE[1]].T.reshape(-1,2)


def process_stereo_calibration_frame():

    with state.frame_lock:

        left=state.latest_frames[STREAM_PORT_LEFT]
        right=state.latest_frames[STREAM_PORT_RIGHT]

        if left is None or right is None:
            canvas=np.zeros((FRAME_HEIGHT,FRAME_WIDTH*2,3),dtype=np.uint8)
            cv2.putText(canvas,"Aguardando cameras",
                        (300,240),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,(0,200,255),2)

        else:
            corners_l,box_l,status_l=calibration_utils.analyze_chessboard(left)
            corners_r,box_r,status_r=calibration_utils.analyze_chessboard(right)

            frame_left=left.copy()
            frame_right=right.copy()

            good_pose=False

            if corners_l is not None and corners_r is not None:

                center_l=np.mean(corners_l,axis=0)
                center_r=np.mean(corners_r,axis=0)

                baseline=abs(center_l[0][0]-center_r[0][0])

                tilt=calibration_utils.compute_tilt(corners_l)

                sig=calibration_utils.pose_signature(corners_l)

                duplicate=calibration_utils.is_duplicate(sig)

                if (
                    status_l=="ok"
                    and status_r=="ok"
                    and MIN_BASELINE<baseline<MAX_BASELINE
                    and tilt<MAX_TILT_DEG
                    and not duplicate
                ):
                    good_pose=True

            frame_left=calibration_utils.draw_overlay(frame_left,corners_l,good_pose)
            frame_right=calibration_utils.draw_overlay(frame_right,corners_r,good_pose)

            if good_pose and not state.dataset_complete:

                if time.time()-last_capture_time>AUTO_CAPTURE_DELAY:

                    name_l=f"{LEFT_CALIBRATION_FOLDER}/{state.capture_count}.jpg"
                    name_r=f"{RIGHT_CALIBRATION_FOLDER}/{state.capture_count}.jpg"

                    cv2.imwrite(name_l,left)
                    cv2.imwrite(name_r,right)

                    objpoints.append(objp)

                    imgpoints_l.append(corners_l)
                    imgpoints_r.append(corners_r)

                    pose_history.append(sig)

                    state.capture_count+=1
                    last_capture_time=time.time()

                    state.reproject_error_left, state.reproject_error_right =calibration_utils.run_calibration_simulation(
                        objpoints,
                        imgpoints_l,
                        imgpoints_r,
                        FRAME_WIDTH,
                        FRAME_HEIGHT
                    )

                    if state.capture_count>=TARGET_CAPTURE_COUNT:
                        state.dataset_complete=True

            if corners_l is not None:
                cv2.drawChessboardCorners(frame_left,CHESSBOARD_SIZE,corners_l,True)

            if corners_r is not None:
                cv2.drawChessboardCorners(frame_right,CHESSBOARD_SIZE,corners_r,True)

            if state.reproject_error_left is not None:
                state.quality="RUIM"
                if state.reproject_error_left<0.3 and state.reproject_error_right<0.3:
                    state.quality="EXCELENTE"
                elif state.reproject_error_left<0.5:
                    state.quality="MUITO BOA"
                elif state.reproject_error_left<0.8:
                    state.quality="BOA"

            if state.dataset_complete:
                print("DATASET DE CALIBRAÇÃO COMPLETO")
                reset_stereo_calibration_data()

    return frame_left, frame_right