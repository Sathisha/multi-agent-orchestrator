
import React, { useState, useEffect } from 'react';
import {
    Box,
    Typography,
    Button,
    Grid,
    Card,
    CardContent,
    CardActions,
    Chip,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    TextField,
    FormControl,
    InputLabel,
    Select,
    MenuItem,
    CircularProgress,
    IconButton,
    Alert,
    Tabs,
    Tab,
    Tooltip
} from '@mui/material';
import { Add, Refresh, Delete, PowerSettingsNew, Link as LinkIcon, Storage, Security, Code } from '@mui/icons-material';
import { useMCP } from '../contexts/MCPContext';
import { MCPServer, mcpApi, MCPProtocol } from '../api/mcp';
import { mcpBridgeApi, BridgeServer } from '../api/mcpBridge';
import { useNavigate } from 'react-router-dom';

const MCPServerList: React.FC = () => {
    const { servers, isLoading, error, refreshServers, connectServer, deleteServer } = useMCP();
    const navigate = useNavigate();
    const [openAdd, setOpenAdd] = useState(false);

    // State for dynamically discovered bridge servers
    const [bridgeServers, setBridgeServers] = useState<BridgeServer[]>([]);
    const [loadingBridge, setLoadingBridge] = useState(false);

    // Form State
    const [connectionSource, setConnectionSource] = useState<'custom' | 'bridge'>('custom');
    const [activeTab, setActiveTab] = useState(0);

    const [formData, setFormData] = useState({
        name: '',
        url: '',
        protocol: 'http' as MCPProtocol,
        bridgeTool: '',
        authType: 'none',
        apiKey: '',
        authHeader: 'X-API-Key',
        envVarsText: '' // Key=Value newline separated
    });

    const [createLoading, setCreateLoading] = useState(false);
    const [createError, setCreateError] = useState<string | null>(null);

    // Fetch available bridge servers on component mount
    useEffect(() => {
        const fetchBridgeServers = async () => {
            try {
                setLoadingBridge(true);
                const discovery = await mcpBridgeApi.discoverServers();
                setBridgeServers(discovery.servers);
            } catch (err) {
                console.error('Failed to discover bridge servers:', err);
            } finally {
                setLoadingBridge(false);
            }
        };
        fetchBridgeServers();
    }, []);

    const handleBridgeToolChange = (toolName: string) => {
        const tool = bridgeServers.find(s => s.name === toolName);
        if (tool) {
            setFormData({
                ...formData,
                bridgeTool: toolName,
                name: tool.display_name || tool.name,
                url: tool.websocket_url,
                protocol: 'websocket'
            });
        }
    };

    const handleCreate = async () => {
        try {
            setCreateLoading(true);
            setCreateError(null);

            // Parse Env Vars
            const envVars: Record<string, string> = {};
            if (formData.envVarsText.trim()) {
                formData.envVarsText.split('\n').forEach(line => {
                    const [key, ...valParts] = line.split('=');
                    if (key && valParts.length > 0) {
                        envVars[key.trim()] = valParts.join('=').trim();
                    }
                });
            }

            // Build Auth Config
            let authConfig: any = undefined;
            if (formData.authType === 'api_key') {
                authConfig = {
                    type: 'api_key',
                    api_key: formData.apiKey,
                    key_name: formData.authHeader
                };
            }

            await mcpApi.createServer({
                name: formData.name,
                base_url: formData.url,
                protocol: formData.protocol,
                auth_config: authConfig,
                env_vars: envVars
            });

            await refreshServers();
            setOpenAdd(false);
            // Reset form
            setFormData({
                name: '',
                url: '',
                protocol: 'http',
                bridgeTool: '',
                authType: 'none',
                apiKey: '',
                authHeader: 'X-API-Key',
                envVarsText: ''
            });
            setConnectionSource('custom');
            setActiveTab(0);
        } catch (err: any) {
            setCreateError(err.response?.data?.detail || err.message || 'Failed to create server');
        } finally {
            setCreateLoading(false);
        }
    };

    return (
        <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', p: 3 }}>
            {/* Header */}
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
                <Box>
                    <Typography variant="h4" gutterBottom sx={{ color: 'text.primary', fontWeight: 600 }}>
                        MCP Servers
                    </Typography>
                    <Typography variant="body1" sx={{ color: 'text.secondary' }}>
                        Connect to external Model Context Protocol servers to extend agent capabilities.
                    </Typography>
                </Box>
                <Box>
                    <Button
                        startIcon={<Refresh />}
                        onClick={() => refreshServers()}
                        sx={{ mr: 2 }}
                        disabled={isLoading}
                    >
                        Refresh
                    </Button>
                    <Button
                        variant="contained"
                        startIcon={<Add />}
                        onClick={() => setOpenAdd(true)}
                    >
                        Add Server
                    </Button>
                </Box>
            </Box>

            {/* Error */}
            {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

            {/* List */}
            <Grid container spacing={3}>
                {servers.map((server) => (
                    <Grid item xs={12} md={6} lg={4} key={server.id}>
                        <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                            <CardContent sx={{ flexGrow: 1 }}>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                        {server.base_url?.includes('mcp-bridge') ? <Storage fontSize="small" color="secondary" /> : <LinkIcon fontSize="small" color="primary" />}
                                        <Typography variant="h6" noWrap title={server.name}>
                                            {server.name}
                                        </Typography>
                                    </Box>
                                    <Chip
                                        label={server.status}
                                        color={server.status === 'connected' ? 'success' : server.status === 'error' ? 'error' : 'default'}
                                        size="small"
                                        variant="outlined"
                                    />
                                </Box>

                                <Typography variant="body2" color="text.secondary" sx={{ mb: 1, fontFamily: 'monospace', fontSize: '0.8rem', wordBreak: 'break-all' }}>
                                    {server.base_url || 'No URL configured'}
                                </Typography>

                                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 1 }}>
                                    <Chip label={server.protocol} size="small" sx={{ fontSize: '0.7rem' }} />
                                    {server.tools && server.tools.length > 0 && <Chip label={`${server.tools.length} Tools`} size="small" variant="outlined" />}
                                    {server.resources && server.resources.length > 0 && <Chip label={`${server.resources.length} Resources`} size="small" variant="outlined" />}
                                    {server.prompts && server.prompts.length > 0 && <Chip label={`${server.prompts.length} Prompts`} size="small" variant="outlined" />}
                                </Box>

                            </CardContent>

                            <CardActions sx={{ justifyContent: 'space-between', px: 2, pb: 2 }}>
                                <Button size="small" onClick={() => navigate(`/mcp/${server.id}`)}>
                                    Manage
                                </Button>
                                <Box>
                                    <IconButton
                                        size="small"
                                        color="primary"
                                        title="Re-Introspect"
                                        onClick={() => connectServer(server.id)}
                                    >
                                        <Refresh />
                                    </IconButton>
                                    <IconButton
                                        size="small"
                                        color="error"
                                        title="Delete"
                                        onClick={() => { if (window.confirm('Delete this server?')) deleteServer(server.id) }}
                                    >
                                        <Delete />
                                    </IconButton>
                                </Box>
                            </CardActions>
                        </Card>
                    </Grid>
                ))}
            </Grid>

            {/* Add Dialog */}
            <Dialog open={openAdd} onClose={() => setOpenAdd(false)} maxWidth="sm" fullWidth>
                <DialogTitle>Add MCP Server</DialogTitle>
                <DialogContent>
                    {createError && <Alert severity="error" sx={{ mb: 2, mt: 1 }}>{createError}</Alert>}

                    <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
                        <Tabs value={activeTab} onChange={(e, v) => setActiveTab(v)}>
                            <Tab label="Connection" />
                            <Tab label="Authentication" />
                            <Tab label="Environment" />
                        </Tabs>
                    </Box>

                    {/* Connection Tab */}
                    {activeTab === 0 && (
                        <>
                            <FormControl fullWidth sx={{ mb: 2, mt: 1 }}>
                                <InputLabel>Source</InputLabel>
                                <Select
                                    value={connectionSource}
                                    label="Source"
                                    onChange={(e) => {
                                        setConnectionSource(e.target.value as 'custom' | 'bridge');
                                        if (e.target.value === 'custom') {
                                            setFormData(prev => ({ ...prev, bridgeTool: '' }));
                                        }
                                    }}
                                >
                                    <MenuItem value="custom">Custom Server</MenuItem>
                                    <MenuItem value="bridge">Internal Bridge (Docker)</MenuItem>
                                </Select>
                            </FormControl>

                            {connectionSource === 'bridge' ? (
                                <FormControl fullWidth sx={{ mb: 2 }}>
                                    <InputLabel>Bridge Tool</InputLabel>
                                    <Select
                                        value={formData.bridgeTool}
                                        label="Bridge Tool"
                                        onChange={(e) => handleBridgeToolChange(e.target.value)}
                                        disabled={loadingBridge}
                                    >
                                        {loadingBridge ? (
                                            <MenuItem value="">Loading...</MenuItem>
                                        ) : bridgeServers.length > 0 ? (
                                            bridgeServers.map(server => (
                                                <MenuItem key={server.name} value={server.name}>
                                                    {server.display_name}
                                                </MenuItem>
                                            ))
                                        ) : (
                                            <MenuItem value="" disabled>No bridge servers available</MenuItem>
                                        )}
                                    </Select>
                                </FormControl>
                            ) : null}

                            <TextField
                                autoFocus
                                margin="dense"
                                label="Server Name"
                                fullWidth
                                variant="outlined"
                                value={formData.name}
                                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                sx={{ mb: 2 }}
                            />

                            <Grid container spacing={2}>
                                <Grid item xs={4}>
                                    <FormControl fullWidth>
                                        <InputLabel>Protocol</InputLabel>
                                        <Select
                                            value={formData.protocol}
                                            label="Protocol"
                                            onChange={(e) => setFormData({ ...formData, protocol: e.target.value as MCPProtocol })}
                                            disabled={connectionSource === 'bridge'} // Bridge enforces websocket
                                        >
                                            <MenuItem value="http">HTTP</MenuItem>
                                            <MenuItem value="sse">SSE</MenuItem>
                                            <MenuItem value="websocket">WebSocket</MenuItem>
                                            <MenuItem value="streamable-http">Streamable HTTP</MenuItem>
                                        </Select>
                                    </FormControl>
                                </Grid>
                                <Grid item xs={8}>
                                    <TextField
                                        label="Server URL"
                                        fullWidth
                                        variant="outlined"
                                        value={formData.url}
                                        onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                                        disabled={connectionSource === 'bridge'}
                                        helperText={connectionSource === 'bridge' ? "Managed by Bridge" : "e.g., http://localhost:8000/mcp"}
                                    />
                                </Grid>
                            </Grid>
                        </>
                    )}

                    {/* Auth Tab */}
                    {activeTab === 1 && (
                        <>
                            <FormControl fullWidth sx={{ mb: 2, mt: 1 }}>
                                <InputLabel>Authentication Type</InputLabel>
                                <Select
                                    value={formData.authType}
                                    label="Authentication Type"
                                    onChange={(e) => setFormData({ ...formData, authType: e.target.value })}
                                >
                                    <MenuItem value="none">None</MenuItem>
                                    <MenuItem value="api_key">API Key</MenuItem>
                                </Select>
                            </FormControl>

                            {formData.authType === 'api_key' && (
                                <>
                                    <TextField
                                        margin="dense"
                                        label="Header Name"
                                        fullWidth
                                        variant="outlined"
                                        value={formData.authHeader}
                                        onChange={(e) => setFormData({ ...formData, authHeader: e.target.value })}
                                        sx={{ mb: 2 }}
                                        helperText="e.g. X-API-Key or Authorization"
                                    />
                                    <TextField
                                        margin="dense"
                                        label="API Key Value"
                                        type="password"
                                        fullWidth
                                        variant="outlined"
                                        value={formData.apiKey}
                                        onChange={(e) => setFormData({ ...formData, apiKey: e.target.value })}
                                    />
                                </>
                            )}
                        </>
                    )}

                    {/* Env Tab */}
                    {activeTab === 2 && (
                        <Box sx={{ mt: 1 }}>
                            <Typography variant="body2" color="text.secondary" gutterBottom>
                                Enter environment variables for the server (KEY=VALUE), one per line.
                            </Typography>
                            <TextField
                                multiline
                                rows={6}
                                placeholder="API_KEY=12345&#10;DEBUG=true"
                                fullWidth
                                variant="outlined"
                                value={formData.envVarsText}
                                onChange={(e) => setFormData({ ...formData, envVarsText: e.target.value })}
                                sx={{ fontFamily: 'monospace' }}
                            />
                        </Box>
                    )}

                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setOpenAdd(false)}>Cancel</Button>
                    <Button
                        onClick={handleCreate}
                        variant="contained"
                        disabled={createLoading || !formData.name || !formData.url}
                    >
                        {createLoading ? <CircularProgress size={24} /> : 'Add Server'}
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
};

export default MCPServerList;
