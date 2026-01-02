import React, { memo } from 'react'
import { Handle, Position, NodeProps } from 'reactflow'
import { Box, Typography, Chip } from '@mui/material'
import { SmartToy as AgentIcon } from '@mui/icons-material'

interface AgentNodeData {
    label: string
    agentId?: string
    agentName?: string
    nodeType: string
}

const AgentNode: React.FC<NodeProps<AgentNodeData>> = ({ data, selected }) => {
    return (
        <Box
            sx={{
                padding: 2,
                borderRadius: 2,
                border: selected ? '2px solid #007acc' : '1px solid #ddd',
                backgroundColor: '#ffffff',
                minWidth: 180,
                boxShadow: selected ? '0 4px 12px rgba(0,122,204,0.3)' : '0 2px 8px rgba(0,0,0,0.1)',
                transition: 'all 0.2s',
                '&:hover': {
                    boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                },
            }}
        >
            {/* Input Handle */}
            <Handle
                type="target"
                position={Position.Top}
                style={{
                    background: '#007acc',
                    width: 10,
                    height: 10,
                    border: '2px solid #fff',
                }}
            />

            {/* Node Content */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <AgentIcon sx={{ color: '#007acc', fontSize: 20 }} />
                <Typography variant="body2" fontWeight="bold">
                    {data.label}
                </Typography>
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
                    background: '#007acc',
                    width: 10,
                    height: 10,
                    border: '2px solid #fff',
                }}
            />
        </Box>
    )
}

export default memo(AgentNode)
