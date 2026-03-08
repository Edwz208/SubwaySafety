import cv2
import os
import time
import threading
from collections import deque
from datetime import datetime
from pathlib import Path

PRE_ALERT_SECONDS = 8
POST_ALERT_SECONDS = 5
BUFFER_FPS = 15
CLIPS_DIR = Path("Clips").resolve()

class ClipRecorder:
    def __init__(self, camera_id: str, fps: int = BUFFER_FPS):
        self.camera_id = camera_id
        self.fps = fps
        self._buffer = deque(maxlen=int(PRE_ALERT_SECONDS * fps))
        self._active = False
        self._lock = threading.Lock()

    def add_frame(self, frame):
        with self._lock:
            self._buffer.append((time.time(), frame.copy()))

    def trigger_clip(self, alert_event, severity, frame_w, frame_h):
        with self._lock:
            if self._active:
                print("[clip_recorder] Already recording, skipping")
                return None

            self._active = True
            pre_frames = [f.copy() for _, f in list(self._buffer)]

        CLIPS_DIR.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.camera_id}_{alert_event}_{severity}_{ts}.mp4"
        filepath = CLIPS_DIR / filename

        print(f"[clip_recorder] Starting: {filename}")
        print(f"[clip_recorder] Path:     {filepath}")
        print(f"[clip_recorder] Pre-frames buffered: {len(pre_frames)}")

        thread = threading.Thread(
            target=self._record,
            args=(filepath, pre_frames, frame_w, frame_h),
            daemon=True,
        )
        thread.start()
        return filename

    def _record(self, filepath: Path, pre_frames, frame_w, frame_h):
        writer = None
        try:
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(filepath), fourcc, self.fps, (frame_w, frame_h))

            if not writer.isOpened():
                print(f"[clip_recorder] VideoWriter failed to open: {filepath}")
                return

            for frame in pre_frames:
                writer.write(cv2.resize(frame, (frame_w, frame_h)))

            end_time = time.time() + POST_ALERT_SECONDS
            last_frame_ts = 0.0
            post_count = 0

            while time.time() < end_time:
                frame_to_write = None

                with self._lock:
                    if self._buffer:
                        ts, frame = self._buffer[-1]
                        if ts > last_frame_ts:
                            frame_to_write = frame.copy()
                            last_frame_ts = ts

                if frame_to_write is not None:
                    writer.write(cv2.resize(frame_to_write, (frame_w, frame_h)))
                    post_count += 1

                time.sleep(1.0 / self.fps)

            writer.release()
            writer = None

            if filepath.exists():
                size_kb = filepath.stat().st_size / 1024
                print(f"[clip_recorder] Saved: {filepath}")
                print(f"[clip_recorder] Size: {size_kb:.1f} KB | Frames: {len(pre_frames) + post_count}")
            else:
                print(f"[clip_recorder] File was not created: {filepath}")

        except Exception:
            import traceback
            traceback.print_exc()
        finally:
            if writer is not None:
                writer.release()
            with self._lock:
                self._active = False