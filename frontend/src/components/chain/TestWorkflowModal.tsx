import React, { useState, useEffect, useRef } from 'react';
import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Button,
    Grid,
    Paper,
    Typography,
    Box,
    TextField,
    CircularProgress,
    IconButton,
    Tabs,
    Tab,
    Chip,
    Alert,
    Divider,
    Accordion,
    AccordionSummary,
    AccordionDetails,
    FormControl,
    InputLabel,
    Select,
    MenuItem,
    Stack
} from '@mui/material';
import {
    Close,
    PlayArrow,
    Stop,
    Refresh,
    CheckCircle,
    Error as ErrorIcon,
    HourglassEmpty,
    ExpandMore
} from '@mui/icons-material';
import { Node, Edge } from 'reactflow';
import { useQuery, useMutation, useQueryClient } from 'react-query';

import { executeChain, getExecution, getExecutionLogs, cancelExecution } from '../../api/chains';
import { getModels } from '../../api/llmModels';
import { Chain, ChainExecutionStatusResponse, ChainExecutionLog, ChainExecution } from '../../types/chain';
import ChainCanvas from './ChainCanvas';

interface TestWorkflowModalProps {
    open: boolean;
    onClose: () => void;
    chain: Chain;
}

interface LogEntry {
    timestamp: string;
    level: string;
    message: string;
    node_id?: string;
    metadata?: any;
}

