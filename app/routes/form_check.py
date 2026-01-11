import base64
import numpy as np
import cv2
from typing import List, Optional
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Form
from app.dependencies import get_current_user_id
from app.models.mongodb import FormCheckDocument
from app.services.gemini import gemini_service
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize MediaPipe Pose configuration (with fallback for new API)
mp_pose = None
mp_drawing = None
mp_drawing_styles = None
MEDIAPIPE_AVAILABLE = False

try:
    import mediapipe as mp
    # Try the legacy solutions API first
    if hasattr(mp, 'solutions'):
        mp_pose = mp.solutions.pose
        mp_drawing = mp.solutions.drawing_utils
        mp_drawing_styles = mp.solutions.drawing_styles
        MEDIAPIPE_AVAILABLE = True
        logger.info("MediaPipe legacy solutions API loaded successfully")
    else:
        logger.warning("MediaPipe solutions API not available - skeleton overlay disabled")
except ImportError as e:
    logger.warning(f"MediaPipe not available: {e} - skeleton overlay disabled")

@router.post("/upload")
async def analyze_form(
    exercise: str = Form(...),
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id)
):
    """
    Analyze exercise form from uploaded image/video.
    Returns Gemini analysis + Image with Skeleton Overlay.
    """
    # Validate file type
    if not file.content_type.startswith(('image/', 'video/')):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image or video.")

    try:
        # Read file content
        content = await file.read()
        
        # Determine input for MediaPipe (Image or first frame of video)
        # For simplicity in V1, we treat everything as an image buffer or try to decode it
        nparr = np.frombuffer(content, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
             raise HTTPException(status_code=400, detail="Could not decode image.")

        # MEDIA PIPE: Process image to draw skeleton (if available)
        annotated_image = image.copy()
        
        # Run MediaPipe Pose if available
        if MEDIAPIPE_AVAILABLE and mp_pose is not None:
            try:
                with mp_pose.Pose(
                    static_image_mode=True,
                    model_complexity=1,
                    enable_segmentation=False,
                    min_detection_confidence=0.5
                ) as pose:
                    results = pose.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
                    
                    if results.pose_landmarks:
                        # Draw landmarks on the image
                        mp_drawing.draw_landmarks(
                            annotated_image,
                            results.pose_landmarks,
                            mp_pose.POSE_CONNECTIONS,
                            landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style()
                        )
            except Exception as e:
                logger.warning(f"MediaPipe pose detection failed: {e}")
        else:
            logger.info("Skeleton overlay skipped - MediaPipe not available")

        # Encode ANNOTATED image to base64 for frontend display
        _, buffer_annotated = cv2.imencode('.jpg', annotated_image)
        annotated_base64 = base64.b64encode(buffer_annotated).decode('utf-8')
        
        # Encode ORIGINAL image for Gemini (better quality without overlays)
        original_base64 = base64.b64encode(content).decode("utf-8")
        
        # Analyze with Gemini (using original image)
        analysis = await gemini_service.analyze_form_check(original_base64, exercise)
        
        if not analysis:
            # Fallback if Gemini fails (return skeletal data at least)
            analysis = {
                "form_score": 50,
                "alignment_feedback": "AI analysis unavailable, but skeleton detected.",
                "rom_feedback": "Check visual overlay.",
                "stability_feedback": "N/A",
                "corrections": ["Retry analysis later"],
                "tips": [],
                "next_step": "N/A"
            }
            
        # Create Result Record
        # We don't save the base64 image to DB to save space, assuming it's returned to UI
        form_check = FormCheckDocument(
            user_id=user_id,
            exercise_name=exercise,
            score=analysis.get("form_score", 0),
            alignment_feedback=analysis.get("alignment_feedback"),
            rom_feedback=analysis.get("rom_feedback"),
            stability_feedback=analysis.get("stability_feedback"),
            corrections=analysis.get("corrections", []),
            tips=" ".join(analysis.get("tips", [])),
            next_step=analysis.get("next_step"),
            analysis_raw=analysis
        )
        await form_check.insert()
        
        return {
            "id": str(form_check.uid),
            "form_score": form_check.score,
            "alignment_feedback": form_check.alignment_feedback,
            "rom_feedback": form_check.rom_feedback,
            "stability_feedback": form_check.stability_feedback,
            "corrections": form_check.corrections,
            "tips": analysis.get("tips", []),
            "next_step": form_check.next_step,
            "annotated_image": f"data:image/jpeg;base64,{annotated_base64}"  # Return the skeleton image
        }

    except Exception as e:
        logger.error(f"Form check upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
async def get_history(user_id: str = Depends(get_current_user_id)):
    """Get form check history."""
    checks = await FormCheckDocument.find(
        FormCheckDocument.user_id == user_id
    ).sort(-FormCheckDocument.created_at).limit(20).to_list()
    
    return [
        {
            "id": str(c.uid),
            "exercise": c.exercise_name,
            "score": c.score,
            "date": c.created_at,
            "alignment_feedback": c.alignment_feedback,
            "rom_feedback": c.rom_feedback,
            "corrections": c.corrections,
            "tips": c.tips
        } 
        for c in checks
    ]
