"""
AI Log Monitoring - ML Service
FastAPI application for anomaly detection using Isolation Forest
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from datetime import datetime

from app.api import health, anomaly
from app.services.model_service import ModelService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global model service instance
model_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    global model_service
    
    # Startup
    logger.info("Starting ML Service...")
    model_service = ModelService()
    
    # Try to load existing model
    try:
        model_service.load_model()
        logger.info("Loaded existing model successfully")
    except FileNotFoundError:
        logger.warning("No existing model found. Train a new model using /api/v1/train endpoint")
    except Exception as e:
        logger.error(f"Error loading model: {e}")
    
    app.state.model_service = model_service
    logger.info("ML Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ML Service...")


# Create FastAPI application
app = FastAPI(
    title="AI Log Monitoring - ML Service",
    description="Machine Learning service for log anomaly detection",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(anomaly.router, prefix="/api/v1", tags=["Anomaly Detection"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "AI Log Monitoring - ML Service",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

# Made with Bob
