"""
Health check endpoints
"""
from fastapi import APIRouter, Request
from typing import Dict, Any
from app.utils import get_current_timestamp, is_model_loaded

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
    
    if is_model_loaded(model_service):
        model_status = "loaded"
        model_info = {
            "version": model_service.model_version,
            "trained_at": model_service.trained_at,
            "contamination": model_service.contamination
        }
    
    return {
        "status": "UP",
        "service": "ml-service",
        "timestamp": get_current_timestamp(),
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
    
    return {
        "ready": is_model_loaded(model_service),
        "timestamp": get_current_timestamp()
    }

# Made with Bob
