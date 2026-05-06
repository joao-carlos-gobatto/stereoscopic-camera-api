import numpy as np
import cv2

def pose_signature(corners):
    center=np.mean(corners,axis=0)
    vec=corners[-1]-corners[0]
    angle=np.arctan2(vec[0][1],vec[0][0])
    return np.array([center[0][0],center[0][1],angle])


def is_duplicate(sig, pose_history, POSE_DUPLICATE_THRESHOLD):
    for p in pose_history:
        if np.linalg.norm(sig-p)<POSE_DUPLICATE_THRESHOLD:
            return True
    return False


def compute_tilt(corners, CHESSBOARD_SIZE):
    pts=corners.reshape(-1,2)
    v1=pts[1]-pts[0]
    v2=pts[CHESSBOARD_SIZE[0]]-pts[0]
    normal=np.cross(np.append(v1,0),np.append(v2,0))
    normal=normal/np.linalg.norm(normal)
    tilt=np.degrees(np.arccos(normal[2]))
    return abs(tilt)

def compute_reprojection_error(objpoints, imgpoints, rvecs, tvecs, mtx, dist):
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


def run_calibration_simulation(objpoints, imgpoints_l, imgpoints_r, FRAME_WIDTH, FRAME_HEIGHT):
    if len(objpoints)<10:
        return None,None
    ret_l,mtx_l,dist_l,rvecs_l,tvecs_l = cv2.calibrateCamera(
        objpoints,
        imgpoints_l,
        (FRAME_WIDTH,FRAME_HEIGHT),
        None,
        None
    )
    ret_r,mtx_r,dist_r,rvecs_r,tvecs_r = cv2.calibrateCamera(
        objpoints,
        imgpoints_r,
        (FRAME_WIDTH,FRAME_HEIGHT),
        None,
        None
    )
    reproj_error_l = compute_reprojection_error(
        objpoints,imgpoints_l,rvecs_l,tvecs_l,mtx_l,dist_l
    )
    reproj_error_r = compute_reprojection_error(
        objpoints,imgpoints_r,rvecs_r,tvecs_r,mtx_r,dist_r
    )
    return reproj_error_l,reproj_error_r

def analyze_chessboard(frame, CHESSBOARD_SIZE, FRAME_WIDTH, FRAME_HEIGHT, MIN_AREA_RATIO):
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

def draw_overlay(frame,corners,good):
    if corners is None:
        return frame
    pts=corners.reshape(-1,2).astype(int)
    hull=cv2.convexHull(pts)
    overlay=frame.copy()
    color=(255,0,0) if good else (0,255,0)
    cv2.fillConvexPoly(overlay,hull,color)
    return cv2.addWeighted(overlay,0.25,frame,0.75,0)