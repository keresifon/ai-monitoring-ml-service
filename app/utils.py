"""
Utility functions for the ML service
"""
from datetime import datetime, timezone
from typing import Optional
from app.services.model_service import ModelService


def get_current_timestamp() -> str:
    """
    Get current UTC timestamp in ISO format
    
    Returns:
        ISO formatted timestamp string
    """
    return datetime.now(timezone.utc).isoformat()


def is_model_loaded(model_service: Optional[ModelService]) -> bool:
    """
    Check if model service has a loaded model
    
    Args:
        model_service: ModelService instance
        
    Returns:
        True if model is loaded, False otherwise
    """
    return model_service is not None and model_service.model is not None

# Made with Bob
