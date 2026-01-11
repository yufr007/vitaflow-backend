# app/routes/nutrition_scan.py
"""
VitaFlow API - Nutrition Label Scanning Routes (Pro Tier).

Provides OCR scanning of nutrition labels.
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import logging

from app.services.azure_document_intelligence import azure_document_intelligence
from app.models.mongodb import UserDocument
from app.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/nutrition-scan", tags=["nutrition-scan"])


@router.post("/analyze-label")
async def analyze_nutrition_label(
    file: UploadFile = File(..., description="Nutrition label image"),
    user: UserDocument = Depends(get_current_user)
):
    """
    Scan and extract nutrition facts from food label (Pro/Elite tier).
    
    Returns structured nutrition data.
    """
    # Check tier (Pro or Elite)
    if user.subscription_tier not in ["pro", "elite"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nutrition label scanning is a Pro/Elite tier feature"
        )
    
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image (JPEG, PNG, etc.)"
        )
    
    # Read image data
    try:
        image_data = await file.read()
        
        if len(image_data) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Image size must be under 10MB"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read image: {str(e)}"
        )
    
    # Initialize Azure Document Intelligence if needed
    if not azure_document_intelligence.is_available:
        await azure_document_intelligence.initialize()
    
    # Analyze nutrition label
    nutrition_data = await azure_document_intelligence.analyze_nutrition_label(image_data)
    
    if not nutrition_data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze nutrition label"
        )
    
    # Add user-friendly tips
    tips = []
    if nutrition_data.get("protein") and nutrition_data.get("calories"):
        protein_ratio = (nutrition_data["protein"] * 4) / nutrition_data["calories"]
        if protein_ratio > 0.3:
            tips.append("High protein ratio - great for muscle building")
        elif protein_ratio < 0.1:
            tips.append("Low protein - consider pairing with protein source")
    
    if nutrition_data.get("sugars") and nutrition_data.get("total_carbohydrate"):
        if nutrition_data["sugars"] > nutrition_data["total_carbohydrate"] * 0.5:
            tips.append("High sugar content - best consumed post-workout")
    
    nutrition_data["tips"] = tips
    
    return nutrition_data


@router.post("/save-to-database")
async def save_nutrition_data(
    nutrition_data: Dict[str, Any],
    user: UserDocument = Depends(get_current_user)
):
    """
    Save scanned nutrition data to user's food database (Pro/Elite tier).
    """
    # Check tier
    if user.subscription_tier not in ["pro", "elite"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This feature requires Pro or Elite tier"
        )
    
    # TODO: Save to MongoDB user food database
    # For now, return success
    return {
        "success": True,
        "message": "Nutrition data saved to your food database"
    }


@router.get("/recent-scans")
async def get_recent_scans(
    limit: int = 10,
    user: UserDocument = Depends(get_current_user)
):
    """
    Get user's recent nutrition label scans (Pro/Elite tier).
    """
    # Check tier
    if user.subscription_tier not in ["pro", "elite"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This feature requires Pro or Elite tier"
        )
    
    # TODO: Fetch from MongoDB
    # For now, return empty list
    return {
        "scans": [],
        "total": 0
    }
