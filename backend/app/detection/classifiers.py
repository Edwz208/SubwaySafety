"""
detection/classifiers.py

All custom event classifiers for Transit Guardian.
Each function receives YOLOv8-Pose keypoints + bounding box and returns
(detected: bool, confidence: float, metadata: dict).

Keypoint index reference:
  0: nose        1: left_eye      2: right_eye
  3: left_ear    4: right_ear     5: left_shoulder
  6: right_shoulder               7: left_elbow
  8: right_elbow  9: left_wrist  10: right_wrist
 11: left_hip   12: right_hip    13: left_knee
 14: right_knee 15: left_ankle   16: right_ankle
"""

import numpy as np
import time
from collections import deque


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION — tune these thresholds for your camera angle + environment
# ─────────────────────────────────────────────────────────────────────────────

CFG = {
    # Lying down / fallen
    "LYING_ASPECT_RATIO":       1.6,   # bbox width/height ratio to flag as horizontal
    "LYING_KP_Y_TOLERANCE":     0.5,   # keypoints Y-spread as fraction of bbox height

    # Stationary
    "STATIONARY_SECONDS":       10,    # seconds without movement to trigger alert
    "STATIONARY_PX_THRESHOLD":  15,    # max pixels moved to count as "not moving"
    "HISTORY_WINDOW_SECONDS":   15,    # how long to keep position history

    # Erratic movement
    "ERRATIC_MIN_DELTA":        5,     # minimum avg pixels/frame to count as moving
    "ERRATIC_CV_THRESHOLD":     0.6,   # coefficient of variation (chaos level)

    # Near restricted zone (train tracks)
    "TRACKS_ZONE_Y":            0.85,  # anything below this Y% = restricted zone

    # Crouching
    "CROUCH_RATIO_THRESHOLD":   0.35,  # (hip_y - nose_y) / bbox_height below this = crouching

    # Keypoint confidence — ignore keypoints below this confidence score
    "MIN_KP_CONFIDENCE":        0.3,
}


# ─────────────────────────────────────────────────────────────────────────────
# MOTION HISTORY STORE
# Tracks position history per person across frames.
# Key: track_id (assigned by YOLOv8 tracker)
# Value: deque of (timestamp, center_x, center_y)
# ─────────────────────────────────────────────────────────────────────────────

motion_history: dict[int, deque] = {}


def update_motion_history(track_id: int, cx: float, cy: float):
    """Call this every frame for every tracked person before running classifiers."""
    max_len = int(CFG["HISTORY_WINDOW_SECONDS"] * 15)  # ~15fps
    if track_id not in motion_history:
        motion_history[track_id] = deque(maxlen=max_len)
    motion_history[track_id].append((time.time(), cx, cy))


def clear_stale_tracks(active_ids: list[int]):
    """Call this each frame to remove history for people no longer in frame."""
    stale = [tid for tid in motion_history if tid not in active_ids]
    for tid in stale:
        del motion_history[tid]


# ─────────────────────────────────────────────────────────────────────────────
# HELPER — safe keypoint accessor
# ─────────────────────────────────────────────────────────────────────────────

def kp(keypoints: np.ndarray, idx: int) -> tuple[float, float, float]:
    """
    Returns (x, y, confidence) for keypoint at index idx.
    Returns (0, 0, 0) if keypoints are missing or confidence is too low.
    """
    if keypoints is None or len(keypoints) <= idx:
        return 0.0, 0.0, 0.0
    x, y, conf = float(keypoints[idx][0]), float(keypoints[idx][1]), float(keypoints[idx][2])
    return x, y, conf


def visible_ys(keypoints: np.ndarray, indices: list[int]) -> list[float]:
    """Return Y values of keypoints that meet the minimum confidence threshold."""
    return [kp(keypoints, i)[1] for i in indices if kp(keypoints, i)[2] >= CFG["MIN_KP_CONFIDENCE"]]


