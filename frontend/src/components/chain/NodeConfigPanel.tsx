import React, { useState, useEffect } from 'react'
import {
    Box,
    Typography,
    TextField,
    Select,
    MenuItem,
    FormControl,
    InputLabel,
    Button,
    Divider,
    Accordion,
    AccordionSummary,
    AccordionDetails,
    IconButton,
    Chip
} from '@mui/material'
import {
    Close as CloseIcon,
    ExpandMore as ExpandMoreIcon,
    Settings as SettingsIcon
} from '@mui/icons-material'
import { Node } from 'reactflow'
import { Agent } from '../../api/agents'

interface NodeConfigPanelProps {
    node: Node | null
    agents: Agent[]
    onClose: () => void
    onSave: (nodeId: string, updates: Partial<Node>) => void
}

const NodeConfigPanel: React.FC<NodeConfigPanelProps> = ({ node, agents, onClose, onSave }) => {
    const [label, setLabel] = useState('')
    const [selectedAgentId, setSelectedAgentId] = useState<string>('')
    const [timeout, setTimeout] = useState<number>(30)
    const [retryAttempts, setRetryAttempts] = useState<number>(0)
    const [retryDelay, setRetryDelay] = useState<number>(1)
    const [description, setDescription] = useState('')

    useEffect(() => {
        if (node) {
            setLabel(node.data.label || '')
            setSelectedAgentId(node.data.agentId || '')
            setDescription(node.data.description || '')

            // Load from config
            const config = node.data.config || {}
            setTimeout(config.timeout || 30)
            setRetryAttempts(config.retryAttempts || 0)
            setRetryDelay(config.retryDelay || 1)
        }
    }, [node])

    if (!node) {
        return null
    }

    const handleSave = () => {
        const selectedAgent = agents.find(a => a.id === selectedAgentId)

        const updates: Partial<Node> = {
            data: {
                ...node.data,
                label,
                agentId: selectedAgentId,
                agentName: selectedAgent?.name || node.data.agentName,
                description,
                config: {
                    ...node.data.config,
                    timeout,
                    retryAttempts,
                    retryDelay
                }
            }
        }

        onSave(node.id, updates)
        onClose()
    }

    const handleApply = () => {
        const selectedAgent = agents.find(a => a.id === selectedAgentId)

        const updates: Partial<Node> = {
            data: {
                ...node.data,
                label,
                agentId: selectedAgentId,
                agentName: selectedAgent?.name || node.data.agentName,
                description,
                config: {
                    ...node.data.config,
                    timeout,
                    retryAttempts,
                    retryDelay
                }
            }
        }

        onSave(node.id, updates)
        // Don't close panel - allows continuing to edit
    }

    const isAgentNode = node.data.nodeType === 'agent'
    const nodeTypeLabel = node.data.nodeType || 'Unknown'

    return (
        <Box
            sx={{
                width: 350,
                height: '100%',
                borderLeft: '1px solid #e0e0e0',
                backgroundColor: '#fafafa',
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden'
            }}
        >
            {/* Header */}
            <Box
                sx={{
                    p: 2,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    borderBottom: '1px solid #e0e0e0',
                    backgroundColor: '#fff'
                }}
            >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <SettingsIcon color="primary" />
                    <Typography variant="h6" fontWeight="bold">
                        Node Configuration
                    </Typography>
                </Box>
                <IconButton size="small" onClick={onClose}>
                    <CloseIcon />
                </IconButton>
            </Box>

            {/* Content */}
            <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
                {/* General Settings */}
                <Box sx={{ mb: 3 }}>
                    <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
                        General
                    </Typography>

                    <TextField
                        label="Label"
                        fullWidth
                        size="small"
                        value={label}
                        onChange={(e) => setLabel(e.target.value)}
                        sx={{ mb: 2 }}
                    />

                    <Box sx={{ mb: 2 }}>
                        <Typography variant="caption" color="text.secondary" gutterBottom>
                            Node Type
                        </Typography>
                        <Box sx={{ mt: 0.5 }}>
                            <Chip
                                label={nodeTypeLabel}
                                size="small"
                                sx={{
                                    backgroundColor: '#e3f2fd',
                                    color: '#007acc',
                                    textTransform: 'capitalize'
                                }}
                            />
                        </Box>
                    </Box>

                    {isAgentNode && (
                        <FormControl fullWidth size="small" sx={{ mb: 2 }}>
                            <InputLabel>Agent</InputLabel>
                            <Select
                                value={selectedAgentId}
                                label="Agent"
                                onChange={(e) => setSelectedAgentId(e.target.value)}
                            >
                                <MenuItem value="">
                                    <em>Select an agent...</em>
                                </MenuItem>
                                {agents.map((agent) => (
                                    <MenuItem key={agent.id} value={agent.id}>
                                        {agent.name}
                                    </MenuItem>
                                ))}
                            </Select>
                        </FormControl>
                    )}

                    <TextField
                        label="Description (Optional)"
                        fullWidth
                        multiline
                        rows={2}
                        size="small"
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                        placeholder="Add a description for this node..."
                    />
                </Box>

                <Divider sx={{ my: 2 }} />

                {/* Advanced Settings */}
                <Accordion defaultExpanded={false} elevation={0}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                        <Typography variant="subtitle2" fontWeight="bold">
                            Advanced Settings
                        </Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                        <Box>
                            <TextField
                                label="Timeout (seconds)"
                                type="number"
                                fullWidth
                                size="small"
                                value={timeout}
                                onChange={(e) => setTimeout(Number(e.target.value))}
                                inputProps={{ min: 1, max: 300 }}
                                sx={{ mb: 2 }}
                                helperText="Maximum execution time for this node"
                            />

                            <TextField
                                label="Retry Attempts"
                                type="number"
                                fullWidth
                                size="small"
                                value={retryAttempts}
                                onChange={(e) => setRetryAttempts(Number(e.target.value))}
                                inputProps={{ min: 0, max: 5 }}
                                sx={{ mb: 2 }}
                                helperText="Number of retry attempts on failure"
                            />

                            {retryAttempts > 0 && (
                                <TextField
                                    label="Retry Delay (seconds)"
                                    type="number"
                                    fullWidth
                                    size="small"
                                    value={retryDelay}
                                    onChange={(e) => setRetryDelay(Number(e.target.value))}
                                    inputProps={{ min: 1, max: 60 }}
                                    helperText="Delay between retry attempts"
                                />
                            )}
                        </Box>
                    </AccordionDetails>
                </Accordion>
            </Box>

            {/* Footer Actions */}
            <Box
                sx={{
                    p: 2,
                    borderTop: '1px solid #e0e0e0',
                    backgroundColor: '#fff',
                    display: 'flex',
                    gap: 1,
                    justifyContent: 'flex-end'
                }}
            >
                <Button variant="outlined" onClick={onClose}>
                    Cancel
                </Button>
                <Button
                    variant="outlined"
                    onClick={handleApply}
                    disabled={isAgentNode && !selectedAgentId}
                >
                    Apply
                </Button>
                <Button
                    variant="contained"
                    onClick={handleSave}
                    disabled={isAgentNode && !selectedAgentId}
                >
                    Save & Close
                </Button>
            </Box>
        </Box>
    )
}

export default NodeConfigPanel
