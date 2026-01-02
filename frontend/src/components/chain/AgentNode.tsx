import React, { memo } from 'react'
import { Handle, Position, NodeProps } from 'reactflow'
import { Box, Typography, Chip } from '@mui/material'
import { SmartToy as AgentIcon } from '@mui/icons-material'

interface AgentNodeData {
    label: string
    agentId?: string
    agentName?: string
    nodeType: string
    status?: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
}

const getStatusColor = (status?: string) => {
    switch (status) {
        case 'running': return '#2196f3'
        case 'completed': return '#4caf50'
        case 'failed': return '#f44336'
        case 'skipped': return '#9e9e9e'
        default: return '#007acc'
    }
}

const AgentNode: React.FC<NodeProps<AgentNodeData>> = ({ data, selected }) => {
    const statusColor = getStatusColor(data.status)
    const isRunning = data.status === 'running'

    return (
        <Box
            sx={{
                padding: 2,
                borderRadius: 2,
                border: selected ? `2px solid ${statusColor}` : `1px solid ${data.status ? statusColor : '#ddd'}`,
                backgroundColor: '#ffffff',
                minWidth: 180,
                boxShadow: selected || isRunning
                    ? `0 4px 12px ${statusColor}40`
                    : '0 2px 8px rgba(0,0,0,0.1)',
                transition: 'all 0.2s',
                animation: isRunning ? 'pulse 1.5s infinite' : 'none',
                '@keyframes pulse': {
                    '0%': { boxShadow: `0 0 0 0 ${statusColor}40` },
                    '70%': { boxShadow: `0 0 0 10px ${statusColor}00` },
                    '100%': { boxShadow: `0 0 0 0 ${statusColor}00` },
                },
            }}
        >
            {/* Input Handle */}
            <Handle
                type="target"
                position={Position.Top}
                style={{
                    background: statusColor,
                    width: 10,
                    height: 10,
                    border: '2px solid #fff',
                }}
            />

            {/* Node Content */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <AgentIcon sx={{ color: statusColor, fontSize: 20 }} />
                <Typography variant="body2" fontWeight="bold">
                    {data.label}
                </Typography>
                {data.status && (
                    <Chip
                        label={data.status}
                        size="small"
                        sx={{
                            ml: 'auto',
                            height: 16,
                            fontSize: '0.6rem',
                            bgcolor: `${statusColor}20`,
                            color: statusColor
                        }}
                    />
                )}
            </Box>

            {data.agentName && (
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                    Agent: {data.agentName}
                </Typography>
            )}

            <Chip
                label={data.nodeType}
                size="small"
                sx={{
                    height: 20,
                    fontSize: '0.7rem',
                    backgroundColor: '#e3f2fd',
                    color: '#007acc',
                }}
            />

            {/* Output Handle */}
            <Handle
                type="source"
                position={Position.Bottom}
                style={{
                    background: statusColor,
                    width: 10,
                    height: 10,
                    border: '2px solid #fff',
                }}
            />
        </Box>
    )
}

export default memo(AgentNode)
