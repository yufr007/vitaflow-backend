"""
Azure Foundry-Orchestrated Form Check Pipeline.

Eliminates hallucination by separating COMPUTATION from EXPLANATION.
This service orchestrates the multi-step workflow:
1. MediaPipe Pose Extraction
2. Biomechanics Calculation (Math, not AI)
3. Reference Baseline Comparison
4. PhysioNet Enrichment
5. AI Coaching (Explanation)
"""
import logging
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import time

from app.services.azure_foundry import azure_foundry
from app.services.gemini import gemini_service
from app.services.physionet_service import physionet_service
from integrations.biomechanics import (
    FormAnalyzer, MovementType, SkeletonFrame, 
    MovementSequence, SkeletonLandmark
)
# Import route-level helpers if needed, but better to duplicate for decoupling
# or move to common utility. For now, we assume this service is called by the route.

logger = logging.getLogger(__name__)


@dataclass
class PipelineStep:
    name: str
    status: str = "pending"  # pending, running, completed, failed
    duration_ms: float = 0
    error: Optional[str] = None


class FormCheckPipeline:
    """
    Multi-step pipeline for form analysis.
    """
    
    def __init__(self):
        self.form_analyzer = FormAnalyzer()

    def _mediapipe_to_skeleton_frame(self, mp_results, frame_num: int = 0) -> Optional[SkeletonFrame]:
        """Convert MediaPipe Pose results to VitaFlow SkeletonFrame."""
        if not mp_results or not mp_results.pose_landmarks:
            return None
        
        landmarks = {}
        MP_LANDMARK_MAP = {
            11: 'left_shoulder', 12: 'right_shoulder',
            13: 'left_elbow', 14: 'right_elbow',
            15: 'left_wrist', 16: 'right_wrist',
            23: 'left_hip', 24: 'right_hip',
            25: 'left_knee', 26: 'right_knee',
            27: 'left_ankle', 28: 'right_ankle',
            29: 'left_heel', 30: 'right_heel',
            31: 'left_foot_index', 32: 'right_foot_index',
        }
        
        for mp_idx, joint_name in MP_LANDMARK_MAP.items():
            lm = mp_results.pose_landmarks.landmark[mp_idx]
            landmarks[joint_name] = SkeletonLandmark(
                name=joint_name,
                x=lm.x, y=lm.y, z=lm.z,
                confidence=lm.visibility
            )
        
        return SkeletonFrame(
            frame_number=frame_num,
            timestamp=frame_num / 30.0,
            landmarks=landmarks
        )

    def _exercise_to_movement_type(self, exercise: str) -> MovementType:
        """Map exercise name to MovementType enum."""
        exercise_lower = exercise.lower().strip()
        mapping = {
            'squat': MovementType.SQUAT,
            'deadlift': MovementType.DEADLIFT,
            'running': MovementType.GAIT,
            'gait': MovementType.GAIT,
            'walking': MovementType.GAIT,
            'bench press': MovementType.BENCH_PRESS,
            'overhead press': MovementType.OVERHEAD_PRESS,
        }
        
        for key, mt in mapping.items():
            if key in exercise_lower:
                return mt
        
        if any(word in exercise_lower for word in ['squat', 'lunge', 'leg']):
            return MovementType.SQUAT
        return MovementType.GAIT

    async def run(
        self,
        image_base64: str,
        exercise: str,
        user_id: str,
        mp_results: Any
    ) -> Dict[str, Any]:
        """
        Execute the full form check pipeline.
        
        Args:
            image_base64: Original image for Gemini
            exercise: Exercise name
            user_id: ID of the user
            mp_results: Results from MediaPipe pose detection
        """
        start_time = time.time()
        steps: List[PipelineStep] = []
        
        # --- Step 1: Biomechanics Analysis ---
        biomech_step = PipelineStep(name="Biomechanics Analysis")
        steps.append(biomech_step)
        computed_metrics = {}
        
        try:
            step_start = time.time()
            skeleton_frame = self._mediapipe_to_skeleton_frame(mp_results)
            
            if skeleton_frame:
                movement_type = self._exercise_to_movement_type(exercise)
                sequence = MovementSequence(
                    id=f"pipeline_{user_id}_{int(time.time())}",
                    movement_type=movement_type,
                    frames=[skeleton_frame],
                    sample_rate=30.0,
                    source_dataset="user_upload"
                )
                
                biomech_result = None
                if movement_type == MovementType.SQUAT:
                    biomech_result = self.form_analyzer.analyze_squat(sequence)
                elif movement_type == MovementType.GAIT:
                    biomech_result = self.form_analyzer.analyze_gait(sequence)
                elif movement_type == MovementType.DEADLIFT:
                    biomech_result = self.form_analyzer.analyze_deadlift(sequence)
                
                if biomech_result:
                    computed_metrics = {
                        "form_score": biomech_result.overall_score,
                        "risk_level": biomech_result.risk_level.value,
                        "key_metrics": biomech_result.key_metrics,
                        "issues": [
                            {
                                "type": issue.issue.value,
                                "severity": issue.severity,
                                "risk": issue.risk_level.value,
                                "description": issue.description,
                                "cues": issue.corrective_cues
                            }
                            for issue in biomech_result.issues
                        ],
                        "comparison": biomech_result.comparison_to_reference
                    }
            
            biomech_step.status = "completed" if computed_metrics else "failed"
            biomech_step.duration_ms = (time.time() - step_start) * 1000
        except Exception as e:
            biomech_step.status = "failed"
            biomech_step.error = str(e)
            logger.error(f"Biomechanics step failed: {e}", exc_info=True)

        # --- Step 2: PhysioNet Enrichment ---
        enrichment_step = PipelineStep(name="PhysioNet Enrichment")
        steps.append(enrichment_step)
        
        try:
            step_start = time.time()
            citations = await physionet_service.get_citations_for_activity(exercise)
            citation_text = "; ".join([f"{c.title} ({c.id})" for c in citations[:2]])
            computed_metrics["research_citations"] = citation_text
            
            enrichment_step.status = "completed"
            enrichment_step.duration_ms = (time.time() - step_start) * 1000
        except Exception as e:
            enrichment_step.status = "completed_with_warning"
            logger.warning(f"PhysioNet enrichment failed: {e}")

        # --- Step 3: AI Coaching (Azure Foundry / Gemini) ---
        coaching_step = PipelineStep(name="AI Coaching")
        steps.append(coaching_step)
        analysis_result = None
        
        try:
            step_start = time.time()
            # This is the "COMPUTE-THEN-EXPLAIN" core
            analysis_result = await gemini_service.analyze_form_check(
                image_base64,
                exercise,
                computed_metrics=computed_metrics if computed_metrics else None
            )
            
            coaching_step.status = "completed" if analysis_result else "failed"
            coaching_step.duration_ms = (time.time() - step_start) * 1000
        except Exception as e:
            coaching_step.status = "failed"
            coaching_step.error = str(e)
            logger.error(f"Coaching step failed: {e}")

        total_duration = (time.time() - start_time) * 1000
        
        if not analysis_result:
            return None

        # Add pipeline metadata to result
        analysis_result["pipeline_metadata"] = {
            "pipeline_id": f"pipe_{user_id}_{int(start_time)}",
            "total_duration_ms": total_duration,
            "steps": [
                {"name": s.name, "status": s.status, "duration_ms": s.duration_ms} 
                for s in steps
            ],
            "research_citations": computed_metrics.get("research_citations")
        }
        
        return analysis_result


# Singleton instance
form_check_pipeline = FormCheckPipeline()

