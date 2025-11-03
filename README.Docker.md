# Docker Setup for GCP FinOps Dashboard

This guide explains how to run the GCP FinOps Dashboard CLI using Docker Compose.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- GCP credentials (either Application Default Credentials or Service Account key)

## Quick Start

### 1. Set Up Environment Variables

Create a `.env` file in the project root:

```bash
# GCP Configuration
GCP_PROJECT_ID=your-project-id
GCP_BILLING_DATASET=your-project.billing_export
GCP_REGIONS=us-central1,us-east1

# AI Configuration (optional)
AI_PROVIDER=groq
AI_MODEL=llama-3.3-70b-versatile
GROQ_API_KEY=your-groq-api-key

# API Server (optional)
API_PORT=8000
```

### 2. GCP Authentication

You have two options for GCP authentication:

#### Option A: Application Default Credentials (Recommended for local dev)

Mount your local gcloud credentials:

```bash
# Authenticate with gcloud
gcloud auth application-default login

# The docker-compose.yml will automatically mount ~/.config/gcloud
```

#### Option B: Service Account Key

1. Download your service account JSON key file
2. Place it in the project root as `gcp-credentials.json`
3. The compose file will mount it automatically

### 3. Build and Run

```bash
# Build the Docker image
docker-compose build

# Run interactive CLI
docker-compose run --rm cli

# Or start in detached mode and attach later
docker-compose up -d cli
docker-compose exec cli gcp-finops setup --interactive
```

## Common Use Cases

### Interactive Mode

```bash
# Start interactive menu
docker-compose run --rm cli gcp-finops setup --interactive
```

### Run Specific Commands

```bash
# Generate dashboard
docker-compose run --rm cli gcp-finops dashboard \
  --billing-dataset your-project.billing_export

# Run audit
docker-compose run --rm cli gcp-finops audit cloud-run \
  --billing-dataset your-project.billing_export

# Generate forecast
docker-compose run --rm cli gcp-finops forecast \
  --billing-dataset your-project.billing_export
```

### API Server

```bash
# Start API server
docker-compose --profile api up -d api

# Access API at http://localhost:8000
# View docs at http://localhost:8000/docs
```

### Custom Commands

Create a `docker-compose.override.yml` to customize:

```yaml
version: '3.8'

services:
  cli:
    command: ["gcp-finops", "dashboard", "--billing-dataset", "my-project.billing_export"]
```

## Volume Mounts

The Docker Compose setup automatically mounts:

- **GCP Credentials**: `~/.config/gcloud` → `/home/appuser/.config/gcloud`
- **Service Account**: `./gcp-credentials.json` → `/home/appuser/gcp-credentials.json`
- **Data Directory**: `./data` → `/home/appuser/.gcp-finops` (persistent storage for RAG, reports, etc.)
- **Workspace**: `.` → `/workspace` (project files)

## Persistent Data

All persistent data is stored in the `./data` directory:
- RAG document storage
- Generated reports
- Configuration files
- Vector databases

Make sure to back up this directory or add it to `.gitignore`.

## Troubleshooting

### Permission Issues

If you encounter permission issues with mounted volumes:

```bash
# Fix ownership
sudo chown -R $USER:$USER ./data
```

### GCP Authentication Errors

```bash
# Verify credentials are mounted
docker-compose run --rm cli ls -la /home/appuser/.config/gcloud

# Test authentication
docker-compose run --rm cli gcloud auth list
```

### Missing Dependencies

If you need additional system packages, modify the Dockerfile:

```dockerfile
RUN apt-get update && apt-get install -y \
    your-package \
    && rm -rf /var/lib/apt/lists/*
```

### Interactive Terminal Issues

If the terminal doesn't work interactively:

```bash
# Use -it flags explicitly
docker-compose run --rm -it cli
```

## Development

### Rebuild After Code Changes

```bash
# Rebuild image
docker-compose build --no-cache

# Or use volume mount for live code updates
# The workspace is mounted, but Python packages need rebuild
```

### Run Tests in Docker

```bash
docker-compose run --rm cli python -m pytest
```

### Access Container Shell

```bash
docker-compose run --rm cli /bin/bash
```

## Production Deployment

For production, consider:

1. Using a service account with minimal permissions
2. Setting up proper secret management
3. Using Docker secrets or external secret managers
4. Configuring resource limits
5. Setting up health checks

Example production override:

```yaml
version: '3.8'

services:
  cli:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
    restart: unless-stopped
```

## Clean Up

```bash
# Stop and remove containers
docker-compose down

# Remove volumes (WARNING: deletes data)
docker-compose down -v

# Remove image
docker-compose down --rmi local
```

## Environment Variables Reference

| Variable | Description | Required |
|----------|-------------|----------|
| `GCP_PROJECT_ID` | GCP project ID | Yes |
| `GCP_BILLING_DATASET` | BigQuery billing dataset | Yes |
| `GCP_REGIONS` | Comma-separated regions | No |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account key | If using SA |
| `AI_PROVIDER` | AI provider (groq/openai/anthropic) | No |
| `GROQ_API_KEY` | Groq API key | If using Groq |
| `OPENAI_API_KEY` | OpenAI API key | If using OpenAI |
| `ANTHROPIC_API_KEY` | Anthropic API key | If using Anthropic |
| `BIGQUERY_LOCATION` | BigQuery location | No (default: US) |
| `API_PORT` | API server port | No (default: 8000) |

## Security Notes

1. **Never commit** `gcp-credentials.json` or `.env` files
2. Use Docker secrets or environment variable injection in production
3. Rotate service account keys regularly
4. Use minimal IAM permissions for service accounts
5. Consider using Workload Identity for GKE deployments

