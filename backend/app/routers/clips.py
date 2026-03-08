"""
routers/clips.py
Serves saved .mp4 clip files to the React frontend.
"""

import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/clips", tags=["Clips"])

CLIPS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "clips")


@router.get("/")
def list_clips():
    """Returns all saved clips, newest first."""
    if not os.path.exists(CLIPS_DIR):
        return {"clips": []}
    files = sorted(
        [f for f in os.listdir(CLIPS_DIR) if f.endswith(".mp4")],
        reverse=True,
    )
    return {"clips": files}


@router.get("/{filename}")
def get_clip(filename: str):
    """Streams a clip to the browser — use directly in a <video> src tag."""
    filename = os.path.basename(filename)  # strip any path traversal
    filepath = os.path.join(CLIPS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Clip not found")
    return FileResponse(path=filepath, media_type="video/mp4", filename=filename)


@router.delete("/{filename}")
def delete_clip(filename: str):
    filename = os.path.basename(filename)
    filepath = os.path.join(CLIPS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Clip not found")
    os.remove(filepath)
    return {"deleted": filename}
