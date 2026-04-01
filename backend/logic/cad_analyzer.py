import trimesh
import os
import numpy as np
import base64
import io
import uuid
import time
import logging

# Import the GMSH-based precise analyzer (no OCP dependency)
from .step_engine_ocp import PreciseSTEPAnalyzer

logger = logging.getLogger(__name__)


def analyze_cad(file_path):
    """
    Analyzes a CAD file using a simplified, robust pipeline:
    
    1. GMSH (Primary) — Reads STEP/IGES natively via its built-in OCCT kernel
    2. Trimesh (Fallback) — For STL/OBJ/PLY and as a secondary mesh loader
    
    No cadquery-ocp dependency. No pybind11 compatibility issues.
    """
    analysis_id = str(uuid.uuid4())
    ext = os.path.splitext(file_path)[1].lower()
    mesh = None
    precise_data = {}

    try:
        # ── Step 1: GMSH-Based Precise Analysis (for STEP/IGES) ──────────
        if ext in ['.step', '.stp', '.iges', '.igs']:
            logger.info(f"ANALYZER: Processing {ext} file via GMSH engine...")
            analyzer = PreciseSTEPAnalyzer()
            precise_data = analyzer.analyze(file_path)
            
            if precise_data.get("status") == "success":
                logger.info("ANALYZER: GMSH precise analysis succeeded.")
            else:
                logger.warning(f"ANALYZER: GMSH analysis returned: {precise_data.get('reason', 'unknown')}")

        # ── Step 2: Trimesh Mesh Load (for preview + fallback metrics) ───
        try:
            mesh_raw = trimesh.load(file_path)
            if isinstance(mesh_raw, trimesh.Scene):
                geometries = [g for g in mesh_raw.geometry.values() if isinstance(g, trimesh.Trimesh)]
                if geometries:
                    mesh = trimesh.util.concatenate(geometries)
            elif isinstance(mesh_raw, trimesh.Trimesh):
                mesh = mesh_raw
        except Exception as e:
            logger.warning(f"Trimesh direct load failed: {e}")

        # ── Step 3: If both methods produced nothing, hard fail ──────────
        if mesh is None and precise_data.get("status") != "success":
            reason = precise_data.get("reason", "No engine could parse this file")
            err_msg = (
                f"GEOMETRY_PARSE_FAILURE: File {ext} could not be read by "
                f"GMSH ({reason}) or Trimesh. Please ensure it is a valid 3D file."
            )
            raise ValueError(err_msg)

        # ── Step 4: Synthesize Traits ─────────────────────────────────────
        # Prefer GMSH precise data > Trimesh mesh approximation
        volume_cm3 = precise_data.get("precise_volume_cm3")
        surface_cm2 = precise_data.get("precise_surface_cm2")

        if volume_cm3 is None and mesh is not None:
            volume_cm3 = abs(mesh.volume) / 1000.0
        if surface_cm2 is None and mesh is not None:
            surface_cm2 = mesh.area / 100.0

        # Dimensions
        if "dimensions" in precise_data:
            dims = precise_data["dimensions"]
            dimensions = {"x": dims["x"], "y": dims["y"], "z": dims["z"]}
        elif mesh is not None:
            bounds = mesh.extents
            dimensions = {
                "x": round(float(bounds[0]), 2),
                "y": round(float(bounds[1]), 2),
                "z": round(float(bounds[2]), 2)
            }
        else:
            dimensions = {"x": 1.0, "y": 1.0, "z": 1.0}

        # Auto-Scale Detection (meter → mm)
        scale_factor = 1.0
        if max(dimensions.values()) < 1.0 and max(dimensions.values()) > 0:
            logger.info(f"ANALYZER: Tiny part detected ({max(dimensions.values())} units). Auto-scaling 1000x.")
            scale_factor = 1000.0
            dimensions = {k: v * scale_factor for k, v in dimensions.items()}
            volume_cm3 *= (scale_factor ** 3) / 1000000.0
            surface_cm2 *= (scale_factor ** 2) / 100.0

        # Projected Area
        max_projected_area = precise_data.get("projected_area_mm2")
        if max_projected_area is not None:
            max_projected_area *= (scale_factor ** 2)

        if max_projected_area is None:
            if mesh is not None:
                try:
                    areas = []
                    for ax in [[1, 0, 0], [0, 1, 0], [0, 0, 1]]:
                        proj = trimesh.path.polygons.projected(mesh, normal=ax)
                        areas.append(proj.area * (scale_factor ** 2))
                    max_projected_area = float(max(areas))
                except Exception:
                    max_projected_area = float(max(
                        dimensions['x'] * dimensions['y'],
                        dimensions['y'] * dimensions['z'],
                        dimensions['x'] * dimensions['z']
                    ))
            else:
                max_projected_area = float(max(
                    dimensions['x'] * dimensions['y'],
                    dimensions['y'] * dimensions['z'],
                    dimensions['x'] * dimensions['z']
                ))

        logger.info(f"GEOMETRY_DETECTED: Vol={round(volume_cm3, 2)}cm3, Area={round(max_projected_area, 2)}mm2 (Scale: {scale_factor}x)")

        # ── Step 5: Preview Generation ────────────────────────────────────
        preview_mesh_base64 = ""
        if mesh is not None:
            stl_io = io.BytesIO()
            mesh.export(stl_io, file_type='stl')
            preview_mesh_base64 = base64.b64encode(stl_io.getvalue()).decode('utf-8')

        # Topology
        topology = precise_data.get("topology", {
            "solids": 1,
            "faces": int(len(mesh.faces)) if mesh is not None else 0,
            "edges": 0,
            "vertices": int(len(mesh.vertices)) if mesh is not None else 0
        })
        
        # Validation
        validation = precise_data.get("validation", {
            "is_manifold": bool(mesh.is_watertight) if mesh is not None else False,
            "integrity_score": 100 if (mesh is not None and mesh.is_watertight) else 50
        })

        traits = {
            "volume": float(volume_cm3 * 1000.0),  # mm3
            "surface_area": float(surface_cm2 * 100.0),  # mm2
            "dimensions": dimensions,
            "projected_area": float(max_projected_area),
            "preview_mesh": f"data:model/stl;base64,{preview_mesh_base64}" if preview_mesh_base64 else "",
            "topology": topology,
            "validation": validation,
        }

        # Engine determination
        engine_name = "GMSH_PRECISE" if precise_data.get("status") == "success" else "TRIMESH_FALLBACK"

        return {
            "analysis_id": analysis_id,
            "traits": traits,
            "engine": engine_name,
            "metadata": {
                "location": "PENDING_SYNC",
                "timestamp": time.time()
            }
        }
    except Exception as e:
        logger.error(f"CRITICAL_BACKEND_FAILURE: {e}", exc_info=True)
        return {"error": str(e)}
