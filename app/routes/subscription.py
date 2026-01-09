from fastapi import APIRouter

router = APIRouter()

@router.post("/create")
async def create_subscription():
    return {"message": "Subscription creation - to be implemented"}
