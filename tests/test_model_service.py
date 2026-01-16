"""
Unit tests for ML Model Service
"""
import os
import pytest
import numpy as np
from app.services.model_service import ModelService


class TestModelService:
    """Test cases for ModelService"""
    
    @pytest.fixture
    def model_service(self):
        """Create a ModelService instance for testing"""
        return ModelService()
    
    @pytest.fixture
    def trained_model_service(self):
        """Create a trained ModelService instance for testing"""
        service = ModelService()
        # Create simple training data
        training_data = [
            {"message_length": 50, "level": "INFO", "service": "test", "has_exception": False, "has_timeout": False, "has_connection_error": False},
            {"message_length": 45, "level": "INFO", "service": "test", "has_exception": False, "has_timeout": False, "has_connection_error": False},
            {"message_length": 55, "level": "INFO", "service": "test", "has_exception": False, "has_timeout": False, "has_connection_error": False},
            {"message_length": 200, "level": "ERROR", "service": "test", "has_exception": True, "has_timeout": False, "has_connection_error": False},
        ]
        service.train(training_data, contamination=0.25)
        return service
    
    def test_extract_features(self, model_service):
        """Test feature extraction from log data"""
        log_data = {
            "message_length": 100,
            "level": "ERROR",
            "service": "api-service",
            "has_exception": True,
            "has_timeout": False,
            "has_connection_error": False
        }
        
        features = model_service._extract_features(log_data)
        
        assert isinstance(features, np.ndarray)
        assert features.shape == (1, 6)  # 6 features
    
    def test_predict_with_trained_model(self, trained_model_service):
        """Test prediction with a trained model"""
        log_data = {
            "message_length": 50,
            "level": "INFO",
            "service": "test-service",
            "has_exception": False,
            "has_timeout": False,
            "has_connection_error": False
        }
        
        result = trained_model_service.predict(log_data)
        
        assert "is_anomaly" in result
        assert "anomaly_score" in result
        assert "confidence" in result
        assert isinstance(result["is_anomaly"], bool)
        assert 0 <= result["anomaly_score"] <= 1
        assert 0 <= result["confidence"] <= 1
    
    def test_predict_without_training_raises_error(self, model_service):
        """Test that prediction without training raises an error"""
        log_data = {"message_length": 50, "level": "INFO", "service": "test"}
        
        with pytest.raises(ValueError, match="Model not trained"):
            model_service.predict(log_data)
    
    def test_model_version(self, model_service):
        """Test that model has a version"""
        assert model_service.model_version == "1.0.0"
    
    def test_train_updates_metadata(self, model_service):
        """Test that training updates model metadata"""
        training_data = [
            {"message_length": 50, "level": "INFO", "service": "test", "has_exception": False, "has_timeout": False, "has_connection_error": False},
            {"message_length": 100, "level": "ERROR", "service": "test", "has_exception": True, "has_timeout": False, "has_connection_error": False},
        ]
        
        model_service.train(training_data, contamination=0.2)
        
        assert model_service.model is not None
        assert model_service.scaler is not None
        assert model_service.trained_at is not None
        assert model_service.contamination == 0.2
        assert model_service.model_version.startswith("1.0.")
    
    def test_extract_features_with_all_fields(self, model_service):
        """Test feature extraction with all fields present"""
        log_data = {
            "message_length": 150,
            "level": "ERROR",
            "service": "payment-service",
            "has_exception": True,
            "has_timeout": True,
            "has_connection_error": True
        }
        
        features = model_service._extract_features(log_data)
        
        assert features.shape == (1, 6)
        assert features[0][0] == 150  # message_length
        assert features[0][1] == 1    # has_exception
        assert features[0][2] == 1    # has_timeout
        assert features[0][3] == 1    # has_connection_error
        assert features[0][4] == 3    # ERROR level = 3
    
    def test_extract_features_with_missing_fields(self, model_service):
        """Test feature extraction with missing optional fields"""
        log_data = {
            "message_length": 75
        }
        
        features = model_service._extract_features(log_data)
        
        assert features.shape == (1, 6)
        assert features[0][0] == 75   # message_length
        assert features[0][1] == 0    # has_exception default False
        assert features[0][2] == 0    # has_timeout default False
        assert features[0][3] == 0    # has_connection_error default False
        assert features[0][4] == 1    # INFO level default = 1
    
    def test_extract_features_with_different_log_levels(self, model_service):
        """Test feature extraction with different log levels"""
        levels_and_expected = [
            ("DEBUG", 0),
            ("INFO", 1),
            ("WARN", 2),
            ("ERROR", 3),
            ("FATAL", 4),
            ("UNKNOWN", 1)  # Unknown defaults to INFO
        ]
        
        for level, expected_value in levels_and_expected:
            log_data = {
                "message_length": 100,
                "level": level,
                "service": "test",
                "has_exception": False,
                "has_timeout": False,
                "has_connection_error": False
            }
            features = model_service._extract_features(log_data)
            assert features[0][4] == expected_value, f"Level {level} should map to {expected_value}"
    
    def test_prepare_training_data(self, model_service):
        """Test preparation of training data"""
        training_data = [
            {"message_length": 50, "level": "INFO", "service": "api", "has_exception": False, "has_timeout": False, "has_connection_error": False},
            {"message_length": 100, "level": "ERROR", "service": "db", "has_exception": True, "has_timeout": False, "has_connection_error": False},
            {"message_length": 75, "level": "WARN", "service": "cache", "has_exception": False, "has_timeout": True, "has_connection_error": False}
        ]
        
        X = model_service._prepare_training_data(training_data)
        
        assert X.shape == (3, 6)  # 3 samples, 6 features each
        assert isinstance(X, np.ndarray)
    
    def test_predict_anomaly_detection(self, trained_model_service):
        """Test that model can detect anomalies"""
        # Normal log (similar to training data)
        normal_log = {
            "message_length": 48,
            "level": "INFO",
            "service": "test",
            "has_exception": False,
            "has_timeout": False,
            "has_connection_error": False
        }
        
        # Anomalous log (very different from training data)
        anomalous_log = {
            "message_length": 500,
            "level": "FATAL",
            "service": "unknown-service",
            "has_exception": True,
            "has_timeout": True,
            "has_connection_error": True
        }
        
        normal_result = trained_model_service.predict(normal_log)
        anomalous_result = trained_model_service.predict(anomalous_log)
        
        # Anomalous log should have higher anomaly score
        assert anomalous_result["anomaly_score"] > normal_result["anomaly_score"]
    
    def test_model_persistence_directory_creation(self):
        """Test that model directory is created"""
        import tempfile
        import shutil
        
        temp_dir = tempfile.mkdtemp()
        model_dir = os.path.join(temp_dir, "test_models")
        
        try:
            service = ModelService(model_dir=model_dir)
            assert os.path.exists(model_dir)
        finally:
            shutil.rmtree(temp_dir)

# Made with Bob
