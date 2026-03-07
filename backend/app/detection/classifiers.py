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
    "LYING_ASPECT_RATIO":       1.6,   # bbox width/height ratio threshold
    "LYING_KP_Y_TOLERANCE":     0.5,   # keypoint Y-spread as fraction of bbox height

    # Stationary (all thresholds are fractions of bbox height — scale invariant)
    "STATIONARY_SECONDS":       10,
    "STATIONARY_NORM_THRESHOLD": 0.03, # movement < 3% of bbox height = not moving

    # History
    "HISTORY_WINDOW_SECONDS":   15,

    # Erratic movement (normalized — scale invariant)
    "ERRATIC_MIN_DELTA_NORM":   0.02,  # mean movement must exceed 2% of bbox height
    "ERRATIC_CV_THRESHOLD":     0.65,  # coefficient of variation threshold

    # Aggressive movement — wrist speed (normalized)
    "AGGRESSION_WRIST_SPEED":   0.25,  # wrist must move >25% of bbox height per frame
    "AGGRESSION_MIN_FRAMES":    2,     # must sustain for at least N frames

    # Crouching
    "CROUCH_RATIO_THRESHOLD":   0.35,

    # Minimum bbox height to bother classifying (filters far-away noise)
    "MIN_BBOX_HEIGHT_PX":       80,

    # Keypoint confidence
    "MIN_KP_CONFIDENCE":        0.3,
}


