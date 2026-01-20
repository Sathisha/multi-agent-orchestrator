
import client from './client';

export type MCPProtocol = 'stdio' | 'websocket' | 'http' | 'sse' | 'streamable-http';

export interface MCPResource {
    uri: string;
    name: string;
    description?: string;
    mimeType?: string;
}

export interface MCPArgument {
    name: string;
    description?: string;
    required?: boolean;
}

export interface MCPPrompt {
    name: string;
    description?: string;
    arguments?: MCPArgument[];
}

export interface MCPServer {
    id: string;
    name: string;
    description?: string;
    base_url: string;
    protocol: MCPProtocol;
    status: 'connected' | 'connecting' | 'disconnected' | 'error';
    health_status?: string;
    last_connected_at?: string;
    created_at: string;
    tools?: Tool[];
    resources?: MCPResource[];
    prompts?: MCPPrompt[];
    env_vars?: Record<string, string>;
    auth_config?: Record<string, any>;
    server_info?: Record<string, any>;
    capabilities?: string[];
}

export interface Tool {
    name: string;
    description: string;
    input_schema: Record<string, any>;
}

export interface CreateMCPServerRequest {
    name: string;
    description?: string;
    base_url: string;
    protocol: MCPProtocol;
    auth_config?: Record<string, any>; // { type: 'api_key', api_key: '...' } etc
    env_vars?: Record<string, string>;
}

export interface UpdateMCPServerRequest {
    name?: string;
    description?: string;
    base_url?: string;
    protocol?: MCPProtocol;
    auth_config?: Record<string, any>;
    env_vars?: Record<string, string>;
}

export const mcpApi = {
    // List all servers
    listServers: async (): Promise<MCPServer[]> => {
        const response = await client.get('/mcp-servers/');
        return response.data;
    },

    // Get single server details
    getServer: async (id: string): Promise<MCPServer> => {
        const response = await client.get(`/mcp-servers/${id}`);
        return response.data;
    },

    // Create a new server config
    createServer: async (data: CreateMCPServerRequest): Promise<MCPServer> => {
        const response = await client.post('/mcp-servers/', data);
        return response.data;
    },

    // Update server
    updateServer: async (id: string, data: UpdateMCPServerRequest): Promise<MCPServer> => {
        const response = await client.put(`/mcp-servers/${id}`, data);
        return response.data;
    },

    // Delete a server
    deleteServer: async (id: string): Promise<void> => {
        await client.delete(`/mcp-servers/${id}`);
    },

    // Trigger connection / introspection
    connectServer: async (id: string): Promise<any> => {
        // We use the connect endpoint which now triggers introspection
        const response = await client.post(`/mcp-servers/${id}/connect`);
        return response.data;
    },

    // Explicit Introspection
    introspectServer: async (id: string): Promise<MCPServer> => {
        const response = await client.post(`/mcp-servers/${id}/introspect`);
        return response.data;
    },

    // Refresh/Discover tools (wrapper around list tools from server if needed, or re-introspect)
    refreshTools: async (id: string): Promise<{ tools: Tool[] }> => {
        const response = await client.post(`/mcp-servers/${id}/discover`, null, { params: { force_refresh: true } });
        return response.data;
    },

    // Execute a tool
    executeTool: async (serverId: string, toolName: string, args: any): Promise<any> => {
        const response = await client.post(`/mcp-servers/${serverId}/tools/${toolName}/execute`, {
            inputs: args
        });
        return response.data;
    },

    // Read Resource
    readResource: async (serverId: string, uri: string): Promise<any> => {
        const response = await client.post(`/mcp-servers/${serverId}/resources/read`, null, {
            params: { uri }
        });
        return response.data;
    },

    // Get Prompt
    getPrompt: async (serverId: string, promptName: string, args: Record<string, string> = {}): Promise<any> => {
        const response = await client.post(`/mcp-servers/${serverId}/prompts/${promptName}/get`, args);
        return response.data;
    }
};
