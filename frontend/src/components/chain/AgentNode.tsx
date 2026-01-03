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

const getNodeColor = (nodeType: string) => {
    switch (nodeType?.toLowerCase()) {
        case 'start': return { bg: '#5b9bd5', border: '#4a90e2', icon: '#fff', text: '#fff' }
        case 'end': return { bg: '#ff9563', border: '#ff8142', icon: '#fff', text: '#fff' }
        case 'agent': return { bg: '#5ec97a', border: '#4caf50', icon: '#fff', text: '#fff' }
        default: return { bg: '#ff9563', border: '#ff8142', icon: '#fff', text: '#fff' }
    }
}

const AgentNode: React.FC<NodeProps<AgentNodeData>> = ({ data, selected }) => {
    const statusColor = getStatusColor(data.status)
    const isRunning = data.status === 'running'
    const colors = getNodeColor(data.nodeType)

    return (
        <Box
            sx={{
                padding: 2.5,
                borderRadius: 3,
                border: selected ? `3px solid ${statusColor}` : 'none',
                backgroundColor: colors.bg,
                minWidth: 160,
                maxWidth: 200,
                boxShadow: selected || isRunning
                    ? `0 8px 24px ${statusColor}40, 0 0 0 3px ${statusColor}30`
                    : '0 6px 16px rgba(0,0,0,0.15)',
                transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                animation: isRunning ? 'pulse 1.5s infinite' : 'none',
                '@keyframes pulse': {
                    '0%': { transform: 'scale(1)', boxShadow: `0 6px 16px rgba(0,0,0,0.15)` },
                    '50%': { transform: 'scale(1.02)', boxShadow: `0 8px 24px ${statusColor}60` },
                    '100%': { transform: 'scale(1)', boxShadow: `0 6px 16px rgba(0,0,0,0.15)` },
                },
                '&:hover': {
                    transform: 'translateY(-2px)',
                    boxShadow: `0 10px 28px rgba(0,0,0,0.2)`,
                },
                cursor: 'pointer',
            }}
        >
            {/* Input Handle */}
            <Handle
                type="target"
                position={Position.Top}
                style={{
                    background: '#fff',
                    width: 12,
                    height: 12,
                    border: `3px solid ${colors.border}`,
                    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                }}
            />

            {/* Node Icon and Label */}
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1 }}>
                <AgentIcon sx={{ color: colors.icon, fontSize: 40, mb: 0.5 }} />
                <Typography
                    variant="subtitle1"
                    fontWeight="700"
                    sx={{
                        color: colors.text,
                        textAlign: 'center',
                        lineHeight: 1.2,
                    }}
                >
                    {data.label}
                </Typography>

                {data.agentName && (
                    <Typography
                        variant="caption"
                        sx={{
                            display: 'block',
                            color: colors.text,
                            opacity: 0.9,
                            textAlign: 'center',
                            fontSize: '0.7rem'
                        }}
                    >
                        {data.agentName}
                    </Typography>
                )}

                {data.status && (
                    <Chip
                        label={data.status}
                        size="small"
                        sx={{
                            mt: 0.5,
                            height: 20,
                            fontSize: '0.6rem',
                            bgcolor: '#ffffff40',
                            color: colors.text,
                            fontWeight: 600,
                            backdropFilter: 'blur(4px)',
                        }}
                    />
                )}
            </Box>

            {/* Output Handle */}
            <Handle
                type="source"
                position={Position.Bottom}
                style={{
                    background: '#fff',
                    width: 12,
                    height: 12,
                    border: `3px solid ${colors.border}`,
                    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                }}
            />
        </Box>
    )
}

export default memo(AgentNode)
