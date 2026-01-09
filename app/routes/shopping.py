from fastapi import APIRouter

router = APIRouter()

@router.post("/generate")
async def generate_shopping():
    return {"message": "Shopping list generation - to be implemented"}
