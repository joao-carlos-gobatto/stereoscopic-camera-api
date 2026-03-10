### Requirements:
- opencv-python
- numpy
- websockets

### Websocket API
This project exposes two websocket endpoints:

1. **Video stream** – binary JPEG frames are sent continuously. Default port `8765` (see `VIDEO_WEBSOCKET_PORT`).
   * Each frame message begins with a single ASCII byte (`'L'` or `'R'`) indicating left/right camera, followed by the JPEG payload. Clients can use two `<img>` elements and update them based on this prefix.
2. **System status & commands** – JSON objects containing current state (broadcasting, calibrating, camera connectivity and FPS) are pushed periodically. Commands such as `save`, `reset`, `shutdown`, `start_calibration` and `stop_calibration` may be sent on this channel. Default port `8766` (see `CONTROL_WEBSOCKET_PORT`).

Use the example `image_stream.html` for a simple client demonstration.