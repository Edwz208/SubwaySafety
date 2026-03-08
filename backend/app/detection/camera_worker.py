"""
detection/camera_worker.py

Runs the full detection pipeline on any camera stream URL.
Designed for phone cameras (IP Webcam app).
"""

import cv2
import os
import time

from detection.model         import get_model
from detection               import tracker, classifiers, annotator
from detection.clip_recorder import get_recorder, CLIPS_DIR


def run_camera(
    source:       str,
    camera_id:    str      = "camera",
    camera_angle: str      = "horizontal",
    cooldown:     int      = 20,
    on_alert:     callable = None,
):
    """
    Connects to a camera stream and runs detection continuously.

    Parameters:
        source       — IP Webcam URL e.g. "http://192.168.1.45:8080/video"
        camera_id    — name used in clip filenames e.g. "platform_1"
        camera_angle — "horizontal" or "topdown"
        cooldown     — seconds between alerts for the same person
        on_alert     — optional callback: on_alert(track_id, events, severity, clip_file)
    """

    print(f"[{camera_id}] Connecting to {source}")

    model = get_model()
    cap   = cv2.VideoCapture(source)

    if not cap.isOpened():
        print(f"[{camera_id}] ❌ Could not connect to {source}")
        return

    ret, frame = cap.read()
    if not ret:
        print(f"[{camera_id}] ❌ Could not read first frame")
        cap.release()
        return

    frame_h, frame_w     = frame.shape[:2]
    recorder             = get_recorder(camera_id, fps=15)
    last_alert: dict     = {}

    print(f"[{camera_id}] ✅ Connected | {frame_w}x{frame_h} | clips → {CLIPS_DIR}")
    print(f"[{camera_id}] Press Q to quit | S = screenshot")

    while cap.isOpened():

        ret, frame = cap.read()
        if not ret:
            print(f"[{camera_id}] Lost connection")
            break

        frame_h, frame_w = frame.shape[:2]
        recorder.add_frame(frame)

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
                tracker.update(track_id, cx, cy)
                active_ids.append(track_id)

                result = classifiers.run_all_classifiers(
                    kps_np, bbox, track_id, frame_w, frame_h,
                    camera_angle=camera_angle,
                )

                if result["severity"] == "critical":
                    now = time.time()
                    if now - last_alert.get(track_id, 0) > cooldown:
                        last_alert[track_id] = now

                        clip_file = recorder.trigger_clip(
                            alert_event = result["events"][0],
                            severity    = result["severity"],
                            frame_w     = frame_w,
                            frame_h     = frame_h,
                        )

                        print(f"\n🚨 [{camera_id}] CRITICAL | track={track_id} | {result['events']}")
                        print(f"   📹 {clip_file}\n")

                        if on_alert and clip_file:
                            on_alert(track_id, result["events"], result["severity"], clip_file)

                detections.append({
                    "track_id":  track_id,
                    "bbox":      bbox,
                    "keypoints": kps_np,
                    **result,
                })

        classifiers.clear_stale_tracks(active_ids)
        tracker.clear_stale(active_ids)

        annotated = annotator.annotate_frame(frame, detections)

        for d in detections:
            if d.get("skipped") or not d["events"]:
                continue
            x1, y1, x2, y2 = d["bbox"]
            aspect = round((x2 - x1) / max(y2 - y1, 1), 2)
            print(f"  [{camera_id}] ID:{d['track_id']} | aspect={aspect} | {d['events']} | {d['severity']}")

        cv2.imshow(f"Transit Guardian — {camera_id}", annotated)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("s"):
            cv2.imwrite(f"screenshot_{camera_id}.jpg", annotated)
            print("Screenshot saved")

    cap.release()
    cv2.destroyAllWindows()
    print(f"[{camera_id}] Stopped.")
