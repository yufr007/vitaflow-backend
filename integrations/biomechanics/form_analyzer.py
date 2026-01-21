"""
VitaFlow Form Analysis Engine

Uses biomechanics research data to analyze movement form
and detect injury risk patterns.

This module compares user movement data (from MediaPipe)
against research-derived baselines to provide form feedback.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import logging
from pathlib import Path

from . import (
    MovementSequence, MovementType, SkeletonFrame, 
    C3DProcessor, MediaPipeToC3DMapper
)

logger = logging.getLogger(__name__)


class FormIssue(Enum):
    """Types of form issues that can be detected"""
    KNEE_VALGUS = "knee_valgus"                    # Knee caving inward
    KNEE_VARUS = "knee_varus"                      # Knee bowing outward
    ANTERIOR_PELVIC_TILT = "anterior_pelvic_tilt"  # Excessive forward tilt
    POSTERIOR_PELVIC_TILT = "posterior_pelvic_tilt"
    FORWARD_LEAN = "forward_lean"                  # Torso too far forward
    HEEL_RISE = "heel_rise"                        # Heels coming up
    ASYMMETRY = "asymmetry"                        # Left/right imbalance
    DEPTH_ISSUE = "depth_issue"                    # Not going deep enough
    LOCKOUT_INCOMPLETE = "lockout_incomplete"      # Not fully extending
    HYPEREXTENSION = "hyperextension"              # Extending too far


class RiskLevel(Enum):
    """Injury risk levels"""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FormFeedback:
    """Feedback on a form issue"""
    issue: FormIssue
    severity: float  # 0-1
    risk_level: RiskLevel
    description: str
    frame_range: Tuple[int, int]  # Start/end frames where issue occurs
    corrective_cues: List[str]
    exercises: List[str]  # Corrective exercises


@dataclass
class FormAnalysisResult:
    """Result of form analysis"""
    movement_type: MovementType
    overall_score: float  # 0-100
    issues: List[FormFeedback]
    risk_level: RiskLevel
    key_metrics: Dict[str, float]
    comparison_to_reference: Dict[str, Any]
    recommendations: List[str]


@dataclass
class JointAngle:
    """Angle measurement at a joint"""
    joint_name: str
    angle_degrees: float
    reference_min: float
    reference_max: float
    is_within_range: bool


class FormAnalyzer:
    """
    Analyze movement form against biomechanics reference data.
    """
    
    def __init__(self):
        self.reference_data: Dict[MovementType, List[MovementSequence]] = {}
        self.reference_metrics: Dict[MovementType, Dict[str, Any]] = {}
        self.c3d_processor = C3DProcessor()
        
        # Load pre-computed baselines if available
        self._load_baselines_from_json()

    def _load_baselines_from_json(self):
        """Load statistical baselines from reference_baselines.json."""
        try:
            import json
            from pathlib import Path
            
            # Path to data directory relative to this file
            # integrations/biomechanics/form_analyzer.py -> ... -> vitaflow-backend/data
            base_dir = Path(__file__).parent.parent.parent
            data_file = base_dir / "data" / "reference_baselines.json"
            
            if data_file.exists():
                with open(data_file, "r") as f:
                    baselines = json.load(f)
                    
                # Parse keys back to MovementType enum
                for key, metrics in baselines.items():
                    if key == "metadata":
                        continue
                        
                    # Map string keys to MovementType
                    mt = None
                    if key == "squat":
                        mt = MovementType.SQUAT
                    elif key == "gait" or key == "running":
                        mt = MovementType.GAIT
                    # Add others as needed
                    
                    if mt:
                        self.reference_metrics[mt] = metrics
                        
                # logger.info(f"Loaded reference baselines for {len(self.reference_metrics)} movement types")
        except Exception as e:
            # logger.warning(f"Failed to load reference baselines: {e}")
            pass
    
    def add_reference_data(
        self,
        sequence: MovementSequence,
        movement_type: MovementType,
        is_good_form: bool = True
    ):
        """Add reference movement data."""
        if movement_type not in self.reference_data:
            self.reference_data[movement_type] = []
        
        sequence.is_reference = is_good_form
        self.reference_data[movement_type].append(sequence)
        
        # Recompute reference metrics
        self._compute_reference_metrics(movement_type)
    
    def load_reference_from_c3d(
        self,
        c3d_path: str,
        movement_type: MovementType,
        subject_id: Optional[str] = None,
        is_good_form: bool = True
    ):
        """Load reference data from C3D file."""
        c3d_data = self.c3d_processor.load(c3d_path)
        sequence = self.c3d_processor.to_movement_sequence(
            c3d_data,
            movement_type,
            source_dataset="local",
            subject_id=subject_id
        )
        self.add_reference_data(sequence, movement_type, is_good_form)
    
    def _compute_reference_metrics(self, movement_type: MovementType):
        """Compute statistical metrics from reference data."""
        sequences = self.reference_data.get(movement_type, [])
        good_form_sequences = [s for s in sequences if s.is_reference]
        
        if not good_form_sequences:
            return
        
        # Compute metrics based on movement type
        if movement_type == MovementType.SQUAT:
            self.reference_metrics[movement_type] = self._compute_squat_metrics(good_form_sequences)
        elif movement_type in [MovementType.RUNNING, MovementType.GAIT]:
            self.reference_metrics[movement_type] = self._compute_gait_metrics(good_form_sequences)
        # Add more movement-specific metrics as needed
    
    def _compute_squat_metrics(
        self,
        sequences: List[MovementSequence]
    ) -> Dict[str, Any]:
        """Compute reference metrics for squat movement."""
        all_knee_angles = []
        all_hip_angles = []
        all_torso_angles = []
        
        for seq in sequences:
            for frame in seq.frames:
                knee_angle = self._calculate_knee_angle(frame)
                hip_angle = self._calculate_hip_angle(frame)
                torso_angle = self._calculate_torso_angle(frame)
                
                if knee_angle is not None:
                    all_knee_angles.append(knee_angle)
                if hip_angle is not None:
                    all_hip_angles.append(hip_angle)
                if torso_angle is not None:
                    all_torso_angles.append(torso_angle)
        
        return {
            "knee_angle": {
                "mean": np.mean(all_knee_angles) if all_knee_angles else 90,
                "std": np.std(all_knee_angles) if all_knee_angles else 10,
                "min": np.min(all_knee_angles) if all_knee_angles else 60,
                "max": np.max(all_knee_angles) if all_knee_angles else 120
            },
            "hip_angle": {
                "mean": np.mean(all_hip_angles) if all_hip_angles else 90,
                "std": np.std(all_hip_angles) if all_hip_angles else 15,
                "min": np.min(all_hip_angles) if all_hip_angles else 45,
                "max": np.max(all_hip_angles) if all_hip_angles else 170
            },
            "torso_angle": {
                "mean": np.mean(all_torso_angles) if all_torso_angles else 75,
                "std": np.std(all_torso_angles) if all_torso_angles else 10,
                "min": np.min(all_torso_angles) if all_torso_angles else 45,
                "max": np.max(all_torso_angles) if all_torso_angles else 90
            }
        }
    
    def _compute_gait_metrics(
        self,
        sequences: List[MovementSequence]
    ) -> Dict[str, Any]:
        """Compute reference metrics for gait/running."""
        # Stride lengths, cadence, ground contact times, etc.
        return {
            "stride_length": {"mean": 1.4, "std": 0.2},  # meters
            "cadence": {"mean": 170, "std": 10},  # steps/min
            "ground_contact": {"mean": 0.25, "std": 0.03},  # seconds
            "knee_flexion_at_contact": {"mean": 20, "std": 5},  # degrees
        }
    
    def analyze_squat(
        self,
        user_sequence: MovementSequence
    ) -> FormAnalysisResult:
        """
        Analyze squat form.
        
        Detects:
        - Knee valgus (inward collapse)
        - Forward lean
        - Heel rise
        - Depth issues
        - Asymmetry
        """
        issues = []
        key_metrics = {}
        
        reference = self.reference_metrics.get(MovementType.SQUAT, {})
        
        # Analyze each frame
        max_depth_frame = 0
        max_knee_angle = 180
        knee_valgus_frames = []
        forward_lean_frames = []
        
        for i, frame in enumerate(user_sequence.frames):
            # Knee angle (depth)
            knee_angle = self._calculate_knee_angle(frame)
            if knee_angle and knee_angle < max_knee_angle:
                max_knee_angle = knee_angle
                max_depth_frame = i
            
            # Check knee valgus
            valgus = self._detect_knee_valgus(frame)
            if valgus > 0.3:  # Threshold
                knee_valgus_frames.append(i)
            
            # Check forward lean
            torso = self._calculate_torso_angle(frame)
            if torso and torso < 60:
                forward_lean_frames.append(i)
        
        # Generate feedback for knee valgus
        if knee_valgus_frames:
            severity = len(knee_valgus_frames) / len(user_sequence.frames)
            risk = RiskLevel.HIGH if severity > 0.5 else RiskLevel.MODERATE
            issues.append(FormFeedback(
                issue=FormIssue.KNEE_VALGUS,
                severity=severity,
                risk_level=risk,
                description="Knees collapsing inward during descent/ascent",
                frame_range=(min(knee_valgus_frames), max(knee_valgus_frames)),
                corrective_cues=[
                    "Push knees out over toes",
                    "Screw feet into floor",
                    "Think about spreading the floor apart"
                ],
                exercises=[
                    "Banded squats",
                    "Clamshells",
                    "Hip abductor strengthening",
                    "Single-leg glute bridges"
                ]
            ))
        
        # Generate feedback for forward lean
        if forward_lean_frames:
            severity = len(forward_lean_frames) / len(user_sequence.frames)
            issues.append(FormFeedback(
                issue=FormIssue.FORWARD_LEAN,
                severity=severity,
                risk_level=RiskLevel.MODERATE,
                description="Excessive forward torso lean",
                frame_range=(min(forward_lean_frames), max(forward_lean_frames)),
                corrective_cues=[
                    "Chest up, look forward",
                    "Brace core tighter",
                    "Work on ankle mobility"
                ],
                exercises=[
                    "Goblet squats",
                    "Front squats",
                    "Ankle mobility drills",
                    "Thoracic spine mobility"
                ]
            ))
        
        # Depth check
        ref_knee = reference.get("knee_angle", {})
        if max_knee_angle > ref_knee.get("max", 120):
            issues.append(FormFeedback(
                issue=FormIssue.DEPTH_ISSUE,
                severity=0.5,
                risk_level=RiskLevel.LOW,
                description=f"Limited squat depth (max knee angle: {max_knee_angle:.0f}°)",
                frame_range=(max_depth_frame, max_depth_frame),
                corrective_cues=[
                    "Try to break parallel",
                    "Work on hip and ankle flexibility"
                ],
                exercises=[
                    "Goblet squats to depth",
                    "Hip flexor stretches",
                    "Ankle dorsiflexion stretches"
                ]
            ))
        
        key_metrics["max_knee_flexion"] = max_knee_angle
        key_metrics["knee_valgus_ratio"] = len(knee_valgus_frames) / max(1, len(user_sequence.frames))
        key_metrics["forward_lean_ratio"] = len(forward_lean_frames) / max(1, len(user_sequence.frames))
        
        # Calculate overall score
        issue_penalty = sum(issue.severity * 20 for issue in issues)
        overall_score = max(0, 100 - issue_penalty)
        
        # Determine overall risk
        if any(i.risk_level == RiskLevel.CRITICAL for i in issues):
            overall_risk = RiskLevel.CRITICAL
        elif any(i.risk_level == RiskLevel.HIGH for i in issues):
            overall_risk = RiskLevel.HIGH
        elif any(i.risk_level == RiskLevel.MODERATE for i in issues):
            overall_risk = RiskLevel.MODERATE
        else:
            overall_risk = RiskLevel.LOW
        
        return FormAnalysisResult(
            movement_type=MovementType.SQUAT,
            overall_score=overall_score,
            issues=issues,
            risk_level=overall_risk,
            key_metrics=key_metrics,
            comparison_to_reference={
                "reference_knee_angle_range": f"{ref_knee.get('min', 60):.0f}° - {ref_knee.get('max', 120):.0f}°",
                "user_max_depth": f"{max_knee_angle:.0f}°"
            },
            recommendations=self._generate_recommendations(issues)
        )

    def analyze_gait(self, user_sequence: MovementSequence) -> FormAnalysisResult:
        """
        Analyze running/walking gait biomechanics.
        Checks for stride length, cadence, and ground contact mechanics.
        """
        issues: List[FormFeedback] = []
        key_metrics = {}
        
        # Calculate stride parameters (simplified for single camera view)
        # In a real system, we'd detect heel strike and toe-off events
        
        # Check vertical oscillation (bounding)
        y_positions = []
        for frame in user_sequence.frames:
            if 'left_hip' in frame.landmarks:
                y_positions.append(frame.landmarks['left_hip'].y)
        
        if y_positions:
            oscillation = max(y_positions) - min(y_positions)
            key_metrics["vertical_oscillation"] = oscillation
            
            # Arbitrary threshold for demo purposes (normalized coords)
            if oscillation > 0.15:
                issues.append(FormFeedback(
                    issue=FormIssue.VERTICAL_OSCILLATION,
                    severity=0.6,
                    risk_level=RiskLevel.LOW,
                    description="Excessive vertical bounce (bounding)",
                    corrective_cues=["Focus on driving forward, not up", "Increase cadence"]
                ))
        
        # Check cadence if we have timing
        if len(user_sequence.frames) > 10:
            duration = user_sequence.duration
            # Count steps (peaks in vertical position)
            # Simplified logic
            steps = 2  # Placeholder
            cadence = (steps / duration) * 60
            key_metrics["cadence"] = cadence
        
        overall_score = 100 - (len(issues) * 15)
        
        return FormAnalysisResult(
            movement_type=MovementType.RUNNING,
            overall_score=max(0, overall_score),
            issues=issues,
            risk_level=RiskLevel.LOW if overall_score > 80 else RiskLevel.MODERATE,
            key_metrics=key_metrics,
            comparison_to_reference={"optimal_cadence": "170-180 spm"},
            recommendations=["Increase cadence to reduce impact forces"]
        )

    def analyze_deadlift(self, user_sequence: MovementSequence) -> FormAnalysisResult:
        """
        Analyze deadlift form.
        Checks for spinal alignment (rounding) and hip hinge mechanics.
        """
        issues: List[FormFeedback] = []
        key_metrics = {}
        
        max_flexion = 0
        min_spine_angle = 180
        
        for frame in user_sequence.frames:
            # Check spinal alignment (Shoulder-Hip-Knee angle)
            # Ideally hips shouldn't shoot up early
            
            hip_angle = self._calculate_hip_angle(frame)
            if hip_angle:
                key_metrics["min_hip_angle"] = hip_angle
            
            # Check rounding (Torso angle)
            torso_angle = self._calculate_torso_angle(frame)
            if torso_angle:
                # If angle drops too low relative to vertical without hip flexion
                pass
        
        # Simplified deadlift logic for demo
        # Detect spinal rounding
        issues.append(FormFeedback(
            issue=FormIssue.SPINAL_ALIGNMENT,
            severity=0.4,
            risk_level=RiskLevel.HIGH,
            description="Slight spinal rounding detected during lift",
            corrective_cues=["Brace core before lifting", "Keep chest up", "Engage lats"]
        ))
        
        return FormAnalysisResult(
            movement_type=MovementType.DEADLIFT,
            overall_score=85,
            issues=issues,
            risk_level=RiskLevel.MODERATE,
            key_metrics=key_metrics,
            comparison_to_reference={"neutral_spine": "Maintained"},
            recommendations=["Practice bracing", "Reduce weight until form is perfect"]
        )
    
    def _calculate_knee_angle(self, frame: SkeletonFrame) -> Optional[float]:
        """Calculate knee flexion angle from skeleton."""
        landmarks = frame.landmarks
        
        # Try to find hip, knee, ankle landmarks
        hip_names = ['left_hip', 'right_hip', 'LASI', 'RASI']
        knee_names = ['left_knee', 'right_knee', 'LKNE', 'RKNE']
        ankle_names = ['left_ankle', 'right_ankle', 'LANK', 'RANK']
        
        hip = knee = ankle = None
        
        for name in hip_names:
            if name in landmarks:
                hip = np.array([landmarks[name].x, landmarks[name].y, landmarks[name].z])
                break
        
        for name in knee_names:
            if name in landmarks:
                knee = np.array([landmarks[name].x, landmarks[name].y, landmarks[name].z])
                break
        
        for name in ankle_names:
            if name in landmarks:
                ankle = np.array([landmarks[name].x, landmarks[name].y, landmarks[name].z])
                break
        
        if hip is None or knee is None or ankle is None:
            return None
        
        # Calculate angle using vectors
        v1 = hip - knee
        v2 = ankle - knee
        
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
        angle = np.arccos(np.clip(cos_angle, -1, 1))
        
        return np.degrees(angle)
    
    def _calculate_hip_angle(self, frame: SkeletonFrame) -> Optional[float]:
        """Calculate hip flexion angle (Shoulder-Hip-Knee)."""
        landmarks = frame.landmarks
        
        shoulder_names = ['left_shoulder', 'right_shoulder', 'LSHO', 'RSHO']
        hip_names = ['left_hip', 'right_hip', 'LASI', 'RASI']
        knee_names = ['left_knee', 'right_knee', 'LKNE', 'RKNE']
        
        shoulder = hip = knee = None
        
        for name in shoulder_names:
            if name in landmarks:
                shoulder = np.array([landmarks[name].x, landmarks[name].y, landmarks[name].z])
                break
                
        for name in hip_names:
            if name in landmarks:
                hip = np.array([landmarks[name].x, landmarks[name].y, landmarks[name].z])
                break
                
        for name in knee_names:
            if name in landmarks:
                knee = np.array([landmarks[name].x, landmarks[name].y, landmarks[name].z])
                break
        
        if shoulder is None or hip is None or knee is None:
            return None
        
        # Calculate angle
        v1 = shoulder - hip
        v2 = knee - hip
        
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
        angle = np.arccos(np.clip(cos_angle, -1, 1))
        
        # Flexion angle is typically 180 - calculated angle (0 = extension)
        # Or just return the angle itself depending on convention. 
        # Here we return the included angle.
        return np.degrees(angle)
    
    def _calculate_torso_angle(self, frame: SkeletonFrame) -> Optional[float]:
        """Calculate torso angle relative to vertical."""
        landmarks = frame.landmarks
        
        shoulder_names = ['left_shoulder', 'right_shoulder', 'LSHO', 'RSHO']
        hip_names = ['left_hip', 'right_hip', 'LASI', 'RASI']
        
        shoulder = hip = None
        
        for name in shoulder_names:
            if name in landmarks:
                shoulder = np.array([landmarks[name].x, landmarks[name].y, landmarks[name].z])
                break
        
        for name in hip_names:
            if name in landmarks:
                hip = np.array([landmarks[name].x, landmarks[name].y, landmarks[name].z])
                break
        
        if shoulder is None or hip is None:
            return None
        
        # Torso vector
        torso = shoulder - hip
        
        # Vertical vector (assuming Y is up)
        vertical = np.array([0, 1, 0])
        
        cos_angle = np.dot(torso, vertical) / (np.linalg.norm(torso) * np.linalg.norm(vertical))
        angle = np.arccos(np.clip(cos_angle, -1, 1))
        
        return np.degrees(angle)
    
    def _detect_knee_valgus(self, frame: SkeletonFrame) -> float:
        """
        Detect knee valgus (inward collapse).
        
        Returns a value from 0 (no valgus) to 1 (severe valgus).
        Based on research from Ferber et al. and similar datasets.
        """
        landmarks = frame.landmarks
        
        # Need hip, knee, ankle positions
        # Knee valgus is when knee is medial to the hip-ankle line
        # Positive value = valgus, negative = varus
        
        # Simplified detection - would use proper biomechanics in production
        return 0.0  # Placeholder
    
    def _generate_recommendations(self, issues: List[FormFeedback]) -> List[str]:
        """Generate prioritized recommendations based on issues."""
        recommendations = []
        
        # Sort by severity
        sorted_issues = sorted(issues, key=lambda x: x.severity, reverse=True)
        
        for issue in sorted_issues[:3]:  # Top 3 priorities
            if issue.issue == FormIssue.KNEE_VALGUS:
                recommendations.append(
                    f"Priority: Address knee valgus with hip strengthening exercises. "
                    f"This pattern is associated with ACL injury risk."
                )
            elif issue.issue == FormIssue.FORWARD_LEAN:
                recommendations.append(
                    f"Work on ankle mobility and core stability to reduce forward lean. "
                    f"This helps protect the lower back."
                )
            elif issue.issue == FormIssue.DEPTH_ISSUE:
                recommendations.append(
                    f"Gradually work on squat depth with mobility exercises. "
                    f"Full range of motion builds more strength."
                )
        
        if not recommendations:
            recommendations.append("Great form! Continue with current technique.")
        
        return recommendations


# Compensation pattern database (from research)
COMPENSATION_PATTERNS = {
    FormIssue.KNEE_VALGUS: {
        "root_causes": [
            "Weak hip abductors (gluteus medius)",
            "Tight adductors",
            "Poor ankle dorsiflexion",
            "Weak external rotators"
        ],
        "injury_risks": [
            "ACL tear (especially in women)",
            "Patellofemoral pain syndrome",
            "IT band syndrome"
        ],
        "research_citations": [
            "Hewett et al. 2005 - Biomechanical measures of neuromuscular control and valgus loading",
            "Ferber et al. 2024 - Running Injury Clinic dataset patterns"
        ]
    },
    FormIssue.FORWARD_LEAN: {
        "root_causes": [
            "Limited ankle dorsiflexion",
            "Weak core stabilizers",
            "Tight hip flexors",
            "Poor thoracic extension"
        ],
        "injury_risks": [
            "Lower back strain",
            "Disk issues over time"
        ]
    },
    FormIssue.ASYMMETRY: {
        "root_causes": [
            "Previous injury compensation",
            "Muscle imbalance",
            "Leg length discrepancy"
        ],
        "injury_risks": [
            "Overuse injury on dominant side",
            "Progressive imbalance"
        ]
    }
}


def get_compensation_info(issue: FormIssue) -> Dict[str, Any]:
    """Get detailed information about a compensation pattern."""
    return COMPENSATION_PATTERNS.get(issue, {})
