from fastapi import APIRouter

router = APIRouter()

@router.post("/generate")
async def generate_workout():
    return {"message": "Workout generation - to be implemented"}
