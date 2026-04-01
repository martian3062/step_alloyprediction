"""
STEP/IGES Geometry Engine — GMSH-Primary Architecture (V2)
No OCP dependency. Uses GMSH for STEP→Mesh conversion, Trimesh for analysis.
Includes: Metal Auto-Detection from STEP file metadata.
"""

import logging
import os
import gc
import uuid
import trimesh
import numpy as np
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# ─── Metal Keyword Detection Map ────────────────────────────────────────────
METAL_KEYWORDS = {
    "A380": "Aluminum_A380",
    "A383": "Aluminum_A380",
    "A360": "Aluminum_A380",
    "ADC12": "Aluminum_A380",
    "ALUMINUM": "Aluminum_A380",
    "ALUMINIUM": "Aluminum_A380",
    "AL": "Aluminum_A380",
    "6061": "Aluminum_A380",
    "6063": "Aluminum_A380",
    "ZINC": "Zinc_ZD3",
    "ZAMAK": "Zinc_ZD3",
    "ZA": "Zinc_ZD3",
    "ZDC": "Zinc_ZD3",
    "MAGNESIUM": "Magnesium_AZ91D",
    "AZ91": "Magnesium_AZ91D",
    "AM60": "Magnesium_AZ91D",
    "MG": "Magnesium_AZ91D",
}

def detect_metal_from_step(file_path: str) -> Optional[str]:
    try:
        with open(file_path, 'r', errors='ignore') as f:
            content = f.read(8192)
        content_upper = content.upper()
        for keyword, metal_name in METAL_KEYWORDS.items():
            if keyword in content_upper:
                return metal_name
    except Exception as e:
        logger.warning(f"Metal detection scan failed: {e}")
    return None


# ═══════════════════════════════════════════════════════════════════════════
#  GMSH-Based Precise Analyzer (Primary Engine — No OCP needed)
# ═══════════════════════════════════════════════════════════════════════════

class PreciseSTEPAnalyzer:
    """
    Production-grade STEP analyzer using GMSH for geometry + Trimesh for metrics.
    
    Pipeline:
      1. GMSH reads the STEP/IGES file natively (it has its own OCCT kernel built-in)
      2. GMSH generates a high-quality surface mesh
      3. Trimesh analyzes the mesh for volume, area, bbox, topology
    
    This completely bypasses the cadquery-ocp pybind11 bindings that are
    incompatible with the Render deployment environment.
    """

    def __init__(self):
        self._gmsh_available = None

    def _check_gmsh(self) -> bool:
        """Lazy-check for GMSH availability."""
        if self._gmsh_available is not None:
            return self._gmsh_available
        try:
            import gmsh
            self._gmsh_available = True
            return True
        except ImportError:
            logger.error("GMSH not installed. PreciseSTEPAnalyzer disabled.")
            self._gmsh_available = False
            return False
        except Exception as e:
            logger.error(f"GMSH init check failed: {e}")
            self._gmsh_available = False
            return False

    def _step_to_mesh(self, file_path: str) -> Optional[trimesh.Trimesh]:
        """
        Convert STEP/IGES → high-quality trimesh using GMSH's built-in OCCT kernel.
        GMSH ships with its own OpenCascade, so this works independently of cadquery-ocp.
        """
        if not self._check_gmsh():
            return None

        import gmsh
        temp_stl = None
        try:
            gmsh.initialize()
            gmsh.option.setNumber("General.Terminal", 0)  # Suppress console output
            gmsh.model.add("StepAnalysis")
            
            # GMSH natively supports STEP and IGES via its built-in OCCT kernel
            gmsh.merge(file_path)
            
            # Generate a fine surface mesh for accurate volume/area calculation
            gmsh.option.setNumber("Mesh.MeshSizeMin", 0.1)
            gmsh.option.setNumber("Mesh.MeshSizeMax", 5.0)
            gmsh.option.setNumber("Mesh.Algorithm", 6)  # Frontal-Delaunay
            gmsh.model.mesh.generate(2)  # Surface mesh only — lighter on RAM
            
            # Export to temporary STL
            temp_stl = f"/tmp/gmsh_precise_{uuid.uuid4().hex[:8]}.stl"
            gmsh.write(temp_stl)
            gmsh.finalize()
            
            # Load with trimesh
            mesh = trimesh.load(temp_stl)
            if isinstance(mesh, trimesh.Scene):
                mesh = trimesh.util.concatenate(
                    [g for g in mesh.geometry.values() if isinstance(g, trimesh.Trimesh)]
                )
            
            return mesh

        except Exception as e:
            logger.error(f"GMSH STEP→Mesh conversion failed: {e}")
            try:
                gmsh.finalize()
            except:
                pass
            return None
        finally:
            # Cleanup temp file
            if temp_stl and os.path.exists(temp_stl):
                try:
                    os.remove(temp_stl)
                except:
                    pass
            gc.collect()

    def analyze(self, file_path: str) -> Dict[str, Any]:
        """
        Full geometry analysis pipeline.
        Returns precise volume, surface area, dimensions, topology,
        and validation metrics from the GMSH-generated mesh.
        """
        mesh = self._step_to_mesh(file_path)
        
        if mesh is None or not hasattr(mesh, 'vertices') or len(mesh.vertices) == 0:
            return {"status": "fallback", "reason": "GMSH_MESH_FAILED"}

        try:
            # Volume & Surface Area from mesh
            volume_mm3 = abs(mesh.volume) if mesh.volume else 0.0
            surface_mm2 = mesh.area if mesh.area else 0.0
            
            # Bounding box
            bounds = mesh.bounds  # [[xmin,ymin,zmin], [xmax,ymax,zmax]]
            dims = mesh.extents   # [dx, dy, dz]
            dx, dy, dz = float(dims[0]), float(dims[1]), float(dims[2])
            
            # Projected area (max of 3 bounding-box face areas)
            projected_area = max(dx * dy, dy * dz, dx * dz)
            
            # Basic topology from mesh
            topology = {
                "solids": 1,
                "shells": 1,
                "faces": int(len(mesh.faces)),
                "edges": int(len(mesh.edges_unique)) if hasattr(mesh, 'edges_unique') else 0,
                "vertices": int(len(mesh.vertices))
            }
            
            # Validation
            is_watertight = bool(mesh.is_watertight)
            
            result = {
                "status": "success",
                "precise_volume_cm3": round(volume_mm3 / 1000.0, 4),
                "precise_surface_cm2": round(surface_mm2 / 100.0, 4),
                "projected_area_mm2": round(projected_area, 2),
                "dimensions": {
                    "x": round(dx, 2),
                    "y": round(dy, 2),
                    "z": round(dz, 2)
                },
                "topology": topology,
                "validation": {
                    "is_manifold": is_watertight,
                    "integrity_score": 100 if is_watertight else 70
                }
            }
            
            # Memory cleanup
            del mesh
            gc.collect()
            return result

        except Exception as e:
            logger.error(f"Mesh analysis failed: {e}", exc_info=True)
            return {"status": "fallback", "reason": f"MESH_ANALYSIS_ERROR: {str(e)}"}
