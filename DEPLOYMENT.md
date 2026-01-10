# Deployment Guide

This guide explains how to deploy the AI Agent Framework using Docker Compose and pre-built images from the GitHub Container Registry.

## Deployment Options

### Option 1: Standalone Deployment Package (Recommended)

The simplest way to deploy is using the pre-packaged `deployment` folder, which includes all necessary configuration files.

**What you need:**
- The `deployment` folder from this repository
- Docker and Docker Compose installed on your server

**Files included in deployment package:**
```
deployment/
├── docker-compose.prod.yml          # Production compose file
├── .env.example                     # Environment template
├── README.md                        # Deployment instructions
└── infrastructure/                  # Configuration files
    └── docker/
        ├── kong/kong.yml
        ├── prometheus/prometheus.yml
        └── superset/superset_config.py
```

**Quick start:**
1. Copy the `deployment` folder to your server
2. Navigate to the folder: `cd deployment`
3. Configure environment: `cp .env.example .env` and edit as needed
4. Start services: `docker-compose -f docker-compose.prod.yml up -d`

See `deployment/README.md` for detailed instructions.

### Option 2: Full Repository Clone

If you plan to modify the application or contribute to development:

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/sathisha/multi-agent-orchestrator.git
    cd multi-agent-orchestrator
    ```

2.  **Configure Environment Variables**

    Create a `.env` file based on `.env.example`:
    ```bash
    cp .env.example .env
    ```

    **Critical Variables:**
    - `OPENAI_API_KEY`: Required if using OpenAI models
    - `POSTGRES_PASSWORD`: Set a strong password for production
    - `SUPERSET_SECRET_KEY`: Set a secure key for Superset
    - `GITHUB_REPOSITORY_OWNER`: (Optional) Defaults to `sathisha`

3.  **Start Services**

    Run the production compose file:
    ```bash
    docker-compose -f docker-compose.prod.yml up -d
    ```

    This will pull the latest images from `ghcr.io` and start all services.

## Accessing the Application

Once deployed, access the application at:

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000 (or :8001 depending on configuration)
- **API Documentation**: http://localhost:8000/docs
- **Superset**: http://localhost:8088 (default: admin/admin)
- **Prometheus**: http://localhost:9090

## Updating the Application

To update to the latest version:

1.  Pull the latest images:
    ```bash
    docker-compose -f docker-compose.prod.yml pull
    ```

2.  Restart the services:
    ```bash
    docker-compose -f docker-compose.prod.yml up -d
    ```

## GitHub Actions (CI/CD)

The repository includes a GitHub Actions workflow (`.github/workflows/docker-publish.yml`) that automatically builds and pushes Docker images to the GitHub Container Registry (ghcr.io) whenever changes are pushed to the `main` branch.

### Images Published

The workflow builds and publishes three images:
- `ghcr.io/<owner>/multi-agent-orchestrator-backend:latest`
- `ghcr.io/<owner>/multi-agent-orchestrator-frontend:latest`
- `ghcr.io/<owner>/multi-agent-orchestrator-ollama:latest`

### Authentication

The workflow uses `GITHUB_TOKEN` to authenticate with GHCR during the build process. No additional secrets configuration is required for public repositories.

For private repositories, deployment servers will need to authenticate:
```bash
docker login ghcr.io -u USERNAME -p GITHUB_PAT
```

**Required PAT Scopes:**
- `write:packages` (to upload images)
- `read:packages` (to download images)
- `delete:packages` (optional, to remove old images)

## Production Considerations

### Security
- Change all default passwords in `.env`
- Use HTTPS via a reverse proxy (nginx, Traefik, Caddy)
- Restrict network access with firewall rules
- Regular security updates

### Performance
- Allocate sufficient resources (minimum 8GB RAM, 16GB recommended)
- GPU support is optional but recommended for LLM inference
- Consider using external managed databases for production scale

### Monitoring
- Prometheus metrics are available at `:9090`
- Superset dashboards at `:8088`
- Backend health check at `/health`

### Backups
Backup critical data regularly:
```bash
# Database backup
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U postgres ai_agent_framework > backup.sql

# Volume backup
docker run --rm -v deployment_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz /data
```

## Support

- Full documentation: See repository README.md
- Issues: https://github.com/sathisha/multi-agent-orchestrator/issues
- Deployment package: See `deployment/README.md` for detailed instructions
