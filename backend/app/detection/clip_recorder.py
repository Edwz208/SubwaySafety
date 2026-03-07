"""
detection/clip_recorder.py
"""

import cv2
import os
import time
import threading
from collections import deque
from datetime import datetime

PRE_ALERT_SECONDS  = 8
POST_ALERT_SECONDS = 5
BUFFER_FPS         = 15
CLIPS_DIR          = r"C:\Users\indom\OneDrive\Desktop\SubwaySafety\backend\clips"


class ClipRecorder:

    def __init__(self, camera_id: str, fps: int = BUFFER_FPS):
        self.camera_id = camera_id
        self.fps       = fps
        self._buffer   = deque(maxlen=int(PRE_ALERT_SECONDS * fps))
        self._active   = False
        self._lock     = threading.Lock()

    def add_frame(self, frame):
        with self._lock:
            self._buffer.append((time.time(), frame.copy()))

    def trigger_clip(self, alert_event, severity, frame_w, frame_h):
        if self._active:
            print(f"[clip_recorder] Already recording, skipping")
            return None

        os.makedirs(CLIPS_DIR, exist_ok=True)

        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.camera_id}_{alert_event}_{severity}_{ts}.avi"
        filepath = os.path.join(CLIPS_DIR, filename)

        with self._lock:
            pre_frames = [f.copy() for _, f in list(self._buffer)]

        print(f"[clip_recorder] Starting: {filename}")
        print(f"[clip_recorder] Path:     {filepath}")
        print(f"[clip_recorder] Pre-frames buffered: {len(pre_frames)}")

        thread = threading.Thread(
            target=self._record,
            args=(filepath, pre_frames, frame_w, frame_h),
            daemon=True,
        )
        self._active = True
        thread.start()
        return filename

    def _record(self, filepath, pre_frames, frame_w, frame_h):
        try:
            fourcc = cv2.VideoWriter_fourcc(*"XVID")
            writer = cv2.VideoWriter(filepath, fourcc, self.fps, (frame_w, frame_h))

            if not writer.isOpened():
                print(f"[clip_recorder] ❌ VideoWriter failed to open: {filepath}")
                return

            # Write pre-alert frames
            for frame in pre_frames:
                writer.write(cv2.resize(frame, (frame_w, frame_h)))

            print(f"[clip_recorder] Pre-alert written: {len(pre_frames)} frames")

            # Write post-alert frames
            end_time      = time.time() + POST_ALERT_SECONDS
            last_frame_ts = 0.0
            post_count    = 0

            while time.time() < end_time:
                with self._lock:
                    if self._buffer:
                        ts, frame = self._buffer[-1]
                        if ts > last_frame_ts:
                            writer.write(cv2.resize(frame.copy(), (frame_w, frame_h)))
                            last_frame_ts = ts
                            post_count   += 1
                time.sleep(1.0 / self.fps)

            writer.release()

            size_kb = os.path.getsize(filepath) / 1024
            print(f"[clip_recorder] ✅ Saved: {filepath}")
            print(f"[clip_recorder]    Size: {size_kb:.1f} KB | Frames: {len(pre_frames) + post_count}")

        except Exception as e:
            import traceback
            print(f"[clip_recorder] ❌ Failed:")
            traceback.print_exc()
        finally:
            self._active = False


# ── Registry ──────────────────────────────────────────────────────────────────

_recorders: dict[str, ClipRecorder] = {}

def get_recorder(camera_id: str, fps: int = BUFFER_FPS) -> ClipRecorder:
    if camera_id not in _recorders:
        _recorders[camera_id] = ClipRecorder(camera_id, fps)
    return _recorders[camera_id]
