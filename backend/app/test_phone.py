# test_phone.py
# Run from backend/ folder: python test_phone.py

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from detection.camera_worker import run_camera

run_camera(
    source    = "http://172.20.10.7:8080/video",  # change to your phone's IP
    camera_id = "phone",
)
