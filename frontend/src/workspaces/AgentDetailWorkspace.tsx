import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
    Box, Typography, Button, Tabs, Tab, TextField,
    Paper, Grid, Chip, CircularProgress, Alert, Snackbar
} from '@mui/material'
import {
    Save as SaveIcon, ArrowBack as ArrowBackIcon,
    PlayArrow as RunIcon, Terminal as ConsoleIcon
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import Editor from '@monaco-editor/react'

import { getAgent, updateAgent, Agent } from '../api/agents'

interface TabPanelProps {
    children?: React.ReactNode;
    index: number;
    value: number;
}

function CustomTabPanel(props: TabPanelProps) {
    const { children, value, index, ...other } = props;

    return (
        <div
            role="tabpanel"
            hidden={value !== index}
            id={`agent-tabpanel-${index}`}
            aria-labelledby={`agent-tab-${index}`}
            {...other}
            style={{ height: '100%', overflow: 'auto' }}
        >
            {value === index && (
                <Box sx={{ p: 3 }}>
                    {children}
                </Box>
            )}
        </div>
    );
}

const AgentDetailWorkspace: React.FC = () => {
    const { agentId } = useParams<{ agentId: string }>()
    const navigate = useNavigate()
    const queryClient = useQueryClient()
    const [tabValue, setTabValue] = useState(0)
    const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' })

    // Form State
    const [name, setName] = useState('')
    const [description, setDescription] = useState('')
    const [systemPrompt, setSystemPrompt] = useState('')
    const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)

    // Fetch Agent
    const { data: agent, isLoading, error } = useQuery(
        ['agent', agentId],
        () => getAgent(agentId!),
        {
            enabled: !!agentId,
            onSuccess: (data) => {
                setName(data.name)
                setDescription(data.description || '')
                setSystemPrompt(data.system_prompt || '')
            }
        }
    )

    // Update Mutation
    const updateMutation = useMutation(
        (data: Partial<Agent>) => updateAgent(agentId!, data),
        {
            onSuccess: () => {
                queryClient.invalidateQueries(['agent', agentId])
                queryClient.invalidateQueries('agents')
                setSnackbar({ open: true, message: 'Agent saved successfully', severity: 'success' })
                setHasUnsavedChanges(false)
            },
            onError: (err: any) => {
                setSnackbar({ open: true, message: `Failed to save: ${err.message}`, severity: 'error' })
            }
        }
    )

    const handleSave = () => {
        updateMutation.mutate({
            name,
            description,
            system_prompt: systemPrompt,
            // config, llm_config etc to be added
        })
    }

    const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
        setTabValue(newValue)
    }

    const handleCloseSnackbar = () => setSnackbar({ ...snackbar, open: false })

    if (isLoading) return <Box sx={{ display: 'flex', justifyContent: 'center', mt: 10 }}><CircularProgress /></Box>
    if (error || !agent) return <Box sx={{ p: 3 }}><Typography color="error">Agent not found or error loading.</Typography></Box>

    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            {/* Header */}
            <Box sx={{
                p: 2,
                borderBottom: '1px solid #2d2d30',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                bgcolor: '#252526'
            }}>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Button
                        startIcon={<ArrowBackIcon />}
                        onClick={() => navigate('/agents')}
                        sx={{ mr: 2, color: '#969696' }}
                    >
                        Back
                    </Button>
                    <Typography variant="h6" sx={{ color: '#cccccc' }}>
                        {agent.name}
                    </Typography>
                    <Chip
                        label={agent.status}
                        size="small"
                        sx={{ ml: 2, bgcolor: agent.status === 'active' ? '#4ec9b0' : '#3c3c3c', color: '#fff' }}
                    />
                    {hasUnsavedChanges && <Typography variant="caption" sx={{ ml: 2, color: '#e2c08d' }}>● Unsaved changes</Typography>}
                </Box>
                <Box>
                    <Button
                        startIcon={<RunIcon />}
                        variant="outlined"
                        sx={{ mr: 1, borderColor: '#4ec9b0', color: '#4ec9b0' }}
                        onClick={() => navigate(`/monitoring?agent=${agentId}`)}
                    >
                        Test / Run
                    </Button>
                    <Button
                        startIcon={<SaveIcon />}
                        variant="contained"
                        disabled={!hasUnsavedChanges && !updateMutation.isLoading}
                        onClick={handleSave}
                    >
                        Save
                    </Button>
                </Box>
            </Box>

            {/* Tabs */}
            <Box sx={{ borderBottom: 1, borderColor: 'divider', bgcolor: '#1e1e1e' }}>
                <Tabs value={tabValue} onChange={handleTabChange} aria-label="agent tabs">
                    <Tab label="Overview" />
                    <Tab label="Prompt Engineering" />
                    <Tab label="Tools & Capabilities" />
                    <Tab label="LLM Settings" />
                </Tabs>
            </Box>

            {/* Content */}
            <Box sx={{ flex: 1, overflow: 'hidden', bgcolor: '#1e1e1e' }}>
                {/* Overview Tab */}
                <CustomTabPanel value={tabValue} index={0}>
                    <Grid container spacing={3}>
                        <Grid item xs={12} md={8}>
                            <Paper sx={{ p: 3, bgcolor: '#252526', mb: 3 }}>
                                <Typography variant="h6" sx={{ mb: 2, color: '#cccccc' }}>General Information</Typography>
                                <TextField
                                    label="Name"
                                    fullWidth
                                    value={name}
                                    onChange={(e) => { setName(e.target.value); setHasUnsavedChanges(true); }}
                                    margin="normal"
                                    variant="outlined"
                                />
                                <TextField
                                    label="Description"
                                    fullWidth
                                    multiline
                                    rows={3}
                                    value={description}
                                    onChange={(e) => { setDescription(e.target.value); setHasUnsavedChanges(true); }}
                                    margin="normal"
                                    variant="outlined"
                                />
                            </Paper>
                        </Grid>
                        <Grid item xs={12} md={4}>
                            <Paper sx={{ p: 3, bgcolor: '#252526' }}>
                                <Typography variant="h6" sx={{ mb: 2, color: '#cccccc' }}>Metadata</Typography>
                                <Typography variant="body2" sx={{ color: '#969696', mb: 1 }}>
                                    ID: {agent.id}
                                </Typography>
                                <Typography variant="body2" sx={{ color: '#969696', mb: 1 }}>
                                    Type: {agent.type}
                                </Typography>
                                <Typography variant="body2" sx={{ color: '#969696', mb: 1 }}>
                                    Version: {agent.version}
                                </Typography>
                                <Typography variant="body2" sx={{ color: '#969696' }}>
                                    Created: {new Date(agent.created_at).toLocaleDateString()}
                                </Typography>
                            </Paper>
                        </Grid>
                    </Grid>
                </CustomTabPanel>

                {/* Prompt Tab */}
                <CustomTabPanel value={tabValue} index={1}>
                    <Paper sx={{ p: 0, bgcolor: '#1e1e1e', height: '100%', border: '1px solid #3c3c3c', display: 'flex', flexDirection: 'column' }}>
                        <Box sx={{ p: 1, borderBottom: '1px solid #3c3c3c', bgcolor: '#252526' }}>
                            <Typography variant="subtitle2" sx={{ color: '#cccccc' }}>System Prompt</Typography>
                        </Box>
                        <Box sx={{ flex: 1 }}>
                            <Editor
                                height="100%"
                                defaultLanguage="markdown"
                                theme="vs-dark"
                                value={systemPrompt}
                                onChange={(value) => { setSystemPrompt(value || ''); setHasUnsavedChanges(true); }}
                                options={{
                                    minimap: { enabled: false },
                                    fontSize: 14,
                                    wordWrap: 'on',
                                    scrollBeyondLastLine: false
                                }}
                            />
                        </Box>
                    </Paper>
                </CustomTabPanel>

                <CustomTabPanel value={tabValue} index={2}>
                    <Typography sx={{ color: '#969696' }}>Tool configuration coming soon.</Typography>
                </CustomTabPanel>

                <CustomTabPanel value={tabValue} index={3}>
                    <Typography sx={{ color: '#969696' }}>LLM configuration coming soon.</Typography>
                </CustomTabPanel>
            </Box>

            <Snackbar open={snackbar.open} autoHideDuration={6000} onClose={handleCloseSnackbar}>
                <Alert onClose={handleCloseSnackbar} severity={snackbar.severity} sx={{ width: '100%' }}>
                    {snackbar.message}
                </Alert>
            </Snackbar>
        </Box>
    )
}

export default AgentDetailWorkspace
