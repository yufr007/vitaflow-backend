from fastapi import APIRouter

router = APIRouter()

@router.post("/upload")
async def upload_formcheck():
    return {"message": "Form check upload - to be implemented"}
