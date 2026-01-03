import React, { useState, useCallback, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { Node, Edge } from 'reactflow'
import {
    Box,
    Typography,
    IconButton,
    Button,
    Paper,
    TextField,
    CircularProgress,
    Alert,
    Divider,
    Chip,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    List,
    ListItem,
    ListItemText,
    ListItemButton,
} from '@mui/material'
import {
    ArrowBack as ArrowBackIcon,
    Save as SaveIcon,
    PlayArrow as PlayArrowIcon,
} from '@mui/icons-material'
import { getChain, updateChain, executeChain, validateChain, getChainExecutions, getExecutionStatus } from '../api/chains'
import { Agent } from '../api/agents'
import { Chain, ChainExecuteRequest, ChainNodeRequest, ChainEdgeRequest, ChainExecutionListItem, ChainExecutionStatusResponse } from '../types/chain'
import ChainCanvas from '../components/chain/ChainCanvas'
import EdgeConditionDialog from '../components/chain/EdgeConditionDialog'
import ExecutionHistory from '../components/chain/ExecutionHistory'
import NodeConfigPanel from '../components/chain/NodeConfigPanel'
import TestWorkflowModal from '../components/chain/TestWorkflowModal'
import { useNotification } from '../contexts/NotificationContext'

const ChainDetailWorkspace: React.FC = () => {
    const { chainId } = useParams<{ chainId: string }>()
    const navigate = useNavigate()
    const queryClient = useQueryClient()
    const { showError, showSuccess } = useNotification()

    const [editMode, setEditMode] = useState(false)
    const [editedName, setEditedName] = useState('')
    const [editedDescription, setEditedDescription] = useState('')
    const [executionInput, setExecutionInput] = useState('{}')
    const [validationResult, setValidationResult] = useState<any>(null)
    const [addNodeDialogOpen, setAddNodeDialogOpen] = useState(false)

    // Edge configuration state
    const [selectedEdge, setSelectedEdge] = useState<Edge | null>(null)
    const [edgeConfigDialogOpen, setEdgeConfigDialogOpen] = useState(false)

    // Node configuration state
    const [selectedNode, setSelectedNode] = useState<Node | null>(null)
    const [nodeConfigPanelOpen, setNodeConfigPanelOpen] = useState(false)

    // Test Modal state
    const [isTestModalOpen, setIsTestModalOpen] = useState(false)

    // Execution state
    const [showExecutionPanel, setShowExecutionPanel] = useState(true)
    const [selectedExecutionId, setSelectedExecutionId] = useState<string | null>(null)

    // Canvas state
    const [nodes, setNodes] = useState<Node[]>([])
    const [edges, setEdges] = useState<Edge[]>([])

    // Fetch chain
    const { data: chain, isLoading, error } = useQuery<Chain>(
        ['chain', chainId],
        () => getChain(chainId!),
        {
            enabled: !!chainId,
            onSuccess: (data) => {
                setEditedName(data.name)
                setEditedDescription(data.description || '')

                // Convert chain nodes to React Flow nodes
                const flowNodes: Node[] = data.nodes.map((node) => ({
                    id: node.node_id,
                    type: 'agentNode',
                    position: { x: node.position_x, y: node.position_y },
                    data: {
                        label: node.label,
                        agentId: node.agent_id,
                        nodeType: node.node_type,
                    },
                }))
                setNodes(flowNodes)

                // Convert chain edges to React Flow edges
                const flowEdges: Edge[] = data.edges.map((edge) => ({
                    id: edge.edge_id,
                    source: edge.source_node_id,
                    target: edge.target_node_id,
                    label: edge.label,
                    animated: true,
                    style: edge.condition && Object.keys(edge.condition || {}).length > 0
                        ? { stroke: '#ff9800', strokeDasharray: '5,5', strokeWidth: 2 }
                        : { stroke: '#007acc', strokeWidth: 2 },
                }))
                setEdges(flowEdges)
            },
        }
    )

    // Fetch agents for the add node dialog
    const { data: agents = [] } = useQuery<Agent[]>('agents', async () => {
        const response = await fetch('/api/v1/agents')
        if (!response.ok) throw new Error('Failed to fetch agents')
        return response.json()
    })

    // Fetch executions
    const { data: executions = [], refetch: refetchExecutions, isLoading: isLoadingExecutions } = useQuery<ChainExecutionListItem[]>(
        ['chainExecutions', chainId],
        () => getChainExecutions(chainId!),
        { enabled: !!chainId }
    )

    // Poll execution status if selected and running
    const { data: executionStatus } = useQuery<ChainExecutionStatusResponse>(
        ['executionStatus', selectedExecutionId],
        () => getExecutionStatus(selectedExecutionId!),
        {
            enabled: !!selectedExecutionId,
            refetchInterval: (data) => (data?.status === 'running' || data?.status === 'pending' ? 1000 : false),
            onSuccess: (data) => {
                // Update node statuses based on execution progress
                if (nodes.length > 0) {
                    setNodes(currentNodes => currentNodes.map(node => {
                        let status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped' | undefined = undefined;

                        if (data.node_states && data.node_states[node.id]) {
                            const backendStatus = data.node_states[node.id].toLowerCase();
                            if (['pending', 'running', 'completed', 'failed', 'skipped'].includes(backendStatus)) {
                                status = backendStatus as any;
                            }
                        }

                        if (!status) {
                            if (data.current_node_id === node.id) {
                                status = 'running'
                            } else if (data.completed_nodes?.includes(node.id)) {
                                status = 'completed'
                            } else if (data.status === 'failed' && data.current_node_id === node.id) {
                                status = 'failed'
                            }
                        }

                        if (status && status !== node.data.status) {
                            return {
                                ...node,
                                data: {
                                    ...node.data,
                                    status
                                }
                            }
                        }
                        return node
                    }))
                }
            }
        }
    )

    // Update chain mutation
    const updateMutation = useMutation(
        () => updateChain(chainId!, {
            name: editedName,
            description: editedDescription,
        }),
        {
            onSuccess: () => {
                queryClient.invalidateQueries(['chain', chainId])
                setEditMode(false)
            },
        }
    )

    // Save chain structure mutation
    const saveChainMutation = useMutation(
        (data: { nodes: ChainNodeRequest[]; edges: ChainEdgeRequest[] }) =>
            updateChain(chainId!, data),
        {
            onSuccess: () => {
                queryClient.invalidateQueries(['chain', chainId])
                alert('Chain saved successfully!')
            },
        }
    )

    // Execute chain mutation
    const executeMutation = useMutation(
        (request: ChainExecuteRequest) => executeChain(chainId!, request),
        {
            onSuccess: (execution) => {
                // alert(`Chain execution started! Execution ID: ${execution.id}`)
                queryClient.invalidateQueries(['chainExecutions', chainId])
                setSelectedExecutionId(execution.id)
                setShowExecutionPanel(true)
            },
            onError: (error: any) => {
                const message = error.response?.data?.detail || error.message || 'Execution failed'
                showError(`Error executing chain: ${message}`)
            }
        }
    )

    // Validate chain
    const handleValidate = async () => {
        try {
            const result = await validateChain(chainId!)
            setValidationResult(result)
        } catch (error: any) {
            setValidationResult({ is_valid: false, errors: [error.message] })
        }
    }

    // Execute chain
    const handleExecute = () => {
        try {
            const inputData = JSON.parse(executionInput)
            executeMutation.mutate({ input_data: inputData })
        } catch (error) {
            alert('Invalid JSON input')
        }
    }

    // Save chain canvas
    const handleSaveCanvas = useCallback((savedNodes: Node[], savedEdges: Edge[]) => {
        // Convert React Flow nodes to chain nodes
        const chainNodes: ChainNodeRequest[] = savedNodes.map((node, index) => ({
            node_id: node.id,
            node_type: node.data.nodeType || 'agent',
            agent_id: node.data.agentId,
            label: node.data.label,
            position_x: node.position.x,
            position_y: node.position.y,
            config: node.data.config || {},
            order_index: index,
        }))

        // Convert React Flow edges to chain edges
        const chainEdges: ChainEdgeRequest[] = savedEdges.map((edge) => ({
            edge_id: edge.id,
            source_node_id: edge.source,
            target_node_id: edge.target,
            label: typeof edge.label === 'string' ? edge.label : undefined,
            condition: edge.data?.condition || {},
        }))

        saveChainMutation.mutate({ nodes: chainNodes, edges: chainEdges })
    }, [saveChainMutation])

    // Handle edge click
    const handleEdgeClick = useCallback((edge: Edge) => {
        setSelectedEdge(edge)
        setEdgeConfigDialogOpen(true)
    }, [])

    // Handle edge config save
    const handleEdgeConfigSave = (label: string, conditions: any[]) => {
        if (!selectedEdge) return

        setEdges((eds) =>
            eds.map((e) => {
                if (e.id === selectedEdge.id) {
                    return {
                        ...e,
                        label: label,
                        data: {
                            ...e.data,
                            condition: { rules: conditions },
                        },
                        // Update style if condition added/removed
                        style: conditions && conditions.length > 0
                            ? { stroke: '#ff9800', strokeDasharray: '5,5', strokeWidth: 2 }
                            : { stroke: '#007acc', strokeWidth: 2 }
                    }
                }
                return e
            })
        )
        setEdgeConfigDialogOpen(false)
        setSelectedEdge(null)
    }

    // Handle node click
    const handleNodeClick = useCallback((node: Node) => {
        setSelectedNode(node)
        setNodeConfigPanelOpen(true)
    }, [])

    // Handle node config save
    const handleNodeConfigSave = (nodeId: string, updates: Partial<Node>) => {
        setNodes((nds) =>
            nds.map((n) => {
                if (n.id === nodeId) {
                    return { ...n, ...updates }
                }
                return n
            })
        )
        setNodeConfigPanelOpen(false)
        setSelectedNode(null)
    }

    // Add new node
    const handleAddNode = (agentId: string, agentName: string) => {
        const newNode: Node = {
            id: `node-${Date.now()}`,
            type: 'agentNode',
            position: { x: 250, y: nodes.length * 100 + 50 },
            data: {
                label: agentName,
                agentId: agentId,
                nodeType: 'agent',
                agentName: agentName,
            },
        }
        setNodes((nds) => [...nds, newNode])
        setAddNodeDialogOpen(false)
    }

    if (isLoading) {
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                <CircularProgress />
            </Box>
        )
    }

    if (error || !chain) {
        return (
            <Box sx={{ p: 3 }}>
                <Alert severity="error">Chain not found</Alert>
            </Box>
        )
    }

    return (
        <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            {/* Header */}
            <Box sx={{ p: 2, borderBottom: '1px solid #ddd', display: 'flex', alignItems: 'center', gap: 2 }}>
                <IconButton onClick={() => navigate('/chains')} size="small">
                    <ArrowBackIcon />
                </IconButton>

                {editMode ? (
                    <TextField
                        value={editedName}
                        onChange={(e) => setEditedName(e.target.value)}
                        variant="outlined"
                        size="small"
                        sx={{ flex: 1 }}
                    />
                ) : (
                    <Typography variant="h6">{chain.name}</Typography>
                )}

                <Chip
                    label={chain.status}
                    color={chain.status === 'active' ? 'success' : 'default'}
                    size="small"
                />

                <Box sx={{ ml: 'auto', display: 'flex', gap: 1 }}>
                    {editMode ? (
                        <>
                            <Button
                                variant="outlined"
                                size="small"
                                onClick={() => {
                                    setEditMode(false)
                                    setEditedName(chain.name)
                                    setEditedDescription(chain.description || '')
                                }}
                            >
                                Cancel
                            </Button>
                            <Button
                                variant="contained"
                                size="small"
                                startIcon={<SaveIcon />}
                                onClick={() => updateMutation.mutate()}
                                disabled={updateMutation.isLoading}
                            >
                                Save
                            </Button>
                        </>
                    ) : (
                        <>
                            <Button variant="outlined" size="small" onClick={() => setEditMode(true)}>
                                Edit Info
                            </Button>
                            <Button variant="outlined" size="small" onClick={handleValidate}>
                                Validate
                            </Button>

                            {chain.nodes.length > 0 && (
                                <Button
                                    variant="contained"
                                    color="secondary"
                                    size="small"
                                    startIcon={<PlayArrowIcon />}
                                    onClick={() => setIsTestModalOpen(true)}
                                >
                                    Test Workflow
                                </Button>
                            )}
                        </>
                    )}
                </Box>
            </Box>

            <Box sx={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
                {/* Chain Canvas */}
                <Box sx={{ flex: 1, position: 'relative' }}>
                    <ChainCanvas
                        nodes={nodes}
                        edges={edges}
                        onNodesChange={setNodes}
                        onEdgesChange={setEdges}
                        onSave={handleSaveCanvas}
                        onAddNode={() => setAddNodeDialogOpen(true)}
                        onEdgeClick={handleEdgeClick}
                        onNodeClick={handleNodeClick}
                    />
                </Box>

                {/* Execution Panel */}
                {showExecutionPanel && (
                    <Paper
                        elevation={3}
                        sx={{
                            width: 320,
                            borderLeft: '1px solid #ddd',
                            display: 'flex',
                            flexDirection: 'column',
                            zIndex: 10
                        }}
                    >
                        <Box sx={{ p: 2, borderBottom: '1px solid #eee' }}>
                            <Typography variant="subtitle2" gutterBottom>Execute Chain</Typography>
                            <TextField
                                multiline
                                rows={3}
                                fullWidth
                                placeholder='{"input": "value"}'
                                value={executionInput}
                                onChange={(e) => setExecutionInput(e.target.value)}
                                size="small"
                                sx={{ mb: 1, fontFamily: 'monospace' }}
                            />
                            <Button
                                fullWidth
                                variant="contained"
                                color="success"
                                startIcon={executeMutation.isLoading ? <CircularProgress size={20} color="inherit" /> : <PlayArrowIcon />}
                                onClick={handleExecute}
                                disabled={executeMutation.isLoading}
                            >
                                {executeMutation.isLoading ? 'Starting...' : 'Run Chain'}
                            </Button>
                        </Box>

                        <ExecutionHistory
                            executions={executions}
                            selectedExecutionId={selectedExecutionId || undefined}
                            onSelectExecution={setSelectedExecutionId}
                            isLoading={isLoadingExecutions}
                            onRefresh={refetchExecutions}
                        />
                    </Paper>
                )}
            </Box>

            {/* Edge Condition Dialog */}
            <EdgeConditionDialog
                open={edgeConfigDialogOpen}
                onClose={() => setEdgeConfigDialogOpen(false)}
                onSave={handleEdgeConfigSave}
                initialLabel={selectedEdge?.label as string}
                initialConditions={selectedEdge?.data?.condition?.rules}
            />

            {/* Validation Results */}
            {
                validationResult && (
                    <Paper sx={{ position: 'absolute', bottom: 20, right: 20, p: 2, maxWidth: 400, zIndex: 1000 }}>
                        <Alert severity={validationResult.is_valid ? 'success' : 'error'}>
                            {validationResult.is_valid ? (
                                'Chain is valid!'
                            ) : (
                                <>
                                    <Typography variant="body2" fontWeight="bold">Errors:</Typography>
                                    {validationResult.errors.map((error: string, idx: number) => (
                                        <Typography key={idx} variant="body2">• {error}</Typography>
                                    ))}
                                </>
                            )}
                        </Alert>
                    </Paper>
                )
            }

            {/* Add Node Dialog */}
            <Dialog open={addNodeDialogOpen} onClose={() => setAddNodeDialogOpen(false)} maxWidth="sm" fullWidth>
                <DialogTitle>Add Agent Node</DialogTitle>
                <DialogContent>
                    <List>
                        {agents.map((agent) => (
                            <ListItemButton
                                key={agent.id}
                                onClick={() => handleAddNode(agent.id, agent.name)}
                            >
                                <ListItemText
                                    primary={agent.name}
                                    secondary={agent.description || 'No description'}
                                />
                            </ListItemButton>
                        ))}
                    </List>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setAddNodeDialogOpen(false)}>Cancel</Button>
                </DialogActions>
            </Dialog>

            {/* Node Configuration Panel */}
            {
                nodeConfigPanelOpen && selectedNode && (
                    <Box
                        sx={{
                            position: 'fixed',
                            top: 48,
                            right: 0,
                            height: 'calc(100vh - 48px)',
                            zIndex: 1300,
                            backgroundColor: '#fafafa',
                            boxShadow: '-2px 0 8px rgba(0,0,0,0.1)'
                        }}
                    >
                        <NodeConfigPanel
                            node={selectedNode}
                            agents={agents}
                            onClose={() => {
                                setNodeConfigPanelOpen(false)
                                setSelectedNode(null)
                            }}
                            onSave={handleNodeConfigSave}
                        />
                    </Box>
                )
            }

            {/* Edge Configuration Dialog */}
            <EdgeConditionDialog
                open={edgeConfigDialogOpen}
                initialLabel={selectedEdge?.label as string || ''}
                initialConditions={selectedEdge?.data?.condition?.rules || []}
                onClose={() => {
                    setEdgeConfigDialogOpen(false)
                    setSelectedEdge(null)
                }}
                onSave={handleEdgeConfigSave}

            />

            {/* Test Workflow Modal */}
            <TestWorkflowModal
                open={isTestModalOpen}
                onClose={() => setIsTestModalOpen(false)}
                chain={chain}
            />
        </Box >
    )
}

export default ChainDetailWorkspace
