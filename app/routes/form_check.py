import base64
import numpy as np
import cv2
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Form
from app.dependencies import get_current_user_id
from app.middleware.auth import JWTBearer
from app.models.mongodb import FormCheckDocument
from app.services.gemini import gemini_service
from app.services.physionet_service import physionet_service
from app.services.form_check_pipeline import form_check_pipeline
import logging

# Add biomechanics integration to path
backend_root = Path(__file__).parent.parent.parent.parent / "vitaflow-backend"
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

# Import biomechanics module
try:
    from integrations.biomechanics import (
        MovementType, SkeletonFrame, SkeletonLandmark, 
        MovementSequence, FormAnalyzer
    )
    BIOMECHANICS_AVAILABLE = True
    logger.info("✓ Biomechanics integration loaded successfully")
except ImportError as e:
    BIOMECHANICS_AVAILABLE = False
    logger.warning(f"Biomechanics integration not available: {e}")

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

# Initialize FormAnalyzer (if biomechanics available)
form_analyzer = None
if BIOMECHANICS_AVAILABLE:
    try:
        form_analyzer = FormAnalyzer()
        logger.info("✓ FormAnalyzer initialized")
    except Exception as e:
        logger.error(f"Failed to initialize FormAnalyzer: {e}")
        BIOMECHANICS_AVAILABLE = False


# Exercise name to MovementType mapping
EXERCISE_TO_MOVEMENT_TYPE = {
    "squat": MovementType.SQUAT,
    "deadlift": MovementType.SQUAT,  # Similar mechanics
    "running": MovementType.RUNNING,
    "gait": MovementType.GAIT,
    "walk": MovementType.GAIT,
    "lunge": MovementType.SQUAT,  # Similar lower body pattern
}


def mediapipe_to_skeleton_frame(mp_results, frame_num: int = 0) -> Optional['SkeletonFrame']:
    """
    Convert MediaPipe Pose results to VitaFlow SkeletonFrame.
    
    This bridges the gap between MediaPipe's 33-landmark model and
    the biomechanics engine's joint-based analysis.
    """
    if not mp_results or not mp_results.pose_landmarks:
        return None
    
    landmarks = {}
    
    # MediaPipe landmark indices → VitaFlow joint names
    # Using MediaPipe's 33-point pose model
    MP_LANDMARK_MAP = {
        11: 'left_shoulder',
        12: 'right_shoulder',
        13: 'left_elbow',
        14: 'right_elbow',
        15: 'left_wrist',
        16: 'right_wrist',
        23: 'left_hip',
        24: 'right_hip',
        25: 'left_knee',
        26: 'right_knee',
        27: 'left_ankle',
        28: 'right_ankle',
        29: 'left_heel',
        30: 'right_heel',
        31: 'left_foot_index',
        32: 'right_foot_index',
    }
    
    for mp_idx, joint_name in MP_LANDMARK_MAP.items():
        lm = mp_results.pose_landmarks.landmark[mp_idx]
        landmarks[joint_name] = SkeletonLandmark(
            name=joint_name,
            x=lm.x,
            y=lm.y,
            z=lm.z,
            confidence=lm.visibility
        )
    
    return SkeletonFrame(
        frame_number=frame_num,
        timestamp=frame_num / 30.0,  # Assume 30fps
        landmarks=landmarks
    )


def exercise_name_to_movement_type(exercise: str) -> MovementType:
    """Map exercise name to MovementType enum."""
    exercise_lower = exercise.lower().strip()
    
    # Try exact match first
    if exercise_lower in EXERCISE_TO_MOVEMENT_TYPE:
        return EXERCISE_TO_MOVEMENT_TYPE[exercise_lower]
    
    # Try partial match
    for key, movement_type in EXERCISE_TO_MOVEMENT_TYPE.items():
        if key in exercise_lower:
            return movement_type
    
    # Default to SQUAT for lower body, GAIT for others
    if any(word in exercise_lower for word in ['squat', 'lunge', 'leg', 'deadlift']):
        return MovementType.SQUAT
    
    return MovementType.GAIT


@router.post("/upload")
async def analyze_form(
    exercise_name: str = Form(...),
    file: UploadFile = File(...),
    user_id: Optional[str] = Depends(JWTBearer(auto_error=False))
):
    # GUEST MODE: If no user, generate random ID for this session
    if not user_id:
        user_id = str(uuid.uuid4())
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
        mp_results = None
        
        # Run MediaPipe Pose if available
        if MEDIAPIPE_AVAILABLE and mp_pose is not None:
            try:
                with mp_pose.Pose(
                    static_image_mode=True,
                    model_complexity=1,
                    enable_segmentation=False,
                    min_detection_confidence=0.5
                ) as pose:
                    mp_results = pose.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
                    
                    if mp_results.pose_landmarks:
                        # Draw landmarks on the image
                        mp_drawing.draw_landmarks(
                            annotated_image,
                            mp_results.pose_landmarks,
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
        
        # NEW: Execute full orchestration pipeline
        analysis = await form_check_pipeline.run(
            image_base64=original_base64,
            exercise=exercise_name,
            user_id=user_id,
            mp_results=mp_results
        )
        
        if not analysis:
            raise HTTPException(status_code=500, detail="Form analysis failed in pipeline.")
            
        # Create Result Record
        form_check = FormCheckDocument(
            user_id=user_id,
            exercise_name=exercise_name,
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
            "form_check_id": str(form_check.uid),
            "form_score": form_check.score,
            "alignment_feedback": form_check.alignment_feedback,
            "rom_feedback": form_check.rom_feedback,
            "stability_feedback": form_check.stability_feedback,
            "corrections": form_check.corrections,
            "tips": analysis.get("tips", []),
            "next_step": form_check.next_step,
            "annotated_image": f"data:image/jpeg;base64,{annotated_base64}",
            "research_citations": analysis.get("pipeline_metadata", {}).get("research_citations")
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
