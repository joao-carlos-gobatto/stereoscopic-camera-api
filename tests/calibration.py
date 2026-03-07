#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import cv2
import os
import numpy as np
import threading
import time
import warnings
import shutil

# ==============================
# CONFIGURAÇÕES
# ==============================

BROADCAST_MSG = b"ESP_DISCOVERY"
BROADCAST_ADDR = "192.168.15.255"
BROADCAST_PORT = 12345

STREAM_PORT_RIGHT = 8080
STREAM_PORT_LEFT  = 8081

CAMERAS = {
    STREAM_PORT_RIGHT: {"name": "Câmera Direita", "side": "right"},
    STREAM_PORT_LEFT:  {"name": "Câmera Esquerda", "side": "left"}
}

FRAME_WIDTH = 640
FRAME_HEIGHT = 480

DISPLAY_WINDOW = "Stereo Calibration Viewer"
DISPLAY_SIZE = (FRAME_WIDTH*2, FRAME_HEIGHT)

CHESSBOARD_SIZE = (7,10)

MIN_AREA_RATIO = 0.20

AUTO_CAPTURE_DELAY = 2.0
POSE_DUPLICATE_THRESHOLD = 40

MIN_BASELINE = 30
MAX_BASELINE = 350

MAX_TILT_DEG = 15

TARGET_CAPTURE_COUNT = 20

leftCalibrationFolder = "stereoCalibrationLeft"
rightCalibrationFolder = "stereoCalibrationRight"

# ==============================
# VARIÁVEIS
# ==============================

stop_event = threading.Event()
frame_lock = threading.Lock()

latest_frames = {port: None for port in CAMERAS}
frame_timestamps = {port: 0.0 for port in CAMERAS}

connected_cameras=set()

capture_count=0
coverage_map = np.zeros((FRAME_HEIGHT,FRAME_WIDTH),dtype=np.float32)

pose_history=[]
pose_vectors=[]

last_capture_time=0
dataset_complete=False

# calibração simulada
objpoints=[]
imgpoints_l=[]
imgpoints_r=[]

reproj_error_l=None
reproj_error_r=None

# ==============================
# TABULEIRO 3D
# ==============================

objp = np.zeros((CHESSBOARD_SIZE[0]*CHESSBOARD_SIZE[1],3), np.float32)
objp[:,:2] = np.mgrid[0:CHESSBOARD_SIZE[0],0:CHESSBOARD_SIZE[1]].T.reshape(-1,2)

# ==============================
# UTILIDADES
# ==============================

def delete_folder_contents(folder):

    if not os.path.isdir(folder):
        return

    for f in os.listdir(folder):

        p=os.path.join(folder,f)

        try:
            if os.path.isfile(p):
                os.unlink(p)
            else:
                shutil.rmtree(p)
        except:
            pass


def stereo_calibration_setup():

    os.makedirs(leftCalibrationFolder,exist_ok=True)
    os.makedirs(rightCalibrationFolder,exist_ok=True)

    delete_folder_contents(leftCalibrationFolder)
    delete_folder_contents(rightCalibrationFolder)

# ==============================
# POSE
# ==============================

def pose_signature(corners):

    center=np.mean(corners,axis=0)

    vec=corners[-1]-corners[0]

    angle=np.arctan2(vec[0][1],vec[0][0])

    return np.array([center[0][0],center[0][1],angle])


def is_duplicate(sig):

    for p in pose_history:

        if np.linalg.norm(sig-p)<POSE_DUPLICATE_THRESHOLD:
            return True

    return False

# ==============================
# TILT
# ==============================

def compute_tilt(corners):

    pts=corners.reshape(-1,2)

    v1=pts[1]-pts[0]
    v2=pts[CHESSBOARD_SIZE[0]]-pts[0]

    normal=np.cross(np.append(v1,0),np.append(v2,0))

    normal=normal/np.linalg.norm(normal)

    tilt=np.degrees(np.arccos(normal[2]))

    return abs(tilt)

# ==============================
# CALIBRATION SIMULATOR
# ==============================

