# test_visual.py
# Run from backend/ folder: python test_visual.py

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from detection.camera_worker import run_camera

run_camera(
    source    = 0,        # 0 = laptop webcam
    camera_id = "webcam",
)