def visible_xs(keypoints: np.ndarray, indices: list[int]) -> list[float]:
    """Return X values of keypoints that meet the minimum confidence threshold."""
    return [kp(keypoints, i)[0] for i in indices if kp(keypoints, i)[2] >= CFG["MIN_KP_CONFIDENCE"]]


# ─────────────────────────────────────────────────────────────────────────────
# EVENT 1 — LYING DOWN
# ─────────────────────────────────────────────────────────────────────────────

def detect_lying_down(
    keypoints: np.ndarray,
    bbox: list[float]
) -> tuple[bool, float, dict]:
    """
    Detects if a person is lying horizontally.

    Two independent signals that both point to the same conclusion:

    Signal A — Bounding box aspect ratio:
      A standing person's bounding box is tall (height > width).
      A lying person's bounding box is wide (width > height).
      Ratio = width / height. Anything above 1.4 is strongly horizontal.

    Signal B — Keypoint Y-spread:
      When standing, body keypoints span a large vertical range
      (nose near top, ankles near bottom — big Y difference).
      When lying, all keypoints cluster at roughly the same Y value
      (small Y spread relative to bounding box height).

    We require EITHER signal alone to trigger (with different confidence levels),
    but BOTH together gives highest confidence.
    """
    x1, y1, x2, y2 = bbox
    box_w = x2 - x1
    box_h = y2 - y1

    if box_h < 1:
        return False, 0.0, {}

    # ── Signal A: aspect ratio ──
    aspect_ratio = box_w / box_h
    signal_a = aspect_ratio >= CFG["LYING_ASPECT_RATIO"]

    # ── Signal B: keypoint Y spread ──
    # Use shoulders, hips, ankles — the "spine" of the body
    body_ys = visible_ys(keypoints, [5, 6, 11, 12, 15, 16])
    signal_b = False
    if len(body_ys) >= 3:
        y_spread = max(body_ys) - min(body_ys)
        # If the vertical spread of body keypoints is less than 60% of bbox height
        # → they're all at roughly the same Y → horizontal
        signal_b = y_spread < (box_h * CFG["LYING_KP_Y_TOLERANCE"])

    if not (signal_a or signal_b):
        return False, 0.0, {}

    # Confidence: both signals = high, one signal = moderate
    if signal_a and signal_b:
        confidence = min(1.0, aspect_ratio / 2.0)
    elif signal_a:
        confidence = min(0.65, aspect_ratio / 2.5)
    else:
        confidence = 0.45

    meta = {
        "aspect_ratio": round(aspect_ratio, 2),
        "signal_aspect_ratio": signal_a,
        "signal_keypoint_spread": signal_b,
    }
    return True, round(confidence, 2), meta


# ─────────────────────────────────────────────────────────────────────────────
# EVENT 2 — FALLEN (lying + head near ground level)
# ─────────────────────────────────────────────────────────────────────────────

def detect_fallen(
    keypoints: np.ndarray,
    bbox: list[float]
) -> tuple[bool, float, dict]:
    """
    Detects a fall: person is horizontal AND head is close to ground.

    Builds on detect_lying_down. The extra check:
    When someone lies down voluntarily (e.g. sleeping), their head
    can be anywhere. After a fall, the head tends to be at mid-body height
    or lower relative to the bounding box.

    Logic:
      1. Person must pass the lying_down check first.
      2. nose_y (head position) must be in the lower 60% of the bounding box.
         (If nose_y is near the TOP of bbox, they are lying with head elevated —
          less likely a collapse. If near bottom/middle — head on ground.)
    """
    is_lying, lying_conf, lying_meta = detect_lying_down(keypoints, bbox)

    if not is_lying:
        return False, 0.0, {}

    x1, y1, x2, y2 = bbox
    box_h = y2 - y1

    nose_x, nose_y, nose_conf = kp(keypoints, 0)

    if nose_conf >= CFG["MIN_KP_CONFIDENCE"] and box_h > 0:
        # Normalize nose position within bounding box: 0 = top, 1 = bottom
        relative_nose_y = (nose_y - y1) / box_h
        # Head in lower half of bbox = likely on the ground
        head_near_ground = relative_nose_y > 0.4

        if head_near_ground:
            confidence = min(1.0, lying_conf * 1.25)
            meta = {**lying_meta, "relative_nose_y": round(relative_nose_y, 2), "head_near_ground": True}
            return True, round(confidence, 2), meta

    # No confident nose keypoint — fall back to lying_down with slightly lower confidence
    meta = {**lying_meta, "head_near_ground": "unknown"}
    return True, round(lying_conf * 0.85, 2), meta


