import React, { useState, useEffect } from 'react'
import {
    Dialog, DialogTitle, DialogContent, DialogActions, Box, Tabs, Tab, TextField, Button,
    FormControl, InputLabel, Select, MenuItem, Typography, Chip, IconButton,
    Slider, Tooltip, Divider, CircularProgress, Alert, Stack, InputAdornment,
    LinearProgress, FormControlLabel, Checkbox, List, ListItem, ListItemText,
    ListItemIcon
} from '@mui/material'
import {
    AutoAwesome as RefineIcon,
    CheckCircle as CheckCircleIcon,
    RadioButtonUnchecked as UncheckIcon,
    Close as CloseIcon,
    NavigateBefore as BackIcon,
    NavigateNext as NextIcon,
    Save as SaveIcon
} from '@mui/icons-material'
import { useMutation, useQuery } from 'react-query'
import { getModels, LLMModel } from '../../api/llmModels'
import { getRAGSources, RAGSource } from '../../api/rag'
import { MenuBook } from '@mui/icons-material'

interface TabPanelProps {
    children?: React.ReactNode
    index: number
    value: number
}

function TabPanel(props: TabPanelProps) {
    const { children, value, index, ...other } = props
    return (
        <div
            role="tabpanel"
            hidden={value !== index}
            id={`agent-tabpanel-${index}`}
            {...other}
        >
            {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
        </div>
    )
}

interface AgentWizardProps {
    open: boolean
    onClose: () => void
    onCreate: (agentData: any) => void
    isLoading?: boolean
}

const AgentCreationWizard: React.FC<AgentWizardProps> = ({
    open,
    onClose,
    onCreate,
    isLoading = false
}) => {
    const [activeTab, setActiveTab] = useState(0)
    const [refiningPrompt, setRefiningPrompt] = useState(false)

    // Form state
    const [name, setName] = useState('')
    const [description, setDescription] = useState('')
    const [type, setType] = useState('conversational')
    const [status, setStatus] = useState('active')

    // Refinement State
    const [refinementData, setRefinementData] = useState<{ refined_prompt: string, improvements: string[] } | null>(null)
    const [showRefinementReview, setShowRefinementReview] = useState(false)

    // Configuration
    const [llmModelId, setLlmModelId] = useState<string>('')
    const [temperature, setTemperature] = useState(0.7)
    const [maxTokens, setMaxTokens] = useState(1000)
    const [topP, setTopP] = useState<number | ''>('')
    const [topK, setTopK] = useState<number | ''>('')
    const [stopSequences, setStopSequences] = useState<string>('')
    const [systemPrompt, setSystemPrompt] = useState('')

    // Tools
    const [selectedTools, setSelectedTools] = useState<string[]>([])
    const [memoryEnabled, setMemoryEnabled] = useState(false)
    const [guardrailsEnabled, setGuardrailsEnabled] = useState(false)

    // Test


    // RAG Sources
    const [selectedRagSources, setSelectedRagSources] = useState<string[]>([])

    const { data: models } = useQuery('llmModels', getModels)
    const { data: ragSources } = useQuery('ragSources', getRAGSources)

    const availableTools = ['calculator', 'web_search', 'code_executor'] // TODO: Load from API

    const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
        if (canProceedToTab(newValue)) {
            setActiveTab(newValue)
        }
    }

    const canProceedToTab = (tabIndex: number): boolean => {
        if (tabIndex === 0) return true

        // Tab 1 validation (Basic Info)
        if (tabIndex > 0 && (!name || !type)) return false

        // Tab 2 validation (Configuration)
        if (tabIndex > 1 && !llmModelId) return false

        return true
    }

    const isTabComplete = (tabIndex: number): boolean => {
        switch (tabIndex) {
            case 0: return !!(name && type)
            case 1: return !!llmModelId
            case 2: return true // Tools are optional
            case 3: return true // Knowledge is optional
            default: return false
        }
    }

    const handleRefinePrompt = async () => {
        if (!systemPrompt || !llmModelId) {
            alert('Please select an LLM model and enter a system prompt first.');
            return;
        }

        setRefiningPrompt(true)
        try {
            const response = await fetch('/api/v1/agents/refine-prompt', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    original_prompt: systemPrompt,
                    agent_type: type,
                    llm_model_id: llmModelId
                })
            })

            if (!response.ok) {
                throw new Error(`Failed to refine prompt: ${response.statusText}`)
            }

            const result = await response.json()
            if (result.refined_prompt) {
                setRefinementData(result)
                setShowRefinementReview(true)
            }
        } catch (error) {
            console.error('Failed to refine prompt:', error)
            alert('Failed to refine prompt: ' + (error instanceof Error ? error.message : 'Unknown error'))
        } finally {
            setRefiningPrompt(false)
        }
    }



    const handleCreate = () => {
        const stopSeqArray = stopSequences
            ? stopSequences.split(',').map(s => s.trim()).filter(s => s)
            : undefined

        onCreate({
            name,
            description,
            type,
            status,
            llm_model_id: llmModelId,
            system_prompt: systemPrompt,
            config: {
                temperature,
                max_tokens: maxTokens,
                top_p: topP !== '' ? topP : undefined,
                top_k: topK !== '' ? topK : undefined,
                stop_sequences: stopSeqArray,
                tools: selectedTools,
                memory_enabled: memoryEnabled,
                guardrails_enabled: guardrailsEnabled
            },
            rag_sources: selectedRagSources
        })
    }

    const handleClose = () => {
        // Reset form
        setActiveTab(0)
        setName('')
        setDescription('')
        setType('conversational')
        setStatus('active')
        setLlmModelId('')
        setTemperature(0.7)
        setMaxTokens(1000)
        setTopP('')
        setTopK('')
        setStopSequences('')
        setSystemPrompt('')
        setSelectedTools([])
        setMemoryEnabled(false)
        setGuardrailsEnabled(false)
        setSelectedRagSources([])
        onClose()
    }

    const tabProgress = [0, 1, 2, 3].filter(i => isTabComplete(i)).length / 4 * 100

    return (
        <Dialog
            open={open}
            onClose={handleClose}
            maxWidth="md"
            fullWidth
            PaperProps={{
                sx: { bgcolor: '#1e1e1e', minHeight: '600px' }
            }}
        >
            <DialogTitle sx={{ bgcolor: '#252526', color: '#cccccc', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>Create New Agent</Box>
                <IconButton onClick={handleClose} sx={{ color: '#969696' }}>
                    <CloseIcon />
                </IconButton>
            </DialogTitle>

            <LinearProgress
                variant="determinate"
                value={tabProgress}
                sx={{
                    bgcolor: '#2d2d30',
                    '& .MuiLinearProgress-bar': {
                        bgcolor: '#007acc'
                    }
                }}
            />

            <Box sx={{ borderBottom: 1, borderColor: '#2d2d30' }}>
                <Tabs
                    value={activeTab}
                    onChange={handleTabChange}
                    sx={{
                        '& .MuiTab-root': {
                            color: '#969696',
                            '&.Mui-selected': {
                                color: '#007acc'
                            }
                        }
                    }}
                >
                    <Tab
                        label={
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <span>Basic Info</span>
                                {isTabComplete(0) && <CheckCircleIcon sx={{ fontSize: 16, color: '#4ec9b0' }} />}
                            </Box>
                        }
                    />
                    <Tab
                        label={
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <span>Configuration</span>
                                {isTabComplete(1) && <CheckCircleIcon sx={{ fontSize: 16, color: '#4ec9b0' }} />}
                            </Box>
                        }
                        disabled={!canProceedToTab(1)}
                    />
                    <Tab
                        label="Tools"
                        disabled={!canProceedToTab(2)}
                    />
                    <Tab
                        label="Knowledge"
                        disabled={!canProceedToTab(3)}
                    />
                </Tabs>
            </Box>

            <DialogContent sx={{ bgcolor: '#1e1e1e', minHeight: '400px' }}>
                {/* Tab 0: Basic Info*/}
                <TabPanel value={activeTab} index={0}>
                    <Stack spacing={3}>
                        <TextField
                            autoFocus
                            label="Agent Name"
                            fullWidth
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            required
                            helperText="A unique name for your agent"
                        />

                        <TextField
                            label="Description"
                            fullWidth
                            multiline
                            rows={3}
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            helperText="What does this agent do?"
                        />

                        <FormControl fullWidth>
                            <InputLabel>Agent Type</InputLabel>
                            <Select
                                value={type}
                                label="Agent Type"
                                onChange={(e) => setType(e.target.value)}
                            >
                                <MenuItem value="conversational">Conversational</MenuItem>
                                <MenuItem value="task">Task</MenuItem>
                                <MenuItem value="content_generation">Content Generation</MenuItem>
                                <MenuItem value="data_analysis">Data Analysis</MenuItem>
                                <MenuItem value="custom">Custom</MenuItem>
                            </Select>
                        </FormControl>

                        <FormControl fullWidth>
                            <InputLabel>Status</InputLabel>
                            <Select
                                value={status}
                                label="Status"
                                onChange={(e) => setStatus(e.target.value)}
                            >
                                <MenuItem value="active">Active</MenuItem>
                                <MenuItem value="inactive">Inactive</MenuItem>
                                <MenuItem value="draft">Draft</MenuItem>
                            </Select>
                        </FormControl>
                    </Stack>
                </TabPanel>

                {/* Tab 1: Configuration */}
                <TabPanel value={activeTab} index={1}>
                    <Stack spacing={3}>
                        <FormControl fullWidth required>
                            <InputLabel>LLM Model</InputLabel>
                            <Select
                                value={llmModelId}
                                label="LLM Model"
                                onChange={(e) => setLlmModelId(e.target.value)}
                            >
                                {models?.map((model: LLMModel) => (
                                    <MenuItem key={model.id} value={model.id}>
                                        {model.name} ({model.provider})
                                    </MenuItem>
                                ))}
                            </Select>
                        </FormControl>

                        <Box>
                            <Typography gutterBottom>Temperature: {temperature}</Typography>
                            <Slider
                                value={temperature}
                                onChange={(_, value) => setTemperature(value as number)}
                                min={0}
                                max={2}
                                step={0.1}
                                marks={[
                                    { value: 0, label: '0 (Focused)' },
                                    { value: 1, label: '1' },
                                    { value: 2, label: '2 (Creative)' }
                                ]}
                                sx={{ color: '#007acc' }}
                            />
                        </Box>

                        <TextField
                            label="Max Tokens"
                            type="number"
                            fullWidth
                            value={maxTokens}
                            onChange={(e) => setMaxTokens(parseInt(e.target.value) || 1000)}
                            InputProps={{ inputProps: { min: 1, max: 8000 } }}
                        />

                        <Divider sx={{ borderColor: '#2d2d30' }} />
                        <Typography variant="subtitle2" sx={{ color: '#569cd6' }}>Advanced Parameters</Typography>

                        <TextField
                            label="Top P (Nucleus Sampling)"
                            type="number"
                            fullWidth
                            value={topP}
                            onChange={(e) => setTopP(e.target.value === '' ? '' : parseFloat(e.target.value))}
                            InputProps={{ inputProps: { min: 0, max: 1, step: 0.01 } }}
                            helperText="Cumulative probability threshold (0.0-1.0)"
                        />

                        <TextField
                            label="Top K"
                            type="number"
                            fullWidth
                            value={topK}
                            onChange={(e) => setTopK(e.target.value === '' ? '' : parseInt(e.target.value))}
                            InputProps={{ inputProps: { min: 1 } }}
                            helperText="Number of top tokens to consider"
                        />

                        <TextField
                            label="Stop Sequences"
                            fullWidth
                            value={stopSequences}
                            onChange={(e) => setStopSequences(e.target.value)}
                            helperText="Comma-separated sequences to stop generation"
                            placeholder="e.g., ###, END, STOP"
                        />

                        <Divider sx={{ borderColor: '#2d2d30' }} />

                        <TextField
                            label="System Prompt"
                            fullWidth
                            multiline
                            rows={6}
                            value={systemPrompt}
                            onChange={(e) => setSystemPrompt(e.target.value)}
                            helperText="Instructions for the agent's behavior"
                            InputProps={{
                                endAdornment: (
                                    <InputAdornment position="end">
                                        <Tooltip title="Refine using AI">
                                            <IconButton
                                                onClick={handleRefinePrompt}
                                                disabled={!systemPrompt || !llmModelId || refiningPrompt}
                                                sx={{ color: '#cc99cd' }}
                                            >
                                                {refiningPrompt ? <CircularProgress size={24} /> : <RefineIcon />}
                                            </IconButton>
                                        </Tooltip>
                                    </InputAdornment>
                                )
                            }}
                        />
                    </Stack>
                </TabPanel>

                {/* Tab 2: Tools */}
                <TabPanel value={activeTab} index={2}>
                    <Stack spacing={3}>
                        <Typography variant="subtitle1" sx={{ color: '#cccccc' }}>
                            Select Tools
                        </Typography>

                        <List>
                            {availableTools.map((tool) => (
                                <ListItem
                                    key={tool}
                                    button
                                    onClick={() => {
                                        setSelectedTools(prev =>
                                            prev.includes(tool)
                                                ? prev.filter(t => t !== tool)
                                                : [...prev, tool]
                                        )
                                    }}
                                    sx={{
                                        bgcolor: '#252526',
                                        mb: 1,
                                        borderRadius: 1,
                                        border: selectedTools.includes(tool) ? '1px solid #007acc' : '1px solid #2d2d30'
                                    }}
                                >
                                    <ListItemIcon>
                                        {selectedTools.includes(tool) ? (
                                            <CheckCircleIcon sx={{ color: '#4ec9b0' }} />
                                        ) : (
                                            <UncheckIcon sx={{ color: '#969696' }} />
                                        )}
                                    </ListItemIcon>
                                    <ListItemText
                                        primary={tool}
                                        sx={{ color: '#cccccc' }}
                                    />
                                </ListItem>
                            ))}
                        </List>

                        <Divider sx={{ borderColor: '#2d2d30' }} />

                        <FormControlLabel
                            control={
                                <Checkbox
                                    checked={memoryEnabled}
                                    onChange={(e) => setMemoryEnabled(e.target.checked)}
                                    sx={{ color: '#007acc' }}
                                />
                            }
                            label="Enable Memory"
                            sx={{ color: '#cccccc' }}
                        />

                        <FormControlLabel
                            control={
                                <Checkbox
                                    checked={guardrailsEnabled}
                                    onChange={(e) => setGuardrailsEnabled(e.target.checked)}
                                    sx={{ color: '#007acc' }}
                                />
                            }
                            label="Enable Guardrails"
                            sx={{ color: '#cccccc' }}
                        />
                    </Stack>
                </TabPanel>

                {/* Tab 3: Knowledge Base */}
                <TabPanel value={activeTab} index={3}>
                    <Stack spacing={3}>
                        <Box>
                            <Typography variant="subtitle1" sx={{ color: '#cccccc', mb: 1 }}>
                                Knowledge Base Sources
                            </Typography>
                            <Typography variant="body2" sx={{ color: '#969696' }}>
                                Connect RAG sources to give your agent access to specific documents or websites.
                            </Typography>
                        </Box>

                        <List sx={{ maxHeight: 400, overflow: 'auto' }}>
                            {ragSources && ragSources.length > 0 ? (
                                ragSources.map((source: RAGSource) => (
                                    <ListItem
                                        key={source.id}
                                        button
                                        onClick={() => {
                                            setSelectedRagSources(prev =>
                                                prev.includes(source.id)
                                                    ? prev.filter(id => id !== source.id)
                                                    : [...prev, source.id]
                                            )
                                        }}
                                        sx={{
                                            bgcolor: '#252526',
                                            mb: 1,
                                            borderRadius: 1,
                                            border: selectedRagSources.includes(source.id) ? '1px solid #007acc' : '1px solid #2d2d30'
                                        }}
                                    >
                                        <ListItemIcon>
                                            {selectedRagSources.includes(source.id) ? (
                                                <CheckCircleIcon sx={{ color: '#4ec9b0' }} />
                                            ) : (
                                                <UncheckIcon sx={{ color: '#969696' }} />
                                            )}
                                        </ListItemIcon>
                                        <ListItemText
                                            primary={source.name}
                                            secondary={`${source.source_type} • ${source.status}`}
                                            primaryTypographyProps={{ color: '#cccccc' }}
                                            secondaryTypographyProps={{ color: '#969696' }}
                                        />
                                        <Chip
                                            label={source.source_type}
                                            size="small"
                                            sx={{
                                                bgcolor: 'rgba(255, 255, 255, 0.1)',
                                                color: '#ccc',
                                                height: 24
                                            }}
                                        />
                                    </ListItem>
                                ))
                            ) : (
                                <Box sx={{ p: 4, textAlign: 'center', bgcolor: '#252526', borderRadius: 1 }}>
                                    <MenuBook sx={{ fontSize: 40, color: '#555', mb: 2 }} />
                                    <Typography variant="body2" color="text.secondary">
                                        No knowledge base sources found.
                                    </Typography>
                                </Box>
                            )}
                        </List>

                        <FormControlLabel
                            control={
                                <Checkbox
                                    checked={selectedRagSources.length > 0}
                                    disabled={true}
                                    sx={{ color: '#007acc', '&.Mui-disabled': { color: selectedRagSources.length > 0 ? '#007acc' : '#555' } }}
                                />
                            }
                            label={
                                <Typography variant="body2" sx={{ color: '#969696' }}>
                                    {selectedRagSources.length} source(s) selected
                                </Typography>
                            }
                        />
                    </Stack>
                </TabPanel>


            </DialogContent>

            <Box sx={{ display: 'flex', justifyContent: 'space-between', p: 2, bgcolor: '#252526', borderTop: '1px solid #2d2d30' }}>
                <Button
                    onClick={() => setActiveTab(Math.max(0, activeTab - 1))}
                    disabled={activeTab === 0}
                    startIcon={<BackIcon />}
                    sx={{ color: '#969696' }}
                >
                    Back
                </Button>

                <Box sx={{ display: 'flex', gap: 1 }}>
                    {activeTab < 3 ? (
                        <Button
                            onClick={() => setActiveTab(activeTab + 1)}
                            disabled={!canProceedToTab(activeTab + 1)}
                            endIcon={<NextIcon />}
                            variant="contained"
                            sx={{ bgcolor: '#007acc' }}
                        >
                            Next
                        </Button>
                    ) : (
                        <Button
                            onClick={handleCreate}
                            disabled={!name || !llmModelId || isLoading}
                            startIcon={isLoading ? <CircularProgress size={20} /> : <SaveIcon />}
                            variant="contained"
                            sx={{ bgcolor: '#4ec9b0' }}
                        >
                            Create Agent
                        </Button>
                    )}
                </Box>
            </Box>

            {/* Refinement Review Dialog */}
            <Dialog
                open={showRefinementReview}
                onClose={() => setShowRefinementReview(false)}
                maxWidth="md"
                fullWidth
                PaperProps={{ sx: { bgcolor: '#1e1e1e' } }}
            >
                <DialogTitle sx={{ bgcolor: '#252526', color: '#cccccc' }}>
                    Review Refined Prompt
                </DialogTitle>
                <DialogContent sx={{ bgcolor: '#1e1e1e', pt: 3 }} dividers>
                    <Stack spacing={3}>
                        <Box>
                            <Typography variant="subtitle2" sx={{ color: '#4ec9b0', mb: 1 }}>
                                Improvements Made:
                            </Typography>
                            <List dense>
                                {refinementData?.improvements?.map((imp, i) => (
                                    <ListItem key={i}>
                                        <ListItemIcon sx={{ minWidth: 30 }}>
                                            <CheckCircleIcon sx={{ fontSize: 16, color: '#4ec9b0' }} />
                                        </ListItemIcon>
                                        <ListItemText primary={imp} sx={{ color: '#cccccc' }} />
                                    </ListItem>
                                ))}
                            </List>
                        </Box>

                        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
                            <Box>
                                <Typography variant="caption" sx={{ color: '#969696', mb: 1, display: 'block' }}>
                                    Original Prompt
                                </Typography>
                                <Box sx={{ p: 2, bgcolor: '#252526', borderRadius: 1, color: '#888', whiteSpace: 'pre-wrap', maxHeight: '300px', overflow: 'auto' }}>
                                    {systemPrompt}
                                </Box>
                            </Box>
                            <Box>
                                <Typography variant="caption" sx={{ color: '#4ec9b0', mb: 1, display: 'block' }}>
                                    Refined Prompt
                                </Typography>
                                <Box sx={{ p: 2, bgcolor: '#2d2d30', borderRadius: 1, color: '#fff', whiteSpace: 'pre-wrap', maxHeight: '300px', overflow: 'auto', border: '1px solid #007acc' }}>
                                    {refinementData?.refined_prompt}
                                </Box>
                            </Box>
                        </Box>
                    </Stack>
                </DialogContent>
                <DialogActions sx={{ bgcolor: '#252526', p: 2 }}>
                    <Button
                        onClick={() => setShowRefinementReview(false)}
                        variant="outlined"
                        sx={{ color: '#969696' }}
                    >
                        Cancel
                    </Button>
                    <Button
                        onClick={() => {
                            if (refinementData) {
                                setSystemPrompt(refinementData.refined_prompt)
                                setShowRefinementReview(false)
                            }
                        }}
                        variant="contained"
                        sx={{ bgcolor: '#007acc' }}
                        startIcon={<CheckCircleIcon />}
                    >
                        Accept Refine
                    </Button>
                </DialogActions>
            </Dialog>
        </Dialog>
    )
}

export default AgentCreationWizard
