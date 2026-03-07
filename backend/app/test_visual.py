# test_visual.py
# Run this from backend/ folder:  python test_visual.py
# Press Q to quit, SPACE to pause

import cv2
import sys
import os

# Add app/ to Python path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from detection.model import get_model
from detection import tracker, classifiers, annotator

# ── Change this to your test video path ──
VIDEO_SOURCE = 0  # 0 = webcam, or "path/to/video.mp4"

model  = get_model()
cap    = cv2.VideoCapture(VIDEO_SOURCE)
paused = False

print("Controls: Q = quit | SPACE = pause | S = save screenshot")

while cap.isOpened():
    if not paused:
        ret, frame = cap.read()
        if not ret:
            print("Video ended")
            break

    frame_h, frame_w = frame.shape[:2]

    # ── Run full pipeline ──
    results = model.track(frame, persist=True, verbose=False, conf=0.35)

    detections = []
    active_ids = []

    if results and results[0].boxes is not None and results[0].keypoints is not None:
        for box, kps in zip(results[0].boxes, results[0].keypoints.data):
            track_id = int(box.id[0]) if box.id is not None else 0
            bbox     = box.xyxy[0].tolist()
            kps_np   = kps.cpu().numpy()
            cx       = (bbox[0] + bbox[2]) / 2
            cy       = (bbox[1] + bbox[3]) / 2

            tracker.update(track_id, cx, cy)
            active_ids.append(track_id)

            result = classifiers.run_all_classifiers(
                kps_np, bbox, track_id, frame_w, frame_h
            )

            detections.append({
                "track_id":  track_id,
                "bbox":      bbox,
                "keypoints": kps_np,
                **result,
            })

    tracker.clear_stale(active_ids)

    # ── Annotate ──
    annotated = annotator.annotate_frame(frame, detections)

    # ── Print detections to terminal in real time ──
    for d in detections:
        x1, y1, x2, y2 = d["bbox"]
        box_w = x2 - x1
        box_h = max(y2 - y1, 1)
        aspect = round(box_w / box_h, 2)
        print(f"  ID:{d['track_id']} | aspect={aspect} | events={d['events']} | details={d['details']}")

    # ── Show frame ──
    cv2.imshow("Transit Guardian - Detection Test", annotated)

    key = cv2.waitKey(1) & 0xFF
    if key == ord("q"):
        break
    elif key == ord(" "):
        paused = not paused
        print("PAUSED" if paused else "RESUMED")
    elif key == ord("s"):
        cv2.imwrite("screenshot.jpg", annotated)
        print("Screenshot saved")

cap.release()
cv2.destroyAllWindows()
