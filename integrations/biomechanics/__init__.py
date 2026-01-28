"""
VitaFlow Biomechanics Integration Module

This module provides utilities for working with biomechanics research datasets
and C3D motion capture files for form analysis and injury prevention.

Data Sources:
- mkjung99/biomechanics_dataset: Curated index of 80+ public datasets
- mkjung99/pyc3dserver: C3D file processing (Windows only)
- EZC3D: Cross-platform C3D processing

License:
- PyC3Dserver: MIT License (Moon Ki Jung, 2020)
- EZC3D: MIT License
- Individual datasets have their own licenses - verify before commercial use
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from pathlib import Path
import logging
import json

logger = logging.getLogger(__name__)

from .form_analyzer import (
    FormAnalyzer, FormAnalysisResult, FormFeedback, 
    FormIssue, RiskLevel
)


class DatasetCategory(Enum):
    """Categories of biomechanics datasets"""
    KINEMATICS_FORCES_EMG = "kinematics_forces_emg"       # Full data
    KINEMATICS_FORCES_OR_EMG = "kinematics_forces_or_emg"  # Partial
    KINEMATICS_ONLY = "kinematics_only"                    # Motion only
    OTHER = "other"                                         # Specialized


class MovementType(Enum):
    """Types of movement in datasets"""
    GAIT = "gait"
    RUNNING = "running"
    SQUAT = "squat"
    THROWING = "throwing"
    MARTIAL_ARTS = "martial_arts"
    DANCE = "dance"
    REHABILITATION = "rehabilitation"
    DAILY_LIVING = "daily_living"
    SPORT_SPECIFIC = "sport_specific"
    DEADLIFT = "deadlift"
    BENCH_PRESS = "bench_press"
    OVERHEAD_PRESS = "overhead_press"
    LUNGE = "lunge"
    PUSHUP = "pushup"


@dataclass
class BiomechanicsDataset:
    """Metadata for a biomechanics dataset"""
    id: str
    name: str
    doi: Optional[str]
    data_url: str
    category: DatasetCategory
    movement_types: List[MovementType]
    subjects: Optional[int] = None
    includes_injured: bool = False
    file_format: str = "c3d"
    license: Optional[str] = None
    description: str = ""
    vitaflow_priority: int = 0  # 1-10, higher = more valuable


# High-priority datasets for VitaFlow
PRIORITY_DATASETS: List[BiomechanicsDataset] = [
    BiomechanicsDataset(
        id="ferber_2024",
        name="Running Injury Clinic Kinematic Dataset",
        doi="10.1038/s41597-024-04011-7",
        data_url="https://figshare.com/articles/dataset/Running_Injury_Clinic_Kinematic_Dataset/24255795",
        category=DatasetCategory.KINEMATICS_ONLY,
        movement_types=[MovementType.RUNNING, MovementType.GAIT],
        subjects=1798,
        includes_injured=True,
        description="1,798 healthy and injured subjects during treadmill walking and running",
        vitaflow_priority=10
    ),
    BiomechanicsDataset(
        id="gaitrec",
        name="GaitRec Ground Reaction Force Dataset",
        doi="10.6084/m9.figshare.c.4788012.v1",
        data_url="https://doi.org/10.6084/m9.figshare.c.4788012.v1",
        category=DatasetCategory.OTHER,
        movement_types=[MovementType.GAIT],
        includes_injured=True,
        description="Ground reaction forces from healthy and impaired gait",
        vitaflow_priority=9
    ),
    BiomechanicsDataset(
        id="mohr_squat",
        name="Squat EMG Dataset",
        doi="10.17632/37wyv32y8j.1",
        data_url="http://dx.doi.org/10.17632/37wyv32y8j.1",
        category=DatasetCategory.KINEMATICS_FORCES_OR_EMG,
        movement_types=[MovementType.SQUAT],
        description="Monopolar and bipolar EMG during squatting",
        vitaflow_priority=9
    ),
    BiomechanicsDataset(
        id="van_criekinge_2023",
        name="Lifespan Gait + Stroke Survivors",
        doi="10.1038/s41597-023-02767-y",
        data_url="https://doi.org/10.6084/m9.figshare.c.6503791.v1",
        category=DatasetCategory.KINEMATICS_FORCES_OR_EMG,
        movement_types=[MovementType.GAIT, MovementType.REHABILITATION],
        subjects=188,  # 138 healthy + 50 stroke
        includes_injured=True,
        description="138 able-bodied adults + 50 stroke survivors",
        vitaflow_priority=8
    ),
    BiomechanicsDataset(
        id="ozkaya_throwing",
        name="Overarm Throwing Motion Capture",
        doi="10.1038/sdata.2018.272",
        data_url="https://doi.org/10.6084/m9.figshare.c.4017808.v1",
        category=DatasetCategory.KINEMATICS_FORCES_OR_EMG,
        movement_types=[MovementType.THROWING, MovementType.SPORT_SPECIFIC],
        description="3D motion capture during repetitive overarm throwing",
        vitaflow_priority=8
    ),
    BiomechanicsDataset(
        id="szcz_karate",
        name="Kyokushin Karate Techniques",
        doi="10.1038/s41597-021-00801-5",
        data_url="https://doi.org/10.6084/m9.figshare.c.4981073",
        category=DatasetCategory.KINEMATICS_ONLY,
        movement_types=[MovementType.MARTIAL_ARTS, MovementType.SPORT_SPECIFIC],
        includes_injured=False,
        description="Beginner vs advanced karate athletes - skill progression data",
        vitaflow_priority=7
    ),
    BiomechanicsDataset(
        id="mohr_knee_injury",
        name="Knee Injury History EMG",
        doi="10.17632/f2fv7gb577.1",
        data_url="http://dx.doi.org/10.17632/f2fv7gb577.1",
        category=DatasetCategory.OTHER,
        movement_types=[MovementType.GAIT],
        includes_injured=True,
        description="EMG patterns in individuals with/without knee injury history",
        vitaflow_priority=8
    ),
    BiomechanicsDataset(
        id="toronto_elderly",
        name="Toronto Older Adults Gait Archive",
        doi="10.1038/s41597-022-01495-z",
        data_url="https://doi.org/10.6084/m9.figshare.c.5515953.v1",
        category=DatasetCategory.KINEMATICS_ONLY,
        movement_types=[MovementType.GAIT],
        description="Video and 3D IMU data of older adults walking - fall risk",
        vitaflow_priority=6
    ),
]


@dataclass
class SkeletonLandmark:
    """A single skeleton landmark/joint"""
    name: str
    x: float
    y: float
    z: float
    confidence: float = 1.0


@dataclass
class SkeletonFrame:
    """A single frame of skeleton data"""
    frame_number: int
    timestamp: float  # seconds
    landmarks: Dict[str, SkeletonLandmark]
    
    def to_array(self) -> np.ndarray:
        """Convert landmarks to numpy array [N x 3]"""
        points = []
        for name, landmark in self.landmarks.items():
            points.append([landmark.x, landmark.y, landmark.z])
        return np.array(points)


@dataclass  
class MovementSequence:
    """A sequence of skeleton frames representing a movement"""
    id: str
    movement_type: MovementType
    frames: List[SkeletonFrame]
    sample_rate: float  # Hz
    source_dataset: Optional[str] = None
    subject_id: Optional[str] = None
    is_reference: bool = False  # True if this is "good form"
    is_injured: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> float:
        """Duration in seconds"""
        return len(self.frames) / self.sample_rate
    
    @property
    def num_frames(self) -> int:
        return len(self.frames)


class C3DProcessor:
    """
    Processor for C3D biomechanics files.
    
    Supports two backends:
    - 'pyc3dserver': Windows only, requires C3Dserver installation
    - 'ezc3d': Cross-platform, pip installable
    """
    
    def __init__(self, backend: str = "auto"):
        """
        Initialize C3D processor.
        
        Args:
            backend: 'pyc3dserver', 'ezc3d', or 'auto' (try ezc3d first)
        """
        self.backend = self._detect_backend(backend)
        self._c3d = None
        
    def _detect_backend(self, preferred: str) -> str:
        """Detect available C3D backend"""
        if preferred != "auto":
            return preferred
            
        # Try ezc3d first (cross-platform)
        try:
            import ezc3d
            logger.info("Using ezc3d backend")
            return "ezc3d"
        except ImportError:
            pass
            
        # Try pyc3dserver (Windows only)
        try:
            import pyc3dserver
            logger.info("Using pyc3dserver backend")
            return "pyc3dserver"
        except ImportError:
            pass
            
        raise ImportError(
            "No C3D backend available. Install ezc3d (pip install ezc3d) "
            "or pyc3dserver (pip install pyc3dserver, Windows only)"
        )
    
    def load(self, filepath: str) -> Dict[str, Any]:
        """
        Load a C3D file and return extracted data.
        
        Returns:
            Dict containing:
            - markers: Dict[str, np.ndarray] - marker positions [frames x 3]
            - analogs: Dict[str, np.ndarray] - analog signals (forces, EMG)
            - sample_rate: float - marker sample rate (Hz)
            - analog_rate: float - analog sample rate (Hz)
            - metadata: Dict - file metadata
        """
        if self.backend == "ezc3d":
            return self._load_ezc3d(filepath)
        else:
            return self._load_pyc3dserver(filepath)
    
    def _load_ezc3d(self, filepath: str) -> Dict[str, Any]:
        """Load C3D using ezc3d"""
        import ezc3d
        
        c3d = ezc3d.c3d(filepath)
        
        # Extract marker data
        markers = {}
        point_labels = c3d['parameters']['POINT']['LABELS']['value']
        point_data = c3d['data']['points']  # [4 x n_markers x n_frames]
        
        # Use actual data dimensions, not label count (they may differ)
        n_markers_in_data = point_data.shape[1]
        
        for i, label in enumerate(point_labels):
            if i >= n_markers_in_data:
                # More labels than data columns - skip extra labels
                break
            # XYZ positions, ignore residual (4th component)
            markers[label] = point_data[:3, i, :].T  # [frames x 3]
        
        # Extract analog data (forces, EMG)
        analogs = {}
        if 'ANALOG' in c3d['parameters'] and 'LABELS' in c3d['parameters']['ANALOG']:
            analog_labels = c3d['parameters']['ANALOG']['LABELS']['value']
            analog_data = c3d['data']['analogs']  # [1 x n_channels x n_samples]
            
            # Use actual data dimensions, not label count
            n_analogs_in_data = analog_data.shape[1]
            
            for i, label in enumerate(analog_labels):
                if i >= n_analogs_in_data:
                    break
                analogs[label] = analog_data[0, i, :]
        
        # Extract sample rates
        sample_rate = c3d['parameters']['POINT']['RATE']['value'][0]
        analog_rate = c3d['parameters']['ANALOG']['RATE']['value'][0] if 'ANALOG' in c3d['parameters'] else 0
        
        return {
            'markers': markers,
            'analogs': analogs,
            'sample_rate': sample_rate,
            'analog_rate': analog_rate,
            'metadata': {
                'num_frames': c3d['header']['points']['last_frame'] - c3d['header']['points']['first_frame'] + 1,
                'num_markers': len(point_labels),
                'num_analogs': len(analogs)
            }
        }
    
    def _load_pyc3dserver(self, filepath: str) -> Dict[str, Any]:
        """Load C3D using pyc3dserver"""
        import pyc3dserver as c3d
        
        itf = c3d.c3dserver(msg=False)
        c3d.open_c3d(itf, filepath)
        
        # Get marker data
        markers = c3d.get_dict_markers(itf)
        
        # Get analog data (forces, EMG)
        analogs = c3d.get_dict_analogs(itf)
        
        # Get header info
        header = c3d.get_dict_header(itf)
        
        c3d.close_c3d(itf)
        
        return {
            'markers': markers,
            'analogs': analogs,
            'sample_rate': header.get('video_rate', 100),
            'analog_rate': header.get('analog_rate', 0),
            'metadata': header
        }
    
    def to_movement_sequence(
        self,
        c3d_data: Dict[str, Any],
        movement_type: MovementType,
        source_dataset: Optional[str] = None,
        subject_id: Optional[str] = None
    ) -> MovementSequence:
        """
        Convert C3D data to VitaFlow MovementSequence format.
        """
        markers = c3d_data['markers']
        sample_rate = c3d_data['sample_rate']
        
        # Get number of frames from first marker
        first_marker = list(markers.values())[0]
        num_frames = first_marker.shape[0]
        
        frames = []
        for i in range(num_frames):
            landmarks = {}
            for name, data in markers.items():
                landmarks[name] = SkeletonLandmark(
                    name=name,
                    x=float(data[i, 0]),
                    y=float(data[i, 1]),
                    z=float(data[i, 2])
                )
            
            frames.append(SkeletonFrame(
                frame_number=i,
                timestamp=i / sample_rate,
                landmarks=landmarks
            ))
        
        return MovementSequence(
            id=f"{source_dataset}_{subject_id}_{movement_type.value}",
            movement_type=movement_type,
            frames=frames,
            sample_rate=sample_rate,
            source_dataset=source_dataset,
            subject_id=subject_id,
            metadata=c3d_data.get('metadata', {})
        )


class MediaPipeToC3DMapper:
    """
    Map between MediaPipe Pose landmarks and C3D marker conventions.
    
    MediaPipe uses 33 pose landmarks, C3D uses variable marker sets.
    This mapper enables comparison between phone camera analysis and research data.
    """
    
    # MediaPipe Pose landmark indices
    MEDIAPIPE_LANDMARKS = {
        'nose': 0, 'left_eye_inner': 1, 'left_eye': 2, 'left_eye_outer': 3,
        'right_eye_inner': 4, 'right_eye': 5, 'right_eye_outer': 6,
        'left_ear': 7, 'right_ear': 8, 'mouth_left': 9, 'mouth_right': 10,
        'left_shoulder': 11, 'right_shoulder': 12, 'left_elbow': 13,
        'right_elbow': 14, 'left_wrist': 15, 'right_wrist': 16,
        'left_pinky': 17, 'right_pinky': 18, 'left_index': 19,
        'right_index': 20, 'left_thumb': 21, 'right_thumb': 22,
        'left_hip': 23, 'right_hip': 24, 'left_knee': 25, 'right_knee': 26,
        'left_ankle': 27, 'right_ankle': 28, 'left_heel': 29, 'right_heel': 30,
        'left_foot_index': 31, 'right_foot_index': 32
    }
    
    # Common C3D marker name mappings (varies by lab/system)
    C3D_TO_MEDIAPIPE = {
        # Plug-in Gait / Vicon common names
        'LFHD': 'left_ear', 'RFHD': 'right_ear',
        'LSHO': 'left_shoulder', 'RSHO': 'right_shoulder',
        'LELB': 'left_elbow', 'RELB': 'right_elbow',
        'LWRA': 'left_wrist', 'RWRA': 'right_wrist',
        'LASI': 'left_hip', 'RASI': 'right_hip',
        'LKNE': 'left_knee', 'RKNE': 'right_knee',
        'LANK': 'left_ankle', 'RANK': 'right_ankle',
        'LHEE': 'left_heel', 'RHEE': 'right_heel',
        'LTOE': 'left_foot_index', 'RTOE': 'right_foot_index',
        # Alternative naming conventions
        'L_Shoulder': 'left_shoulder', 'R_Shoulder': 'right_shoulder',
        'L_Elbow': 'left_elbow', 'R_Elbow': 'right_elbow',
        'L_Wrist': 'left_wrist', 'R_Wrist': 'right_wrist',
        'L_Hip': 'left_hip', 'R_Hip': 'right_hip',
        'L_Knee': 'left_knee', 'R_Knee': 'right_knee',
        'L_Ankle': 'left_ankle', 'R_Ankle': 'right_ankle',
    }
    
    @classmethod
    def map_c3d_to_mediapipe(
        cls,
        c3d_markers: Dict[str, np.ndarray]
    ) -> Dict[str, np.ndarray]:
        """
        Map C3D marker names to MediaPipe landmark names.
        
        Returns dict with MediaPipe landmark names as keys.
        """
        mapped = {}
        for c3d_name, mp_name in cls.C3D_TO_MEDIAPIPE.items():
            if c3d_name in c3d_markers:
                mapped[mp_name] = c3d_markers[c3d_name]
            # Try case-insensitive match
            elif c3d_name.upper() in [k.upper() for k in c3d_markers]:
                for k, v in c3d_markers.items():
                    if k.upper() == c3d_name.upper():
                        mapped[mp_name] = v
                        break
        return mapped
    
    @classmethod
    def get_common_landmarks(
        cls,
        c3d_markers: Dict[str, np.ndarray]
    ) -> List[str]:
        """Get list of landmarks available in both MediaPipe and C3D data."""
        mapped = cls.map_c3d_to_mediapipe(c3d_markers)
        return list(mapped.keys())


def get_dataset_registry() -> List[BiomechanicsDataset]:
    """Get the registry of all tracked biomechanics datasets."""
    return PRIORITY_DATASETS


def get_high_priority_datasets(min_priority: int = 7) -> List[BiomechanicsDataset]:
    """Get datasets with priority >= min_priority."""
    return [d for d in PRIORITY_DATASETS if d.vitaflow_priority >= min_priority]


def search_datasets(
    movement_type: Optional[MovementType] = None,
    include_injured: Optional[bool] = None,
    min_subjects: Optional[int] = None
) -> List[BiomechanicsDataset]:
    """
    Search datasets by criteria.
    
    Args:
        movement_type: Filter by movement type
        include_injured: If True, only datasets with injured population
        min_subjects: Minimum number of subjects
    """
    results = PRIORITY_DATASETS.copy()
    
    if movement_type:
        results = [d for d in results if movement_type in d.movement_types]
    
    if include_injured is not None:
        results = [d for d in results if d.includes_injured == include_injured]
    
    if min_subjects:
        results = [d for d in results if d.subjects and d.subjects >= min_subjects]
    
    return sorted(results, key=lambda d: d.vitaflow_priority, reverse=True)


# Dataset index location (from cloned repo)
DATASET_INDEX_PATH = Path(__file__).parent.parent.parent.parent / "research-data" / "biomechanics_dataset" / "README.md"


if __name__ == "__main__":
    # Demo usage
    print("VitaFlow Biomechanics Integration")
    print("=" * 50)
    
    print("\nHigh-Priority Datasets:")
    for ds in get_high_priority_datasets(8):
        injured_tag = " [INJURED+HEALTHY]" if ds.includes_injured else ""
        subjects = f" ({ds.subjects} subjects)" if ds.subjects else ""
        print(f"  [{ds.vitaflow_priority}] {ds.name}{subjects}{injured_tag}")
    
    print("\nDatasets for injury pattern detection:")
    injury_datasets = search_datasets(include_injured=True)
    for ds in injury_datasets[:5]:
        print(f"  - {ds.name}: {ds.description}")
