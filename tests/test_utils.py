"""
Tests for app.utils module
"""
import pytest
from unittest.mock import Mock
from app.utils import get_current_timestamp, is_model_loaded


class TestGetCurrentTimestamp:
    """Tests for get_current_timestamp"""

    def test_returns_string(self):
        """Timestamp should be a string"""
        result = get_current_timestamp()
        assert isinstance(result, str)

    def test_returns_iso_format(self):
        """Timestamp should be ISO 8601 format"""
        result = get_current_timestamp()
        assert "T" in result
        assert result[-1] in "0123456789" or result[-6:] == "+00:00"


class TestIsModelLoaded:
    """Tests for is_model_loaded"""

    def test_returns_false_when_none(self):
        """Should return False when model_service is None"""
        assert is_model_loaded(None) is False

    def test_returns_false_when_model_not_loaded(self):
        """Should return False when model is None"""
        mock_service = Mock()
        mock_service.model = None
        assert is_model_loaded(mock_service) is False

    def test_returns_true_when_model_loaded(self):
        """Should return True when model is loaded"""
        mock_service = Mock()
        mock_service.model = Mock()
        assert is_model_loaded(mock_service) is True
