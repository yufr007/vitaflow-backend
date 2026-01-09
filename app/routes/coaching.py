from fastapi import APIRouter

router = APIRouter()

@router.get("/message")
async def get_coaching():
    return {"message": "Coaching message - to be implemented"}