# ─────────────────────────────────────────────────────────────────────────────
# EVENT 4 — ERRATIC MOVEMENT
# ─────────────────────────────────────────────────────────────────────────────

def detect_erratic_movement(track_id: int) -> tuple[bool, float, dict]:
    """
    Detects chaotic, unpredictable movement patterns.

    A person walking normally has consistent frame-to-frame movement:
    similar step sizes, consistent direction. Their movement deltas are
    regular → LOW variance relative to mean.

    An agitated, distressed, or erratic person moves inconsistently:
    sudden bursts, direction changes, varying speeds. Their deltas
    have HIGH variance relative to their mean.

    We measure this with Coefficient of Variation (CV):
        CV = standard_deviation / mean

    CV > 0.8 with sufficient movement = erratic.
    CV alone isn't enough — we also require the mean movement to exceed
    a threshold, so a person standing very still doesn't get flagged
    (their CV would be high but mean would be tiny).
    """
    if track_id not in motion_history:
        return False, 0.0, {}

    history = list(motion_history[track_id])
    if len(history) < 6:
        # Need at least 6 frames to calculate meaningful variance
        return False, 0.0, {}

    # Frame-to-frame Euclidean distances
    deltas = []
    for i in range(1, len(history)):
        dx = history[i][1] - history[i-1][1]  # x delta
        dy = history[i][2] - history[i-1][2]  # y delta
        deltas.append(np.sqrt(dx**2 + dy**2))

    mean_delta = float(np.mean(deltas))
    std_delta = float(np.std(deltas))

    if mean_delta < CFG["ERRATIC_MIN_DELTA"]:
        # Not moving enough to distinguish erratic from stationary noise
        return False, 0.0, {}

    cv = std_delta / (mean_delta + 1e-6)
    is_erratic = cv >= CFG["ERRATIC_CV_THRESHOLD"]

    if not is_erratic:
        return False, 0.0, {}

    confidence = min(1.0, (cv - CFG["ERRATIC_CV_THRESHOLD"]) * 2 + 0.4)
    meta = {
        "mean_delta_px": round(mean_delta, 2),
        "std_delta_px": round(std_delta, 2),
        "coefficient_of_variation": round(cv, 2),
    }
    return True, round(confidence, 2), meta


# ─────────────────────────────────────────────────────────────────────────────
# EVENT 5 — CROUCHING / HUNCHED OVER
# ─────────────────────────────────────────────────────────────────────────────

