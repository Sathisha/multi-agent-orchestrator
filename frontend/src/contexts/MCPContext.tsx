
import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { MCPServer, mcpApi } from '../api/mcp';
import { useAuth } from '../context/AuthContext';

interface MCPContextType {
    servers: MCPServer[];
    isLoading: boolean;
    error: string | null;
    refreshServers: () => Promise<void>;
    connectServer: (id: string) => Promise<void>;
    deleteServer: (id: string) => Promise<void>;
}

const MCPContext = createContext<MCPContextType | null>(null);

export const MCPProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [servers, setServers] = useState<MCPServer[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const { isAuthenticated } = useAuth(); // Assuming generic AuthContext exists

    const refreshServers = useCallback(async () => {
        try {
            setError(null);
            const data = await mcpApi.listServers();
            setServers(data);
        } catch (err: any) {
            setError(err.message || 'Failed to fetch MCP servers');
        }
    }, []);

    // Initial load
    useEffect(() => {
        if (isAuthenticated) {
            setIsLoading(true);
            refreshServers().finally(() => setIsLoading(false));
        }
    }, [isAuthenticated, refreshServers]);

    // Polling for status updates (every 10 seconds)
    useEffect(() => {
        if (!isAuthenticated) return;

        const interval = setInterval(() => {
            refreshServers(); // Silent refresh
        }, 10000);

        return () => clearInterval(interval);
    }, [isAuthenticated, refreshServers]);

    const connectServer = async (id: string) => {
        await mcpApi.connectServer(id);
        await refreshServers();
    };



    const deleteServer = async (id: string) => {
        await mcpApi.deleteServer(id);
        await refreshServers();
    };

    return (
        <MCPContext.Provider
            value={{
                servers,
                isLoading,
                error,
                refreshServers,
                connectServer,
                deleteServer,
            }}
        >
            {children}
        </MCPContext.Provider>
    );
};

export const useMCP = () => {
    const context = useContext(MCPContext);
    if (!context) {
        throw new Error('useMCP must be used within an MCPProvider');
    }
    return context;
};
