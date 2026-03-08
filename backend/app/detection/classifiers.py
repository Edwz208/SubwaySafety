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
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

CFG = {
    # Lying down / fallen
    "LYING_ASPECT_RATIO":        1.6,
    "LYING_KP_Y_TOLERANCE":      0.5,

    # Stationary
    "STATIONARY_SECONDS":        10,
    "STATIONARY_NORM_THRESHOLD": 0.03,

    # History
    "HISTORY_WINDOW_SECONDS":    15,

    # Erratic movement (normalized — scale invariant)
    "ERRATIC_MIN_DELTA_NORM":    0.05,
    "ERRATIC_CV_THRESHOLD":      0.85,

    # Punch detection — requires BOTH speed AND arm extension
    #
    # TUNING GUIDE:
    #   Still triggers on normal movement → raise PUNCH_WRIST_SPEED_NORM (try 2.5, 3.0)
    #   Punches not detected             → lower PUNCH_ELBOW_ANGLE (try 135, 130)
    "PUNCH_WRIST_SPEED_NORM":    2.0,   # wrist body-heights/sec — walking ~0.3-0.6, punch ~2.0+
    "PUNCH_ELBOW_ANGLE":         140,   # degrees — realistic punch extension (was hardcoded 155, too strict)

    # Crouching
    "CROUCH_RATIO_THRESHOLD":    0.35,

    # Minimum bbox height — skip far-away noisy detections
    "MIN_BBOX_HEIGHT_PX":        80,

    # Keypoint confidence
    "MIN_KP_CONFIDENCE":         0.3,
}


# ─────────────────────────────────────────────────────────────────────────────
# MOTION HISTORY STORE
# Each entry: (timestamp, cx, cy, bbox_h, lw_x, lw_y, rw_x, rw_y)
# ─────────────────────────────────────────────────────────────────────────────

motion_history: dict[int, deque] = {}


def update_motion_history(
    track_id: int,
    cx: float,
    cy: float,
    bbox_h: float,
    keypoints: np.ndarray,
):
    """
    Call this EVERY FRAME for every tracked person, BEFORE run_all_classifiers.
    Stores body center + wrist positions for motion analysis.
    """
    max_len = int(CFG["HISTORY_WINDOW_SECONDS"] * 15)
    if track_id not in motion_history:
        motion_history[track_id] = deque(maxlen=max_len)

    lw_x, lw_y, lw_c = kp(keypoints, 9)
    rw_x, rw_y, rw_c = kp(keypoints, 10)

    motion_history[track_id].append((
        time.time(),
        cx, cy,
        max(bbox_h, 1.0),
        lw_x if lw_c >= CFG["MIN_KP_CONFIDENCE"] else None,
        lw_y if lw_c >= CFG["MIN_KP_CONFIDENCE"] else None,
        rw_x if rw_c >= CFG["MIN_KP_CONFIDENCE"] else None,
        rw_y if rw_c >= CFG["MIN_KP_CONFIDENCE"] else None,
    ))


def clear_stale_tracks(active_ids: list[int]):
    stale = [tid for tid in motion_history if tid not in active_ids]
    for tid in stale:
        del motion_history[tid]


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def kp(keypoints: np.ndarray, idx: int) -> tuple[float, float, float]:
    if keypoints is None or len(keypoints) <= idx:
        return 0.0, 0.0, 0.0
    x, y, conf = float(keypoints[idx][0]), float(keypoints[idx][1]), float(keypoints[idx][2])
    return x, y, conf


def visible_ys(keypoints: np.ndarray, indices: list[int]) -> list[float]:
    return [kp(keypoints, i)[1] for i in indices if kp(keypoints, i)[2] >= CFG["MIN_KP_CONFIDENCE"]]


def visible_xs(keypoints: np.ndarray, indices: list[int]) -> list[float]:
    return [kp(keypoints, i)[0] for i in indices if kp(keypoints, i)[2] >= CFG["MIN_KP_CONFIDENCE"]]


