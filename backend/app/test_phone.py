# test_phone.py
# Run from backend/ folder: python test_phone.py

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from detection.camera_worker import run_camera

run_camera(
    source = "rtsp://155.138.128.95:8554/live/phone", # change to ip
    camera_id = "phone",
)
