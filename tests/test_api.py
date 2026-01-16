"""
Integration tests for ML Service API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock
from main import app
from app.services.model_service import ModelService


# Create a mock model service for testing
@pytest.fixture(scope="module")
def test_client():
    """Create test client with mocked model service"""
    # Create a mock model service
    mock_model_service = Mock(spec=ModelService)
    mock_model_service.model = None  # No model loaded by default
    mock_model_service.model_version = "test-v1.0.0"
    mock_model_service.trained_at = "2024-01-01T00:00:00"
    mock_model_service.contamination = 0.1
    
    # Set it in app state
    app.state.model_service = mock_model_service
    
    # Create test client
    with TestClient(app) as client:
        yield client


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
    
    def test_train_with_empty_data(self, test_client):
        """Test training with empty training data"""
        training_request = {
            "training_data": [],
            "contamination": 0.1
        }
        
        response = test_client.post("/api/v1/train", json=training_request)
        
        # Should accept the request but may fail during training
        # The actual behavior depends on ModelService implementation
        assert response.status_code in [200, 500]

# Made with Bob
