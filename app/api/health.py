"""
Health check endpoints
"""
from fastapi import APIRouter, Request
from datetime import datetime
from typing import Dict, Any

router = APIRouter()


@router.get("/health")
async def health_check(request: Request) -> Dict[str, Any]:
    """
    Health check endpoint
    
    Returns:
        Health status information
    """
    model_service = request.app.state.model_service
    
    model_status = "not_loaded"
    model_info = None
    
    if model_service and model_service.model is not None:
        model_status = "loaded"
        model_info = {
            "version": model_service.model_version,
            "trained_at": model_service.trained_at,
            "contamination": model_service.contamination
        }
    
    return {
        "status": "UP",
        "service": "ml-service",
        "timestamp": datetime.utcnow().isoformat(),
        "model": {
            "status": model_status,
            "info": model_info
        }
    }


@router.get("/ready")
async def readiness_check(request: Request) -> Dict[str, Any]:
    """
    Readiness check endpoint
    
    Returns:
        Readiness status
    """
    model_service = request.app.state.model_service
    
    is_ready = model_service is not None and model_service.model is not None
    
    return {
        "ready": is_ready,
        "timestamp": datetime.utcnow().isoformat()
    }

# Made with Bob
