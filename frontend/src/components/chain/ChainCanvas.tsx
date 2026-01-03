import React, { useCallback, useMemo, useState } from 'react'
import ReactFlow, {
    Node,
    Edge,
    Controls,
    Background,
    BackgroundVariant,
    MiniMap,
    useNodesState,
    useEdgesState,
    addEdge,
    Connection,
    ConnectionMode,
    Panel,
    MarkerType,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { Box, Button, IconButton, Tooltip } from '@mui/material'
import { Add as AddIcon, Save as SaveIcon, Delete as DeleteIcon } from '@mui/icons-material'
import AgentNode from './AgentNode'

interface ChainCanvasProps {
    nodes: Node[]
    edges: Edge[]
    onNodesChange?: (nodes: Node[]) => void
    onEdgesChange?: (edges: Edge[]) => void
    onSave?: (nodes: Node[], edges: Edge[]) => void
    onAddNode?: () => void
    onEdgeClick?: (edge: Edge) => void
    onNodeClick?: (node: Node) => void
    readonly?: boolean
}

const ChainCanvas: React.FC<ChainCanvasProps> = ({
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    onSave,
    onAddNode,
    onEdgeClick,
    onNodeClick,
    readonly = false,
}) => {
    // Use controlled state from parent
    const [localNodes, setLocalNodes, onNodesChangeInternal] = useNodesState(nodes)
    const [localEdges, setLocalEdges, onEdgesChangeInternal] = useEdgesState(edges)

    // Sync with parent when nodes/edges change externally
    React.useEffect(() => {
        setLocalNodes(nodes)
    }, [nodes, setLocalNodes])

    React.useEffect(() => {
        setLocalEdges(edges)
    }, [edges, setLocalEdges])

    // Custom node types
    const nodeTypes = useMemo(
        () => ({
            agentNode: AgentNode,
        }),
        []
    )

    // Handle nodes change and notify parent
    const handleNodesChange = useCallback(
        (changes: any) => {
            onNodesChangeInternal(changes)
            if (onNodesChange && !readonly) {
                // Get updated nodes after applying changes
                setTimeout(() => onNodesChange(localNodes), 0)
            }
        },
        [onNodesChangeInternal, onNodesChange, readonly, localNodes]
    )

    // Handle edges change and notify parent
    const handleEdgesChange = useCallback(
        (changes: any) => {
            onEdgesChangeInternal(changes)
            if (onEdgesChange && !readonly) {
                setTimeout(() => onEdgesChange(localEdges), 0)
            }
        },
        [onEdgesChangeInternal, onEdgesChange, readonly, localEdges]
    )

    // Handle new connections
    const onConnect = useCallback(
        (params: Connection) => {
            if (!readonly) {
                setLocalEdges((eds) => addEdge(params, eds))
                if (onEdgesChange) {
                    setTimeout(() => onEdgesChange(localEdges), 0)
                }
            }
        },
        [setLocalEdges, readonly, onEdgesChange, localEdges]
    )

    // Handle node deletion
    const handleNodesDelete = useCallback(
        (deleted: Node[]) => {
            if (!readonly) {
                setLocalNodes((nds) => nds.filter((n) => !deleted.find((d) => d.id === n.id)))
                // Also remove edges connected to deleted nodes
                setLocalEdges((eds) => eds.filter((e) =>
                    !deleted.find((d) => d.id === e.source || d.id === e.target)
                ))
                if (onNodesChange) {
                    setTimeout(() => onNodesChange(localNodes), 0)
                }
            }
        },
        [readonly, onNodesChange, localNodes, setLocalNodes, setLocalEdges]
    )

    // Handle edge deletion
    const handleEdgesDelete = useCallback(
        (deleted: Edge[]) => {
            if (!readonly) {
                setLocalEdges((eds) => eds.filter((e) => !deleted.find((d) => d.id === e.id)))
                if (onEdgesChange) {
                    setTimeout(() => onEdgesChange(localEdges), 0)
                }
            }
        },
        [readonly, onEdgesChange, localEdges, setLocalEdges]
    )

    // Handle save
    const handleSave = useCallback(() => {
        if (onSave) {
            onSave(localNodes, localEdges)
        }
    }, [localNodes, localEdges, onSave])

    return (
        <Box sx={{ width: '100%', height: '100%', position: 'relative' }}>
            <ReactFlow
                nodes={localNodes}
                edges={localEdges}
                onNodesChange={readonly ? undefined : handleNodesChange}
                onEdgesChange={readonly ? undefined : handleEdgesChange}
                onConnect={onConnect}
                nodeTypes={nodeTypes}
                connectionMode={ConnectionMode.Loose}
                fitView
                snapToGrid
                snapGrid={[15, 15]}
                defaultEdgeOptions={{
                    animated: true,
                    style: { stroke: '#007acc', strokeWidth: 2 },
                    type: 'smoothstep',
                    markerEnd: {
                        type: MarkerType.ArrowClosed,
                        color: '#007acc',
                        width: 20,
                        height: 20,
                    },
                }}
                nodesDraggable={!readonly}
                nodesConnectable={!readonly}
                elementsSelectable={!readonly}
                deleteKeyCode={readonly ? null : ['Delete', 'Backspace']}
                onNodesDelete={readonly ? undefined : handleNodesDelete}
                onEdgesDelete={readonly ? undefined : handleEdgesDelete}
                onEdgeClick={readonly ? undefined : (_, edge) => onEdgeClick && onEdgeClick(edge)}
                onNodeClick={readonly ? undefined : (_, node) => onNodeClick && onNodeClick(node)}
            >
                <Background
                    variant={BackgroundVariant.Dots}
                    gap={15}
                    size={1}
                    color="#3e3e42"
                    style={{ backgroundColor: '#1e1e1e' }}
                />
                <Controls showInteractive={!readonly} />
                <MiniMap
                    nodeColor={(node) => {
                        switch (node.type) {
                            case 'agentNode':
                                return '#007acc'
                            default:
                                return '#666'
                        }
                    }}
                    nodeStrokeWidth={3}
                    zoomable
                    pannable
                    maskColor="#252526dd"
                    style={{ backgroundColor: '#1e1e1e', border: '1px solid #3e3e42' }}
                />

                {/* Toolbar */}
                {!readonly && (
                    <Panel position="top-right">
                        <Box sx={{ display: 'flex', gap: 1, backgroundColor: 'white', p: 1, borderRadius: 1, boxShadow: 1 }}>
                            {onAddNode && (
                                <Tooltip title="Add Agent Node">
                                    <IconButton
                                        size="small"
                                        onClick={onAddNode}
                                        sx={{ color: '#007acc' }}
                                    >
                                        <AddIcon />
                                    </IconButton>
                                </Tooltip>
                            )}
                            {onSave && (
                                <Tooltip title="Save Chain">
                                    <IconButton
                                        size="small"
                                        onClick={handleSave}
                                        sx={{ color: '#007acc' }}
                                    >
                                        <SaveIcon />
                                    </IconButton>
                                </Tooltip>
                            )}
                            {localNodes.some(n => n.selected) || localEdges.some(e => e.selected) ? (
                                <Tooltip title="Delete Selected (Delete key)">
                                    <IconButton
                                        size="small"
                                        onClick={() => {
                                            const selectedNodes = localNodes.filter(n => n.selected)
                                            const selectedEdges = localEdges.filter(e => e.selected)
                                            if (selectedNodes.length > 0) {
                                                handleNodesDelete(selectedNodes)
                                            }
                                            if (selectedEdges.length > 0) {
                                                handleEdgesDelete(selectedEdges)
                                            }
                                        }}
                                        sx={{ color: '#f44336' }}
                                    >
                                        <DeleteIcon />
                                    </IconButton>
                                </Tooltip>
                            ) : null}
                        </Box>
                    </Panel>
                )}
            </ReactFlow>
        </Box>
    )
}

export default ChainCanvas