# ─────────────────────────────────────────────────────────────────────────────
# MOTION HISTORY STORE
# Each entry: (timestamp, cx, cy, bbox_h, wrist_lx, wrist_ly, wrist_rx, wrist_ry)
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
    Call this EVERY FRAME for every tracked person, BEFORE running classifiers.
    Stores body center + wrist positions normalized by bbox height.
    """
    max_len = int(CFG["HISTORY_WINDOW_SECONDS"] * 15)
    if track_id not in motion_history:
        motion_history[track_id] = deque(maxlen=max_len)

    # Pull wrist keypoints (indices 9=left_wrist, 10=right_wrist)
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


# ─────────────────────────────────────────────────────────────────────────────
# EVENT 1 — LYING DOWN
# ─────────────────────────────────────────────────────────────────────────────

def detect_lying_down(
    keypoints: np.ndarray,
    bbox: list[float],
    camera_angle: str = "horizontal",  # "horizontal" or "topdown"
) -> tuple[bool, float, dict]:
    """
    Detects horizontal body position.

    For horizontal cameras: uses bbox aspect ratio + keypoint Y-spread.
    For top-down cameras: aspect ratio is useless (standing looks square too),
    so we rely purely on keypoint spread and shoulder-hip distance.

    Signal A — bbox aspect ratio (horizontal cameras only):
      Standing = tall bbox (height > width). Lying = wide bbox (width > height).

    Signal B — keypoint Y-spread:
      Standing = large vertical spread (nose high, ankles low).
      Lying = all keypoints at roughly same Y → small spread.

    Signal C — shoulder-to-hip distance (top-down):
      Top-down view: standing person has shoulders directly above hips.
      Lying person: shoulders and hips are side by side (similar Y, spread in X).
    """
    x1, y1, x2, y2 = bbox
    box_w = x2 - x1
    box_h = y2 - y1

    if box_h < 1:
        return False, 0.0, {}

    aspect_ratio = box_w / max(box_h, 1)

    # ── Signal A: aspect ratio (skip for top-down) ──
    signal_a = False
    if camera_angle == "horizontal":
        signal_a = aspect_ratio >= CFG["LYING_ASPECT_RATIO"]

    # ── Signal B: keypoint Y spread ──
    body_ys = visible_ys(keypoints, [5, 6, 11, 12, 15, 16])
    signal_b = False
    required_kps = 5 if not signal_a else 3  # stricter when aspect ratio didn't fire
    if len(body_ys) >= required_kps:
        y_spread = max(body_ys) - min(body_ys)
        signal_b = y_spread < (box_h * CFG["LYING_KP_Y_TOLERANCE"])

    # ── Signal C: shoulder/hip lateral spread (top-down helper) ──
    signal_c = False
    if camera_angle == "topdown":
        shoulder_xs = visible_xs(keypoints, [5, 6])
        hip_xs = visible_xs(keypoints, [11, 12])
        shoulder_ys = visible_ys(keypoints, [5, 6])
        hip_ys = visible_ys(keypoints, [11, 12])
        if shoulder_xs and hip_xs and shoulder_ys and hip_ys:
            # When lying top-down: shoulders and hips are at very different X,
            # but similar Y. Measure X spread vs Y gap.
            all_xs = shoulder_xs + hip_xs
            all_ys = shoulder_ys + hip_ys
            x_spread = max(all_xs) - min(all_xs)
            y_gap = abs(np.mean(shoulder_ys) - np.mean(hip_ys))
            # Lying: wide X spread, small Y gap between shoulders and hips
            signal_c = x_spread > box_w * 0.5 and y_gap < box_h * 0.3

    triggered = signal_a or signal_b or signal_c
    if not triggered:
        return False, 0.0, {}

    signal_count = sum([signal_a, signal_b, signal_c])
    if signal_count >= 2:
        confidence = min(1.0, 0.5 + signal_count * 0.2 + (aspect_ratio / 5.0 if signal_a else 0))
    else:
        confidence = 0.45

    meta = {
        "aspect_ratio": round(aspect_ratio, 2),
        "signal_aspect_ratio": signal_a,
        "signal_keypoint_spread": signal_b,
        "signal_topdown": signal_c,
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
    """
    Fallen = lying down AND head near ground level.
    Builds on detect_lying_down — requires it to pass first.
    """
    is_lying, lying_conf, lying_meta = detect_lying_down(keypoints, bbox, camera_angle)

    if not is_lying:
        return False, 0.0, {}

    x1, y1, x2, y2 = bbox
    box_h = y2 - y1
    nose_x, nose_y, nose_conf = kp(keypoints, 0)

    if nose_conf >= CFG["MIN_KP_CONFIDENCE"] and box_h > 0:
        relative_nose_y = (nose_y - y1) / box_h
        head_near_ground = relative_nose_y > 0.4
        if head_near_ground:
            # Reduced multiplier — was 1.25, amplified borderline cases too aggressively
            confidence = min(1.0, lying_conf * 1.1)
            meta = {**lying_meta, "relative_nose_y": round(relative_nose_y, 2), "head_near_ground": True}
            return True, round(confidence, 2), meta

    meta = {**lying_meta, "head_near_ground": "unknown"}
    return True, round(lying_conf * 0.85, 2), meta


# ─────────────────────────────────────────────────────────────────────────────
# EVENT 3 — AGGRESSIVE MOVEMENT (punching, striking)
# ─────────────────────────────────────────────────────────────────────────────

def detect_aggression(track_id: int) -> tuple[bool, float, dict]:
    """
    Detects punching/striking via wrist speed spikes.
    
    A punch = one explosive wrist movement (1-2 frames fast, then stops or retracts).
    The old consecutive-frames approach reset the counter on deceleration,
    so real punches never triggered.
    
    New approach:
    - Track the PEAK wrist speed across recent frames (sliding window)
    - A single frame exceeding SPIKE threshold = strike detected
    - Direction reversal bonus: if wrist reverses direction after spike = more confident
    - Separate lower threshold for sustained shoving/pushing
    """
    if track_id not in motion_history:
        return False, 0.0, {}

    history = list(motion_history[track_id])
    # Need enough frames for a meaningful window
    if len(history) < 3:
        return False, 0.0, {}

    SPIKE_THRESHOLD     = 0.35  # single-frame peak — fast punch
    SUSTAINED_THRESHOLD = 0.20  # lower bar if sustained 2+ frames (shoving)
    WINDOW              = 8     # only look at last 8 frames (~0.25s at 30fps)

    recent = history[-WINDOW:]

    max_speed_l = 0.0
    max_speed_r = 0.0
    fast_frames_l = 0
    fast_frames_r = 0

    # Track velocity vectors for direction reversal detection
    prev_vel_l = None
    prev_vel_r = None
    reversal_detected = False

    for i in range(1, len(recent)):
        bbox_h = recent[i][3]

        # ── Left wrist ──
        if recent[i][4] is not None and recent[i-1][4] is not None:
            dlx = recent[i][4] - recent[i-1][4]
            dly = recent[i][5] - recent[i-1][5]
            speed_l = np.sqrt(dlx**2 + dly**2) / bbox_h
            max_speed_l = max(max_speed_l, speed_l)
            if speed_l > SUSTAINED_THRESHOLD:
                fast_frames_l += 1
            # Check for direction reversal (punch then retract)
            if prev_vel_l is not None and speed_l > 0.05:
                dot = (dlx * prev_vel_l[0] + dly * prev_vel_l[1])
                if dot < 0:  # negative dot = opposite direction = reversal
                    reversal_detected = True
            if speed_l > 0.05:
                prev_vel_l = (dlx, dly)

        # ── Right wrist ──
        if recent[i][6] is not None and recent[i-1][6] is not None:
            drx = recent[i][6] - recent[i-1][6]
            dry = recent[i][7] - recent[i-1][7]
            speed_r = np.sqrt(drx**2 + dry**2) / bbox_h
            max_speed_r = max(max_speed_r, speed_r)
            if speed_r > SUSTAINED_THRESHOLD:
                fast_frames_r += 1
            if prev_vel_r is not None and speed_r > 0.05:
                dot = (drx * prev_vel_r[0] + dry * prev_vel_r[1])
                if dot < 0:
                    reversal_detected = True
            if speed_r > 0.05:
                prev_vel_r = (drx, dry)

    max_speed = max(max_speed_l, max_speed_r)

    # ── Decision logic ──
    spike_detected     = max_speed >= SPIKE_THRESHOLD
    sustained_detected = fast_frames_l >= 2 or fast_frames_r >= 2

    if not spike_detected and not sustained_detected:
        return False, 0.0, {}

    # Confidence: spike alone = base confidence, reversal = more confident
    if spike_detected:
        confidence = min(1.0, 0.5 + (max_speed - SPIKE_THRESHOLD) * 1.5)
        if reversal_detected:
            confidence = min(1.0, confidence + 0.2)  # punch + retract = very confident
    else:
        confidence = min(0.65, 0.35 + fast_frames_l * 0.05 + fast_frames_r * 0.05)

    meta = {
        "max_wrist_speed_norm": round(float(max_speed), 3),
        "spike_detected": spike_detected,
        "reversal_detected": reversal_detected,
        "fast_frames_left": fast_frames_l,
        "fast_frames_right": fast_frames_r,
    }
    return True, round(confidence, 2), meta


# ─────────────────────────────────────────────────────────────────────────────
# EVENT 4 — ERRATIC MOVEMENT
# ─────────────────────────────────────────────────────────────────────────────

def detect_erratic_movement(track_id: int) -> tuple[bool, float, dict]:
    """
    Detects chaotic body movement using Coefficient of Variation (CV).

    CV = std / mean of frame-to-frame body center displacements.
    High CV = inconsistent movement = erratic behaviour.

    All distances are normalized by bbox height — scale invariant.
    Previously this used raw pixels, which broke at distance.

    Also previously: avg_bbox_h was referenced but never defined — crash bug.
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
        # BUG FIX: normalize by bbox_h (index 3) — was using undefined avg_bbox_h
        avg_bbox_h = (history[i][3] + history[i-1][3]) / 2.0
        if avg_bbox_h > 0:
            deltas.append(np.sqrt(dx**2 + dy**2) / avg_bbox_h)

    if len(deltas) < 5:
        return False, 0.0, {}

    mean_delta = float(np.mean(deltas))
    std_delta = float(np.std(deltas))

    # BUG FIX: threshold is now normalized (0.02 = 2% of bbox height per frame)
    if mean_delta < CFG["ERRATIC_MIN_DELTA_NORM"]:
        return False, 0.0, {}

    cv = std_delta / (mean_delta + 1e-6)
    is_erratic = cv >= CFG["ERRATIC_CV_THRESHOLD"]

    if not is_erratic:
        return False, 0.0, {}

    confidence = min(1.0, (cv - CFG["ERRATIC_CV_THRESHOLD"]) * 2 + 0.4)
    meta = {
        "mean_delta_norm": round(mean_delta, 4),
        "std_delta_norm": round(std_delta, 4),
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
    """
    Detects crouching by measuring vertical gap between nose and hips
    relative to bbox height.

    Standing: large gap (head far above hips).
    Crouching: small gap (head drops toward hip level).

    Guards against lying-down false positives via aspect ratio check.
    """
    x1, y1, x2, y2 = bbox
    box_w = x2 - x1
    box_h = y2 - y1

    if box_h < 1:
        return False, 0.0, {}

    # Lying down guard
    if box_w / box_h > 1.2:
        return False, 0.0, {}

    nose_x, nose_y, nose_c     = kp(keypoints, 0)
    l_hip_x, l_hip_y, l_hip_c = kp(keypoints, 11)
    r_hip_x, r_hip_y, r_hip_c = kp(keypoints, 12)

    hip_ys = [y for y, c in [(l_hip_y, l_hip_c), (r_hip_y, r_hip_c)]
              if c >= CFG["MIN_KP_CONFIDENCE"]]

    if nose_c < CFG["MIN_KP_CONFIDENCE"] or not hip_ys:
        return False, 0.0, {}

    avg_hip_y = float(np.mean(hip_ys))
    vertical_gap_ratio = (avg_hip_y - nose_y) / box_h

    if vertical_gap_ratio >= CFG["CROUCH_RATIO_THRESHOLD"]:
        return False, 0.0, {}

    confidence = max(0.4, min(1.0, 1.0 - (vertical_gap_ratio / CFG["CROUCH_RATIO_THRESHOLD"])))
    meta = {
        "vertical_gap_ratio": round(float(vertical_gap_ratio), 3),
        "avg_hip_y": round(avg_hip_y, 1),
        "nose_y": round(float(nose_y), 1),
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
    camera_angle: str = "horizontal",  # "horizontal" or "topdown"
) -> dict:
    """
    Runs every classifier for a single detected person.

    IMPORTANT: Call update_motion_history() BEFORE calling this function
    every frame — otherwise erratic/aggression detection has no data.

    Args:
        camera_angle: "horizontal" for wall/eye-level mount,
                      "topdown" for ceiling ~90° mount.
    """
    x1, y1, x2, y2 = bbox
    box_h = y2 - y1

    # Skip people who are too small — unreliable keypoints at distance
    if box_h < CFG["MIN_BBOX_HEIGHT_PX"]:
        return {"events": [], "severity": "none", "details": {}, "skipped": "too_small"}

    events = []
    details = {}

    # ── Fallen / Lying down ──────────────────────────────────
    fallen, conf, meta = detect_fallen(keypoints, bbox, camera_angle)
    if fallen:
        events.append("FALLEN")
        details["FALLEN"] = {"confidence": conf, **meta}
    else:
        lying, conf, meta = detect_lying_down(keypoints, bbox, camera_angle)
        if lying:
            events.append("LYING_DOWN")
            details["LYING_DOWN"] = {"confidence": conf, **meta}

    # ── Aggression (punching/striking — wrist speed) ─────────
    aggression, conf, meta = detect_aggression(track_id)
    if aggression:
        events.append("AGGRESSION")
        details["AGGRESSION"] = {"confidence": conf, **meta}

    # ── Erratic body movement ────────────────────────────────
    erratic, conf, meta = detect_erratic_movement(track_id)
    if erratic:
        events.append("ERRATIC")
        details["ERRATIC"] = {"confidence": conf, **meta}

    # ── Crouching ────────────────────────────────────────────
    crouching, conf, meta = detect_crouching(keypoints, bbox)
    if crouching:
        events.append("CROUCHING")
        details["CROUCHING"] = {"confidence": conf, **meta}

    severity = classify_severity(events)

    return {
        "events": events,
        "severity": severity,
        "details": details,
    }

