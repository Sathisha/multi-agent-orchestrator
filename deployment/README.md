# AI Agent Framework - Production Deployment

This deployment package contains everything you need to deploy the AI Agent Framework using pre-built Docker images from GitHub Container Registry.

## 📦 What's Included

```
deployment/
├── docker-compose.prod.yml          # Production docker compose file
├── .env.example                     # Environment configuration template
├── README.md                        # This file
└── infrastructure/
    └── docker/
        ├── kong/                    # API Gateway configuration
        │   └── kong.yml
        ├── prometheus/              # Monitoring configuration
        │   └── prometheus.yml
        └── superset/                # Analytics configuration
            └── superset_config.py
```

## 🚀 Quick Start

### Prerequisites

- **Docker** (20.10+) and **Docker Compose** (2.0+) installed
- **Minimum 8GB RAM** (16GB recommended for running Ollama with LLMs)
- **GPU support** (optional, for faster LLM inference)

### Installation Steps

1. **Download this deployment package**
   
   Simply download/clone the `deployment` folder to your server.

2. **Configure environment variables**

   ```bash
   cd deployment
   cp .env.example .env
   ```

   Edit `.env` and update the following **critical** values:
   - `POSTGRES_PASSWORD` - Set a strong database password
   - `SUPERSET_SECRET_KEY` - Generate a long random string
   - `OPENAI_API_KEY` - Your OpenAI API key (if using OpenAI models)

3. **Start the application**

   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

   This will pull all images from GitHub Container Registry and start the services.

4. **Verify deployment**

   Wait for all services to be healthy (30-60 seconds), then access:
   - **Frontend**: http://localhost:3000
   - **Backend API**: http://localhost:8001
   - **API Docs**: http://localhost:8001/docs
   - **Superset**: http://localhost:8088 (admin/admin)
   - **Prometheus**: http://localhost:9090

## 🔧 Configuration

### Using OpenAI Instead of Ollama

Edit `.env`:
```bash
MEMORY_EMBEDDING_PROVIDER=openai
MEMORY_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_API_KEY=sk-your-actual-api-key
```

### GPU Support

The compose file includes GPU support for NVIDIA GPUs. If you don't have a GPU or want to disable GPU usage, remove the `deploy.resources` sections from the backend and ollama services in `docker-compose.prod.yml`.

### Custom Domain

To use a custom domain, update the Kong configuration in `infrastructure/docker/kong/kong.yml` to include your domain in the CORS origins.

## 📊 Monitoring & Analytics

- **Prometheus**: Metrics collection at http://localhost:9090
- **Superset**: Dashboards and visualization at http://localhost:8088
  - Default credentials: `admin` / `admin`
  - Change these immediately after first login!

## 🔄 Updating

To update to the latest version:

```bash
# Pull latest images
docker-compose -f docker-compose.prod.yml pull

# Restart services
docker-compose -f docker-compose.prod.yml up -d
```

## 🛑 Stopping & Cleanup

```bash
# Stop all services
docker-compose -f docker-compose.prod.yml down

# Stop and remove all data (CAUTION: This deletes all data!)
docker-compose -f docker-compose.prod.yml down -v
```

## 🔐 Security Considerations

### For Production Deployments:

1. **Change default passwords** in `.env`
2. **Use HTTPS** - Put the application behind a reverse proxy (nginx, Traefik, etc.)
3. **Restrict network access** - Use firewall rules to limit exposure
4. **Regular backups** - Backup the PostgreSQL database and volumes
5. **Update regularly** - Pull latest images to get security patches

### Backup Data

```bash
# Backup PostgreSQL database
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U postgres ai_agent_framework > backup.sql

# Backup volumes
docker run --rm -v deployment_ollama_data:/data -v $(pwd):/backup alpine tar czf /backup/ollama_backup.tar.gz /data
```

## 📖 Additional Resources

- [Full Documentation](https://github.com/sathisha/multi-agent-orchestrator)
- [API Documentation](http://localhost:8001/docs) (when running)
- [Report Issues](https://github.com/sathisha/multi-agent-orchestrator/issues)

## 📜 Licensing & Legal

### Software License

This deployment package includes software from multiple sources:

- **Ollama**: MIT License - Copyright (c) Ollama
  - We extend the official Ollama Docker image
  - See `LICENSES/OLLAMA-LICENSE` for full license text
  - Source: https://github.com/ollama/ollama

- **Other Docker Images**: PostgreSQL, Redis, Kong, Prometheus, Superset, etc.
  - Each has its own permissive open-source license
  - See `LICENSES/THIRD-PARTY-NOTICES.md` for details

### LLM Model Licensing

> **⚠️ Important**: LLM models have **separate licenses** from the Ollama software.

**Auto-Downloaded Models** (on first startup):
- `nomic-embed-text` - Apache License 2.0
- `tinyllama` - Apache License 2.0  
- `phi` - MIT License

**Your Responsibility**: When you pull additional models using `ollama pull <model>`, you must:
1. Review the model's license (check https://ollama.com/library/<model>)
2. Ensure it permits your intended use (commercial, research, etc.)
3. Comply with attribution requirements (some models like Meta Llama require "Built with Llama" notices)

See `LICENSES/THIRD-PARTY-NOTICES.md` for detailed model licensing information.

## ❓ Troubleshooting

### Services won't start
- Check `docker-compose -f docker-compose.prod.yml logs` for errors
- Ensure ports 3000, 5432, 6379, 8000, 8001, 8080, 8088, 9090, 11434 are not in use

### Out of memory errors
- Ollama requires significant RAM for LLM models
- Reduce `OLLAMA_MAX_LOADED_MODELS` in compose file
- Or switch to OpenAI provider

### Images fail to pull
- Ensure you have internet connectivity
- For private repositories, authenticate with: `docker login ghcr.io`

## 📝 License

See the main repository for license information.

---

**Need help?** Open an issue at https://github.com/sathisha/multi-agent-orchestrator/issues
