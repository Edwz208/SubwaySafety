# detection/annotator.py
"""
Draws bounding boxes, skeleton keypoints, event labels,
and severity indicators onto a frame (numpy array).
Returns the annotated frame — does not modify the original.
"""

import cv2
import numpy as np

# ─────────────────────────────────────────────
# COLORS (BGR format — OpenCV uses BGR not RGB)
# ─────────────────────────────────────────────

SEVERITY_COLOR = {
    "critical": (0,   0,   255),  # red
    "high":     (0,   100, 255),  # orange
    "medium":   (0,   200, 255),  # yellow
    "low":      (0,   255, 100),  # green
    "none":     (80,  80,  80),   # grey — drawn faintly
}

# Skeleton connections — pairs of keypoint indices to draw lines between
# This draws the "stick figure" connecting body parts
SKELETON = [
    (0, 1),   # nose → left eye
    (0, 2),   # nose → right eye
    (1, 3),   # left eye → left ear
    (2, 4),   # right eye → right ear
    (5, 6),   # left shoulder → right shoulder
    (5, 7),   # left shoulder → left elbow
    (7, 9),   # left elbow → left wrist
    (6, 8),   # right shoulder → right elbow
    (8, 10),  # right elbow → right wrist
    (5, 11),  # left shoulder → left hip
    (6, 12),  # right shoulder → right hip
    (11, 12), # left hip → right hip
    (11, 13), # left hip → left knee
    (13, 15), # left knee → left ankle
    (12, 14), # right hip → right knee
    (14, 16), # right knee → right ankle
]


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _get_kp(keypoints: np.ndarray, idx: int) -> tuple[int, int, float]:
    """Returns (x, y, confidence) as integers for drawing. Returns (0,0,0) if missing."""
    if keypoints is None or len(keypoints) <= idx:
        return 0, 0, 0.0
    x, y, conf = keypoints[idx]
    return int(x), int(y), float(conf)


def _draw_label(
    frame: np.ndarray,
    text: str,
    x: int,
    y: int,
    color: tuple,
    font_scale: float = 0.5,
):
    """
    Draws a filled rectangle behind text so it's always readable
    regardless of what's in the background.
    """
    font = cv2.FONT_HERSHEY_SIMPLEX
    thickness = 1
    (text_w, text_h), baseline = cv2.getTextSize(text, font, font_scale, thickness)

    # Background rectangle
    cv2.rectangle(
        frame,
        (x, y - text_h - 6),
        (x + text_w + 4, y + baseline),
        color,
        cv2.FILLED,
    )
    # Text in black on top of the colored background
    cv2.putText(frame, text, (x + 2, y - 2), font, font_scale, (0, 0, 0), thickness, cv2.LINE_AA)


# ─────────────────────────────────────────────
# MAIN DRAWING FUNCTIONS
# ─────────────────────────────────────────────

def draw_bounding_box(
    frame: np.ndarray,
    bbox: list[float],
    severity: str,
    track_id: int,
):
    """
    Draws the bounding box rectangle around a detected person.
    Box thickness and color reflect severity.
    Track ID is shown in the top-left corner of the box.
    """
    color = SEVERITY_COLOR.get(severity, SEVERITY_COLOR["none"])
    thickness = 3 if severity in ("critical", "high") else 2

    x1, y1, x2, y2 = [int(v) for v in bbox]
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)

    # Track ID label (small, top-left corner of box)
    _draw_label(frame, f"ID:{track_id}", x1, y1, color, font_scale=0.4)


