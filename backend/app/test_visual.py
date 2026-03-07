# test_visual.py
# Run from backend/ folder: python test_visual.py
# Controls: Q = quit | SPACE = pause | S = screenshot

import cv2
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))
from detection.model         import get_model
from detection               import tracker, classifiers, annotator
from detection.clip_recorder import get_recorder
from detection.clip_recorder import CLIPS_DIR
import detection.clip_recorder as _cr
print(f"clip_recorder file: {_cr.__file__}")
print(f"CLIPS_DIR: {_cr.CLIPS_DIR}")
print(f"Clips will save to: {CLIPS_DIR}")

# ── Config ────────────────────────────────────────────────────────────────────
VIDEO_SOURCE           = 0              # 0 = webcam
CAMERA_ANGLE           = "horizontal"
CAMERA_ID              = "webcam"       # used as prefix in clip filenames
ALERT_COOLDOWN_SECONDS = 20
# ─────────────────────────────────────────────────────────────────────────────

model  = get_model()
cap    = cv2.VideoCapture(VIDEO_SOURCE)
paused = False

last_alert_time: dict[int, float] = {}

print("Controls: Q = quit | SPACE = pause | S = screenshot")
print(f"Clips will be saved to: {os.path.abspath('clips')}")

# ── Grab one frame to get dimensions ─────────────────────────────────────────
ret, frame = cap.read()
if not ret:
    print("Could not open camera")
    sys.exit(1)

frame_h, frame_w = frame.shape[:2]
recorder = get_recorder(CAMERA_ID, fps=15)

print(f"Frame size: {frame_w}x{frame_h}")

while cap.isOpened():

    # ── Read frame ────────────────────────────────────────────────────────────
    if not paused:
        ret, frame = cap.read()
        if not ret:
            print("Video ended")
            break

    # ── Always feed frame into clip buffer ────────────────────────────────────
    # This MUST be outside the detection block and happen every frame
    # Without this the pre-alert buffer will be empty and clips have no footage
    recorder.add_frame(frame)

    # ── Run YOLOv8 ───────────────────────────────────────────────────────────
    results    = model.track(frame, persist=True, verbose=False, conf=0.35)
    detections = []
    active_ids = []

    if results and results[0].boxes is not None and results[0].keypoints is not None:
        for box, kps in zip(results[0].boxes, results[0].keypoints.data):

            track_id = int(box.id[0]) if box.id is not None else 0
            bbox     = box.xyxy[0].tolist()
            kps_np   = kps.cpu().numpy()
            cx       = (bbox[0] + bbox[2]) / 2
            cy       = (bbox[1] + bbox[3]) / 2
            box_h    = bbox[3] - bbox[1]

            classifiers.update_motion_history(track_id, cx, cy, box_h, kps_np)
            active_ids.append(track_id)

            result = classifiers.run_all_classifiers(
                kps_np, bbox, track_id, frame_w, frame_h,
                camera_angle=CAMERA_ANGLE,
            )

            # ── Trigger clip on critical alert ────────────────────────────────
            if result["severity"] == "critical":
                now  = time.time()
                last = last_alert_time.get(track_id, 0)

                if now - last > ALERT_COOLDOWN_SECONDS:
                    last_alert_time[track_id] = now

                    clip_file = recorder.trigger_clip(
                        alert_event = result["events"][0],
                        severity    = result["severity"],
                        frame_w     = frame_w,
                        frame_h     = frame_h,
                    )

                    if clip_file:
                        print(f"\n🚨 CRITICAL ALERT | track={track_id} | events={result['events']}")
                        print(f"   📹 Clip: {clip_file}")
                        print(f"   📂 Saved to: clips/{clip_file}\n")

            detections.append({
                "track_id":  track_id,
                "bbox":      bbox,
                "keypoints": kps_np,
                **result,
            })

    classifiers.clear_stale_tracks(active_ids)
    tracker.clear_stale(active_ids)

    # ── Annotate and show ─────────────────────────────────────────────────────
    annotated = annotator.annotate_frame(frame, detections)

    for d in detections:
        if d.get("skipped"):
            continue
        if d["events"]:
            x1, y1, x2, y2 = d["bbox"]
            aspect = round((x2 - x1) / max(y2 - y1, 1), 2)
            print(f"  ID:{d['track_id']} | aspect={aspect} | {d['events']} | {d['severity']}")

    cv2.imshow("Transit Guardian", annotated)
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
print("Done.")
