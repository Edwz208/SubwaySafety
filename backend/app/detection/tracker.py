# detection/tracker.py
"""
Manages per-person motion history across frames.
YOLOv8's .track() assigns a stable track_id to each person —
we use that ID as the key to store their position over time.
"""

import time
import numpy as np
from collections import deque

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

HISTORY_WINDOW_SECONDS = 15   # how long to keep positions for
APPROX_FPS = 15               # estimated frame rate — sets deque max length

# ─────────────────────────────────────────────
# THE STORE
# Each entry: deque of (timestamp, cx, cy)
# ─────────────────────────────────────────────

_history: dict[int, deque] = {}


def update(track_id: int, cx: float, cy: float):
    """
    Call this every frame for every detected person, BEFORE running classifiers.
    Appends their current center position to their history deque.
    The deque is capped at maxlen so old entries fall off automatically.
    """
    max_len = int(HISTORY_WINDOW_SECONDS * APPROX_FPS)
    if track_id not in _history:
        _history[track_id] = deque(maxlen=max_len)
    _history[track_id].append((time.time(), cx, cy))


def get_history(track_id: int) -> list[tuple]:
    """
    Returns the full position history for a track_id as a plain list.
    Returns empty list if track_id has never been seen.
    """
    return list(_history.get(track_id, []))


def clear_stale(active_ids: list[int]):
    """
    Call this once per frame after processing all detections.
    Removes history for any person no longer visible in the frame.
    Prevents the dict from growing forever during long sessions.
    """
    stale_ids = [tid for tid in _history if tid not in active_ids]
    for tid in stale_ids:
        del _history[tid]


def reset():
    """Wipes all history. Useful between video uploads in simulation mode."""
    _history.clear()