def _angle_between(a, b, c) -> float:
    """
    Angle at point B in triangle A-B-C, in degrees.
    A=shoulder, B=elbow, C=wrist → elbow bend angle.
    180 = fully straight arm. ~60-90 = resting/bent.
    """
    ba = np.array([a[0] - b[0], a[1] - b[1]], dtype=float)
    bc = np.array([c[0] - b[0], c[1] - b[1]], dtype=float)
    denom = np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6
    return float(np.degrees(np.arccos(np.clip(np.dot(ba, bc) / denom, -1.0, 1.0))))


# ─────────────────────────────────────────────────────────────────────────────
# EVENT 1 — LYING DOWN
# ─────────────────────────────────────────────────────────────────────────────

def detect_lying_down(
    keypoints: np.ndarray,
    bbox: list[float],
    camera_angle: str = "horizontal",
) -> tuple[bool, float, dict]:
    x1, y1, x2, y2 = bbox
    box_w = x2 - x1
    box_h = y2 - y1

    if box_h < 1:
        return False, 0.0, {}

    aspect_ratio = box_w / max(box_h, 1)

    signal_a = False
    if camera_angle == "horizontal":
        signal_a = aspect_ratio >= CFG["LYING_ASPECT_RATIO"]

    body_ys = visible_ys(keypoints, [5, 6, 11, 12, 15, 16])
    signal_b = False
    required_kps = 5 if not signal_a else 3
    if len(body_ys) >= required_kps:
        y_spread = max(body_ys) - min(body_ys)
        signal_b = y_spread < (box_h * CFG["LYING_KP_Y_TOLERANCE"])

    signal_c = False
    if camera_angle == "topdown":
        shoulder_xs = visible_xs(keypoints, [5, 6])
        hip_xs      = visible_xs(keypoints, [11, 12])
        shoulder_ys = visible_ys(keypoints, [5, 6])
        hip_ys      = visible_ys(keypoints, [11, 12])
        if shoulder_xs and hip_xs and shoulder_ys and hip_ys:
            all_xs   = shoulder_xs + hip_xs
            x_spread = max(all_xs) - min(all_xs)
            y_gap    = abs(float(np.mean(shoulder_ys)) - float(np.mean(hip_ys)))
            signal_c = x_spread > box_w * 0.5 and y_gap < box_h * 0.3

    # Require BOTH signals for horizontal — one alone causes false triggers
    if camera_angle == "horizontal":
        if not (signal_a and signal_b):
            return False, 0.0, {}
    else:
        if not (signal_b or signal_c):
            return False, 0.0, {}

    signal_count = sum([signal_a, signal_b, signal_c])
    confidence = (
        min(1.0, 0.5 + signal_count * 0.2 + (aspect_ratio / 5.0 if signal_a else 0))
        if signal_count >= 2 else 0.45
    )

    meta = {
        "aspect_ratio":           round(aspect_ratio, 2),
        "signal_aspect_ratio":    signal_a,
        "signal_keypoint_spread": signal_b,
        "signal_topdown":         signal_c,
    }
    return True, round(confidence, 2), meta


# ─────────────────────────────────────────────────────────────────────────────
# EVENT 2 — FALLEN
# ─────────────────────────────────────────────────────────────────────────────

def detect_fallen(
    keypoints: np.ndarray,
    bbox: list[float],
    camera_angle: str = "horizontal",
) -> tuple[bool, float, dict]:
    is_lying, lying_conf, lying_meta = detect_lying_down(keypoints, bbox, camera_angle)
    if not is_lying:
        return False, 0.0, {}

    x1, y1, x2, y2 = bbox
    box_h = y2 - y1
    nose_x, nose_y, nose_conf = kp(keypoints, 0)

    if nose_conf >= CFG["MIN_KP_CONFIDENCE"] and box_h > 0:
        relative_nose_y = (nose_y - y1) / box_h
        if relative_nose_y > 0.4:
            confidence = min(1.0, lying_conf * 1.1)
            meta = {**lying_meta, "relative_nose_y": round(relative_nose_y, 2), "head_near_ground": True}
            return True, round(confidence, 2), meta

    meta = {**lying_meta, "head_near_ground": "unknown"}
    return True, round(lying_conf * 0.85, 2), meta


