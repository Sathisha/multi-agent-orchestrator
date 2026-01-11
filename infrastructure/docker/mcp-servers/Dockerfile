FROM node:20-alpine

# Install necessary tools
RUN apk add --no-cache \
    python3 \
    py3-pip \
    git \
    bash

# Create directory for MCP servers
WORKDIR /mcp-servers

# Note: Official MCP server packages are not yet published to npm
# This is a placeholder for future integration
# For now, we'll focus on custom tools functionality

# Create config directory
RUN mkdir -p /etc/mcp

# Copy MCP configuration
COPY mcp-config.json /etc/mcp/config.json

# Create a startup script
COPY start-mcp-servers.sh /usr/local/bin/start-mcp-servers.sh
RUN chmod +x /usr/local/bin/start-mcp-servers.sh

# Keep container running
CMD ["/usr/local/bin/start-mcp-servers.sh"]
