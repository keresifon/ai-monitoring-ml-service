"""
Utility functions for ML Service
"""
from datetime import datetime, timezone


def get_current_timestamp() -> str:
    """Return current UTC timestamp in ISO format"""
    return datetime.now(timezone.utc).isoformat()


def is_model_loaded(model_service) -> bool:
    """Check if the model service has a loaded model"""
    return model_service is not None and model_service.model is not None
