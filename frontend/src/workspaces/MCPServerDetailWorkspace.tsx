
import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
    Box,
    Typography,
    Button,
    Grid,
    Paper,
    Tabs,
    Tab,
    CircularProgress,
    List,
    ListItem,
    ListItemText,
    ListItemIcon,
    Chip,
    Accordion,
    AccordionSummary,
    AccordionDetails,
    TextField,
    Alert,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    IconButton,
    Tooltip
} from '@mui/material';
import {
    ArrowBack, Refresh, Construction, BugReport, ExpandMore, PlayArrow,
    Description, ChatBubbleOutline, Visibility, CloudDownload
} from '@mui/icons-material';
import { mcpApi, MCPServer, Tool, MCPResource, MCPPrompt } from '../api/mcp';


interface TabPanelProps {
    children?: React.ReactNode;
    index: number;
    value: number;
}

function TabPanel(props: TabPanelProps) {
    const { children, value, index, ...other } = props;
    return (
        <div
            role="tabpanel"
            hidden={value !== index}
            {...other}
            style={{ height: '100%', overflow: 'hidden' }}
        >
            {value === index && (
                <Box sx={{ p: 3, height: '100%', overflowY: 'auto' }}>
                    {children}
                </Box>
            )}
        </div>
    );
}

const MCPServerDetailWorkspace: React.FC = () => {
    const { serverId } = useParams<{ serverId: string }>();
    const navigate = useNavigate();
    const [server, setServer] = useState<MCPServer | null>(null);
    const [tools, setTools] = useState<Tool[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [tabValue, setTabValue] = useState(0);

    // Tool Testing State
    const [selectedTool, setSelectedTool] = useState<string>('');
    const [testInput, setTestInput] = useState('{}');
    const [testResult, setTestResult] = useState<string | null>(null);
    const [testing, setTesting] = useState(false);

    // Resource State
    const [viewingResource, setViewingResource] = useState<MCPResource | null>(null);
    const [resourceContent, setResourceContent] = useState<string | null>(null);
    const [resourceLoading, setResourceLoading] = useState(false);

    // Prompt State
    const [selectedPrompt, setSelectedPrompt] = useState<MCPPrompt | null>(null);
    const [promptArgs, setPromptArgs] = useState<Record<string, string>>({});
    const [viewingPromptResult, setViewingPromptResult] = useState<string | null>(null); // The prompt content
    const [promptLoading, setPromptLoading] = useState(false);

    useEffect(() => {
        loadData();
    }, [serverId]);

    const loadData = async () => {
        if (!serverId) return;
        try {
            setLoading(true);
            const s = await mcpApi.getServer(serverId);
            setServer(s);
            // If connected, fetch tools. Resources/Prompts are in 's'
            if (s.status === 'connected') {
                const t = await mcpApi.refreshTools(serverId);
                setTools(t.tools);
            }
        } catch (err: any) {
            setError(err.message || 'Failed to load server details');
        } finally {
            setLoading(false);
        }
    };

    const handleTestTool = async () => {
        if (!serverId || !selectedTool) return;
        try {
            setTesting(true);
            setTestResult(null);
            let args = {};
            try {
                args = JSON.parse(testInput);
            } catch (e) {
                setTestResult('Error: Invalid JSON input');
                return;
            }

            const result = await mcpApi.executeTool(serverId, selectedTool, args);
            setTestResult(JSON.stringify(result, null, 2));
        } catch (err: any) {
            setTestResult(`Error: ${err.message || 'Tool execution failed'}`);
        } finally {
            setTesting(false);
        }
    };

    const handleReadResource = async (resource: MCPResource) => {
        if (!serverId) return;
        setViewingResource(resource);
        setResourceContent(null);
        setResourceLoading(true);
        try {
            const data = await mcpApi.readResource(serverId, resource.uri);
            // Result is a list of contents usually
            if (data && data.contents && Array.isArray(data.contents)) {
                const contentStr = data.contents.map((c: any) => c.text || `[Binary: ${c.mimeType}]`).join('\n\n');
                setResourceContent(contentStr);
            } else if (data && data.content && Array.isArray(data.content)) {
                // CallToolResult style
                const contentStr = data.content.map((c: any) => c.text || `[Binary: ${c.mimeType}]`).join('\n\n');
                setResourceContent(contentStr);
            } else {
                setResourceContent(JSON.stringify(data, null, 2));
            }
        } catch (err: any) {
            setResourceContent(`Error reading resource: ${err.message}`);
        } finally {
            setResourceLoading(false);
        }
    };

    const handleGetPrompt = async () => {
        if (!serverId || !selectedPrompt) return;
        setPromptLoading(true);
        setViewingPromptResult(null);
        try {
            const data = await mcpApi.getPrompt(serverId, selectedPrompt.name, promptArgs);
            if (data && data.messages) {
                const contentStr = data.messages.map((m: any) => `Role: ${m.role}\nContent: ${m.content.type === 'text' ? m.content.text : '[Image]'}`).join('\n---\n');
                setViewingPromptResult(contentStr);
            } else {
                setViewingPromptResult(JSON.stringify(data, null, 2));
            }
        } catch (err: any) {
            setViewingPromptResult(`Error getting prompt: ${err.message}`);
        } finally {
            setPromptLoading(false);
        }
    }

    if (loading) {
        return <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}><CircularProgress /></Box>;
    }

    if (error || !server) {
        return <Box sx={{ p: 3 }}><Alert severity="error">{error || 'Server not found'}</Alert></Box>;
    }

    return (
        <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            {/* Header */}
            <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider', display: 'flex', alignItems: 'center', gap: 2 }}>
                <Button startIcon={<ArrowBack />} onClick={() => navigate('/mcp')}>Back</Button>
                <Typography variant="h6">{server.name}</Typography>
                <Chip
                    label={server.status}
                    color={server.status === 'connected' ? 'success' : 'error'}
                    size="small"
                    variant="outlined"
                />
                <Box sx={{ flexGrow: 1 }} />
                <Button startIcon={<Refresh />} onClick={loadData}>Refresh</Button>
            </Box>

            {/* Tabs */}
            <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)}>
                    <Tab label="Overview" />
                    <Tab label={`Tools (${tools.length})`} disabled={server.status !== 'connected'} />
                    <Tab label={`Resources (${server.resources?.length || 0})`} disabled={server.status !== 'connected'} />
                    <Tab label={`Prompts (${server.prompts?.length || 0})`} disabled={server.status !== 'connected'} />
                    <Tab label="Test Lab" disabled={server.status !== 'connected'} />
                </Tabs>
            </Box>

            {/* Content */}
            <Box sx={{ flexGrow: 1, overflow: 'hidden' }}>
                {/* 0. Overview */}
                <TabPanel value={tabValue} index={0}>
                    <Grid container spacing={3}>
                        <Grid item xs={12} md={6}>
                            <Paper sx={{ p: 2 }}>
                                <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 600 }}>Connection Details</Typography>
                                <List dense>
                                    <ListItem><ListItemText primary="URL" secondary={server.base_url} /></ListItem>
                                    <ListItem><ListItemText primary="Protocol" secondary={server.protocol} /></ListItem>
                                    <ListItem><ListItemText primary="Last Connected" secondary={server.last_connected_at || 'Never'} /></ListItem>
                                    <ListItem><ListItemText primary="Server ID" secondary={server.server_info?.name || 'Unknown'} /></ListItem>
                                    <ListItem><ListItemText primary="Server Version" secondary={server.server_info?.version || 'Unknown'} /></ListItem>
                                </List>
                            </Paper>
                        </Grid>
                        <Grid item xs={12} md={6}>
                            <Paper sx={{ p: 2 }}>
                                <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 600 }}>Capabilities</Typography>
                                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                                    {server.capabilities?.map(c => <Chip key={c} label={c} size="small" />)}
                                </Box>
                                {server.env_vars && Object.keys(server.env_vars).length > 0 && (
                                    <Box sx={{ mt: 2 }}>
                                        <Typography variant="subtitle2" gutterBottom>Env Vars Configured</Typography>
                                        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                                            {Object.keys(server.env_vars).map(k => <Chip key={k} label={k} size="small" variant="outlined" />)}
                                        </Box>
                                    </Box>
                                )}
                            </Paper>
                        </Grid>
                    </Grid>
                </TabPanel>

                {/* 1. Tools */}
                <TabPanel value={tabValue} index={1}>
                    {tools.length === 0 ? (
                        <Typography color="text.secondary">No tools discovered. Try refreshing.</Typography>
                    ) : (
                        <Grid container spacing={2}>
                            {tools.map((tool) => (
                                <Grid item xs={12} key={tool.name}>
                                    <Accordion variant="outlined">
                                        <AccordionSummary expandIcon={<ExpandMore />}>
                                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                                                <Construction color="action" />
                                                <Typography sx={{ fontWeight: 600 }}>{tool.name}</Typography>
                                                <Typography variant="body2" color="text.secondary">{tool.description}</Typography>
                                            </Box>
                                        </AccordionSummary>
                                        <AccordionDetails>
                                            <Typography variant="subtitle2" gutterBottom>Input Schema:</Typography>
                                            <Paper variant="outlined" sx={{ p: 1, bgcolor: 'background.default' }}>
                                                <pre style={{ margin: 0, fontSize: '0.8rem' }}>
                                                    {JSON.stringify(tool.input_schema, null, 2)}
                                                </pre>
                                            </Paper>
                                        </AccordionDetails>
                                    </Accordion>
                                </Grid>
                            ))}
                        </Grid>
                    )}
                </TabPanel>

                {/* 2. Resources */}
                <TabPanel value={tabValue} index={2}>
                    {!server.resources || server.resources.length === 0 ? (
                        <Typography color="text.secondary">No resources discovered.</Typography>
                    ) : (
                        <List>
                            {server.resources.map((res: any) => (
                                <Paper key={res.uri} variant="outlined" sx={{ mb: 1 }}>
                                    <ListItem
                                        secondaryAction={
                                            <IconButton edge="end" onClick={() => handleReadResource(res)}>
                                                <Visibility />
                                            </IconButton>
                                        }
                                    >
                                        <ListItemIcon><Description /></ListItemIcon>
                                        <ListItemText
                                            primary={res.name}
                                            secondary={
                                                <React.Fragment>
                                                    <Typography component="span" variant="body2" color="text.primary" sx={{ display: 'block' }}>
                                                        {res.uri}
                                                    </Typography>
                                                    {res.description} • {res.mimeType}
                                                </React.Fragment>
                                            }
                                        />
                                    </ListItem>
                                </Paper>
                            ))}
                        </List>
                    )}
                </TabPanel>

                {/* 3. Prompts */}
                <TabPanel value={tabValue} index={3}>
                    {!server.prompts || server.prompts.length === 0 ? (
                        <Typography color="text.secondary">No prompts discovered.</Typography>
                    ) : (
                        <List>
                            {server.prompts.map((prompt: any) => (
                                <Paper key={prompt.name} variant="outlined" sx={{ mb: 1 }}>
                                    <ListItem
                                        secondaryAction={
                                            <Button variant="outlined" size="small" onClick={() => { setSelectedPrompt(prompt); setPromptArgs({}); setViewingPromptResult(null); }}>
                                                Get Prompt
                                            </Button>
                                        }
                                    >
                                        <ListItemIcon><ChatBubbleOutline /></ListItemIcon>
                                        <ListItemText
                                            primary={prompt.name}
                                            secondary={prompt.description}
                                        />
                                    </ListItem>
                                </Paper>
                            ))}
                        </List>
                    )}
                </TabPanel>

                {/* 4. Test Lab */}
                <TabPanel value={tabValue} index={4}>
                    <Grid container spacing={3} sx={{ height: '100%' }}>
                        <Grid item xs={12} md={4}>
                            <Paper sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
                                <Typography variant="h6" gutterBottom>Select Tool</Typography>
                                <List sx={{ flexGrow: 1, overflow: 'auto' }}>
                                    {tools.map(tool => (
                                        <ListItem
                                            button
                                            key={tool.name}
                                            selected={selectedTool === tool.name}
                                            onClick={() => { setSelectedTool(tool.name); setTestResult(null); }}
                                        >
                                            <ListItemIcon><BugReport /></ListItemIcon>
                                            <ListItemText primary={tool.name} />
                                        </ListItem>
                                    ))}
                                </List>
                            </Paper>
                        </Grid>
                        <Grid item xs={12} md={8}>
                            {selectedTool ? (
                                <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 2 }}>
                                    <Paper sx={{ p: 2, flex: 1, display: 'flex', flexDirection: 'column' }}>
                                        <Typography variant="subtitle2" gutterBottom>Input Arguments (JSON)</Typography>
                                        <Box sx={{ flexGrow: 1, border: 1, borderColor: 'divider', borderRadius: 1 }}>
                                            <TextField
                                                fullWidth
                                                multiline
                                                rows={10}
                                                value={testInput}
                                                placeholder="Enter arguments JSON..."
                                                onChange={(e) => setTestInput(e.target.value)}
                                                inputProps={{
                                                    style: {
                                                        fontFamily: 'monospace',
                                                        fontSize: 12
                                                    }
                                                }}
                                                sx={{
                                                    bgcolor: 'transparent',
                                                    '& .MuiOutlinedInput-notchedOutline': { border: 'none' }
                                                }}
                                            />
                                        </Box>
                                        <Button
                                            variant="contained"
                                            startIcon={<PlayArrow />}
                                            onClick={handleTestTool}
                                            disabled={testing}
                                            sx={{ mt: 2 }}
                                        >
                                            Execute Tool
                                        </Button>
                                    </Paper>

                                    <Paper sx={{ p: 2, flex: 1, display: 'flex', flexDirection: 'column', bgcolor: 'background.default' }}>
                                        <Typography variant="subtitle2" gutterBottom>Result</Typography>
                                        {testing ? (
                                            <CircularProgress size={24} />
                                        ) : (
                                            <pre style={{ margin: 0, overflow: 'auto', whiteSpace: 'pre-wrap' }}>
                                                {testResult || 'Run tool to see output...'}
                                            </pre>
                                        )}
                                    </Paper>
                                </Box>
                            ) : (
                                <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                                    <Typography color="text.secondary">Select a tool to start testing</Typography>
                                </Box>
                            )}
                        </Grid>
                    </Grid>
                </TabPanel>
            </Box>

            {/* Resource Viewer Dialog */}
            <Dialog
                open={!!viewingResource}
                onClose={() => setViewingResource(null)}
                maxWidth="md"
                fullWidth
            >
                <DialogTitle>
                    {viewingResource?.name}
                    <Typography variant="body2" color="text.secondary">{viewingResource?.uri}</Typography>
                </DialogTitle>
                <DialogContent dividers>
                    {resourceLoading ? (
                        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>
                    ) : (
                        <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
                            {resourceContent}
                        </pre>
                    )}
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setViewingResource(null)}>Close</Button>
                </DialogActions>
            </Dialog>

            {/* Prompt Dialog */}
            <Dialog
                open={!!selectedPrompt}
                onClose={() => { if (!promptLoading) setSelectedPrompt(null); }}
                maxWidth="md"
                fullWidth
            >
                <DialogTitle>{selectedPrompt?.name}</DialogTitle>
                <DialogContent dividers>
                    {!viewingPromptResult ? (
                        <Box>
                            <Typography gutterBottom>{selectedPrompt?.description}</Typography>
                            {selectedPrompt?.arguments?.map((arg: any) => (
                                <TextField
                                    key={arg.name}
                                    margin="dense"
                                    label={arg.name + (arg.required ? ' *' : '')}
                                    fullWidth
                                    variant="outlined"
                                    helperText={arg.description}
                                    required={arg.required}
                                    value={promptArgs[arg.name] || ''}
                                    onChange={(e) => setPromptArgs({ ...promptArgs, [arg.name]: e.target.value })}
                                />
                            ))}
                        </Box>
                    ) : (
                        <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
                            {viewingPromptResult}
                        </pre>
                    )}
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setSelectedPrompt(null)}>Close</Button>
                    {!viewingPromptResult && (
                        <Button
                            onClick={handleGetPrompt}
                            variant="contained"
                            disabled={promptLoading}
                        >
                            {promptLoading ? <CircularProgress size={20} /> : 'Get Prompt'}
                        </Button>
                    )}
                </DialogActions>
            </Dialog>

        </Box>
    );
};

export default MCPServerDetailWorkspace;
