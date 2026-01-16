"""
Anomaly detection endpoints
"""
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class LogFeatures(BaseModel):
    """Log features for anomaly detection"""
    message_length: int = Field(..., description="Length of log message")
    level: str = Field(..., description="Log level (INFO, WARN, ERROR, etc.)")
    service: str = Field(..., description="Service name")
    has_exception: bool = Field(default=False, description="Contains exception")
    has_timeout: bool = Field(default=False, description="Contains timeout")
    has_connection_error: bool = Field(default=False, description="Contains connection error")
    timestamp: Optional[str] = Field(None, description="Log timestamp")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class AnomalyPredictionRequest(BaseModel):
    """Request for anomaly prediction"""
    log_id: str = Field(..., description="Unique log identifier")
    features: LogFeatures = Field(..., description="Log features")


class AnomalyPredictionResponse(BaseModel):
    """Response for anomaly prediction"""
    model_config = {"protected_namespaces": ()}
    
    log_id: str
    is_anomaly: bool
    anomaly_score: float
    confidence: float
    timestamp: str
    model_version: str


class TrainingRequest(BaseModel):
    """Request for model training"""
    training_data: List[Dict[str, Any]] = Field(..., description="Training data samples")
    contamination: float = Field(default=0.1, ge=0.0, le=0.5, description="Expected proportion of anomalies")


class TrainingResponse(BaseModel):
    """Response for model training"""
    model_config = {"protected_namespaces": ()}
    
    status: str
    model_version: str
    samples_trained: int
    contamination: float
    trained_at: str


@router.post("/predict", response_model=AnomalyPredictionResponse)
async def predict_anomaly(
    request: Request,
    prediction_request: AnomalyPredictionRequest
) -> AnomalyPredictionResponse:
    """
    Predict if a log entry is anomalous
    
    Args:
        request: FastAPI request object
        prediction_request: Prediction request with log features
        
    Returns:
        Anomaly prediction result
    """
    model_service = request.app.state.model_service
    
    if model_service is None or model_service.model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded. Please train a model first using /api/v1/train endpoint"
        )
    
    try:
        # Predict anomaly
        result = model_service.predict(prediction_request.features.model_dump())
        
        return AnomalyPredictionResponse(
            log_id=prediction_request.log_id,
            is_anomaly=result["is_anomaly"],
            anomaly_score=result["anomaly_score"],
            confidence=result["confidence"],
            timestamp=datetime.utcnow().isoformat(),
            model_version=model_service.model_version
        )
        
    except Exception as e:
        logger.error(f"Error predicting anomaly: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error predicting anomaly: {str(e)}"
        )


@router.post("/predict/batch", response_model=List[AnomalyPredictionResponse])
async def predict_anomaly_batch(
    request: Request,
    prediction_requests: List[AnomalyPredictionRequest]
) -> List[AnomalyPredictionResponse]:
    """
    Predict anomalies for multiple log entries
    
    Args:
        request: FastAPI request object
        prediction_requests: List of prediction requests
        
    Returns:
        List of anomaly prediction results
    """
    model_service = request.app.state.model_service
    
    if model_service is None or model_service.model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded. Please train a model first"
        )
    
    try:
        results = []
        for pred_request in prediction_requests:
            result = model_service.predict(pred_request.features.model_dump())
            results.append(
                AnomalyPredictionResponse(
                    log_id=pred_request.log_id,
                    is_anomaly=result["is_anomaly"],
                    anomaly_score=result["anomaly_score"],
                    confidence=result["confidence"],
                    timestamp=datetime.utcnow().isoformat(),
                    model_version=model_service.model_version
                )
            )
        
        return results
        
    except Exception as e:
        logger.error(f"Error in batch prediction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in batch prediction: {str(e)}"
        )


@router.post("/train", response_model=TrainingResponse)
async def train_model(
    request: Request,
    training_request: TrainingRequest
) -> TrainingResponse:
    """
    Train a new anomaly detection model
    
    Args:
        request: FastAPI request object
        training_request: Training request with data and parameters
        
    Returns:
        Training result
    """
    model_service = request.app.state.model_service
    
    if model_service is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Model service not initialized"
        )
    
    try:
        logger.info(f"Training model with {len(training_request.training_data)} samples")
        
        # Train the model
        model_service.train(
            training_data=training_request.training_data,
            contamination=training_request.contamination
        )
        
        # Save the model
        model_service.save_model()
        
        logger.info(f"Model trained successfully: version {model_service.model_version}")
        
        return TrainingResponse(
            status="success",
            model_version=model_service.model_version,
            samples_trained=len(training_request.training_data),
            contamination=training_request.contamination,
            trained_at=model_service.trained_at
        )
        
    except Exception as e:
        logger.error(f"Error training model: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error training model: {str(e)}"
        )


@router.get("/model/info")
async def get_model_info(request: Request) -> Dict[str, Any]:
    """
    Get information about the current model
    
    Args:
        request: FastAPI request object
        
    Returns:
        Model information
    """
    model_service = request.app.state.model_service
    
    if model_service is None or model_service.model is None:
        return {
            "status": "not_loaded",
            "message": "No model is currently loaded"
        }
    
    return {
        "status": "loaded",
        "version": model_service.model_version,
        "trained_at": model_service.trained_at,
        "contamination": model_service.contamination,
        "model_type": "IsolationForest"
    }

# Made with Bob
