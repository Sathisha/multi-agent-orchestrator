# Third-Party Notices

This deployment package includes the following third-party software components:

## Ollama

- **Source**: https://github.com/ollama/ollama
- **License**: MIT License
- **Copyright**: Copyright (c) Ollama
- **Usage**: We extend the official `ollama/ollama:latest` Docker image with a custom entrypoint script to auto-pull recommended models.
- **License File**: See `LICENSES/OLLAMA-LICENSE`

## LLM Models (Auto-Downloaded)

The custom Ollama image automatically downloads the following models on first startup:

### nomic-embed-text
- **Purpose**: Text embeddings for vector database
- **License**: Apache License 2.0
- **Size**: ~274MB
- **Source**: https://ollama.com/library/nomic-embed-text
- **License URL**: https://www.apache.org/licenses/LICENSE-2.0

### tinyllama
- **Purpose**: Lightweight general-purpose LLM
- **License**: Apache License 2.0
- **Size**: ~637MB
- **Source**: https://ollama.com/library/tinyllama
- **License URL**: https://www.apache.org/licenses/LICENSE-2.0

### phi
- **Purpose**: Small but capable LLM (Microsoft)
- **License**: MIT License
- **Size**: ~1.6GB
- **Source**: https://ollama.com/library/phi
- **License URL**: https://opensource.org/licenses/MIT

## Important Notes on Model Licensing

> **⚠️ User Responsibility**: When you pull additional models using `ollama pull <model>`, you are responsible for reviewing and complying with each model's individual license terms.

### Model License Types

Different models on Ollama have different licenses:

- **Open Source Models** (Apache 2.0, MIT): Can be used commercially without restrictions (e.g., tinyllama, phi, nomic-embed-text)
- **Meta Llama Models** (Community License Agreement): Have specific terms for commercial use, attribution requirements, and usage restrictions
- **Other Proprietary Models**: May have custom license agreements

### Where to Find Model Licenses

1. Visit the model page on https://ollama.com/library/<model-name>
2. Check the model's source repository (usually linked from Ollama page)
3. Review the LICENSE file in the model's repository

### Commercial Use Considerations

If you plan to use this software commercially, ensure:
- All models you use permit commercial use
- You comply with attribution requirements (e.g., Meta Llama requires "Built with Llama X" notices)
- You understand any usage limitations or restrictions

## Other Docker Images

This deployment package uses the following official Docker images, each with their own licenses:

- **PostgreSQL** (postgres:15-alpine) - PostgreSQL License (permissive)
- **Redis** (redis:7-alpine) - BSD 3-Clause License
- **Keycloak** (quay.io/keycloak/keycloak:22.0) - Apache License 2.0
- **Kong** (kong:3.4) - Apache License 2.0
- **Prometheus** (prom/prometheus:v2.47.0) - Apache License 2.0
- **Apache Superset** (apache/superset:3.0.0) - Apache License 2.0
- **nginx** (nginx:alpine) - 2-clause BSD License

## Attribution

This project incorporates or extends the following open-source projects:
- Ollama - https://github.com/ollama/ollama (MIT)

We are grateful to the open-source community for these excellent tools.

---

**Last Updated**: 2026-01-06