const TestWorkflowModal: React.FC<TestWorkflowModalProps> = ({ open, onClose, chain }) => {
    const queryClient = useQueryClient();
    const [inputData, setInputData] = useState('');
    const [executionId, setExecutionId] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState(0);
    const [selectedModelId, setSelectedModelId] = useState<string>('');

    // Fetch LLM Models for override
    const { data: llmModels } = useQuery('llmModels', getModels);

    // Canvas State
    const [nodes, setNodes] = useState<Node[]>([]);
    const [edges, setEdges] = useState<Edge[]>([]);

    // Initialize nodes/edges from chain
    useEffect(() => {
        if (chain && open) {
            // Reset state on open
            if (!executionId) {
                const initialNodes: Node[] = chain.nodes.map((node) => ({
                    id: node.node_id,
                    type: 'agentNode',
                    position: { x: node.position_x, y: node.position_y },
                    data: {
                        label: node.label,
                        agentId: node.agent_id,
                        nodeType: node.node_type,
                        status: 'pending' // Initial status
                    },
                }));
                setNodes(initialNodes);

                const initialEdges: Edge[] = chain.edges.map((edge) => ({
                    id: edge.edge_id,
                    source: edge.source_node_id,
                    target: edge.target_node_id,
                    label: edge.label,
                    animated: false, // Default not animated
                    style: { stroke: '#bdbdbd', strokeWidth: 2 } // Default gray
                }));
                setEdges(initialEdges);
            }
        }
    }, [chain, open, executionId]);

    // Execute Mutation
    const executeMutation = useMutation(
        async () => {
            let data;
            try {
                // Try parsing as JSON first
                data = JSON.parse(inputData);
            } catch (e) {
                // If invalid JSON, treat as raw string input wrapped in default key 'input'
                data = { input: inputData };
            }

            // If it parsed but isn't an object (e.g. number/boolean/string), wrap it
            if (typeof data !== 'object' || data === null) {
                data = { input: data };
            }

            // Prepare execution payload
            const payload: any = { input_data: data };

            // Add model override if selected
            if (selectedModelId && llmModels) {
                const selectedModel = llmModels.find(m => m.id === selectedModelId);
                if (selectedModel) {
                    payload.model_override = {
                        model_name: selectedModel.name,
                        llm_provider: selectedModel.provider,
                        // Pass other config if needed, e.g. api_base
                        ...(selectedModel.api_base ? { api_base: selectedModel.api_base } : {})
                    };
                }
            }

            return await executeChain(chain.id, payload);
        },
        {
            onSuccess: (data: ChainExecution) => {
                setExecutionId(data.id);
            },
            onError: (error: any) => {
                const msg = error.response?.data?.detail || error.message || 'Execution failed';
                alert(`Execution failed: ${msg}`);
            }
        }
    );

    // Cancel Mutation
    const cancelMutation = useMutation(
        async () => {
            if (executionId) {
                await cancelExecution(executionId);
            }
        },
        {
            onSuccess: () => {
                queryClient.invalidateQueries(['executionStatus', executionId]);
            }
        }
    );

    // Poll Execution Details (Full object)
    const { data: status } = useQuery<ChainExecution>(
        ['executionDetails', executionId],
        () => getExecution(executionId!),
        {
            enabled: !!executionId,
            refetchInterval: (data) => {
                if (!data) return 10000;
                return ['running', 'pending'].includes(data.status.toLowerCase()) ? 10000 : false;
            },
            onSuccess: (data) => {
                updateVisuals(data);
            }
        }
    );

    // Poll Logs
    const { data: logs } = useQuery<ChainExecutionLog[]>(
        ['executionLogs', executionId],
        () => getExecutionLogs(executionId!, { skip: 0, limit: 1000 }), // Fetch all (limited to 1000)
        {
            enabled: !!executionId,
            refetchInterval: (data) => {
                // Poll logs at same frequency as status
                return status && ['running', 'pending'].includes(status.status.toLowerCase()) ? 10000 : false;
            }
        }
    );

    const updateVisuals = (statusData: ChainExecution) => {
        // Update Nodes
        setNodes((currentNodes) => currentNodes.map(node => {
            let nodeStatus = 'pending';
            if (statusData.current_node_id === node.id) nodeStatus = 'running';
            else if (statusData.completed_nodes?.includes(node.id)) nodeStatus = 'completed';

            // Check status from node_results if available (more reliable for completed)
            if (statusData.node_results && statusData.node_results[node.id]) {
                // If it has a result, it's completed (unless failed status elsewhere?)
            }

            // Handle failures
            if (statusData.status === 'failed' && nodeStatus === 'running') nodeStatus = 'failed';

            // Get output
            const output = statusData.node_results ? statusData.node_results[node.id] : null;

            return {
                ...node,
                data: {
                    ...node.data,
                    status: nodeStatus,
                    output: output
                }
            };
        }));

        // Update Edges
        setEdges((currentEdges) => currentEdges.map(edge => {
            const isActive = statusData.active_edges?.includes(edge.id);

            // Determine label from edge results
            let edgeLabel = edge.label;
            if (statusData.edge_results && statusData.edge_results[edge.id]) {
                const result = statusData.edge_results[edge.id];
                if (result.met !== undefined) {
                    edgeLabel = result.met ? "True" : "False";
                }
            }

            return {
                ...edge,
                label: edgeLabel,
                animated: isActive,
                style: isActive
                    ? { stroke: '#4caf50', strokeWidth: 3 }
                    : { stroke: '#bdbdbd', strokeWidth: 1 }
            };
        }));
    };

    const handleReset = () => {
        setExecutionId(null);
        // Reset visuals done by useEffect
    };

    // Render Node Outputs Helper
    const renderNodeOutputs = () => {
        if (!status?.node_results || Object.keys(status.node_results).length === 0) {
            return null;
        }

        const nodeEntries = Object.entries(status.node_results).filter(([nodeId]) => nodeId !== '__states__');

        if (nodeEntries.length === 0) return null;

        return (
            <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>Node Outputs</Typography>
                {nodeEntries.map(([nodeId, result]: [string, any]) => {
                    const nodeLabel = chain.nodes.find(n => n.node_id === nodeId)?.label || nodeId;
                    return (
                        <Accordion key={nodeId} defaultExpanded={false}>
                            <AccordionSummary expandIcon={<ExpandMore />}>
                                <Typography variant="body2" sx={{ fontWeight: 500 }}>
                                    {nodeLabel}
                                </Typography>
                            </AccordionSummary>
                            <AccordionDetails>
                                <Box sx={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
                                    {result.input && (
                                        <Box sx={{ mb: 2 }}>
                                            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                                                Input:
                                            </Typography>
                                            <Box component="pre" sx={{
                                                whiteSpace: 'pre-wrap',
                                                bgcolor: '#f5f5f5',
                                                p: 1,
                                                borderRadius: 1,
                                                mt: 0.5,
                                                m: 0
                                            }}>
                                                {JSON.stringify(result.input, null, 2)}
                                            </Box>
                                        </Box>
                                    )}
                                    {result.output && (
                                        <Box>
                                            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                                                Output:
                                            </Typography>
                                            <Box component="pre" sx={{
                                                whiteSpace: 'pre-wrap',
                                                bgcolor: '#e8f5e9',
                                                p: 1,
                                                borderRadius: 1,
                                                mt: 0.5,
                                                m: 0
                                            }}>
                                                {typeof result.output === 'string'
                                                    ? result.output
                                                    : JSON.stringify(result.output, null, 2)}
                                            </Box>
                                        </Box>
                                    )}
                                    {result.timestamp && (
                                        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                                            Completed: {new Date(result.timestamp).toLocaleString()}
                                        </Typography>
                                    )}
                                </Box>
                            </AccordionDetails>
                        </Accordion>
                    );
                })}
            </Box>
        );
    };

    // Render Logs Helper
    const renderLogs = () => {
        if (!logs || logs.length === 0) return <Typography color="text.secondary" sx={{ p: 2 }}>Waiting for logs...</Typography>;

        return (
            <Box sx={{ flex: 1, overflowY: 'auto', p: 1, maxHeight: '60vh', fontFamily: 'monospace', fontSize: '0.9rem' }}>
                {logs.map((log) => (
                    <Box key={log.id} sx={{ mb: 1, borderLeft: `3px solid ${getLogColor(log.level)}`, pl: 1 }}>
                        <Typography variant="caption" color="text.secondary">
                            {new Date(log.timestamp).toLocaleTimeString()} [{log.level}] {log.node_id ? `[${log.node_id}]` : ''}
                        </Typography>
                        <Typography component="pre" sx={{ whiteSpace: 'pre-wrap', m: 0 }}>
                            {log.message}
                        </Typography>
                        {log.metadata && Object.keys(log.metadata).length > 0 && (
                            <Box sx={{ mt: 0.5, bgcolor: '#f5f5f5', p: 0.5, borderRadius: 1 }}>
                                <Typography variant="caption" component="pre" sx={{ fontSize: '0.75rem' }}>
                                    {JSON.stringify(log.metadata, null, 2)}
                                </Typography>
                            </Box>
                        )}
                    </Box>
                ))}
            </Box>
        );
    };

    const getLogColor = (level: string) => {
        switch (level) {
            case 'ERROR': return '#f44336';
            case 'WARNING': return '#ff9800';
            case 'INFO': return '#2196f3';
            default: return '#9e9e9e';
        }
    };

    return (
        <Dialog fullScreen open={open} onClose={onClose}>
            <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                {/* Header */}
                <Box sx={{ p: 2, borderBottom: '1px solid #ddd', display: 'flex', alignItems: 'center', justifyContent: 'space-between', bgcolor: '#f5f5f5' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <Button startIcon={<Close />} onClick={onClose} variant="outlined">
                            Close
                        </Button>
                        <Typography variant="h6">Test Workflow: {chain.name}</Typography>
                        {status && (
                            <Chip
                                label={status.status}
                                color={
                                    status.status === 'completed' ? 'success' :
                                        status.status === 'failed' ? 'error' :
                                            status.status === 'running' ? 'primary' : 'default'
                                }
                            />
                        )}
                    </Box>
                    <Box sx={{ display: 'flex', gap: 1 }}>
                        {!executionId ? (
                            <Button
                                variant="contained"
                                color="success"
                                startIcon={executeMutation.isLoading ? <CircularProgress size={20} color="inherit" /> : <PlayArrow />}
                                onClick={() => executeMutation.mutate()}
                                disabled={executeMutation.isLoading}
                            >
                                Start Execution
                            </Button>
                        ) : (
                            <>
                                <Button
                                    variant="outlined"
                                    startIcon={<Refresh />}
                                    onClick={handleReset}
                                    disabled={['running', 'pending'].includes(status?.status || '')}
                                >
                                    New Test
                                </Button>
                                {['running', 'pending'].includes(status?.status || '') && (
                                    <Button
                                        variant="contained"
                                        color="error"
                                        startIcon={<Stop />}
                                        onClick={() => cancelMutation.mutate()}
                                    >
                                        Stop
                                    </Button>
                                )}
                            </>
                        )}
                    </Box>
                </Box>

                {/* Body */}
                <Box sx={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
                    {/* Left: Canvas */}
                    <Box sx={{ flex: 2, borderRight: '1px solid #ddd', position: 'relative' }}>
                        <ChainCanvas
                            nodes={nodes}
                            edges={edges}
                            readonly={true}
                        />
                    </Box>

                    {/* Right: Controls & Logs */}
                    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', bgcolor: 'white' }}>
                        <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v)} sx={{ borderBottom: 1, borderColor: 'divider' }}>
                            <Tab label="Input & Config" />
                            <Tab label="Logs & Output" />
                        </Tabs>

                        <Box sx={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                            {activeTab === 0 && (
                                <Box sx={{ p: 2, overflowY: 'auto' }}>
                                    <Stack spacing={2}>
                                        <Box>
                                            <Typography variant="subtitle2" gutterBottom>Model Override (Optional)</Typography>
                                            <FormControl fullWidth size="small">
                                                <InputLabel id="model-override-label">Override Agent Models</InputLabel>
                                                <Select
                                                    labelId="model-override-label"
                                                    value={selectedModelId}
                                                    label="Override Agent Models"
                                                    onChange={(e) => setSelectedModelId(e.target.value)}
                                                    disabled={!!executionId}
                                                >
                                                    <MenuItem value="">
                                                        <em>None (Use Agent Defaults)</em>
                                                    </MenuItem>
                                                    {llmModels?.map((model) => (
                                                        <MenuItem key={model.id} value={model.id}>
                                                            {model.name} ({model.provider})
                                                        </MenuItem>
                                                    ))}
                                                </Select>
                                            </FormControl>
                                            <Typography variant="caption" color="text.secondary">
                                                Select a model to force all agents in this workflow to use it during this test.
                                            </Typography>
                                        </Box>

                                        <Box>
                                            <Typography variant="subtitle2" gutterBottom>Execution Input</Typography>
                                            <TextField
                                                fullWidth
                                                multiline
                                                rows={10}
                                                value={inputData}
                                                onChange={(e) => setInputData(e.target.value)}
                                                disabled={!!executionId}
                                                placeholder="Enter plain text or JSON..."
                                                helperText="Enter any text (will be wrapped as {input: 'text'}) or valid JSON object."
                                                sx={{ fontFamily: 'monospace' }}
                                            />
                                        </Box>
                                    </Stack>
                                </Box>
                            )}

                            {activeTab === 1 && (
                                <Box sx={{ p: 2, overflowY: 'auto', flex: 1 }}>
                                    {renderNodeOutputs()}

                                    {logs && logs.length > 0 && (
                                        <>
                                            <Divider sx={{ my: 2 }} />
                                            <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                                                Execution Logs
                                            </Typography>
                                            {renderLogs()}
                                        </>
                                    )}

                                    {status?.error_message && (
                                        <Alert severity="error" sx={{ mt: 2 }}>
                                            {status.error_message}
                                        </Alert>
                                    )}
                                </Box>
                            )}
                        </Box>
                    </Box>
                </Box>
            </Box>
        </Dialog>
    );
};

export default TestWorkflowModal;
