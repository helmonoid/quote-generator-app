# Inspirational Quote Generator

A cloud-native microservices application that generates unique inspirational quotes using a local LLM ([Llama 3.2-1B](https://huggingface.co/meta-llama/Llama-3.2-1B)) inference via [llama.cpp](https://github.com/ggml-org/llama.cpp). The application comprises multiple services including quote generation, database storage, and a user interface, enabling users to view, download, and manage their quote history. This project is part of the PA2577 Applied Cloud Computing and Big Data course, covering "Cloud Provisioning and Deployment" and "The Business Case for Cloud Computing."

<p align="center">
  <img src="demo.gif" alt="Application Demo">
</p>

## Overview

This application demonstrates a production-ready microservice architecture with three independent services:
1. **FastAPI Service** - REST API for quote generation and management
2. **llama.cpp Server** - LLM inference engine
3. **PostgreSQL Database** - Persistent quote storage

The application fulfills the requirements for a Kubernetes-based microservice deployment with horizontal scalability, persistent storage, and comprehensive REST API functionality.

## Features

- **AI-Powered Quote Generation**: Uses [Llama 3.2 1B Instruct](https://huggingface.co/meta-llama/Llama-3.2-1B) model with theme-based prompts
- **Persistent Storage**: PostgreSQL database stores all generated quotes with metadata
- **Quote Management**: View, delete, and export all previously generated quotes
- **Export Functionality**: Download quotes as CSV or JSON
- **Health Checks**: Comprehensive health monitoring for all services
- **Horizontal Scalability**: FastAPI service can scale independently (2+ replicas in K8s)
- **Service Discovery**: Automatic DNS-based service discovery in Kubernetes
- **Responsive UI**: Tab-based interface for quote generation and history management

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│            Kubernetes Cluster / Docker Network              │
│                                                             │
│  ┌──────────────┐    ┌─────────────┐    ┌──────────────┐    │
│  │  FastAPI     │    │ llama.cpp   │    │ PostgreSQL   │    │
│  │  (quote-api) │───→│  (inference)│    │  (storage)   │    │
│  │              │    │             │    │              │    │
│  │ Replicas: 2+ │    │ Port: 8080  │    │ Port: 5432   │    │
│  │ Port: 8000   │    └─────────────┘    │ PersistVol:  │    │
│  │              │                       │ 5Gi          │    │
│  └──────────────┘                       └──────────────┘    │
│       ↑                                                     │
└───────┼─────────────────────────────────────────────────────┘
        │ HTTP LoadBalancer / Browser
        │ localhost:8000
    User / Client
```

## Setup & Installation

### Prerequisites

- Docker Desktop (with Kubernetes enabled) or local Docker installation
- `kubectl` for Kubernetes (included with Docker Desktop)
- `curl` or Postman for API testing

## Running with Docker Compose

### Start Services

```bash
docker-compose up --build
```

This starts three containers:
- `quotes-db` (PostgreSQL database)
- `llama-cpp-server` (LLM inference)
- `quote-api` (FastAPI service)

The `llama-cpp-server` and `quote-api` are pulled from dockerhub. The `Dockerfile` was used to build the `quote-api` image and the `Dockerfile-LM` was used to build the `llama-cpp-server`. The language model was downloaded from [bartowski](https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf) on HuggingFace.

### Access Application

- **Web UI**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Stop Services

```bash
docker-compose down -v
```

## Running with Kubernetes

### Build and Deploy

```bash
# 1. Apply all Kubernetes manifests
kubectl apply -f k8s/

# 2. Monitor deployment
kubectl get pods -n quote-generator-app
```
### Access Application

- **Web UI**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Scale FastAPI Service

By default, the `quote-api` service is set to run with 1 replica. You can scale it up or down as needed:

```bash
# Scale to 3 replicas
kubectl scale deployment quote-api --replicas=3 -n quote-generator-app

# Verify scaling
kubectl get pods -l app=quote-api -n quote-generator-app
```

### Monitor Logs

```bash
# FastAPI logs
kubectl logs -f deployment/quote-api -n quote-generator-app

# All services
kubectl logs -f deployment/postgres -n quote-generator-app
kubectl logs -f deployment/llama-cpp -n quote-generator-app
```


### Exposing Llama Service

The `llama-cpp` service is currently internal (ClusterIP). There are two options to access it:

1. **Quick Testing (Port Forwarding)**:
```bash
kubectl port-forward -n quote-generator-app svc/llama-cpp 8080:8080
````

Then access it at: 
  * http://localhost:8080/ (Llama-server chat UI) and 
  * http://localhost:8080/health


2. **Expose Externally (LoadBalancer)**:
   Modify the service to use `LoadBalancer` instead of `ClusterIP` for external access.

Keeping it internal (ClusterIP) – Only `quote-api` accesses it (recommended for security).

### Cleanup

```bash
kubectl delete -f k8s/
```

## API Endpoints

### Quote Generation & Management

**Generate Quote**
```bash
GET /quote
```
Response:
```json
{
  "id": 1,
  "quote": "...",
  "date": "2025-10-29T12:51:04.705613",
  "theme": "persistence"
}
```

**List Quotes**
```bash
GET /quotes?limit=50
```

**Delete Quote**
```bash
DELETE /quotes/{quote_id}
```

### Export

**Export as CSV**
```bash
GET /quotes/export/csv
```

**Export as JSON**
```bash
GET /quotes/export/json
```

### Utility

**Health Check**
```bash
GET /health
```

**Web Interface**
```bash
GET /
```

**API Documentation**
```bash
GET /docs
```

## Database Schema

```sql
CREATE TABLE quotes (
    id SERIAL PRIMARY KEY,
    quote TEXT NOT NULL,
    generated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    theme VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_generated_at ON quotes(generated_at DESC);
```

## Configuration

### Environment Variables

**Docker Compose** (set in `docker-compose.yml`):
- `LLAMA_CPP_URL`: http://llama:8080
- `DATABASE_URL`: postgresql://quotes_user:quotes_password@postgres:5432/quotes_db

**Kubernetes** (set in deployment manifests):
- `LLAMA_CPP_URL`: http://llama-cpp:8080
- `DATABASE_URL`: postgresql://quotes_user:quotes_password@postgres:5432/quotes_db

### Model Parameters

In `main.py`:
- `n_predict`: 50 (max tokens to generate)
- `temperature`: 0.9 (creativity level)
- `top_p`: 0.95, `top_k`: 40 (diversity controls)
- `repeat_penalty`: 1.2 (reduce repetition)

### LLM Themes

80+ themes for diverse quote generation, including:
- Success, Achievement, Excellence
- Growth, Development, Transformation
- Courage, Confidence, Strength
- Wisdom, Knowledge, Learning
- Hope, Optimism, Faith
- And 40+ more...

## Kubernetes Manifest Files

- `00-namespace.yaml` - Namespace definition
- `01-postgres-secret.yaml` - Database credentials
- `02-postgres-pvc.yaml` - 5Gi persistent volume
- `03-postgres-deployment.yaml` - PostgreSQL deployment
- `04-postgres-configmap.yaml` - Database initialization
- `05-postgres-service.yaml` - ClusterIP service
- `06-llama-deployment.yaml` - LLM inference engine
- `07-llama-service.yaml` - Internal service
- `08-fastapi-deployment.yaml` - Quote API (2 replicas)
- `09-fastapi-service.yaml` - LoadBalancer service
- `10-fastapi-hpa.yaml` - Quote API Horizontal Pod Autoscaler


## License

Academic/educational project, otherwise free to be modified and used for any purpose. No warranty is provided or implied.


## Credits

* The [GGML](https://github.com/ggml-org) team, the creators of [llama.cpp](https://github.com/ggml-org/llama.cpp) used as inference engine in the app.
* Meta AI [Llama 3.2 1B Instruct](https://huggingface.co/meta-llama/Llama-3.2-1B) for providing a free open-weights model.