def compute_reprojection_error(objpoints,imgpoints,rvecs,tvecs,mtx,dist):

    total_error=0

    for i in range(len(objpoints)):

        imgpoints2,_=cv2.projectPoints(
            objpoints[i],
            rvecs[i],
            tvecs[i],
            mtx,
            dist
        )

        error=cv2.norm(imgpoints[i],imgpoints2,cv2.NORM_L2)/len(imgpoints2)

        total_error+=error

    return total_error/len(objpoints)


def run_calibration_simulation():

    global reproj_error_l,reproj_error_r

    if len(objpoints)<10:
        return

    ret_l,mtx_l,dist_l,rvecs_l,tvecs_l=cv2.calibrateCamera(
        objpoints,
        imgpoints_l,
        (FRAME_WIDTH,FRAME_HEIGHT),
        None,
        None
    )

    ret_r,mtx_r,dist_r,rvecs_r,tvecs_r=cv2.calibrateCamera(
        objpoints,
        imgpoints_r,
        (FRAME_WIDTH,FRAME_HEIGHT),
        None,
        None
    )

    reproj_error_l=compute_reprojection_error(
        objpoints,imgpoints_l,rvecs_l,tvecs_l,mtx_l,dist_l
    )

    reproj_error_r=compute_reprojection_error(
        objpoints,imgpoints_r,rvecs_r,tvecs_r,mtx_r,dist_r
    )

# ==============================
# CHESSBOARD
# ==============================

def analyze_chessboard(frame):

    gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)

    found,corners=cv2.findChessboardCorners(
        gray,
        CHESSBOARD_SIZE,
        cv2.CALIB_CB_ADAPTIVE_THRESH+
        cv2.CALIB_CB_FAST_CHECK+
        cv2.CALIB_CB_NORMALIZE_IMAGE
    )

    if not found:
        return None,None,"nao detectado"

    corners=cv2.cornerSubPix(
        gray,
        corners,
        (11,11),
        (-1,-1),
        (cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER,30,0.001)
    )

    pts=corners.reshape(-1,2)

    xmin=np.min(pts[:,0])
    xmax=np.max(pts[:,0])
    ymin=np.min(pts[:,1])
    ymax=np.max(pts[:,1])

    area=(xmax-xmin)*(ymax-ymin)

    ratio=area/(FRAME_WIDTH*FRAME_HEIGHT)

    if ratio<MIN_AREA_RATIO:
        status="longe"
    elif ratio>0.7:
        status="perto"
    else:
        status="ok"

    return corners,(xmin,ymin,xmax,ymax),status

# ==============================
# OVERLAY
# ==============================

def draw_overlay(frame,corners,good):

    if corners is None:
        return frame

    pts=corners.reshape(-1,2).astype(int)

    hull=cv2.convexHull(pts)

    overlay=frame.copy()

    color=(255,0,0) if good else (0,255,0)

    cv2.fillConvexPoly(overlay,hull,color)

    return cv2.addWeighted(overlay,0.25,frame,0.75,0)

# ==============================
# DISPLAY
# ==============================

