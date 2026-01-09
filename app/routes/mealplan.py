from fastapi import APIRouter

router = APIRouter()

@router.post("/generate")
async def generate_mealplan():
    return {"message": "Meal plan generation - to be implemented"}
