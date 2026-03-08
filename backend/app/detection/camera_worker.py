"""
detection/camera_worker.py
"""

import cv2
import time
from datetime import datetime, timezone

from detection.model import get_model
from detection import tracker, classifiers, annotator
from detection.clip_recorder import ClipRecorder, CLIPS_DIR
from db.connection import SessionLocal
from models.camera import Camera
from routers.alert import dispatch_alert


def set_last_detected_at(camera_id: int) -> None:
    db = SessionLocal()
    try:
        camera = db.query(Camera).filter(Camera.id == camera_id).first()
        if camera:
            camera.last_detected_at = datetime.now(timezone.utc)
            db.commit()
    except Exception as e:
        print(f"[{camera_id}] Failed to update last_detected_at: {e}")
        db.rollback()
    finally:
        db.close()


def run_camera(
    source: str,
    camera_id: int,
    camera_name: str = "camera",
    camera_angle: str = "horizontal",
    cooldown: float = 2,
    show_preview: bool = False,
    frame_skip: int = 1,
    stop_event=None,
):
    print(f"[{camera_id}] Connecting to {source}")

    model = get_model()
    recorder = ClipRecorder(str(camera_id), fps=15)
    last_alert: dict[int, float] = {}

    while not (stop_event and stop_event.is_set()):
        cap = None
        try:
            print(f"[{camera_id}] Opening source: {source}")
            cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            if not cap.isOpened():
                print(f"[{camera_id}] Could not connect. Retrying in 3s...")
                time.sleep(3)
                continue

            print(f"[{camera_id}] Stream opened. Warming up...")

            frame = None
            for _ in range(30):
                if stop_event and stop_event.is_set():
                    break
                ret, frame = cap.read()
                if ret and frame is not None:
                    break
                time.sleep(0.05)

            if frame is None:
                print(f"[{camera_id}] Failed to read valid frame. Reconnecting...")
                cap.release()
                time.sleep(2)
                continue

            frame_h, frame_w = frame.shape[:2]

            print(f"[{camera_id}] Connected | {frame_w}x{frame_h} | clips → {CLIPS_DIR}")
            debug_alert_sent = False
            frame_count = 0

            while cap.isOpened() and not (stop_event and stop_event.is_set()):
                ret, frame = cap.read()

                if not ret or frame is None:
                    print(f"[{camera_id}] Lost connection. Reconnecting...")
                    break

                if not debug_alert_sent:
                    debug_alert_sent = True
                    print(f"[{camera_id}] DEBUG: sending test alert from worker")

                    dispatch_alert(
                        events=["DEBUG_ALERT"],
                        clip_file=None,
                        camera_id=camera_id,
                    )

                frame_count += 1

                recorder.add_frame(frame)

                if frame_skip > 1 and frame_count % frame_skip != 0:
                    continue

                frame_h, frame_w = frame.shape[:2]

                results = model.track(frame, persist=True, verbose=False, conf=0.35)

                detections = []
                active_ids = []

                if results and results[0].boxes is not None and results[0].keypoints is not None:
                    for box, kps in zip(results[0].boxes, results[0].keypoints.data):
                        track_id = int(box.id[0]) if box.id is not None else 0
                        bbox = box.xyxy[0].tolist()
                        kps_np = kps.cpu().numpy()

                        cx = (bbox[0] + bbox[2]) / 2
                        cy = (bbox[1] + bbox[3]) / 2
                        box_h = bbox[3] - bbox[1]

                        classifiers.update_motion_history(track_id, cx, cy, box_h, kps_np)
                        tracker.update(track_id, cx, cy)
                        active_ids.append(track_id)

                        result = classifiers.run_all_classifiers(
                            kps_np,
                            bbox,
                            track_id,
                            frame_w,
                            frame_h,
                            camera_angle=camera_angle,
                        )

                        if result["severity"] == "critical":
                            now = time.time()

                            if now - last_alert.get(track_id, 0) > cooldown:
                                last_alert[track_id] = now

                                set_last_detected_at(camera_id)

                                clip_file = recorder.trigger_clip(
                                    alert_event=result["events"][0],
                                    severity=result["severity"],
                                    frame_w=frame_w,
                                    frame_h=frame_h,
                                )

                                print(f"\n🚨 [{camera_id}] CRITICAL | track={track_id} | {result['events']}")
                                print(f"   📹 {clip_file}\n")

                                dispatch_alert(
                                    events=result["events"],
                                    clip_file=clip_file,
                                    camera_id=camera_id,
                                )

                        detections.append({
                            "track_id": track_id,
                            "bbox": bbox,
                            "keypoints": kps_np,
                            **result,
                        })

                classifiers.clear_stale_tracks(active_ids)
                tracker.clear_stale(active_ids)

                stale_ids = set(last_alert.keys()) - set(active_ids)
                for stale_id in stale_ids:
                    last_alert.pop(stale_id, None)

                annotated = annotator.annotate_frame(frame, detections)

                for d in detections:
                    if d.get("skipped") or not d["events"]:
                        continue

                    x1, y1, x2, y2 = d["bbox"]
                    aspect = round((x2 - x1) / max(y2 - y1, 1), 2)

                    print(
                        f"  [{camera_id}] ID:{d['track_id']} | aspect={aspect} | {d['events']} | {d['severity']}"
                    )

                if show_preview:
                    cv2.imshow(f"Transit Guardian — {camera_name}", annotated)

                    key = cv2.waitKey(1) & 0xFF
                    if key == ord("q"):
                        print(f"[{camera_id}] Stopped.")
                        break
                    elif key == ord("s"):
                        cv2.imwrite(f"screenshot_{camera_id}.jpg", annotated)
                        print("Screenshot saved")

        except Exception as e:
            print(f"[{camera_id}] Worker error: {e}")
            time.sleep(2)
        finally:
            if cap is not None:
                cap.release()

    if show_preview:
        cv2.destroyAllWindows()
    print(f"[{camera_id}] Worker exited")