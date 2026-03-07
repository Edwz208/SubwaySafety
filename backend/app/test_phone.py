# test_phone.py
# Run from backend/ folder: python test_phone.py
# Press Q to quit

import cv2
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from detection.model import get_model
from detection import tracker, classifiers, annotator

# ── PUT YOUR PHONE'S URL HERE ──
PHONE_URL = "http://172.20.10.7:8080/video"  # change this IP

print(f"Connecting to {PHONE_URL} ...")

model = get_model()
cap   = cv2.VideoCapture(PHONE_URL)

if not cap.isOpened():
    print("Could not connect. Check:")
    print("  1. Phone and laptop on same WiFi?")
    print("  2. IP Webcam app running on phone?")
    print("  3. IP address correct?")
    sys.exit(1)

print("Connected. Press Q to quit.")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("Lost connection")
        break

    frame_h, frame_w = frame.shape[:2]

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

    # Print events to terminal
    for d in detections:
        x1, y1, x2, y2 = d["bbox"]
        box_w = x2 - x1
        box_h = max(y2 - y1, 1)
        aspect = round(box_w / box_h, 2)
        print(f"  ID:{d['track_id']} | aspect={aspect} | events={d['events']} | details={d['details']}")

    annotated = annotator.annotate_frame(frame, detections)
    cv2.imshow("Phone Camera - Transit Guardian", annotated)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