def draw_skeleton(frame: np.ndarray, keypoints: np.ndarray, severity: str):
    """
    Draws the stick-figure skeleton by connecting keypoint pairs.
    Only draws a connection if BOTH endpoints have sufficient confidence.
    Dot size and line thickness reflect severity.
    """
    MIN_CONF = 0.3
    color = SEVERITY_COLOR.get(severity, SEVERITY_COLOR["none"])
    line_thickness = 2 if severity in ("critical", "high") else 1
    dot_radius = 4 if severity in ("critical", "high") else 3

    # Draw skeleton lines
    for idx_a, idx_b in SKELETON:
        x_a, y_a, conf_a = _get_kp(keypoints, idx_a)
        x_b, y_b, conf_b = _get_kp(keypoints, idx_b)

        # Skip this connection if either endpoint is low confidence
        if conf_a < MIN_CONF or conf_b < MIN_CONF:
            continue

        cv2.line(frame, (x_a, y_a), (x_b, y_b), color, line_thickness, cv2.LINE_AA)

    # Draw dots on each keypoint
    for idx in range(17):
        x, y, conf = _get_kp(keypoints, idx)
        if conf >= MIN_CONF:
            cv2.circle(frame, (x, y), dot_radius, color, cv2.FILLED)


def draw_event_labels(
    frame: np.ndarray,
    bbox: list[float],
    events: list[str],
    severity: str,
):
    """
    Draws detected event names as stacked labels below the bounding box.
    Each event gets its own line so they don't overlap.
    """
    if not events:
        return

    color = SEVERITY_COLOR.get(severity, SEVERITY_COLOR["none"])
    x1, y1, x2, y2 = [int(v) for v in bbox]

    # Stack labels downward from the bottom of the bounding box
    for i, event in enumerate(events):
        label_y = y2 + 18 + (i * 20)  # 20px gap between each label
        _draw_label(frame, event, x1, label_y, color, font_scale=0.45)


def draw_severity_indicator(
    frame: np.ndarray,
    bbox: list[float],
    severity: str,
):
    """
    For critical and high severity, draws an extra visual indicator
    so the operator's eye is immediately drawn to it:
    — critical: pulsing circle + severity badge in top-right of frame
    — high: just the severity badge
    """
    color = SEVERITY_COLOR.get(severity, SEVERITY_COLOR["none"])
    x1, y1, x2, y2 = [int(v) for v in bbox]
    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2

    if severity == "critical":
        # Outer ring — draws attention
        cv2.circle(frame, (cx, cy), 18, color, 2, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), 10, color, cv2.FILLED)

        # "CRITICAL" badge in top-right corner of the whole frame
        frame_h, frame_w = frame.shape[:2]
        _draw_label(frame, "!! CRITICAL ALERT !!", frame_w - 220, 30, color, font_scale=0.6)

    elif severity == "high":
        cv2.circle(frame, (cx, cy), 12, color, 2, cv2.LINE_AA)


# ─────────────────────────────────────────────
# MASTER ANNOTATE FUNCTION
# ─────────────────────────────────────────────

def annotate_frame(
    frame: np.ndarray,
    detections: list[dict],
    draw_skeletons: bool = True,
) -> np.ndarray:
    """
    Draws all detections onto a copy of the frame and returns it.
    Does NOT modify the original frame.

    Each detection dict should be the output of run_all_classifiers() plus bbox/track_id:
    {
        "track_id":  3,
        "bbox":      [x1, y1, x2, y2],
        "keypoints": np.ndarray shape (17, 3),
        "events":    ["FALLEN", "NEAR_TRACKS"],
        "severity":  "critical",
    }

    draw_skeletons: set False to skip skeleton drawing for performance
    """
    annotated = frame.copy()

    for det in detections:
        severity  = det.get("severity", "none")
        bbox      = det["bbox"]
        track_id  = det["track_id"]
        events    = det.get("events", [])
        keypoints = det.get("keypoints")  # may be None if not available

        # Always draw the bounding box
        draw_bounding_box(annotated, bbox, severity, track_id)

        # Draw skeleton if keypoints are available and drawing is enabled
        if draw_skeletons and keypoints is not None:
            draw_skeleton(annotated, keypoints, severity)

        # Draw event name labels below the box
        draw_event_labels(annotated, bbox, events, severity)

        # Draw severity indicator (circle, badge) for serious events
        if severity in ("critical", "high"):
            draw_severity_indicator(annotated, bbox, severity)

    return annotated
