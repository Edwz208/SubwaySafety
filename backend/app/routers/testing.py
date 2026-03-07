from fastapi import APIRouter, HTTPException, status, Depends
from services.gemini import generate_gemini_response
router = APIRouter()

@router.get("/test_gemini")
async def test_gemini():
    text = generate_gemini_response()
    return {"message": text}