# ─────────────────────────────────────────────────────────────────────────────
# EVENT 3 — PUNCH / AGGRESSION
# ─────────────────────────────────────────────────────────────────────────────

def detect_aggression(
    track_id: int,
    keypoints: np.ndarray,
    bbox: list[float],
) -> tuple[bool, float, dict]:
    """
    Punch = fast wrist speed AND extended elbow. BOTH required, no exceptions.

    Speed gate uses CFG["PUNCH_WRIST_SPEED_NORM"] — previously hardcoded to 2.0,
    ignoring CFG entirely. Now reads from CFG so tuning actually works.

    Angle gate uses CFG["PUNCH_ELBOW_ANGLE"] — previously hardcoded to 155
    which was too strict (most real punches only reach 140-150 degrees).
    Now reads from CFG, default 140.
    """
    x1, y1, x2, y2 = bbox
    box_h = max(y2 - y1, 1.0)
    MIN_CONF = CFG["MIN_KP_CONFIDENCE"]

    # ── Step 1: Speed gate — exit immediately if wrists aren't moving fast ───
    wrist_speed_norm = 0.0
    speed_source     = "none"

    if track_id not in motion_history:
        return False, 0.0, {}

    history = list(motion_history[track_id])
    if len(history) < 2:
        return False, 0.0, {}

    now    = history[-1][0]
    recent = [h for h in history if now - h[0] <= 0.25]
    if len(recent) < 2:
        return False, 0.0, {}

    time_span = max(recent[-1][0] - recent[0][0], 0.01)

    def disp_norm(ax, ay, bx, by):
        return np.sqrt((bx - ax)**2 + (by - ay)**2) / time_span / box_h

    lw_start = next(((h[4], h[5]) for h in recent           if h[4] is not None), None)
    lw_end   = next(((h[4], h[5]) for h in reversed(recent)  if h[4] is not None), None)
    if lw_start and lw_end and lw_start != lw_end:
        spd = disp_norm(lw_start[0], lw_start[1], lw_end[0], lw_end[1])
        if spd > wrist_speed_norm:
            wrist_speed_norm = spd
            speed_source     = "left_wrist"

    rw_start = next(((h[6], h[7]) for h in recent           if h[6] is not None), None)
    rw_end   = next(((h[6], h[7]) for h in reversed(recent)  if h[6] is not None), None)
    if rw_start and rw_end and rw_start != rw_end:
        spd = disp_norm(rw_start[0], rw_start[1], rw_end[0], rw_end[1])
        if spd > wrist_speed_norm:
            wrist_speed_norm = spd
            speed_source     = "right_wrist"

    # Reads from CFG — previously this was hardcoded and ignored CFG entirely
    SPEED_THRESH = CFG["PUNCH_WRIST_SPEED_NORM"]
    raw_px_moved = wrist_speed_norm * box_h * time_span
    if raw_px_moved < 40 or wrist_speed_norm < SPEED_THRESH:
        return False, 0.0, {}

