"""
Unit tests for utility functions
"""
import pytest
from unittest.mock import Mock
from app.utils import get_current_timestamp, is_model_loaded
from app.services.model_service import ModelService


class TestUtils:
    """Test cases for utility functions"""
    
    def test_get_current_timestamp(self):
        """Test that get_current_timestamp returns ISO format string"""
        timestamp = get_current_timestamp()
        
        assert isinstance(timestamp, str)
        assert "T" in timestamp  # ISO format contains T
        assert timestamp.endswith("Z") or "+" in timestamp  # UTC indicator
    
    def test_is_model_loaded_with_none_service(self):
        """Test is_model_loaded with None service"""
        assert is_model_loaded(None) is False
    
    def test_is_model_loaded_with_no_model(self):
        """Test is_model_loaded with service but no model"""
        mock_service = Mock(spec=ModelService)
        mock_service.model = None
        
        assert is_model_loaded(mock_service) is False
    
    def test_is_model_loaded_with_model(self):
        """Test is_model_loaded with loaded model"""
        mock_service = Mock(spec=ModelService)
        mock_service.model = Mock()  # Model is loaded
        
        assert is_model_loaded(mock_service) is True
    
    def test_is_model_loaded_with_real_service(self):
        """Test is_model_loaded with real ModelService"""
        service = ModelService()
        
        # Initially no model
        assert is_model_loaded(service) is False
        
        # After training
        training_data = [
            {"message_length": 50, "level": "INFO", "service": "test", 
             "has_exception": False, "has_timeout": False, "has_connection_error": False}
        ]
        service.train(training_data)
        
        assert is_model_loaded(service) is True

# Made with Bob