import cv2


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