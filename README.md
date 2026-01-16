# ML Service - Anomaly Detection

FastAPI-based machine learning service for log anomaly detection using Isolation Forest algorithm.

## Features

- **Isolation Forest Algorithm**: Unsupervised anomaly detection
- **REST API**: FastAPI with automatic OpenAPI documentation
- **Model Persistence**: Save and load trained models
- **Batch Predictions**: Process multiple logs efficiently
- **Health Checks**: Kubernetes-ready health and readiness endpoints

## API Endpoints

### Health & Status
- `GET /api/v1/health` - Health check
- `GET /api/v1/ready` - Readiness check
- `GET /api/v1/model/info` - Model information

### Anomaly Detection
- `POST /api/v1/predict` - Predict single log anomaly
- `POST /api/v1/predict/batch` - Batch prediction
- `POST /api/v1/train` - Train new model

## Quick Start

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the service
uvicorn main:app --reload --port 8000

# Access API documentation
open http://localhost:8000/docs
```

### Docker

```bash
# Build image
docker build -t ml-service:latest .

# Run container
docker run -p 8000:8000 ml-service:latest
```

## Training the Model

First, train a model with sample data:

```bash
curl -X POST http://localhost:8000/api/v1/train \
  -H "Content-Type: application/json" \
  -d '{
    "training_data": [
      {
        "message_length": 100,
        "level": "INFO",
        "service": "api-service",
        "has_exception": false,
        "has_timeout": false,
        "has_connection_error": false
      },
      {
        "message_length": 500,
        "level": "ERROR",
        "service": "api-service",
        "has_exception": true,
        "has_timeout": false,
        "has_connection_error": false
      }
    ],
    "contamination": 0.1
  }'
```

## Making Predictions

```bash
curl -X POST http://localhost:8000/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{
    "log_id": "log-123",
    "features": {
      "message_length": 250,
      "level": "ERROR",
      "service": "api-service",
      "has_exception": true,
      "has_timeout": false,
      "has_connection_error": false
    }
  }'
```

## Model Features

The model uses the following features for anomaly detection:

1. **message_length**: Length of the log message
2. **level**: Log level (DEBUG, INFO, WARN, ERROR, FATAL)
3. **service**: Service name (hashed to numeric)
4. **has_exception**: Boolean - contains exception keywords
5. **has_timeout**: Boolean - contains timeout keywords
6. **has_connection_error**: Boolean - contains connection error keywords

## Configuration

Environment variables:
- `MODEL_DIR`: Directory for model storage (default: `models`)
- `LOG_LEVEL`: Logging level (default: `INFO`)

## Integration with Log Processor

The log-processor service calls this ML service to detect anomalies in real-time:

```python
# In log-processor
import httpx

async def check_anomaly(log_entry):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://ml-service:8000/api/v1/predict",
            json={
                "log_id": log_entry.id,
                "features": extract_features(log_entry)
            }
        )
        return response.json()
```

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Code Quality

```bash
# Format code
black .

# Lint
flake8 .

# Type checking
mypy .
```

## Architecture

```
ml-service/
├── main.py                 # FastAPI application
├── app/
│   ├── api/               # API endpoints
│   │   ├── health.py      # Health checks
│   │   └── anomaly.py     # Anomaly detection endpoints
│   ├── services/          # Business logic
│   │   └── model_service.py  # ML model management
│   └── config/            # Configuration
├── models/                # Trained models storage
├── requirements.txt       # Python dependencies
└── Dockerfile            # Container definition
```

## Performance

- **Training**: ~1-2 seconds for 1000 samples
- **Prediction**: <50ms per log entry
- **Batch Prediction**: ~100ms for 100 logs

## Troubleshooting

### Model Not Loaded
If you see "Model not loaded" errors, train a model first using the `/api/v1/train` endpoint.

### Memory Issues
For large datasets, adjust the `max_samples` parameter in IsolationForest or increase container memory limits.

## License

MIT

---

**Made with Bob**