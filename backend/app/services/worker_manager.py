import asyncio
import threading
from dataclasses import dataclass

from detection.camera_worker import run_camera


@dataclass
class WorkerHandle:
    camera_id: int
    thread: threading.Thread
    stop_event: threading.Event


class WorkerManager:
    def __init__(self) -> None:
        self._workers: dict[int, WorkerHandle] = {}
        self._lock = asyncio.Lock()

    async def start_worker(self, camera_id: int, camera_url: str | None, camera_name: str) -> None:
        if not camera_url:
            return

        async with self._lock:
            if camera_id in self._workers:
                return

            stop_event = threading.Event()

            thread = threading.Thread(
                target=run_camera,
                kwargs={
                    "source": camera_url,
                    "camera_id": camera_id,
                    "camera_name": camera_name,
                    "show_preview": False,
                    "stop_event": stop_event,
                },
                daemon=True,
            )

            self._workers[camera_id] = WorkerHandle(
                camera_id=camera_id,
                thread=thread,
                stop_event=stop_event,
            )

            thread.start()
            print(f"[worker_manager] Started worker for camera {camera_id}")

    async def stop_worker(self, camera_id: int) -> None:
        async with self._lock:
            handle = self._workers.get(camera_id)
            if not handle:
                return

            handle.stop_event.set()
            handle.thread.join(timeout=5)
            self._workers.pop(camera_id, None)
            print(f"[worker_manager] Stopped worker for camera {camera_id}")

    async def restart_worker(self, camera_id: int, camera_url: str | None, camera_name: str) -> None:
        await self.stop_worker(camera_id)
        if camera_url:
            await self.start_worker(camera_id, camera_url, camera_name)

    async def shutdown(self) -> None:
        async with self._lock:
            workers = list(self._workers.values())
            self._workers.clear()

        for handle in workers:
            handle.stop_event.set()

        for handle in workers:
            handle.thread.join(timeout=5)

        print("[worker_manager] All workers shut down")