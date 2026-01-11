#!/bin/bash

# Start Ollama in the background.
/bin/ollama serve &
pid=$!

echo "Waiting for Ollama..."
while ! ollama list > /dev/null 2>&1; do
    sleep 1
done

echo "Ollama ready. Lazy loading enabled."
echo "Waiting for Ollama process..."
wait $pid
