"""
Tests for main application
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from main import app, _get_cors_origins


@pytest.fixture
def client():
    """Create test client"""
    # Mock the model service to avoid file operations
    with patch('main.ModelService') as mock_service_class:
        mock_service = Mock()
        mock_service.model = None
        mock_service_class.return_value = mock_service
        
        with TestClient(app) as test_client:
            yield test_client


class TestMainApp:
    """Test cases for main application"""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns correct information"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "AI Log Monitoring - ML Service"
        assert data["version"] == "1.0.0"
        assert data["status"] == "running"
        assert "timestamp" in data
    
    def test_app_metadata(self):
        """Test FastAPI app metadata"""
        assert app.title == "AI Log Monitoring - ML Service"
        assert app.version == "1.0.0"
        assert "Machine Learning service" in app.description
    
    def test_cors_middleware_configured(self, client):
        """Test that CORS middleware is configured (returns CORS headers)"""
        response = client.get(
            "/",
            headers={"Origin": "http://localhost:3000"},
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in [
            h.lower() for h in response.headers
        ]

    def test_cors_origins_default(self):
        """Test default CORS allows all origins"""
        with patch("main.os.getenv", return_value="*"):
            origins = _get_cors_origins()
        assert origins == ["*"]

    def test_cors_origins_custom(self):
        """Test custom CORS origins from env"""
        with patch("main.os.getenv", return_value="https://a.com,https://b.com"):
            origins = _get_cors_origins()
        assert origins == ["https://a.com", "https://b.com"]

    def test_routers_included(self):
        """Test that routers are included"""
        routes = [route.path for route in app.routes]
        
        # Health endpoints
        assert "/api/v1/health" in routes
        assert "/api/v1/ready" in routes
        
        # Anomaly detection endpoints
        assert "/api/v1/predict" in routes
        assert "/api/v1/predict/batch" in routes
        assert "/api/v1/train" in routes
        assert "/api/v1/model/info" in routes
    
    def test_openapi_docs_available(self, client):
        """Test that OpenAPI documentation is available"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        openapi_schema = response.json()
        assert openapi_schema["info"]["title"] == "AI Log Monitoring - ML Service"
        assert openapi_schema["info"]["version"] == "1.0.0"


class TestLifespan:
    """Test cases for application lifespan"""
    
    def test_lifespan_initializes_model_service(self):
        """Test that lifespan initializes model service"""
        with patch('main.ModelService') as mock_service_class:
            mock_service = Mock()
            mock_service.model = None
            mock_service.load_model.side_effect = FileNotFoundError("No model")
            mock_service_class.return_value = mock_service
            
            with TestClient(app) as client:
                # Model service should be initialized
                assert hasattr(app.state, 'model_service')
                assert app.state.model_service is not None
                
                # load_model should have been called
                mock_service.load_model.assert_called_once()
    
    def test_lifespan_handles_model_load_error(self):
        """Test that lifespan handles model loading errors gracefully"""
        with patch('main.ModelService') as mock_service_class:
            mock_service = Mock()
            mock_service.load_model.side_effect = Exception("Load error")
            mock_service_class.return_value = mock_service
            
            # Should not raise exception, just log error
            with TestClient(app) as client:
                assert hasattr(app.state, 'model_service')
    
    def test_lifespan_loads_existing_model(self):
        """Test that lifespan loads existing model successfully"""
        with patch('main.ModelService') as mock_service_class:
            mock_service = Mock()
            mock_service.model = Mock()  # Model loaded successfully
            mock_service.load_model.return_value = None  # Success
            mock_service_class.return_value = mock_service
            
            with TestClient(app) as client:
                assert app.state.model_service.model is not None
                mock_service.load_model.assert_called_once()

# Made with Bob