# Raw pixel sanity check — wrist must move at least 40px in 0.25s
# This stops close-range perspective jitter from passing the speed gate
    

    # ── Step 2: Arm extension gate — verify elbow is actually extended ────────
    l_shoulder = kp(keypoints, 5)
    r_shoulder = kp(keypoints, 6)
    l_elbow    = kp(keypoints, 7)
    r_elbow    = kp(keypoints, 8)
    l_wrist    = kp(keypoints, 9)
    r_wrist    = kp(keypoints, 10)

    left_chain  = l_shoulder[2] >= MIN_CONF and l_elbow[2] >= MIN_CONF and l_wrist[2] >= MIN_CONF
    right_chain = r_shoulder[2] >= MIN_CONF and r_elbow[2] >= MIN_CONF and r_wrist[2] >= MIN_CONF

    left_angle  = _angle_between(
        (l_shoulder[0], l_shoulder[1]),
        (l_elbow[0],    l_elbow[1]),
        (l_wrist[0],    l_wrist[1]),
    ) if left_chain else None

    right_angle = _angle_between(
        (r_shoulder[0], r_shoulder[1]),
        (r_elbow[0],    r_elbow[1]),
        (r_wrist[0],    r_wrist[1]),
    ) if right_chain else None

    # Reads from CFG — previously hardcoded to 155 which missed most real punches
    ANGLE_THRESH   = CFG["PUNCH_ELBOW_ANGLE"]
    left_extended  = left_angle  is not None and left_angle  > ANGLE_THRESH
    right_extended = right_angle is not None and right_angle > ANGLE_THRESH

    if not (left_extended or right_extended):
        # Fast wrist but arm not extended = waving/gesturing, not a punch
        return False, 0.0, {}

    # ── Both gates cleared: fast wrist + extended elbow = punch ─────────────
    confidence = min(1.0, 0.55 + (wrist_speed_norm - SPEED_THRESH) * 0.15)

    meta = {
        "left_elbow_angle":  round(left_angle,  1) if left_angle  is not None else None,
        "right_elbow_angle": round(right_angle, 1) if right_angle is not None else None,
        "wrist_speed_norm":  round(wrist_speed_norm, 3),
        "speed_source":      speed_source,
    }
    return True, round(confidence, 2), meta


# ─────────────────────────────────────────────────────────────────────────────
# EVENT 4 — ERRATIC MOVEMENT
# ─────────────────────────────────────────────────────────────────────────────

def detect_erratic_movement(track_id: int) -> tuple[bool, float, dict]:
    """
    Detects chaotic body movement via Coefficient of Variation (CV).
    CV = std / mean of normalized frame-to-frame displacements.
    High CV + sufficient mean movement = erratic behaviour.
    """
    if track_id not in motion_history:
        return False, 0.0, {}

    history = list(motion_history[track_id])
    if len(history) < 6:
        return False, 0.0, {}

    deltas = []
    for i in range(1, len(history)):
        dx = history[i][1] - history[i-1][1]
        dy = history[i][2] - history[i-1][2]
        avg_bbox_h = (history[i][3] + history[i-1][3]) / 2.0
        if avg_bbox_h > 0:
            deltas.append(np.sqrt(dx**2 + dy**2) / avg_bbox_h)

    if len(deltas) < 5:
        return False, 0.0, {}

    mean_delta = float(np.mean(deltas))
    std_delta  = float(np.std(deltas))

    if mean_delta < CFG["ERRATIC_MIN_DELTA_NORM"]:
        return False, 0.0, {}

    cv = std_delta / (mean_delta + 1e-6)
    if cv < CFG["ERRATIC_CV_THRESHOLD"]:
        return False, 0.0, {}

    confidence = min(1.0, (cv - CFG["ERRATIC_CV_THRESHOLD"]) * 2 + 0.4)
    meta = {
        "mean_delta_norm":          round(mean_delta, 4),
        "std_delta_norm":           round(std_delta,  4),
        "coefficient_of_variation": round(cv, 2),
    }
    return True, round(confidence, 2), meta


# ─────────────────────────────────────────────────────────────────────────────
# EVENT 5 — CROUCHING
# ─────────────────────────────────────────────────────────────────────────────

