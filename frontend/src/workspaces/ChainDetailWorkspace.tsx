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
import { getChain, updateChain, executeChain, validateChain } from '../api/chains'
import { Chain, ChainExecuteRequest, ChainNodeRequest, ChainEdgeRequest } from '../types/chain'
import ChainCanvas from '../components/chain/ChainCanvas'

interface Agent {
    id: string
    name: string
    description?: string
}

const ChainDetailWorkspace: React.FC = () => {
    const { chainId } = useParams<{ chainId: string }>()
    const navigate = useNavigate()
    const queryClient = useQueryClient()

    const [editMode, setEditMode] = useState(false)
    const [editedName, setEditedName] = useState('')
    const [editedDescription, setEditedDescription] = useState('')
    const [executionInput, setExecutionInput] = useState('{}')
    const [validationResult, setValidationResult] = useState<any>(null)
    const [addNodeDialogOpen, setAddNodeDialogOpen] = useState(false)

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
                alert(`Chain execution started! Execution ID: ${execution.id}`)
                queryClient.invalidateQueries(['chain', chainId])
            },
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
            config: {},
            order_index: index,
        }))

        // Convert React Flow edges to chain edges
        const chainEdges: ChainEdgeRequest[] = savedEdges.map((edge) => ({
            edge_id: edge.id,
            source_node_id: edge.source,
            target_node_id: edge.target,
            label: typeof edge.label === 'string' ? edge.label : undefined,
        }))

        saveChainMutation.mutate({ nodes: chainNodes, edges: chainEdges })
    }, [saveChainMutation])

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
                                    size="small"
                                    startIcon={<PlayArrowIcon />}
                                    onClick={handleExecute}
                                    disabled={executeMutation.isLoading}
                                >
                                    Execute
                                </Button>
                            )}
                        </>
                    )}
                </Box>
            </Box>

            {/* Chain Canvas */}
            <Box sx={{ flex: 1, position: 'relative' }}>
                <ChainCanvas
                    nodes={nodes}
                    edges={edges}
                    onNodesChange={setNodes}
                    onEdgesChange={setEdges}
                    onSave={handleSaveCanvas}
                    onAddNode={() => setAddNodeDialogOpen(true)}
                />
            </Box>

            {/* Validation Results */}
            {validationResult && (
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
            )}

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
        </Box>
    )
}

export default ChainDetailWorkspace
