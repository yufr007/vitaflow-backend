"""
VitaFlow Reference Data Ingestion Script

Loads C3D motion capture files and computes statistical baselines
for form analysis. Run once to populate the reference database.

Usage:
    python scripts/ingest_reference_data.py

Output:
    data/reference_baselines.json - Statistical baselines for all movement types
"""
import sys
from pathlib import Path
from typing import Dict, List, Any
import json
import numpy as np
import logging

# Add backend to path
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

try:
    from integrations.biomechanics import (
        C3DProcessor, MovementType, FormAnalyzer,
        SkeletonFrame, MovementSequence
    )
    print("✓ Biomechanics integration loaded")
except ImportError as e:
    print(f"✗ Failed to import biomechanics: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def compute_squat_baselines(c3d_files: List[Path]) -> Dict[str, Any]:
    """Compute statistical baselines from reference squat files."""
    
    processor = C3DProcessor(backend="ezc3d")
    analyzer = FormAnalyzer()
    
    all_knee_angles = []
    all_hip_angles = []
    all_torso_angles = []
    
    successful_loads = 0
    
    for c3d_path in c3d_files:
        try:
            logger.info(f"Processing: {c3d_path.name}")
            data = processor.load(str(c3d_path))
            
            sequence = processor.to_movement_sequence(
                data, MovementType.SQUAT,
                source_dataset="reference",
                subject_id=c3d_path.stem
            )
            
            # Calculate angles for each frame
            for frame in sequence.frames:
                knee = analyzer._calculate_knee_angle(frame)
                hip = analyzer._calculate_hip_angle(frame)
                torso = analyzer._calculate_torso_angle(frame)
                
                if knee is not None:
                    all_knee_angles.append(knee)
                if hip is not None:
                    all_hip_angles.append(hip)
                if torso is not None:
                    all_torso_angles.append(torso)
            
            successful_loads += 1
                
        except Exception as e:
            logger.warning(f"Error processing {c3d_path.name}: {e}")
    
    if not all_knee_angles:
        logger.warning("No knee angles extracted - using literature defaults")
        return get_default_squat_baselines()
    
    # Compute statistics
    baselines = {
        "knee_angle": {
            "mean": float(np.mean(all_knee_angles)),
            "std": float(np.std(all_knee_angles)),
            "p5": float(np.percentile(all_knee_angles, 5)),
            "p95": float(np.percentile(all_knee_angles, 95)),
            "min": float(np.min(all_knee_angles)),
            "max": float(np.max(all_knee_angles)),
            "optimal_range": [80, 95],  # Literature values for squat depth
            "injury_risk_threshold": 60,  # Below this = insufficient depth
        },
        "hip_angle": {
            "mean": float(np.mean(all_hip_angles)) if all_hip_angles else 90.0,
            "std": float(np.std(all_hip_angles)) if all_hip_angles else 15.0,
            "p5": float(np.percentile(all_hip_angles, 5)) if all_hip_angles else 45.0,
            "p95": float(np.percentile(all_hip_angles, 95)) if all_hip_angles else 170.0,
        },
        "torso_angle": {
            "mean": float(np.mean(all_torso_angles)) if all_torso_angles else 75.0,
            "std": float(np.std(all_torso_angles)) if all_torso_angles else 10.0,
            "p5": float(np.percentile(all_torso_angles, 5)) if all_torso_angles else 45.0,
            "p95": float(np.percentile(all_torso_angles, 95)) if all_torso_angles else 90.0,
            "forward_lean_threshold": 60,  # Below this = excessive forward lean
        },
        "source": "VitaFlow C3D Reference Database",
        "n_samples": len(all_knee_angles),
        "n_files_processed": successful_loads,
    }
    
    logger.info(f"Computed baselines from {successful_loads} files, {len(all_knee_angles)} samples")
    return baselines


def get_default_squat_baselines() -> Dict[str, Any]:
    """Return literature-based default baselines when C3D files unavailable."""
    return {
        "knee_angle": {
            "mean": 90.0,
            "std": 10.0,
            "p5": 70.0,
            "p95": 110.0,
            "min": 60.0,
            "max": 120.0,
            "optimal_range": [80, 95],
            "injury_risk_threshold": 60,
        },
        "hip_angle": {
            "mean": 90.0,
            "std": 15.0,
            "p5": 45.0,
            "p95": 170.0,
        },
        "torso_angle": {
            "mean": 75.0,
            "std": 10.0,
            "p5": 45.0,
            "p95": 90.0,
            "forward_lean_threshold": 60,
        },
        "source": "Literature defaults (Schoenfeld et al. 2010, NSCA guidelines)",
        "n_samples": 0,
        "n_files_processed": 0,
    }


def compute_gait_baselines() -> Dict[str, Any]:
    """Return gait/running baselines from literature."""
    return {
        "stride_length": {
            "mean": 1.4,
            "std": 0.2,
            "unit": "meters"
        },
        "cadence": {
            "mean": 170,
            "std": 10,
            "unit": "steps/min"
        },
        "ground_contact": {
            "mean": 0.25,
            "std": 0.03,
            "unit": "seconds"
        },
        "knee_flexion_at_contact": {
            "mean": 20,
            "std": 5,
            "unit": "degrees"
        },
        "source": "Running biomechanics literature (Ferber et al. 2024)",
        "n_samples": 0,
    }


def main():
    """Main ingestion pipeline."""
    print("=" * 60)
    print("VitaFlow Reference Data Ingestion")
    print("=" * 60)
    
    # Find C3D sample files
    samples_dir = backend_root.parent / "research-data" / "pyc3dserver_examples" / "Samples_C3D"
    
    if not samples_dir.exists():
        logger.warning(f"Samples directory not found: {samples_dir}")
        logger.warning("Using literature defaults instead")
        c3d_files = []
    else:
        c3d_files = list(samples_dir.glob("**/*.c3d")) + list(samples_dir.glob("**/*.C3D"))
        logger.info(f"Found {len(c3d_files)} C3D files")
    
    # Compute baselines for each movement type
    baselines = {
        "squat": compute_squat_baselines(c3d_files) if c3d_files else get_default_squat_baselines(),
        "gait": compute_gait_baselines(),
        "running": compute_gait_baselines(),  # Same as gait for now
        "metadata": {
            "generated_at": "2026-01-21",
            "version": "1.0.0",
            "description": "Statistical baselines for VitaFlow form analysis"
        }
    }
    
    # Save to JSON
    output_dir = backend_root / "data"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "reference_baselines.json"
    
    with open(output_path, "w") as f:
        json.dump(baselines, f, indent=2)
    
    print("\n" + "=" * 60)
    print("✓ Baselines saved to:", output_path)
    print("=" * 60)
    print("\nSummary:")
    print(f"  Squat samples: {baselines['squat']['n_samples']}")
    print(f"  Squat files: {baselines['squat']['n_files_processed']}")
    print(f"  Knee angle range: {baselines['squat']['knee_angle']['min']:.1f}° - {baselines['squat']['knee_angle']['max']:.1f}°")
    print(f"  Source: {baselines['squat']['source']}")
    print("\nNext steps:")
    print("  1. Restart backend to load new baselines")
    print("  2. Test form check with squat image")
    print("  3. Verify computed metrics use reference data")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nIngestion cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        sys.exit(1)