def detect_crouching(
    keypoints: np.ndarray,
    bbox: list[float],
) -> tuple[bool, float, dict]:
    x1, y1, x2, y2 = bbox
    box_w = x2 - x1
    box_h = y2 - y1

    if box_h < 1:
        return False, 0.0, {}

    if box_w / box_h > 1.2:
        return False, 0.0, {}

    nose_x, nose_y, nose_c     = kp(keypoints, 0)
    l_hip_x, l_hip_y, l_hip_c = kp(keypoints, 11)
    r_hip_x, r_hip_y, r_hip_c = kp(keypoints, 12)

    hip_ys = [y for y, c in [(l_hip_y, l_hip_c), (r_hip_y, r_hip_c)]
              if c >= CFG["MIN_KP_CONFIDENCE"]]

    if nose_c < CFG["MIN_KP_CONFIDENCE"] or not hip_ys:
        return False, 0.0, {}

    avg_hip_y          = float(np.mean(hip_ys))
    vertical_gap_ratio = (avg_hip_y - nose_y) / box_h

    if vertical_gap_ratio >= CFG["CROUCH_RATIO_THRESHOLD"]:
        return False, 0.0, {}

    confidence = max(0.4, min(1.0, 1.0 - (vertical_gap_ratio / CFG["CROUCH_RATIO_THRESHOLD"])))
    meta = {
        "vertical_gap_ratio": round(float(vertical_gap_ratio), 3),
        "avg_hip_y":          round(avg_hip_y, 1),
        "nose_y":             round(float(nose_y), 1),
    }
    return True, round(confidence, 2), meta


# ─────────────────────────────────────────────────────────────────────────────
# SEVERITY MAPPER
# ─────────────────────────────────────────────────────────────────────────────

SEVERITY_MAP = [
    ("critical", ["FALLEN", "AGGRESSION"]),
    ("high",     ["LYING_DOWN", "CROUCHING"]),
    ("medium",   ["ERRATIC"]),
    ("low",      []),
]

def classify_severity(events: list[str]) -> str:
    if not events:
        return "none"
    for severity, triggers in SEVERITY_MAP:
        if any(trigger in events for trigger in triggers):
            return severity
    return "low"


# ─────────────────────────────────────────────────────────────────────────────
# MASTER RUNNER
# ─────────────────────────────────────────────────────────────────────────────

def run_all_classifiers(
    keypoints: np.ndarray,
    bbox: list[float],
    track_id: int,
    frame_w: int,
    frame_h: int,
    custom_zones: list[dict] | None = None,
    camera_angle: str = "horizontal",
) -> dict:
    """
    Runs every classifier for a single detected person.
    Call update_motion_history() BEFORE this every frame.

    camera_angle: "horizontal" = wall/eye-level mount
                  "topdown"    = ceiling ~90° mount
    """
    x1, y1, x2, y2 = bbox
    box_h = y2 - y1

    if box_h < CFG["MIN_BBOX_HEIGHT_PX"]:
        return {"events": [], "severity": "none", "details": {}, "skipped": "too_small"}

    events  = []
    details = {}

    fallen, conf, meta = detect_fallen(keypoints, bbox, camera_angle)
    if fallen:
        events.append("FALLEN")
        details["FALLEN"] = {"confidence": conf, **meta}
    else:
        lying, conf, meta = detect_lying_down(keypoints, bbox, camera_angle)
        if lying:
            events.append("LYING_DOWN")
            details["LYING_DOWN"] = {"confidence": conf, **meta}

    aggression, conf, meta = detect_aggression(track_id, keypoints, bbox)
    if aggression:
        events.append("AGGRESSION")
        details["AGGRESSION"] = {"confidence": conf, **meta}

    erratic, conf, meta = detect_erratic_movement(track_id)
    if erratic:
        events.append("ERRATIC")
        details["ERRATIC"] = {"confidence": conf, **meta}

    crouching, conf, meta = detect_crouching(keypoints, bbox)
    if crouching:
        events.append("CROUCHING")
        details["CROUCHING"] = {"confidence": conf, **meta}

    severity = classify_severity(events)

    return {
        "events":   events,
        "severity": severity,
        "details":  details,
    }




