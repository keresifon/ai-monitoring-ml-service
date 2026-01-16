"""
Model service for anomaly detection using Isolation Forest
"""
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler, LabelEncoder
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class ModelService:
    """Service for managing ML models and predictions"""
    
    def __init__(self, model_dir: str = "models"):
        """
        Initialize the model service
        
        Args:
            model_dir: Directory to store model files
        """
        self.model_dir = model_dir
        self.model: Optional[IsolationForest] = None
        self.scaler: Optional[StandardScaler] = None
        self.label_encoders: Dict[str, LabelEncoder] = {}
        self.feature_names: List[str] = []
        self.model_version: str = "1.0.0"
        self.trained_at: Optional[str] = None
        self.contamination: float = 0.1
        
        # Create model directory if it doesn't exist
        os.makedirs(self.model_dir, exist_ok=True)
    
    def _extract_features(self, log_data: Dict[str, Any]) -> np.ndarray:
        """
        Extract features from log data
        
        Args:
            log_data: Log entry data
            
        Returns:
            Feature array
        """
        features = []
        
        # Numeric features
        features.append(log_data.get('message_length', 0))
        
        # Boolean features (convert to int)
        features.append(int(log_data.get('has_exception', False)))
        features.append(int(log_data.get('has_timeout', False)))
        features.append(int(log_data.get('has_connection_error', False)))
        
        # Categorical features - encode log level
        level = log_data.get('level', 'INFO').upper()
        level_mapping = {'DEBUG': 0, 'INFO': 1, 'WARN': 2, 'ERROR': 3, 'FATAL': 4}
        features.append(level_mapping.get(level, 1))
        
        # Service name hash (simple encoding)
        service = log_data.get('service', 'unknown')
        service_hash = hash(service) % 1000  # Simple hash to numeric
        features.append(service_hash)
        
        return np.array(features).reshape(1, -1)
    
    def _prepare_training_data(self, training_data: List[Dict[str, Any]]) -> np.ndarray:
        """
        Prepare training data from log entries
        
        Args:
            training_data: List of log entries
            
        Returns:
            Feature matrix
        """
        features_list = []
        
        for log_entry in training_data:
            features = self._extract_features(log_entry)
            features_list.append(features.flatten())
        
        return np.array(features_list)
    
    def train(self, training_data: List[Dict[str, Any]], contamination: float = 0.1):
        """
        Train the Isolation Forest model
        
        Args:
            training_data: List of log entries for training
            contamination: Expected proportion of anomalies in the dataset
        """
        logger.info(f"Training model with {len(training_data)} samples")
        
        # Prepare features
        X = self._prepare_training_data(training_data)
        
        logger.info(f"Feature matrix shape: {X.shape}")
        
        # Initialize and fit scaler
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        # Train Isolation Forest
        self.contamination = contamination
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100,
            max_samples='auto',
            n_jobs=-1
        )
        
        self.model.fit(X_scaled)
        
        # Update metadata
        self.trained_at = datetime.utcnow().isoformat()
        self.model_version = f"1.0.{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        logger.info(f"Model trained successfully: version {self.model_version}")
    
    def predict(self, log_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict if a log entry is anomalous
        
        Args:
            log_data: Log entry data
            
        Returns:
            Prediction result with anomaly score and classification
        """
        if self.model is None or self.scaler is None:
            raise ValueError("Model not trained. Please train the model first.")
        
        # Extract and scale features
        features = self._extract_features(log_data)
        features_scaled = self.scaler.transform(features)
        
        # Predict
        prediction = self.model.predict(features_scaled)[0]
        anomaly_score = self.model.score_samples(features_scaled)[0]
        
        # Convert to probability-like score (0 to 1, higher = more anomalous)
        # Isolation Forest score is negative, more negative = more anomalous
        normalized_score = 1 / (1 + np.exp(anomaly_score))  # Sigmoid transformation
        
        is_anomaly = prediction == -1
        
        # Calculate confidence (distance from decision boundary)
        confidence = abs(normalized_score - 0.5) * 2  # Scale to 0-1
        
        return {
            "is_anomaly": bool(is_anomaly),
            "anomaly_score": float(normalized_score),
            "confidence": float(confidence),
            "raw_score": float(anomaly_score)
        }
    
    def save_model(self, filename: str = "isolation_forest_model.pkl"):
        """
        Save the trained model to disk
        
        Args:
            filename: Name of the file to save the model
        """
        if self.model is None:
            raise ValueError("No model to save. Train a model first.")
        
        model_path = os.path.join(self.model_dir, filename)
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'label_encoders': self.label_encoders,
            'feature_names': self.feature_names,
            'model_version': self.model_version,
            'trained_at': self.trained_at,
            'contamination': self.contamination
        }
        
        joblib.dump(model_data, model_path)
        logger.info(f"Model saved to {model_path}")
    
    def load_model(self, filename: str = "isolation_forest_model.pkl"):
        """
        Load a trained model from disk
        
        Args:
            filename: Name of the file to load the model from
        """
        model_path = os.path.join(self.model_dir, filename)
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        model_data = joblib.load(model_path)
        
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.label_encoders = model_data.get('label_encoders', {})
        self.feature_names = model_data.get('feature_names', [])
        self.model_version = model_data.get('model_version', '1.0.0')
        self.trained_at = model_data.get('trained_at')
        self.contamination = model_data.get('contamination', 0.1)
        
        logger.info(f"Model loaded from {model_path}, version: {self.model_version}")

# Made with Bob