def detect_crouching(
    keypoints: np.ndarray,
    bbox: list[float]
) -> tuple[bool, float, dict]:
    """
    Detects if a person is crouching, hunched, or doubled over.

    When standing upright, the nose (head) is far above the hips.
    The vertical gap (hip_y - nose_y) is large relative to bbox height.

    When crouching or bent over, the head drops toward hip level.
    That gap shrinks significantly.

    We measure: (avg_hip_y - nose_y) / bbox_height
    Low ratio = head is close to hips = crouching.

    Note: we must EXCLUDE lying_down cases — a lying person also
    has nose near hip level. We add a bbox aspect ratio guard.
    """
    x1, y1, x2, y2 = bbox
    box_h = y2 - y1

    if box_h < 1:
        return False, 0.0, {}

    # If aspect ratio > 1.2 it's probably lying, not crouching — skip
    box_w = x2 - x1
    if box_w / box_h > 1.2:
        return False, 0.0, {}

    nose_x, nose_y, nose_c       = kp(keypoints, 0)
    l_hip_x, l_hip_y, l_hip_c   = kp(keypoints, 11)
    r_hip_x, r_hip_y, r_hip_c   = kp(keypoints, 12)

    # Need at least nose + one hip keypoint with sufficient confidence
    hip_ys = [y for y, c in [(l_hip_y, l_hip_c), (r_hip_y, r_hip_c)]
              if c >= CFG["MIN_KP_CONFIDENCE"]]

    if nose_c < CFG["MIN_KP_CONFIDENCE"] or not hip_ys:
        return False, 0.0, {}

    avg_hip_y = np.mean(hip_ys)
    # Positive = nose is above hips (normal standing)
    # Near zero or negative = nose is at or below hip level (crouching/fallen)
    vertical_gap_ratio = (avg_hip_y - nose_y) / box_h

    is_crouching = vertical_gap_ratio < CFG["CROUCH_RATIO_THRESHOLD"]

    if not is_crouching:
        return False, 0.0, {}

    # Confidence: lower the ratio, more severely crouched
    confidence = max(0.4, min(1.0, 1.0 - (vertical_gap_ratio / CFG["CROUCH_RATIO_THRESHOLD"])))
    meta = {
        "vertical_gap_ratio": round(float(vertical_gap_ratio), 3),
        "avg_hip_y": round(float(avg_hip_y), 1),
        "nose_y": round(float(nose_y), 1),
    }
    return True, round(confidence, 2), meta


# ─────────────────────────────────────────────────────────────────────────────
# SEVERITY MAPPER
# ─────────────────────────────────────────────────────────────────────────────

# Priority order matters — first match wins
SEVERITY_MAP = [
    ("critical", ["FALLEN"]),
    ("high",     ["LYING_DOWN", "CROUCHING"]),
    ("medium",   ["ERRATIC"]),
    ("low",      []),  # catch-all for anything else detected
]

def classify_severity(events: list[str]) -> str:
    """
    Given a list of detected event names, return the highest severity level.
    """
    if not events:
        return "none"

    for severity, triggers in SEVERITY_MAP:
        if any(trigger in events for trigger in triggers):
            return severity

    return "low"


# ─────────────────────────────────────────────────────────────────────────────
# MASTER RUNNER — call this once per person per frame
# ─────────────────────────────────────────────────────────────────────────────

def run_all_classifiers(
    keypoints: np.ndarray,
    bbox: list[float],
    track_id: int,
    frame_w: int,
    frame_h: int,
    custom_zones: list[dict] | None = None,
) -> dict:
    """
    Runs every classifier for a single detected person.
    Returns a unified result dict ready to send to the frontend.

    Call update_motion_history() BEFORE calling this function.

    Returns:
    {
        "events": ["FALLEN"],
        "severity": "critical",
        "details": {
            "FALLEN": { "confidence": 0.91, "aspect_ratio": 1.8, ... },
        }
    }
    """
    events = []
    details = {}

    # ── Run each classifier ──────────────────────────────────

    fallen, conf, meta = detect_fallen(keypoints, bbox)
    if fallen:
        events.append("FALLEN")
        details["FALLEN"] = {"confidence": conf, **meta}
    else:
        # Only check lying_down if not already flagged as fallen
        # (fallen is a superset of lying_down)
        lying, conf, meta = detect_lying_down(keypoints, bbox)
        if lying:
            events.append("LYING_DOWN")
            details["LYING_DOWN"] = {"confidence": conf, **meta}

    erratic, conf, meta = detect_erratic_movement(track_id)
    if erratic:
        events.append("ERRATIC")
        details["ERRATIC"] = {"confidence": conf, **meta}

    crouching, conf, meta = detect_crouching(keypoints, bbox)
    if crouching:
        events.append("CROUCHING")
        details["CROUCHING"] = {"confidence": conf, **meta}

    # ── Classify overall severity ────────────────────────────
    severity = classify_severity(events)

    return {
        "events": events,
        "severity": severity,
        "details": details,

    }
