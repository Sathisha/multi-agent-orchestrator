#!/bin/bash

# Start Ollama in the background.
/bin/ollama serve &
pid=$!

echo "Waiting for Ollama..."
while ! ollama list > /dev/null 2>&1; do
    sleep 1
done

echo "Ollama ready. Pulling default models..."
ollama pull nomic-embed-text
ollama pull llama3.2

echo "Models pulled. Ready to serve."
wait $pid
