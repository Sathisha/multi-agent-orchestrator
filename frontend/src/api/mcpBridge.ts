/**
 * MCP Bridge Discovery API - Dynamically fetch available MCP servers
 */

import client from './client';

export interface BridgeServer {
    name: string;
    display_name: string;
    command: string;
    requires_env: boolean;
    env_vars: string[];
    websocket_url: string;
}

export interface BridgeDiscoveryResponse {
    bridge_url: string;
    available: boolean;
    servers: BridgeServer[];
}

export const mcpBridgeApi = {
    /**
     * Discover all available MCP servers from the bridge
     */
    discoverServers: async (): Promise<BridgeDiscoveryResponse> => {
        const response = await client.get('/mcp-bridge/discover');
        return response.data;
    },

    /**
     * Check if the bridge is healthy and running
     */
    checkHealth: async (): Promise<{ status: string; bridge_url: string }> => {
        const response = await client.get('/mcp-bridge/health');
        return response.data;
    }
};
