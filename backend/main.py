import sys
import os
import io
import time
import zipfile
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse

# Add project root to sys.path
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.routes.predict import router as predict_router
from backend.routes.benchmarks import router as benchmarks_router
from backend.routes.dataset import router as dataset_router
from backend.routes.history import router as history_router
from backend.services.ml_service import ml_service
from backend.services.history_service import history_service

START_TIME = time.time()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load/train models and initialize pipelines
    print("[Quantara FastAPI] Starting server and initializing ML/QML pipelines...")
    ml_service.initialize()
    
    # Pre-seed history with realistic clinical evaluations if empty
    existing = history_service.get_all_history(limit=5)
    if not existing:
        print("[Quantara FastAPI] Seeding sample historical prediction records...")
        presets = ml_service.get_preset_patients()
        for p in presets[:3]:
            pred = ml_service.predict_patient(p["features"])
            history_service.add_history(
                id=pred["patient_id"],
                timestamp=pred["timestamp"],
                patient_name=p["name"],
                risk_level=pred["selected_risk_level"],
                risk_probability=pred["selected_probability"],
                confidence=pred["selected_confidence"],
                selected_model=pred["recommended_model"],
                classical_probability=pred["classical_probability"],
                qml_probability=pred["qml_probability"],
                features=p["features"],
                top_contributor=pred["top_features"][0]["feature"] if pred["top_features"] else "AST",
                notes=f"Initial seeded demonstration record ({p['category']})"
            )
    yield
    print("[Quantara FastAPI] Shutting down.")

app = FastAPI(
    title="Quantara API — Hybrid Quantum Disease Detection Platform",
    description="End-to-End Quantum-Classical Machine Learning Platform for Early Disease Detection, Model Routing, and Clinical Explainability.",
    version="2.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routes
app.include_router(predict_router, prefix="/api")
app.include_router(benchmarks_router, prefix="/api")
app.include_router(dataset_router, prefix="/api")
app.include_router(history_router, prefix="/api")

@app.get("/api/download-zip", tags=["System"])
@app.get("/download-zip", tags=["System"])
def download_zip():
    """Generates and serves a clean ZIP archive of the entire project."""
    zip_path = PROJECT_ROOT.parent / "Quantara-main.zip"
    if zip_path.exists():
        return FileResponse(
            path=str(zip_path),
            filename="Quantara-main.zip",
            media_type="application/zip"
        )
    buffer = io.BytesIO()
    exclude_dirs = {'node_modules', 'venv', '__pycache__', '.git', '.pytest_cache', 'dist', '.vite'}
    exclude_exts = {'.pyc', '.pyo'}
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(PROJECT_ROOT):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for file in files:
                if any(file.endswith(ext) for ext in exclude_exts):
                    continue
                full_path = Path(root) / file
                rel_path = Path('Quantara-main') / full_path.relative_to(PROJECT_ROOT)
                zf.write(full_path, rel_path)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=Quantara-main.zip"}
    )

@app.get("/health", tags=["System"])
def health():
    """System health check and status."""
    uptime_seconds = round(time.time() - START_TIME, 2)
    return {
        "status": "online",
        "system": "Quantara Hybrid Quantum-Classical Platform",
        "version": "2.0.0",
        "uptime_seconds": uptime_seconds,
        "quantum_simulator": "PennyLane default.qubit (Active)",
        "models_loaded": {
            "classical": ["Logistic Regression", "Random Forest", "XGBoost"],
            "quantum": ["Optimized 4-Qubit VQC"]
        },
        "explainability_engine": "Permutation Importance + Latent QML Sensitivity",
        "adaptive_router": "Confidence & Historical Benchmark Weighted"
    }

@app.get("/", tags=["System"])
def root():
    return {
        "message": "Welcome to Quantara Hybrid Quantum-Classical Healthcare Platform API",
        "docs_url": "/docs",
        "health_check": "/health",
        "download_zip": "/api/download-zip"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)

