#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servidor UDP para streaming estéreo de duas ESP32-CAM
Direita -> porta 8080
Esquerda -> porta 8081
Recursos:
- Descoberta automática via broadcast
- Transmissão estéreo via websockets (porta 8765)
- FPS por câmera
- Reconexão automática
- Salvar pares de imagens para calibração
Comandos no console:
q -> sair
s -> salvar par de imagens
"""
import threading
import warnings
import cv2
from src.config import CAMERAS, LEFT_CALIBRATION_FOLDER, RIGHT_CALIBRATION_FOLDER, STREAM_PORT_LEFT, STREAM_PORT_RIGHT
from src.state import stop_event, frame_lock, latest_frames
from src.utils import stereo_calibration_setup
from src.broadcast import send_broadcast
from src.receiver import stream_receiver
from src.watchdog import watchdog
from src.websocket_handler import start_websocket_server

def main():
    warnings.filterwarnings("ignore", category=RuntimeWarning, module="cv2")
    stereo_calibration_setup()
    threads = []
    # Broadcast
    t = threading.Thread(target=send_broadcast, daemon=True)
    t.start()
    threads.append(t)
    # Receivers
    for port, info in CAMERAS.items():
        t = threading.Thread(
            target=stream_receiver,
            args=(port, info["name"], info["side"]),
            daemon=True
        )
        t.start()
        threads.append(t)

    # Watchdog
    t = threading.Thread(target=watchdog, daemon=True)
    t.start()
    threads.append(t)

    # Websocket server
    t = threading.Thread(target=start_websocket_server, daemon=True)
    t.start()
    threads.append(t)

    # Console input loop for commands
    picture_num = 0
    print("Press 'q' to quit")
    print("Press 's' to save")
    while not stop_event.is_set():
        try:
            cmd = input().strip().lower()
            if cmd == 'q':
                stop_event.set()
            elif cmd == 's':
                with frame_lock:
                    fl = latest_frames[STREAM_PORT_LEFT]
                    fr = latest_frames[STREAM_PORT_RIGHT]
                    if fl is not None and fr is not None:
                        name_l = f"{LEFT_CALIBRATION_FOLDER}/{picture_num}.jpg"
                        name_r = f"{RIGHT_CALIBRATION_FOLDER}/{picture_num}.jpg"
                        cv2.imwrite(name_l, fl)
                        cv2.imwrite(name_r, fr)
                        print("Saved:", name_l, name_r)
                        picture_num += 1
        except EOFError:
            pass
    # Cleanup
    for t in threads:
        t.join(timeout=2)
    print("Server closing")

if __name__ == "__main__":
    main()