from fastapi import APIRouter, HTTPException, status, Depends

router = APIRouter()

@router.get("/login")
async def login():
    return {"message": "Login successful"}