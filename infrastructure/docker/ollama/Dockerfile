FROM ollama/ollama:latest

# Basic metadata
LABEL org.opencontainers.image.source=https://github.com/sathisha/multi-agent-orchestrator
LABEL org.opencontainers.image.description="Ollama with auto-model-pulling for Multi-Agent Orchestrator"

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose port
EXPOSE 11434

ENTRYPOINT ["/entrypoint.sh"]
