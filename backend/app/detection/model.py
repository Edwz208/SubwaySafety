from ultralytics import YOLO
import requests

# ─────────────────────────────────────────────
# WHAT IS THIS FILE?
# model.py does two things:
#
# 1. Loads the YOLOv8-pose model (singleton — loads once, reused forever)
# 2. Provides run_detection() which:
#    - Runs classifiers on a single frame
#    - If something is detected, POSTs to /api/events
#      which triggers Gemini summary + WebSocket alert to dashboard
#
# HOW TO USE:
#   from detection.model import get_model, run_detection
#
#   model = get_model()
#   for frame in video_stream:
#       results = model(frame)
#       run_detection(results, frame, camera_id="your-camera-uuid")
# ─────────────────────────────────────────────

# Your FastAPI backend URL
# Change to Tailscale IP when deployed: http://100.x.x.x:8000
BACKEND_URL = "http://localhost:8000"

_model = None

def get_model() -> YOLO:
    """
    Returns a singleton YOLOv8-Pose model instance.
    Loads once on first call, reuses on every subsequent call.
    """
    global _model
    if _model is None:
        print("[model] Loading YOLOv8-pose model...")
        _model = YOLO("yolov8n-pose.pt")
        print("[model] Model loaded.")
    return _model


def run_detection(
    yolo_results,
    frame,
    camera_id: str,
    snapshot_url: str = None,
):
    """
    Runs all classifiers on a YOLO results object for one frame.
    If any events are detected, POSTs to /api/events.

    Parameters:
        yolo_results  — output of model(frame), a YOLO Results object
        frame         — the raw frame (numpy array) for snapshot saving
        camera_id     — UUID string of the camera in your DB
        snapshot_url  — optional URL/path of the saved snapshot image
    """
    # Import here to avoid circular imports
    from detection.classifiers import (
        run_all_classifiers,
        update_motion_history,
        clear_stale_tracks,
    )
    import numpy as np

    # yolo_results[0] = first image in batch (we process one frame at a time)
    result = yolo_results[0]

    # frame dimensions — needed for classifiers
    frame_h, frame_w = frame.shape[:2]

    # boxes.id = tracker IDs assigned by YOLO's built-in tracker
    # If tracking is off, this will be None
    track_ids = (
        result.boxes.id.int().cpu().tolist()
        if result.boxes.id is not None
        else list(range(len(result.boxes)))
    )

    active_ids = []

    for i, (box, track_id) in enumerate(zip(result.boxes, track_ids)):
        active_ids.append(track_id)

        # Get bounding box coordinates [x1, y1, x2, y2]
        bbox = box.xyxy[0].cpu().tolist()

        # Get keypoints for this person
        # keypoints shape: (17, 3) — 17 joints, each with (x, y, confidence)
        keypoints = (
            result.keypoints.data[i].cpu().numpy()
            if result.keypoints is not None
            else None
        )

        if keypoints is None:
            continue

        # Compute body center from bounding box
        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2
        bbox_h = bbox[3] - bbox[1]

        # Update motion history BEFORE running classifiers
        # (classifiers need history to detect erratic movement + aggression)
        update_motion_history(track_id, cx, cy, bbox_h, keypoints)

        # Run all classifiers — returns {"events": [...], "severity": "...", "details": {...}}
        detection_result = run_all_classifiers(
            keypoints=keypoints,
            bbox=bbox,
            track_id=track_id,
            frame_w=frame_w,
            frame_h=frame_h,
        )

        # ── If something was detected, fire the alert ──
        if detection_result["events"]:
            primary_event = detection_result["events"][0]  # most important event
            severity = detection_result["severity"]

            print(f"[model] Detected {primary_event} (severity: {severity}) on track {track_id}")

            # POST to FastAPI → saves to DB → calls Gemini → fires WebSocket to dashboard
            _post_event(
                camera_id=camera_id,
                event_type=primary_event,
                severity=severity,
                details=detection_result["details"],
                snapshot_url=snapshot_url,
            )

    # Clean up motion history for people who left the frame
    clear_stale_tracks(active_ids)


def _post_event(
    camera_id: str,
    event_type: str,
    severity: str,
    details: dict,
    snapshot_url: str = None,
):
    """
    POSTs a detection event to the FastAPI backend.
    This triggers the full chain:
        events.py → Gemini summary → send_alert() → dashboard WebSocket
    """
    payload = {
        "camera_id":    camera_id,
        "event_type":   event_type,
        "severity":     severity,
        "details":      details,
        "snapshot_url": snapshot_url,
    }

    try:
        response = requests.post(
            f"{BACKEND_URL}/api/events",
            json=payload,
            timeout=5,  # don't block the detection loop for more than 5s
        )
        response.raise_for_status()
        print(f"[model] Event posted successfully: {event_type}")

    except requests.exceptions.Timeout:
        print(f"[model] POST /api/events timed out — backend may be slow")

    except requests.exceptions.ConnectionError:
        print(f"[model] Could not connect to backend at {BACKEND_URL}")

    except Exception as e:
        print(f"[model] Failed to post event: {e}")
