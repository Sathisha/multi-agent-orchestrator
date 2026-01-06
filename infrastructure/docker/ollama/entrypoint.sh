#!/bin/bash
# Custom entrypoint for Ollama Docker image
# This script uses Ollama (https://github.com/ollama/ollama)
# Ollama is licensed under the MIT License - Copyright (c) Ollama
#
# Auto-downloaded models and their licenses:
# - nomic-embed-text: Apache License 2.0
# - tinyllama: Apache License 2.0
# - phi: MIT License
set -e


# Start Ollama server in the background
ollama serve &

# Wait for Ollama server to be ready
echo "Waiting for Ollama server to start..."
while ! ollama list > /dev/null 2>&1; do
  sleep 1
done

echo "Ollama server is ready."

# Pull essential and lightweight models
# nomic-embed-text: 274MB - used for embeddings
# tinyllama: 637MB - very lightweight LLM
# phi: 1.6GB - small but capable LLM
for model in "nomic-embed-text" "tinyllama" "phi"; do
    if ! ollama list | grep -q "$model"; then
        echo "Pulling model: $model..."
        ollama pull "$model"
    fi
done

echo "Default lightweight models are present."

# Wait for the background ollama serve process
wait