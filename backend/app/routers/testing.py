from fastapi import APIRouter, HTTPException, status, Depends
from services.gemini import analyze_video, generate_gemini_response
router = APIRouter()

@router.get("/test_gemini")
async def test_gemini():
    text = generate_gemini_response()
    return {"message": text}

@router.get("/test_gemini_video/{video_url}")
async def test_gemini_video(video_url: str):
    text = analyze_video(video_url)
    return {"message": text}