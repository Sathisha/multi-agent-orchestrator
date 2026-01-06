import React, { memo } from 'react'
import { Handle, Position, NodeProps } from 'reactflow'
import { Box, Typography, Chip, Tooltip } from '@mui/material'
import { SmartToy as AgentIcon } from '@mui/icons-material'

interface AgentNodeData {
    label: string
    agentId?: string
    agentName?: string
    nodeType: string
    status?: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
    output?: string | object
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

    // Override background based on status
    let backgroundColor = colors.bg
    let borderColor = colors.border

    if (data.status === 'completed') {
        backgroundColor = '#4caf50'
        borderColor = '#388e3c'
    } else if (data.status === 'failed') {
        backgroundColor = '#ef5350'
        borderColor = '#d32f2f'
    } else if (data.status === 'running') {
        borderColor = '#2196f3'
    }

    const outputText = data.output
        ? (typeof data.output === 'string' ? data.output : JSON.stringify(data.output, null, 2))
        : null

    // Determine tooltip content
    const tooltipContent = outputText ? (
        <Box sx={{ p: 1, maxHeight: 400, overflow: 'auto' }}>
            <Typography variant="caption" sx={{ display: 'block', mb: 1, fontWeight: 'bold' }}>Output:</Typography>
            <Box component="pre" sx={{ m: 0, whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.75rem' }}>
                {outputText}
            </Box>
        </Box>
    ) : (data.agentName || "No output");

    return (
        <Tooltip
            title={tooltipContent}
            placement="top"
            arrow
        >
            <Box
                sx={{
                    padding: 2.5,
                    borderRadius: 3,
                    border: selected ? `3px solid ${borderColor}` : `1px solid ${borderColor}`,
                    backgroundColor: backgroundColor,
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
        </Tooltip>
    )
}

export default memo(AgentNode)
