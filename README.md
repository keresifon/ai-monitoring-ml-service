# ML Service - Anomaly Detection

FastAPI-based machine learning service for log anomaly detection using Isolation Forest algorithm.

## Features

- **Isolation Forest Algorithm**: Unsupervised anomaly detection
- **REST API**: FastAPI with automatic OpenAPI documentation
- **Model Persistence**: Save and load trained models
- **Batch Predictions**: Process multiple logs efficiently
- **Kubernetes/AKS Deployment**: Dedicated node pool with auto-scaling
- **CI/CD Pipeline**: Automated build, test, and deployment
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


### Kubernetes Deployment

The ML service supports deployment to both **Azure Kubernetes Service (AKS)** and **OpenShift** with efficient resource management and auto-scaling.

#### Deploy to AKS

**Quick Deploy:**
```bash
# Get AKS credentials
az aks get-credentials --resource-group <rg-name> --name <cluster-name>

# Deploy with Helm
helm upgrade --install ml-service ./charts \
  --namespace ai-monitoring \
  --create-namespace \
  -f charts/values.yaml
```

**Automated CI/CD:**
- Push to `main` branch to deploy to AKS automatically
- Comment `/deploy aks` on a PR to deploy that PR's code to AKS

#### Deploy to OpenShift

**Quick Deploy:**
```bash
# Login to OpenShift
oc login --token=<your-token> --server=<your-server>

# Create/switch to project
oc new-project ai-monitoring

# Deploy with Helm
helm upgrade --install ml-service ./charts \
  --namespace ai-monitoring \
  --create-namespace \
  -f charts/values.yaml \
  -f charts/values-openshift.yaml
```

**Automated CI/CD:**
- Comment `/deploy openshift` or `/deploy oc` on a PR to deploy that PR's code to OpenShift
- The deployment creates an OpenShift Route for external access

#### Comment-Based Deployment (Choose Deployment Target)

**NEW WORKFLOW**: After merging to main, comment on the merged PR to choose where to deploy.

You can deploy by adding a comment to any PR (open or merged):

- **Deploy to AKS**: Comment `/deploy aks` on the PR
- **Deploy to OpenShift**: Comment `/deploy openshift` or `/deploy oc` on the PR

**When to use:**
- ✅ **After merging to main**: Comment on the merged PR to deploy to production
- ✅ **Before merging**: Test your changes in a live environment
- ✅ **Choose your platform**: Deploy to AKS or OpenShift based on your needs

**Requirements:**
- You must have write access to the repository
- Required secrets must be configured (see Configuration section below)
- Comment must be exactly `/deploy aks` or `/deploy openshift` (no extra text)

**The workflow will:**
1. Detect the deployment target from your comment
2. For merged PRs: Use the merge commit SHA
3. For open PRs: Use the PR's head SHA
4. Deploy to the specified platform
5. Comment back with deployment status and details

**Example workflow:**
```
1. Create PR with your changes
2. (Optional) Comment: /deploy aks to test before merge
3. Merge the PR to main
4. Comment on the merged PR: /deploy aks or /deploy openshift
5. Wait for deployment (2-5 minutes)
6. Your changes are now deployed!
```

**Key Change**: Merging to main no longer automatically deploys. You must comment to choose the deployment target.

See [DEPLOYMENT_WORKFLOW.md](docs/DEPLOYMENT_WORKFLOW.md) for detailed examples and troubleshooting.

#### Configuration

**Common Settings:**
- **Resources**: 250m-1 CPU, 512Mi-2Gi memory
- **Auto-scaling**: HPA enabled (1-2 replicas based on CPU/memory utilization)
- **Storage**: Optional 5Gi persistent volume for model caching
- **Health Checks**: Liveness and readiness probes configured

**Platform-Specific:**
- **AKS**: Uses Ingress for external access, runs on system node pool
- **OpenShift**: Uses Routes for external access, automatic security context assignment

#### Required Secrets

For automated deployments, configure these GitHub secrets:

**For AKS:**
- `AZURE_CREDENTIALS`: Azure service principal credentials
- `AKS_RESOURCE_GROUP`: Azure resource group name
- `AKS_CLUSTER_NAME`: AKS cluster name

**For OpenShift:**
- `OPENSHIFT_TOKEN`: OpenShift authentication token
- `OPENSHIFT_SERVER`: OpenShift API server URL
- `OPENSHIFT_PROJECT`: OpenShift project/namespace name

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
# Recommended: use run_tests.sh (isolates venv from ~/.local packages)
./run_tests.sh

# Or run pytest directly (ensure venv is activated)
pytest tests/ -v
```

**Note:** If you see `Client.__init__() got an unexpected keyword argument 'app'`, Python may be loading packages from `~/.local`. Run `./run_tests.sh` which sets `PYTHONNOUSERSITE=1` to fix this.

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