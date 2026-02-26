"""
Integration tests for ML Service API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock
from fastapi import FastAPI
from app.services.model_service import ModelService
from app.api import health, anomaly
from app.api.anomaly import _build_prediction_response, _require_model_loaded


# Create a test app without lifespan to avoid loading models from disk
@pytest.fixture(scope="module")
def test_app():
    """Create a test FastAPI app without lifespan"""
    from datetime import datetime
    
    test_app = FastAPI(
        title="AI Log Monitoring - ML Service (Test)",
        description="Machine Learning service for log anomaly detection - Test",
        version="1.0.0"
    )
    
    # Include routers
    test_app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    test_app.include_router(anomaly.router, prefix="/api/v1", tags=["Anomaly Detection"])
    
    # Add root endpoint
    @test_app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "service": "AI Log Monitoring - ML Service",
            "version": "1.0.0",
            "status": "running",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    return test_app


# Create a mock model service for testing
@pytest.fixture(scope="module")
def test_client(test_app):
    """Create test client with mocked model service"""
    # Create a mock model service
    mock_model_service = Mock(spec=ModelService)
    mock_model_service.model = None  # No model loaded by default
    mock_model_service.model_version = "test-v1.0.0"
    mock_model_service.trained_at = "2024-01-01T00:00:00"
    mock_model_service.contamination = 0.1
    
    # Set it in app state before creating client
    test_app.state.model_service = mock_model_service
    
    # Create test client
    with TestClient(test_app) as client:
        yield client


class TestAnomalyHelpers:
    """Test cases for anomaly module helpers"""

    def test_build_prediction_response(self):
        """Test _build_prediction_response creates correct response"""
        result = _build_prediction_response(
            log_id="test-1",
            result={"is_anomaly": True, "anomaly_score": 0.9, "confidence": 0.95},
            model_version="v1.0.0"
        )
        assert result.log_id == "test-1"
        assert result.is_anomaly is True
        assert result.anomaly_score == 0.9
        assert result.confidence == 0.95
        assert result.model_version == "v1.0.0"
        assert result.timestamp  # ISO format string from get_current_timestamp

    def test_require_model_loaded_raises_when_none(self):
        """Test _require_model_loaded raises 503 when model not loaded"""
        from fastapi import HTTPException

        mock_service = Mock()
        mock_service.model = None
        with pytest.raises(HTTPException) as exc_info:
            _require_model_loaded(mock_service)
        assert exc_info.value.status_code == 503
        assert "not loaded" in exc_info.value.detail.lower()

    def test_require_model_loaded_passes_when_loaded(self):
        """Test _require_model_loaded does nothing when model loaded"""
        mock_service = Mock()
        mock_service.model = Mock()
        _require_model_loaded(mock_service)  # Should not raise


class TestRootEndpoint:
    """Test cases for root endpoint"""

    def test_root(self, test_client):
        """Test root endpoint"""
        response = test_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert "status" in data


class TestHealthEndpoint:
    """Test cases for health check endpoint"""

    def test_health_check(self, test_client):
        """Test that health endpoint returns 200 OK"""
        response = test_client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "UP"
        assert "service" in data
        assert data["service"] == "ml-service"
        assert "model" in data
        assert data["model"]["status"] == "not_loaded"

    def test_health_check_with_model_loaded(self, test_client):
        """Test health endpoint when model is loaded"""
        test_client.app.state.model_service.model = Mock()
        response = test_client.get("/api/v1/health")
        test_client.app.state.model_service.model = None

        assert response.status_code == 200
        data = response.json()
        assert data["model"]["status"] == "loaded"
        assert "info" in data["model"]
        assert data["model"]["info"]["version"] == "test-v1.0.0"

    def test_readiness_check(self, test_client):
        """Test readiness endpoint"""
        response = test_client.get("/api/v1/ready")
        
        assert response.status_code == 200
        data = response.json()
        assert "ready" in data
        assert data["ready"] is False  # Model not loaded
        assert "timestamp" in data


class TestModelInfo:
    """Test cases for model info endpoint"""
    
    def test_get_model_info_not_loaded(self, test_client):
        """Test getting model information when model not loaded"""
        response = test_client.get("/api/v1/model/info")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "not_loaded"
        assert "message" in data
    
    def test_get_model_info_loaded(self, test_client):
        """Test getting model information when model is loaded"""
        # Mock a loaded model
        from unittest.mock import Mock
        mock_model = Mock()
        test_client.app.state.model_service.model = mock_model
        test_client.app.state.model_service.model_version = "v1.2.3"
        test_client.app.state.model_service.trained_at = "2024-01-15T10:00:00"
        test_client.app.state.model_service.contamination = 0.15
        
        response = test_client.get("/api/v1/model/info")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "loaded"
        assert data["version"] == "v1.2.3"
        assert data["trained_at"] == "2024-01-15T10:00:00"
        assert data["contamination"] == 0.15
        assert data["model_type"] == "IsolationForest"
        
        # Clean up
        test_client.app.state.model_service.model = None


class TestAnomalyPrediction:
    """Test cases for anomaly prediction endpoints"""
    
    def test_predict_without_model_loaded(self, test_client):
        """Test prediction fails when model not loaded"""
        prediction_request = {
            "log_id": "test-log-123",
            "features": {
                "message_length": 100,
                "level": "ERROR",
                "service": "test-service",
                "has_exception": True,
                "has_timeout": False,
                "has_connection_error": False
            }
        }
        
        response = test_client.post("/api/v1/predict", json=prediction_request)
        
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data
        assert "not loaded" in data["detail"].lower()
    
    def test_predict_with_model_loaded(self, test_client):
        """Test successful prediction with loaded model"""
        from unittest.mock import Mock
        
        # Mock a loaded model
        mock_model = Mock()
        test_client.app.state.model_service.model = mock_model
        test_client.app.state.model_service.model_version = "v1.0.0"
        test_client.app.state.model_service.predict = Mock(return_value={
            "is_anomaly": True,
            "anomaly_score": 0.85,
            "confidence": 0.92
        })
        
        prediction_request = {
            "log_id": "test-log-456",
            "features": {
                "message_length": 250,
                "level": "ERROR",
                "service": "payment-service",
                "has_exception": True,
                "has_timeout": True,
                "has_connection_error": False
            }
        }
        
        response = test_client.post("/api/v1/predict", json=prediction_request)
        
        assert response.status_code == 200
        data = response.json()
        assert data["log_id"] == "test-log-456"
        assert data["is_anomaly"] is True
        assert data["anomaly_score"] == 0.85
        assert data["confidence"] == 0.92
        assert "timestamp" in data
        assert data["model_version"] == "v1.0.0"
        
        # Clean up
        test_client.app.state.model_service.model = None
    
    def test_predict_with_optional_features(self, test_client):
        """Test predict accepts LogFeatures with optional timestamp and metadata"""
        test_client.app.state.model_service.model = Mock()
        test_client.app.state.model_service.predict = Mock(
            return_value={"is_anomaly": False, "anomaly_score": 0.2, "confidence": 0.8}
        )

        response = test_client.post(
            "/api/v1/predict",
            json={
                "log_id": "log-opt",
                "features": {
                    "message_length": 80,
                    "level": "WARN",
                    "service": "api",
                    "has_exception": False,
                    "has_timeout": False,
                    "has_connection_error": False,
                    "timestamp": "2024-01-15T10:00:00",
                    "metadata": {"key": "value"},
                },
            },
        )
        test_client.app.state.model_service.model = None

        assert response.status_code == 200
        assert response.json()["log_id"] == "log-opt"

    def test_predict_with_invalid_features(self, test_client):
        """Test prediction with missing required features"""
        prediction_request = {
            "log_id": "test-log-789",
            "features": {
                "message_length": 100
                # Missing required fields: level, service
            }
        }

        response = test_client.post("/api/v1/predict", json=prediction_request)

        assert response.status_code == 422  # Validation error

    def test_predict_exception_handling(self, test_client):
        """Test predict returns 500 when model raises"""
        test_client.app.state.model_service.model = Mock()
        test_client.app.state.model_service.predict = Mock(
            side_effect=ValueError("Model error")
        )

        response = test_client.post(
            "/api/v1/predict",
            json={
                "log_id": "log-1",
                "features": {
                    "message_length": 100,
                    "level": "INFO",
                    "service": "api",
                    "has_exception": False,
                    "has_timeout": False,
                    "has_connection_error": False,
                },
            },
        )

        assert response.status_code == 500
        assert "Error predicting anomaly" in response.json()["detail"]
        test_client.app.state.model_service.model = None

    def test_predict_batch_without_model(self, test_client):
        """Test batch prediction fails when model not loaded"""
        batch_request = [
            {
                "log_id": "log-1",
                "features": {
                    "message_length": 100,
                    "level": "INFO",
                    "service": "api-service",
                    "has_exception": False,
                    "has_timeout": False,
                    "has_connection_error": False
                }
            }
        ]
        
        response = test_client.post("/api/v1/predict/batch", json=batch_request)
        
        assert response.status_code == 503
    
    def test_predict_batch_with_model_loaded(self, test_client):
        """Test successful batch prediction"""
        from unittest.mock import Mock
        
        # Mock a loaded model
        mock_model = Mock()
        test_client.app.state.model_service.model = mock_model
        test_client.app.state.model_service.model_version = "v1.0.0"
        
        # Mock predict to return different results for each call
        predict_results = [
            {"is_anomaly": False, "anomaly_score": 0.25, "confidence": 0.88},
            {"is_anomaly": True, "anomaly_score": 0.92, "confidence": 0.95}
        ]
        test_client.app.state.model_service.predict = Mock(side_effect=predict_results)
        
        batch_request = [
            {
                "log_id": "log-1",
                "features": {
                    "message_length": 50,
                    "level": "INFO",
                    "service": "api-service",
                    "has_exception": False,
                    "has_timeout": False,
                    "has_connection_error": False
                }
            },
            {
                "log_id": "log-2",
                "features": {
                    "message_length": 300,
                    "level": "ERROR",
                    "service": "db-service",
                    "has_exception": True,
                    "has_timeout": True,
                    "has_connection_error": True
                }
            }
        ]
        
        response = test_client.post("/api/v1/predict/batch", json=batch_request)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["log_id"] == "log-1"
        assert data[0]["is_anomaly"] is False
        assert data[1]["log_id"] == "log-2"
        assert data[1]["is_anomaly"] is True
        
        # Clean up
        test_client.app.state.model_service.model = None

    def test_predict_batch_exception_handling(self, test_client):
        """Test batch predict returns 500 when model raises"""
        test_client.app.state.model_service.model = Mock()
        test_client.app.state.model_service.predict = Mock(
            side_effect=RuntimeError("Batch error")
        )

        response = test_client.post(
            "/api/v1/predict/batch",
            json=[
                {
                    "log_id": "log-1",
                    "features": {
                        "message_length": 50,
                        "level": "INFO",
                        "service": "api",
                        "has_exception": False,
                        "has_timeout": False,
                        "has_connection_error": False,
                    },
                },
            ],
        )

        assert response.status_code == 500
        assert "Error in batch prediction" in response.json()["detail"]
        test_client.app.state.model_service.model = None


class TestModelTraining:
    """Test cases for model training endpoint"""
    
    def test_train_model_success(self, test_client):
        """Test successful model training"""
        from unittest.mock import Mock
        
        # Mock the model service methods
        test_client.app.state.model_service.train = Mock()
        test_client.app.state.model_service.save_model = Mock()
        test_client.app.state.model_service.model_version = "v2.0.0"
        test_client.app.state.model_service.trained_at = "2024-01-15T12:00:00"
        
        training_request = {
            "training_data": [
                {"message_length": 50, "level": "INFO", "service": "api", "has_exception": False, "has_timeout": False, "has_connection_error": False},
                {"message_length": 100, "level": "WARN", "service": "db", "has_exception": False, "has_timeout": False, "has_connection_error": False},
                {"message_length": 200, "level": "ERROR", "service": "cache", "has_exception": True, "has_timeout": False, "has_connection_error": False}
            ],
            "contamination": 0.15
        }
        
        response = test_client.post("/api/v1/train", json=training_request)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["model_version"] == "v2.0.0"
        assert data["samples_trained"] == 3
        assert data["contamination"] == 0.15
        assert "trained_at" in data
        
        # Verify methods were called
        test_client.app.state.model_service.train.assert_called_once()
        test_client.app.state.model_service.save_model.assert_called_once()
    
    def test_train_with_invalid_contamination(self, test_client):
        """Test training with invalid contamination value"""
        training_request = {
            "training_data": [
                {"message_length": 50, "level": "INFO", "service": "api", "has_exception": False, "has_timeout": False, "has_connection_error": False}
            ],
            "contamination": 0.6  # Invalid: must be <= 0.5
        }

        response = test_client.post("/api/v1/train", json=training_request)

        assert response.status_code == 422  # Validation error

    def test_train_with_contamination_boundary(self, test_client):
        """Test training with valid contamination at upper boundary (0.5)"""
        test_client.app.state.model_service.train = Mock()
        test_client.app.state.model_service.save_model = Mock()
        test_client.app.state.model_service.model_version = "v1.0.0"
        test_client.app.state.model_service.trained_at = "2024-01-01T00:00:00"

        response = test_client.post(
            "/api/v1/train",
            json={
                "training_data": [
                    {"message_length": 50, "level": "INFO", "service": "api",
                     "has_exception": False, "has_timeout": False, "has_connection_error": False},
                ],
                "contamination": 0.5,
            },
        )
        assert response.status_code == 200
    
    def test_train_with_empty_data(self, test_client):
        """Test training with empty training data"""
        training_request = {
            "training_data": [],
            "contamination": 0.1
        }

        response = test_client.post("/api/v1/train", json=training_request)

        # Should accept the request but may fail during training
        assert response.status_code in [200, 500]

    def test_train_exception_handling(self, test_client):
        """Test train returns 500 when model service raises"""
        test_client.app.state.model_service.train = Mock(
            side_effect=RuntimeError("Training failed")
        )
        test_client.app.state.model_service.save_model = Mock()

        response = test_client.post(
            "/api/v1/train",
            json={
                "training_data": [
                    {
                        "message_length": 50,
                        "level": "INFO",
                        "service": "api",
                        "has_exception": False,
                        "has_timeout": False,
                        "has_connection_error": False,
                    }
                ],
                "contamination": 0.1,
            },
        )

        assert response.status_code == 500
        assert "Error training model" in response.json()["detail"]

    def test_train_save_model_exception(self, test_client):
        """Test train returns 500 when save_model raises"""
        test_client.app.state.model_service.train = Mock()
        test_client.app.state.model_service.save_model = Mock(
            side_effect=OSError("Disk full")
        )
        test_client.app.state.model_service.model_version = "v1.0.0"
        test_client.app.state.model_service.trained_at = "2024-01-01T00:00:00"

        response = test_client.post(
            "/api/v1/train",
            json={
                "training_data": [
                    {
                        "message_length": 50,
                        "level": "INFO",
                        "service": "api",
                        "has_exception": False,
                        "has_timeout": False,
                        "has_connection_error": False,
                    }
                ],
                "contamination": 0.1,
            },
        )

        assert response.status_code == 500
        assert "Error training model" in response.json()["detail"]

    def test_train_with_real_model_service(self, test_app):
        """Test train endpoint with real ModelService (full train/save flow)"""
        import tempfile
        import shutil

        temp_dir = tempfile.mkdtemp()
        try:
            service = ModelService(model_dir=temp_dir)
            test_app.state.model_service = service

            with TestClient(test_app) as client:
                response = client.post(
                    "/api/v1/train",
                    json={
                        "training_data": [
                            {"message_length": 50, "level": "INFO", "service": "api",
                             "has_exception": False, "has_timeout": False, "has_connection_error": False},
                            {"message_length": 100, "level": "ERROR", "service": "db",
                             "has_exception": True, "has_timeout": False, "has_connection_error": False},
                        ],
                        "contamination": 0.1,
                    },
                )
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "success"
                assert data["samples_trained"] == 2
        finally:
            shutil.rmtree(temp_dir)

    def test_train_model_service_not_initialized(self, test_client):
        """Test train returns 500 when model service is None"""
        app = test_client.app
        saved_service = app.state.model_service
        app.state.model_service = None

        response = test_client.post(
            "/api/v1/train",
            json={
                "training_data": [
                    {
                        "message_length": 50,
                        "level": "INFO",
                        "service": "api",
                        "has_exception": False,
                        "has_timeout": False,
                        "has_connection_error": False,
                    }
                ],
                "contamination": 0.1,
            },
        )

        app.state.model_service = saved_service
        assert response.status_code == 500
        assert "not initialized" in response.json()["detail"]

# Made with Bob
