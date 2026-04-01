# HPDC Cost & Geometry Engine (V2.1.1)

A high-performance CAD geometry analyzer and cost estimation engine for High-Pressure Die Casting (HPDC). Optimized for production environments with low memory (512MB RAM) and complex STEP/IGES assemblies.

## 🚀 Quick Start (Docker)

The fastest way to run the engine is via Docker Desktop.

```bash
# 1. Clone the repository
git clone https://github.com/martian3062/step_alloyprediction.git
cd step_alloyprediction

# 2. Deploy locally via Docker Compose
docker compose up -d
```
Access the dashboard at: **[http://localhost:5000](http://localhost:5000)**

---

## 🏗️ Architecture: Dual-Engine Precise Pipeline (V2.1.1)

To solve persistent dependency crashes, V2.1.1 implements a mirrored analysis pipeline:

### 1. Primary Engine: **OCP (OpenCascade)**
- **Method**: Precise B-Rep Topography analysis.
- **Fix**: Uses corrected `_s` suffixes for pybind11 static methods (e.g., `VolumeProperties_s`).
- **Precision**: High-fidelity volume, surface area, and dimension extraction.

### 2. Fallback Engine: **GMSH (Mesh-Based)**
- **Method**: Fast STEP-to-Mesh conversion using GMSH's built-in OCCT kernel.
- **Role**: Automatically takes over if OCP encounters a binary incompatibility or timeout.
- **Resilience**: Ensures 100% parsing success for valid 3D files.

---

## ✨ Features & Metadata

### 🔍 Metal Auto-Detection
The engine scans STEP file descriptors for material keywords and automatically populates the metal parameter:
- **Aluminum**: A380, ADC12, 6061, AL
- **Zinc**: ZAMAK, ZD3, ZDC
- **Magnesium**: AZ91D, AM60, MG

### 📏 Geometric Traits
- **Precise Volume (cm³)**
- **Surface Area (cm²)**
- **Projected Area (mm²)**
- **Manifold Validation** (Watertightness check)

---

## 🛠️ Installation (Manual)

If running without Docker, ensure your environment has the required system libraries:

### OS Dependencies (Linux/Debian)
```bash
sudo apt-get update && sudo apt-get install -y \
    libgl1 libglu1-mesa libgomp1 libx11-6 libxext6 libxrender1
```

### Python Setup
```bash
pip install -r backend/requirements.txt
```

---

## ☁️ Deployment (Render.com)

> [!IMPORTANT]
> When deploying V2.1.1 to Render, you MUST choose **"Clear build cache & deploy"** to remove old broken OCP binaries.

1. Connect your GitHub repo to Render.
2. Use Docker Runtime.
3. Set `PORT=5000`.
4. Deploy using the **Clear Cache** option.

---

## 📜 Version History
- **V2.1.1**: Integrated Metal Detection & Robust BBox.
- **V2.1.0**: Dual-Engine (OCP/GMSH) Architecture.
- **V1.x**: Legacy OCP Engine.