def display_loop():

    global capture_count,last_capture_time,dataset_complete

    cv2.namedWindow(DISPLAY_WINDOW,cv2.WINDOW_NORMAL)
    cv2.resizeWindow(DISPLAY_WINDOW,*DISPLAY_SIZE)

    while not stop_event.is_set():

        with frame_lock:

            left=latest_frames[STREAM_PORT_LEFT]
            right=latest_frames[STREAM_PORT_RIGHT]

        if left is None or right is None:

            canvas=np.zeros((FRAME_HEIGHT,FRAME_WIDTH*2,3),dtype=np.uint8)

            cv2.putText(canvas,"Aguardando cameras",
                        (300,240),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,(0,200,255),2)

            cv2.imshow(DISPLAY_WINDOW,canvas)

        else:

            corners_l,box_l,status_l=analyze_chessboard(left)
            corners_r,box_r,status_r=analyze_chessboard(right)

            display_left=left.copy()
            display_right=right.copy()

            good_pose=False

            if corners_l is not None and corners_r is not None:

                center_l=np.mean(corners_l,axis=0)
                center_r=np.mean(corners_r,axis=0)

                baseline=abs(center_l[0][0]-center_r[0][0])

                tilt=compute_tilt(corners_l)

                sig=pose_signature(corners_l)

                duplicate=is_duplicate(sig)

                if (
                    status_l=="ok"
                    and status_r=="ok"
                    and MIN_BASELINE<baseline<MAX_BASELINE
                    and tilt<MAX_TILT_DEG
                    and not duplicate
                ):
                    good_pose=True

            display_left=draw_overlay(display_left,corners_l,good_pose)
            display_right=draw_overlay(display_right,corners_r,good_pose)

            if good_pose and not dataset_complete:

                if time.time()-last_capture_time>AUTO_CAPTURE_DELAY:

                    name_l=f"{leftCalibrationFolder}/{capture_count}.jpg"
                    name_r=f"{rightCalibrationFolder}/{capture_count}.jpg"

                    cv2.imwrite(name_l,left)
                    cv2.imwrite(name_r,right)

                    objpoints.append(objp)

                    imgpoints_l.append(corners_l)
                    imgpoints_r.append(corners_r)

                    pose_history.append(sig)

                    capture_count+=1
                    last_capture_time=time.time()

                    run_calibration_simulation()

                    if capture_count>=TARGET_CAPTURE_COUNT:
                        dataset_complete=True

            if corners_l is not None:
                cv2.drawChessboardCorners(display_left,CHESSBOARD_SIZE,corners_l,True)

            if corners_r is not None:
                cv2.drawChessboardCorners(display_right,CHESSBOARD_SIZE,corners_r,True)

            canvas=np.hstack([display_left,display_right])

            cv2.putText(canvas,f"Capturas:{capture_count}",
                        (10,30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,(255,255,255),2)

            if reproj_error_l is not None:

                textL=f"Erro L: {reproj_error_l:.3f}px"
                textR=f"Erro R: {reproj_error_r:.3f}px"

                cv2.putText(canvas,textL,(10,70),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7,(0,255,255),2)

                cv2.putText(canvas,textR,(10,100),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7,(0,255,255),2)

                quality="RUIM"

                if reproj_error_l<0.3 and reproj_error_r<0.3:
                    quality="EXCELENTE"
                elif reproj_error_l<0.5:
                    quality="MUITO BOA"
                elif reproj_error_l<0.8:
                    quality="BOA"

                cv2.putText(canvas,f"Qualidade: {quality}",
                            (10,140),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7,(0,255,0),2)

            if dataset_complete:

                cv2.putText(canvas,
                            "CALIBRATION DATASET COMPLETO",
                            (250,50),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            1,(0,255,0),3)

            cv2.imshow(DISPLAY_WINDOW,canvas)

        if cv2.waitKey(10)&0xFF==ord('q'):
            stop_event.set()

    cv2.destroyAllWindows()

# ==============================
# STREAM
# ==============================

def stream_receiver(port,name,side):

    sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    sock.bind(("",port))
    sock.settimeout(1)

    while not stop_event.is_set():

        try:

            data,_=sock.recvfrom(65535)

            frame=cv2.imdecode(
                np.frombuffer(data,np.uint8),
                cv2.IMREAD_COLOR
            )

            if frame is None:
                continue

            with frame_lock:
                latest_frames[port]=frame.copy()

            connected_cameras.add(port)

        except socket.timeout:
            continue

# ==============================
# MAIN
# ==============================

def main():

    warnings.filterwarnings("ignore",category=RuntimeWarning,module="cv2")

    stereo_calibration_setup()

    threads=[]

    for port,info in CAMERAS.items():

        t=threading.Thread(
            target=stream_receiver,
            args=(port,info["name"],info["side"]),
            daemon=True
        )

        t.start()
        threads.append(t)

    try:
        display_loop()

    finally:

        stop_event.set()

        for t in threads:
            t.join(timeout=2)

if __name__=="__main__":
    main()