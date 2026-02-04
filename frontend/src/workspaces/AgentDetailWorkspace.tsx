import React, { useState, useEffect, useRef, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
    Box, Typography, Tabs, Tab, TextField, Button, Card, CardContent,
    IconButton, Chip, Select, MenuItem, FormControl, InputLabel, Snackbar,
    Alert, CircularProgress, Paper, Divider, List, ListItem, Tooltip,
    Avatar, Fade, Zoom, Breadcrumbs, Link, Switch, FormControlLabel,
    InputAdornment, Grid, Dialog, DialogTitle, DialogContent, DialogActions,
    Checkbox, ListItemText, ListItemIcon, Stack
} from '@mui/material'
import {
    ArrowBack, Save, PlayArrow, Stop, Send, Settings as SettingsIcon,
    AutoGraph, Code, Description, Psychology, History, Extension,
    ContentCopy, Delete, Share, OpenInNew, MoreVert, InfoOutlined,
    Done, Refresh, Bolt, Build, Close, CheckBox, CheckBoxOutlineBlank, Security, Add as AddIcon, MenuBook,
    AutoAwesome as RefineIcon, CheckCircle as CheckCircleIcon
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import {
    getAgent,
    updateAgent,
    executeAgent,
    getExecutionStatus,
    UpdateAgentRequest,
    Agent
} from '../api/agents'
import { getModels, discoverOllamaModels, LLMModel, OllamaModel } from '../api/llmModels'
import { getTools, Tool } from '../api/tools'
import { getRoles } from '../api/users'
import { getAgentRoles, assignAgentRole, revokeAgentRole, AgentRoleAssignRequest } from '../api/agents'
import { getRAGSources, getAgentSources, assignSourceToAgent, removeSourceFromAgent, RAGSource } from '../api/rag'
import Editor from '@monaco-editor/react'

interface TabPanelProps {
    children?: React.ReactNode
    index: number
    value: number
}

function TabPanel(props: TabPanelProps) {
    const { children, value, index, ...other } = props
    return (
        <div role="tabpanel" hidden={value !== index} {...other} style={{ height: '100%', overflow: 'auto' }}>
            {value === index && <Box sx={{ p: 3, height: '100%' }}>{children}</Box>}
        </div>
    )
}

const AgentDetailWorkspace: React.FC = () => {
    const { agentId } = useParams<{ agentId: string }>()
    const navigate = useNavigate()
    const queryClient = useQueryClient()
    const chatEndRef = useRef<HTMLDivElement>(null)

    const [activeTab, setActiveTab] = useState(0)
    const [status, setStatus] = useState('draft')
    const [name, setName] = useState('')
    const [description, setDescription] = useState('')
    const [systemPrompt, setSystemPrompt] = useState('')
    const [model, setModel] = useState('gpt-4')
    const [temperature, setTemperature] = useState(0.7)
    const [maxTokens, setMaxTokens] = useState(2000)
    const [successCriteria, setSuccessCriteria] = useState('')
    const [failureCriteria, setFailureCriteria] = useState('')
    const [capabilities, setCapabilities] = useState({
        context_memory_enabled: true,
        knowledge_base_retrieval: true,
        internet_search_access: false,
        code_interpreter: true,
    })
    const [selectedTools, setSelectedTools] = useState<string[]>([])
    const [isToolDialogOpen, setIsToolDialogOpen] = useState(false)
    const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
    const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' })
    // Refinement State
    const [refiningPrompt, setRefiningPrompt] = useState(false)
    const [refinementData, setRefinementData] = useState<{ refined_prompt: string, improvements: string[] } | null>(null)
    const [showRefinementReview, setShowRefinementReview] = useState(false)

    // Chat state
    const [chatMessages, setChatMessages] = useState<Array<{ role: string, content: string, status?: string }>>([])
    const [chatInput, setChatInput] = useState('')
    const [isExecuting, setIsExecuting] = useState(false)
    const [currentExecutionId, setCurrentExecutionId] = useState<string | null>(null)

    // Access Control state
    const [assignRoleDialogOpen, setAssignRoleDialogOpen] = useState(false)
    const [selectedRoleToAssign, setSelectedRoleToAssign] = useState('')
    const [selectedAccessType, setSelectedAccessType] = useState('read')

    const { data: configuredModels, isLoading: isLoadingConfigured } = useQuery<LLMModel[]>('llm_models', getModels)
    const { data: ollamaModels, isLoading: isLoadingOllama } = useQuery<OllamaModel[]>('discovered_ollama_models', discoverOllamaModels, {
        retry: 1,
        refetchOnWindowFocus: false,
        staleTime: 1000 * 60 * 5 // 5 minutes
    })
    const { data: allTools } = useQuery<Tool[]>('tools', getTools)
    const { data: roles } = useQuery('roles', getRoles)
    const { data: agentRoles } = useQuery(
        ['agentRoles', agentId],
        () => getAgentRoles(agentId!),
        { enabled: !!agentId }
    )
    const { data: allRAGSources } = useQuery<RAGSource[]>('rag-sources', getRAGSources)
    const { data: assignedRAGSources, refetch: refetchAssignedSources } = useQuery<RAGSource[]>(
        ['agentRAGSources', agentId],
        () => getAgentSources(agentId!),
        { enabled: !!agentId }
    )

    const { data: agent, isLoading, isError } = useQuery(
        ['agent', agentId],
        () => getAgent(agentId!),
        {
            enabled: !!agentId,
            onSuccess: (data) => {
                setName(data.name)
                setDescription(data.description || '')
                setSystemPrompt(data.system_prompt || '')
                setStatus(data.status || 'draft')
                // Use model from config or fallback
                setModel(data.config?.model || data.config?.model_name || 'gpt-4')
                setTemperature(data.config?.temperature || 0.7)
                setMaxTokens(data.config?.max_tokens || 2000)
                setSuccessCriteria(data.config?.success_criteria || '')
                setFailureCriteria(data.config?.failure_criteria || '')
                setCapabilities(data.config?.capabilities || {
                    context_memory_enabled: true,
                    knowledge_base_retrieval: true,
                    internet_search_access: false,
                    code_interpreter: true,
                })
                setSelectedTools(data.available_tools || [])
            }
        }
    )

    const availableModels = useMemo(() => {
        const models: { value: string; label: string; provider: string; group: string }[] = [];
        const seenValues = new Set<string>();

        // Helper to add unique models
        const addModel = (value: string, label: string, provider: string, group: string) => {
            if (!seenValues.has(value)) {
                models.push({ value, label, provider, group });
                seenValues.add(value);
            }
        };

        if (configuredModels && Array.isArray(configuredModels)) {
            configuredModels.forEach(m => {
                addModel(m.name, `${m.name} (${m.provider})`, m.provider, 'Configured');
            });
        }

        if (ollamaModels && Array.isArray(ollamaModels)) {
            ollamaModels.forEach(m => {
                // Determine label based on available fields (name or model)
                const modelName = m.model || m.name;
                addModel(modelName, `${modelName} (Ollama)`, 'ollama', 'Discovered');
            });
        }

        // If currently selected model is not in the list (and we are not loading), add it nicely
        // This prevents the "empty select" issue or losing the current setting visually
        // We only do this if BOTH queries have finished, otherwise we might be premature
        if (!isLoadingConfigured && !isLoadingOllama && model && !seenValues.has(model)) {
            // Try to determine provider from existing config or default to 'ollama'
            const currentProvider = agent?.config?.llm_provider || 'ollama';
            addModel(model, `${model} (Current)`, currentProvider, 'Current Setting');
        }

        // Only if absolutely nothing found and not loading, show fallback
        if (models.length === 0 && !isLoadingConfigured && !isLoadingOllama) {
            addModel('gpt-4', 'GPT-4 (Default/Fallback)', 'openai', 'Default');
        }

        return models;
    }, [configuredModels, ollamaModels, model, agent, isLoadingConfigured, isLoadingOllama]);

    const updateMutation = useMutation(
        (data: Partial<UpdateAgentRequest>) => updateAgent(agentId!, data),
        {
            onSuccess: () => {
                queryClient.invalidateQueries(['agent', agentId])
                queryClient.invalidateQueries('agents')
                setHasUnsavedChanges(false)
                setSnackbar({ open: true, message: 'Agent updated successfully', severity: 'success' })
            },
            onError: (error: any) => {
                setSnackbar({ open: true, message: `Failed to update agent: ${error.message || 'Unknown error'}`, severity: 'error' })
            }
        }
    )

    const handleSave = () => {
        // Find provider for selected model
        let selectedProvider = 'ollama';
        let selectedModelName = model;

        const foundModel = availableModels.find(m => m.value === model);
        if (foundModel) {
            selectedProvider = foundModel.provider;
        } else {
            // Fallback to existing config if model name didn't change or not in list
            selectedProvider = agent?.config?.llm_provider || 'ollama';
        }

        updateMutation.mutate({
            name,
            description,
            status,
            system_prompt: systemPrompt,
            config: {
                ...agent?.config,
                model: selectedModelName,     // Frontend state often uses 'model'
                model_name: selectedModelName, // Backend executor uses 'model_name'
                llm_provider: selectedProvider,
                temperature,
                max_tokens: maxTokens,
                capabilities,
                available_tools: selectedTools,
                success_criteria: successCriteria,
                failure_criteria: failureCriteria
            },
            available_tools: selectedTools
        })
    }

    const handleRefinePrompt = async () => {
        if (!systemPrompt || !model) {
            alert('Please select an LLM model and enter a system prompt first.');
            return;
        }

        setRefiningPrompt(true)
        try {
            // Determine provider
            let selectedProvider = 'ollama'; // Default
            const foundModel = availableModels.find(m => m.value === model);
            if (foundModel) {
                selectedProvider = foundModel.provider;
            } else {
                selectedProvider = agent?.config?.llm_provider || 'ollama';
            }

            // Find full model ID if possible (especially for configured models which might need ID)
            // For now, passing model name as ID often works or backend handles it.
            // Ideally we pass the ID from the LLMModel object if we have it.
            let llmModelId = model;
            const configModel = configuredModels?.find(m => m.name === model);
            if (configModel) llmModelId = configModel.id;


            const response = await fetch('/api/v1/agents/refine-prompt', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    original_prompt: systemPrompt,
                    agent_type: agent?.type || 'conversational',
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

    const scrollToBottom = () => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }

    // Reset chat when switching agents
    useEffect(() => {
        setChatMessages([])
        setChatInput('')
        setIsExecuting(false)
        setCurrentExecutionId(null)
    }, [agentId])



    useEffect(() => {
        scrollToBottom()
    }, [chatMessages])

    // Polling for execution status
    useEffect(() => {
        let pollInterval: NodeJS.Timeout | null = null;

        if (currentExecutionId && isExecuting) {
            pollInterval = setInterval(async () => {
                try {
                    const status = await getExecutionStatus(currentExecutionId);
                    if (status.status === 'completed') {
                        const output = status.output_data?.content || 'Execution completed with no output.';
                        setChatMessages(prev => {
                            const newMessages = [...prev];
                            const lastMsg = newMessages[newMessages.length - 1];
                            if (lastMsg && lastMsg.role === 'assistant' && lastMsg.status === 'thinking') {
                                lastMsg.content = output;
                                lastMsg.status = undefined;
                            }
                            return newMessages;
                        });
                        setIsExecuting(false);
                        setCurrentExecutionId(null);
                        if (pollInterval) clearInterval(pollInterval);
                    } else if (status.status === 'failed') {
                        setChatMessages(prev => {
                            const newMessages = [...prev];
                            const lastMsg = newMessages[newMessages.length - 1];
                            if (lastMsg && lastMsg.role === 'assistant' && lastMsg.status === 'thinking') {
                                lastMsg.content = `Execution failed: ${status.error_message || 'Unknown error'}`;
                                lastMsg.status = 'error';
                            }
                            return newMessages;
                        });
                        setIsExecuting(false);
                        setCurrentExecutionId(null);
                        if (pollInterval) clearInterval(pollInterval);
                    }
                } catch (error) {
                    console.error('Polling error:', error);
                }
            }, 3000);
        }

        return () => {
            if (pollInterval) clearInterval(pollInterval);
        };
    }, [currentExecutionId, isExecuting]);

    const handleSendMessage = async () => {
        if (!chatInput.trim() || isExecuting) return

        const userMsgContent = chatInput.trim();
        const userMessage = { role: 'user', content: userMsgContent }
        setChatMessages(prev => [...prev, userMessage])
        setChatInput('')
        setIsExecuting(true)

        // Add placeholders for assistant
        setChatMessages(prev => [...prev, { role: 'assistant', content: '', status: 'thinking' }])

        try {
            const response = await executeAgent(agentId!, {
                input_data: { message: userMsgContent },
                session_id: `test-session-${agentId}`
            })
            setCurrentExecutionId(response.execution_id)
        } catch (error: any) {
            setChatMessages(prev => {
                const newMessages = [...prev];
                const lastMsg = newMessages[newMessages.length - 1];
                if (lastMsg && lastMsg.role === 'assistant' && lastMsg.status === 'thinking') {
                    lastMsg.content = `Error starting execution: ${error.message || 'Unknown error'}`;
                    lastMsg.status = 'error';
                }
                return newMessages;
            });
            setIsExecuting(false);
        }
    }

    const assignRoleMutation = useMutation(
        (data: AgentRoleAssignRequest) => assignAgentRole(agentId!, data),
        {
            onSuccess: () => {
                queryClient.invalidateQueries(['agentRoles', agentId])
                setAssignRoleDialogOpen(false)
                setSnackbar({ open: true, message: 'Role assigned successfully', severity: 'success' })
            },
            onError: (error: any) => {
                setSnackbar({ open: true, message: `Failed to assign role: ${error.message || 'Unknown error'}`, severity: 'error' })
            }
        }
    )

    const revokeRoleMutation = useMutation(
        (roleId: string) => revokeAgentRole(agentId!, roleId),
        {
            onSuccess: () => {
                queryClient.invalidateQueries(['agentRoles', agentId])
                setSnackbar({ open: true, message: 'Role revoked successfully', severity: 'success' })
            },
            onError: (error: any) => {
                setSnackbar({ open: true, message: `Failed to revoke role: ${error.message || 'Unknown error'}`, severity: 'error' })
            }
        }
    )

    const handleAssignRole = () => {
        if (!selectedRoleToAssign) return
        assignRoleMutation.mutate({
            role_id: selectedRoleToAssign,
            access_type: selectedAccessType
        })
    }

    // RAG Source Assignment Mutations
    const assignRAGSourceMutation = useMutation(
        (sourceId: string) => assignSourceToAgent(agentId!, sourceId),
        {
            onSuccess: () => {
                refetchAssignedSources()
                setSnackbar({ open: true, message: 'Source assigned successfully', severity: 'success' })
            },
            onError: (error: any) => {
                setSnackbar({ open: true, message: `Failed to assign source: ${error.message || 'Unknown error'}`, severity: 'error' })
            }
        }
    )

    const removeRAGSourceMutation = useMutation(
        (sourceId: string) => removeSourceFromAgent(agentId!, sourceId),
        {
            onSuccess: () => {
                refetchAssignedSources()
                setSnackbar({ open: true, message: 'Source removed successfully', severity: 'success' })
            },
            onError: (error: any) => {
                setSnackbar({ open: true, message: `Failed to remove source: ${error.message || 'Unknown error'}`, severity: 'error' })
            }
        }
    )

    const handleToggleRAGSource = (sourceId: string) => {
        const isAssigned = assignedRAGSources?.some(s => s.id === sourceId)
        if (isAssigned) {
            removeRAGSourceMutation.mutate(sourceId)
        } else {
            assignRAGSourceMutation.mutate(sourceId)
        }
    }

    const getAgentIcon = (type: string) => {
        switch (type?.toUpperCase()) {
            case 'CONVERSATIONAL': return <Psychology sx={{ fontSize: 32 }} />;
            case 'TASK': return <Bolt sx={{ fontSize: 32 }} />;
            case 'ASSISTANT': return <Psychology sx={{ fontSize: 32 }} />;
            default: return <Psychology sx={{ fontSize: 32 }} />;
        }
    }

    if (isLoading) {
        return (
            <Box sx={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', height: '100%', gap: 2 }}>
                <CircularProgress size={40} thickness={4} sx={{ color: '#007acc' }} />
                <Typography variant="body2" sx={{ color: '#969696', fontWeight: 500 }}>
                    Loading agent details...
                </Typography>
            </Box>
        )
    }

    if (isError || !agent) {
        return (
            <Box sx={{ p: 4, textAlign: 'center' }}>
                <Typography color="error" variant="h6">Agent not found or failed to load</Typography>
                <Button variant="outlined" sx={{ mt: 2 }} onClick={() => navigate('/agents')}>
                    Return to Explorer
                </Button>
            </Box>
        )
    }

    return (
        <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden', bgcolor: '#1e1e1e' }}>
            {/* Glassmorphism Header */}
            <Box sx={{
                p: 2,
                borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                bgcolor: 'rgba(30, 30, 30, 0.95)',
                backdropFilter: 'blur(10px)',
                zIndex: 10
            }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <IconButton
                        onClick={() => navigate('/agents')}
                        size="medium"
                        sx={{
                            color: '#cccccc',
                            '&:hover': { bgcolor: 'rgba(255, 255, 255, 0.05)', transform: 'translateX(-2px)' },
                            transition: 'all 0.2s'
                        }}
                    >
                        <ArrowBack />
                    </IconButton>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <Avatar sx={{ bgcolor: agent.status === 'active' ? 'rgba(76, 175, 80, 0.1)' : 'rgba(150, 150, 150, 0.1)', color: agent.status === 'active' ? '#4caf50' : '#969696', borderRadius: '8px', width: 44, height: 44 }}>
                            {getAgentIcon(agent.type)}
                        </Avatar>
                        <Box>
                            <Breadcrumbs aria-label="breadcrumb" sx={{ '& .MuiBreadcrumbs-separator': { color: '#555' } }}>
                                <Link underline="hover" color="inherit" onClick={() => navigate('/agents')} sx={{ cursor: 'pointer', fontSize: '0.8rem', color: '#888' }}>
                                    Agents
                                </Link>
                                <Typography color="text.primary" sx={{ fontSize: '0.8rem', color: '#bbb' }}>{agent.name}</Typography>
                            </Breadcrumbs>
                            <Typography variant="h6" sx={{ color: '#e1e1e1', fontWeight: 600, lineHeight: 1.2 }}>
                                {name}
                            </Typography>
                        </Box>
                    </Box>
                </Box>

                <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                    {hasUnsavedChanges && (
                        <Fade in={hasUnsavedChanges}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                <InfoOutlined sx={{ fontSize: 14, color: '#e2c08d' }} />
                                <Typography variant="caption" sx={{ color: '#e2c08d', fontWeight: 500 }}>
                                    Unsaved changes
                                </Typography>
                            </Box>
                        </Fade>
                    )}
                    <Button
                        variant="contained"
                        startIcon={updateMutation.isLoading ? <CircularProgress size={16} color="inherit" /> : <Save />}
                        onClick={handleSave}
                        disabled={!hasUnsavedChanges || updateMutation.isLoading}
                        sx={{
                            backgroundColor: '#007acc',
                            '&:hover': { backgroundColor: '#0062a3' },
                            textTransform: 'none',
                            fontWeight: 600,
                            px: 3,
                            borderRadius: '6px',
                            boxShadow: '0 4px 14px 0 rgba(0, 122, 204, 0.2)'
                        }}
                    >
                        {updateMutation.isLoading ? 'Saving...' : 'Save Agent'}
                    </Button>
                    <IconButton size="small" sx={{ color: '#888' }}>
                        <MoreVert />
                    </IconButton>
                </Box>
            </Box>

            {/* Custom Styled Tabs */}
            <Box sx={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)', bgcolor: 'rgba(37, 37, 38, 0.5)' }}>
                <Tabs
                    value={activeTab}
                    onChange={(_, v) => setActiveTab(v)}
                    sx={{
                        minHeight: 48,
                        '& .MuiTab-root': {
                            color: '#969696',
                            textTransform: 'none',
                            fontWeight: 500,
                            fontSize: '0.875rem',
                            minHeight: 48,
                            px: 3,
                            '&.Mui-selected': { color: '#007acc' }
                        },
                        '& .MuiTabs-indicator': {
                            backgroundColor: '#007acc',
                            height: 3,
                            borderRadius: '3px 3px 0 0'
                        }
                    }}
                >
                    <Tab icon={<Description sx={{ fontSize: 18 }} />} iconPosition="start" label="Overview" />
                    <Tab icon={<AutoGraph sx={{ fontSize: 18 }} />} iconPosition="start" label="Prompt Engineering" />
                    <Tab icon={<Bolt sx={{ fontSize: 18 }} />} iconPosition="start" label="Chat & Test" />
                    <Tab icon={<SettingsIcon sx={{ fontSize: 18 }} />} iconPosition="start" label="Configuration" />
                    <Tab icon={<Security sx={{ fontSize: 18 }} />} iconPosition="start" label="Access Control" />
                    <Tab icon={<MenuBook sx={{ fontSize: 18 }} />} iconPosition="start" label="Knowledge Base" />
                </Tabs>
            </Box>

            {/* Main Content Area */}
            <Box sx={{ flex: 1, overflow: 'hidden' }}>
                <TabPanel value={activeTab} index={0}>
                    <Grid container spacing={3}>
                        <Grid item xs={12} md={7}>
                            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                                <Box>
                                    <Typography component="span" sx={{ fontSize: '0.75rem', color: '#888', fontWeight: 600, textTransform: 'uppercase', mb: 1, display: 'block' }}>
                                        Agent Identity
                                    </Typography>
                                    <TextField
                                        fullWidth
                                        variant="outlined"
                                        placeholder="Agent name"
                                        value={name}
                                        onChange={(e) => { setName(e.target.value); setHasUnsavedChanges(true) }}
                                        sx={{
                                            '& .MuiOutlinedInput-root': {
                                                bgcolor: 'rgba(255, 255, 255, 0.02)',
                                                '&:hover fieldset': { borderColor: 'rgba(255, 255, 255, 0.1)' }
                                            }
                                        }}
                                    />
                                </Box>
                                <Box>
                                    <Typography component="span" sx={{ fontSize: '0.75rem', color: '#888', fontWeight: 600, textTransform: 'uppercase', mb: 1, display: 'block' }}>
                                        Status
                                    </Typography>
                                    <Select
                                        fullWidth
                                        value={status}
                                        onChange={(e) => { setStatus(e.target.value); setHasUnsavedChanges(true) }}
                                        sx={{
                                            bgcolor: 'rgba(255, 255, 255, 0.02)',
                                            '&:hover': { bgcolor: 'rgba(255, 255, 255, 0.05)' },
                                            '.MuiSelect-select': { display: 'flex', gap: 1, alignItems: 'center' }
                                        }}
                                    >
                                        <MenuItem value="draft">
                                            <Chip label="DRAFT" size="small" sx={{ bgcolor: 'rgba(150, 150, 150, 0.2)', color: '#bbb' }} />
                                            <Typography variant="body2" sx={{ ml: 1 }}>Draft - Not ready for general use</Typography>
                                        </MenuItem>
                                        <MenuItem value="active">
                                            <Chip label="ACTIVE" size="small" sx={{ bgcolor: 'rgba(76, 175, 80, 0.2)', color: '#66bb6a' }} />
                                            <Typography variant="body2" sx={{ ml: 1 }}>Active - Available for execution</Typography>
                                        </MenuItem>
                                        <MenuItem value="inactive">
                                            <Chip label="INACTIVE" size="small" sx={{ bgcolor: 'rgba(244, 67, 54, 0.2)', color: '#ef5350' }} />
                                            <Typography variant="body2" sx={{ ml: 1 }}>Inactive - Temporarily disabled</Typography>
                                        </MenuItem>
                                    </Select>
                                </Box>
                                <Box>
                                    <Typography component="span" sx={{ fontSize: '0.75rem', color: '#888', fontWeight: 600, textTransform: 'uppercase', mb: 1, display: 'block' }}>
                                        Description & Purpose
                                    </Typography>
                                    <TextField
                                        fullWidth
                                        multiline
                                        rows={4}
                                        placeholder="Describe what this agent does..."
                                        value={description}
                                        onChange={(e) => { setDescription(e.target.value); setHasUnsavedChanges(true) }}
                                        sx={{
                                            '& .MuiOutlinedInput-root': {
                                                bgcolor: 'rgba(255, 255, 255, 0.02)',
                                                '&:hover fieldset': { borderColor: 'rgba(255, 255, 255, 0.1)' }
                                            }
                                        }}
                                    />
                                </Box>

                                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 1 }}>
                                    <Chip label={`Type: ${agent.type}`} size="small" variant="outlined" sx={{ color: '#888' }} />
                                    <Chip label={`Version: ${agent.version || '1.0'}`} size="small" variant="outlined" sx={{ color: '#888' }} />
                                </Box>
                            </Box>
                        </Grid>

                        <Grid item xs={12} md={5}>
                            <Card sx={{ bgcolor: 'rgba(255, 255, 255, 0.02)', border: '1px solid rgba(255, 255, 255, 0.05)', borderRadius: '12px' }}>
                                <CardContent sx={{ p: 3 }}>
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
                                        <History sx={{ color: '#007acc' }} />
                                        <Typography variant="h6" sx={{ fontSize: '1rem', fontWeight: 600 }}>Performance</Typography>
                                    </Box>

                                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                            <Typography variant="body2" sx={{ color: '#969696' }}>Total Executions</Typography>
                                            <Typography variant="h5" sx={{ fontWeight: 700 }}>{agent.execution_count}</Typography>
                                        </Box>
                                        <Divider sx={{ borderColor: 'rgba(255, 255, 255, 0.05)' }} />
                                        {/* TODO: Implement avg response time */}
                                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                            <Typography variant="body2" sx={{ color: '#969696' }}>Avg. Response Time</Typography>
                                            <Typography variant="h5" sx={{ fontWeight: 700, color: '#4caf50' }}>1.2s</Typography>
                                        </Box>
                                        <Divider sx={{ borderColor: 'rgba(255, 255, 255, 0.05)' }} />
                                        {/* TODO: Implement success rate */}
                                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                            <Typography variant="body2" sx={{ color: '#969696' }}>Success Rate</Typography>
                                            <Typography variant="h5" sx={{ fontWeight: 700, color: '#007acc' }}>98%</Typography>
                                        </Box>
                                    </Box>
                                    <Button
                                        fullWidth
                                        variant="outlined"
                                        sx={{ mt: 4, textTransform: 'none', border: '1px solid rgba(255, 255, 255, 0.1)', color: '#bbb' }}
                                        startIcon={<History />}
                                    >
                                        View Full History
                                    </Button>
                                </CardContent>
                            </Card>
                        </Grid>
                    </Grid>
                </TabPanel>

                <TabPanel value={activeTab} index={1}>
                    <Box sx={{ height: 'calc(100vh - 240px)', display: 'flex', flexDirection: 'column' }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <Typography variant="subtitle2" sx={{ fontWeight: 600, color: '#007acc' }}>
                                    SYSTEM PROMPT
                                </Typography>
                                <Tooltip title="The system prompt defines the core behavior and persona of the agent.">
                                    <InfoOutlined sx={{ fontSize: 16, color: '#666' }} />
                                </Tooltip>
                            </Box>
                            <Box sx={{ display: 'flex', gap: 1 }}>
                                <Button size="small" variant="text" startIcon={refiningPrompt ? <CircularProgress size={16} /> : <RefineIcon />} sx={{ color: '#007acc', textTransform: 'none' }} onClick={handleRefinePrompt} disabled={refiningPrompt}>
                                    {refiningPrompt ? 'Refining...' : 'Refine'}
                                </Button>
                                <Button size="small" variant="text" startIcon={<ContentCopy />} sx={{ color: '#888', textTransform: 'none' }} onClick={() => {
                                    navigator.clipboard.writeText(systemPrompt)
                                    setSnackbar({ open: true, message: 'Copied to clipboard', severity: 'success' })
                                }}>Copy</Button>
                                <Button size="small" variant="text" startIcon={<Refresh />} sx={{ color: '#888', textTransform: 'none' }} onClick={() => {
                                    setSystemPrompt(agent.system_prompt || '')
                                    setSnackbar({ open: true, message: 'Reverted to original prompt', severity: 'success' })
                                }}>Revert</Button>
                            </Box>
                        </Box>
                        <Box sx={{
                            flex: 1,
                            border: '1px solid rgba(255, 255, 255, 0.05)',
                            borderRadius: '8px',
                            overflow: 'hidden',
                            boxShadow: 'inset 0 2px 10px rgba(0,0,0,0.2)'
                        }}>
                            <Editor
                                height="100%"
                                defaultLanguage="markdown"
                                value={systemPrompt}
                                onChange={(value) => { setSystemPrompt(value || ''); setHasUnsavedChanges(true) }}
                                theme="vs-dark"
                                options={{
                                    minimap: { enabled: false },
                                    fontSize: 14,
                                    lineNumbers: 'on',
                                    wordWrap: 'on',
                                    padding: { top: 16, bottom: 16 },
                                    scrollBeyondLastLine: false,
                                    automaticLayout: true,
                                }}
                            />
                        </Box>

                        <Grid container spacing={2} sx={{ mb: 2, mt: 2 }}>
                            <Grid item xs={12} md={6}>
                                <Typography variant="subtitle2" sx={{ fontWeight: 600, color: '#4caf50', mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
                                    <Done sx={{ fontSize: 16 }} /> SUCCESS CRITERIA
                                </Typography>
                                <TextField
                                    fullWidth
                                    multiline
                                    rows={3}
                                    placeholder="Define what constitutes a successful execution (e.g., 'Correctly extracted the Order ID')"
                                    value={successCriteria}
                                    onChange={(e) => { setSuccessCriteria(e.target.value); setHasUnsavedChanges(true) }}
                                    sx={{
                                        '& .MuiOutlinedInput-root': {
                                            bgcolor: 'rgba(255, 255, 255, 0.02)',
                                            fontSize: '0.875rem'
                                        }
                                    }}
                                />
                            </Grid>
                            <Grid item xs={12} md={6}>
                                <Typography variant="subtitle2" sx={{ fontWeight: 600, color: '#f44336', mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
                                    <Close sx={{ fontSize: 16 }} /> FAILURE CRITERIA
                                </Typography>
                                <TextField
                                    fullWidth
                                    multiline
                                    rows={3}
                                    placeholder="Define what constitutes a failed execution (e.g., 'Could not find the document')"
                                    value={failureCriteria}
                                    onChange={(e) => { setFailureCriteria(e.target.value); setHasUnsavedChanges(true) }}
                                    sx={{
                                        '& .MuiOutlinedInput-root': {
                                            bgcolor: 'rgba(255, 255, 255, 0.02)',
                                            fontSize: '0.875rem'
                                        }
                                    }}
                                />
                            </Grid>
                        </Grid>
                    </Box>
                </TabPanel>

                <TabPanel value={activeTab} index={2}>
                    <Box sx={{ height: 'calc(100vh - 240px)', display: 'flex', flexDirection: 'column', maxWidth: '1000px', mx: 'auto' }}>
                        <Paper sx={{
                            flex: 1,
                            overflow: 'auto',
                            bgcolor: 'rgba(0,0,0,0.1)',
                            p: 3,
                            mb: 2,
                            borderRadius: '12px',
                            border: '1px solid rgba(255, 255, 255, 0.03)',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: 2
                        }}>
                            {chatMessages.length === 0 ? (
                                <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', opacity: 0.5 }}>
                                    <Avatar sx={{ width: 64, height: 64, bgcolor: 'rgba(0,122,204,0.1)', color: '#007acc', mb: 2 }}>
                                        <Bolt sx={{ fontSize: 32 }} />
                                    </Avatar>
                                    <Typography variant="h6">Interactive Playground</Typography>
                                    <Typography variant="body2" sx={{ maxWidth: 300, textAlign: 'center' }}>
                                        Start a conversation to test how this agent responds to specific prompts.
                                    </Typography>
                                </Box>
                            ) : (
                                chatMessages.map((msg, idx) => (
                                    <Box key={idx} sx={{
                                        display: 'flex',
                                        flexDirection: 'column',
                                        alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start'
                                    }}>
                                        <Box sx={{
                                            display: 'flex',
                                            gap: 1.5,
                                            flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
                                            maxWidth: '85%'
                                        }}>
                                            <Avatar
                                                sx={{
                                                    width: 32,
                                                    height: 32,
                                                    fontSize: '0.8rem',
                                                    bgcolor: msg.role === 'user' ? '#007acc' : 'rgba(255, 255, 255, 0.1)',
                                                    color: '#fff'
                                                }}
                                            >
                                                {msg.role === 'user' ? 'U' : agent.name[0]}
                                            </Avatar>
                                            <Box sx={{
                                                p: 2,
                                                borderRadius: msg.role === 'user' ? '18px 4px 18px 18px' : '4px 18px 18px 18px',
                                                bgcolor: msg.role === 'user' ? '#007acc' : 'rgba(255, 255, 255, 0.05)',
                                                border: msg.role === 'assistant' ? '1px solid rgba(255, 255, 255, 0.05)' : 'none',
                                                color: '#e1e1e1',
                                                boxShadow: msg.role === 'user' ? '0 2px 10px rgba(0, 122, 204, 0.2)' : 'none'
                                            }}>
                                                {msg.status === 'thinking' ? (
                                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                                                        <CircularProgress size={12} thickness={5} sx={{ color: '#bbb' }} />
                                                        <Typography variant="body2" sx={{ color: '#969696', fontStyle: 'italic' }}>Thinking...</Typography>
                                                    </Box>
                                                ) : (
                                                    <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{msg.content}</Typography>
                                                )}
                                                {msg.status === 'error' && (
                                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 1, color: '#f44336' }}>
                                                        <InfoOutlined sx={{ fontSize: 14 }} />
                                                        <Typography variant="caption">System Error</Typography>
                                                    </Box>
                                                )}
                                            </Box>
                                        </Box>
                                        <Typography variant="caption" sx={{ color: '#555', mt: 0.5, mx: 6 }}>
                                            {msg.role === 'user' ? 'You' : agent.name}
                                        </Typography>
                                    </Box>
                                ))
                            )}
                            <div ref={chatEndRef} />
                        </Paper>

                        <Box sx={{ pb: 2 }}>
                            <TextField
                                fullWidth
                                placeholder="Send a message to test your agent..."
                                value={chatInput}
                                onChange={(e) => setChatInput(e.target.value)}
                                onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && handleSendMessage()}
                                disabled={isExecuting}
                                InputProps={{
                                    endAdornment: (
                                        <InputAdornment position="end">
                                            <IconButton
                                                onClick={handleSendMessage}
                                                disabled={!chatInput.trim() || isExecuting}
                                                sx={{
                                                    color: '#007acc',
                                                    '&.Mui-disabled': { color: '#444' }
                                                }}
                                            >
                                                {isExecuting ? <CircularProgress size={20} /> : <Send />}
                                            </IconButton>
                                        </InputAdornment>
                                    ),
                                    sx: {
                                        borderRadius: '12px',
                                        bgcolor: 'rgba(255, 255, 255, 0.05)',
                                        '& fieldset': { borderColor: 'rgba(255, 255, 255, 0.1)' },
                                        '&:hover fieldset': { borderColor: 'rgba(255, 255, 255, 0.2)' },
                                        '&.Mui-focused fieldset': { borderColor: '#007acc' }
                                    }
                                }}
                            />
                            <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, mt: 1.5 }}>
                                <Typography variant="caption" sx={{ color: '#666' }}>Press Enter to send, Shift+Enter for new line</Typography>
                            </Box>
                        </Box>
                    </Box>
                </TabPanel>

                <TabPanel value={activeTab} index={3}>
                    <Grid container spacing={4}>
                        <Grid item xs={12} md={6}>
                            <Typography variant="h6" sx={{ fontSize: '1rem', fontWeight: 600, mb: 3 }}>LLM Parameters</Typography>

                            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                                <FormControl fullWidth>
                                    <InputLabel>Model Engine</InputLabel>
                                    <Select
                                        value={model}
                                        label="Model Engine"
                                        onChange={(e) => { setModel(e.target.value); setHasUnsavedChanges(true) }}
                                        sx={{ borderRadius: '8px' }}
                                    >
                                        {availableModels.map((m) => (
                                            <MenuItem key={`${m.provider}-${m.value}`} value={m.value}>
                                                {m.label}
                                            </MenuItem>
                                        ))}
                                    </Select>
                                </FormControl>

                                <Box>
                                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                                        <Typography variant="body2" sx={{ fontWeight: 500 }}>Temperature</Typography>
                                        <Typography variant="body2" sx={{ color: '#007acc', fontWeight: 700 }}>{temperature}</Typography>
                                    </Box>
                                    <TextField
                                        fullWidth
                                        type="number"
                                        value={temperature}
                                        onChange={(e) => { setTemperature(parseFloat(e.target.value)); setHasUnsavedChanges(true) }}
                                        inputProps={{ min: 0, max: 1.5, step: 0.1 }}
                                        helperText="Higher values make output more random, lower values more deterministic."
                                    />
                                </Box>

                                <Box>
                                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                                        <Typography variant="body2" sx={{ fontWeight: 500 }}>Max Tokens</Typography>
                                        <Typography variant="body2" sx={{ color: '#007acc', fontWeight: 700 }}>{maxTokens}</Typography>
                                    </Box>
                                    <TextField
                                        fullWidth
                                        type="number"
                                        value={maxTokens}
                                        onChange={(e) => { setMaxTokens(parseInt(e.target.value)); setHasUnsavedChanges(true) }}
                                        inputProps={{ min: 100, max: 128000, step: 100 }}
                                        helperText="The maximum number of tokens to generate in the response."
                                    />
                                </Box>
                            </Box>
                        </Grid>

                        <Grid item xs={12} md={6}>
                            <Typography variant="h6" sx={{ fontSize: '1rem', fontWeight: 600, mb: 3 }}>Capabilities</Typography>

                            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                                <FormControlLabel
                                    control={<Switch checked={capabilities.context_memory_enabled} onChange={(e) => { setCapabilities({ ...capabilities, context_memory_enabled: e.target.checked }); setHasUnsavedChanges(true) }} sx={{ '& .MuiSwitch-switchBase.Mui-checked': { color: '#007acc' } }} />}
                                    label={<Typography variant="body2">Context Memory Enabled</Typography>}
                                />
                                <FormControlLabel
                                    control={<Switch checked={capabilities.knowledge_base_retrieval} onChange={(e) => { setCapabilities({ ...capabilities, knowledge_base_retrieval: e.target.checked }); setHasUnsavedChanges(true) }} />}
                                    label={<Typography variant="body2">Knowledge Base Retrieval (RAG)</Typography>}
                                />
                                <FormControlLabel
                                    control={<Switch checked={capabilities.internet_search_access} onChange={(e) => { setCapabilities({ ...capabilities, internet_search_access: e.target.checked }); setHasUnsavedChanges(true) }} />}
                                    label={<Typography variant="body2">Internet Search Access</Typography>}
                                />
                                <FormControlLabel
                                    control={<Switch checked={capabilities.code_interpreter} onChange={(e) => { setCapabilities({ ...capabilities, code_interpreter: e.target.checked }); setHasUnsavedChanges(true) }} />}
                                    label={<Typography variant="body2">Code Interpreter</Typography>}
                                />
                            </Box>

                            <Typography variant="h6" sx={{ fontSize: '1rem', fontWeight: 600, mb: 3, mt: 5 }}>Connected Tools</Typography>

                            <Typography variant="h6" sx={{ fontSize: '1rem', fontWeight: 600, mb: 3, mt: 5 }}>Connected Tools</Typography>

                            {selectedTools.length === 0 ? (
                                <Box sx={{ p: 2, borderRadius: '8px', border: '1px dashed rgba(255, 255, 255, 0.1)', textAlign: 'center' }}>
                                    <Typography variant="body2" sx={{ color: '#666', mb: 1.5 }}>No custom tools connected to this agent.</Typography>
                                    <Button variant="text" size="small" startIcon={<Bolt />} sx={{ textTransform: 'none', color: '#007acc' }} onClick={() => setIsToolDialogOpen(true)}>Add Tool</Button>
                                </Box>
                            ) : (
                                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                                    {selectedTools.map(toolId => {
                                        const tool = allTools?.find(t => t.id === toolId);
                                        return (
                                            <Paper key={toolId} sx={{ p: 2, bgcolor: 'rgba(255, 255, 255, 0.02)', border: '1px solid rgba(255, 255, 255, 0.05)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                                                    <Avatar sx={{ bgcolor: 'rgba(0, 122, 204, 0.1)', color: '#007acc' }}><Build sx={{ fontSize: 20 }} /></Avatar>
                                                    <Box>
                                                        <Typography variant="subtitle2">{tool?.name || toolId}</Typography>
                                                        <Typography variant="caption" sx={{ color: '#888' }}>{tool?.description || 'No description available'}</Typography>
                                                    </Box>
                                                </Box>
                                                <IconButton size="small" onClick={() => {
                                                    setSelectedTools(prev => prev.filter(id => id !== toolId));
                                                    setHasUnsavedChanges(true);
                                                }}>
                                                    <Close fontSize="small" />
                                                </IconButton>
                                            </Paper>
                                        );
                                    })}
                                    <Button variant="outlined" startIcon={<Bolt />} onClick={() => setIsToolDialogOpen(true)} sx={{ mt: 1, textTransform: 'none', borderStyle: 'dashed' }}>
                                        Manage Tools
                                    </Button>
                                </Box>
                            )}

                            {/* Tool Selection Dialog */}
                            <Dialog open={isToolDialogOpen} onClose={() => setIsToolDialogOpen(false)} maxWidth="sm" fullWidth PaperProps={{ sx: { bgcolor: '#1e1e1e', backgroundImage: 'none', border: '1px solid rgba(255,255,255,0.1)' } }}>
                                <DialogTitle sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                    Select Tools
                                </DialogTitle>
                                <DialogContent sx={{ p: 0, height: '400px', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                                    <List sx={{ flex: 1, overflow: 'auto', p: 0 }}>
                                        {allTools && allTools.length > 0 ? (
                                            allTools.map((tool) => {
                                                const isSelected = selectedTools.includes(tool.id);
                                                return (
                                                    <ListItem
                                                        key={tool.id}
                                                        button
                                                        onClick={() => {
                                                            if (isSelected) {
                                                                setSelectedTools(prev => prev.filter(id => id !== tool.id));
                                                            } else {
                                                                setSelectedTools(prev => [...prev, tool.id]);
                                                            }
                                                            setHasUnsavedChanges(true);
                                                        }}
                                                        sx={{
                                                            borderBottom: '1px solid rgba(255,255,255,0.05)',
                                                            bgcolor: isSelected ? 'rgba(0, 122, 204, 0.08)' : 'transparent',
                                                            '&:hover': { bgcolor: isSelected ? 'rgba(0, 122, 204, 0.12)' : 'rgba(255,255,255,0.02)' }
                                                        }}
                                                    >
                                                        <ListItemIcon>
                                                            <Checkbox
                                                                edge="start"
                                                                checked={isSelected}
                                                                tabIndex={-1}
                                                                disableRipple
                                                                sx={{
                                                                    color: '#666',
                                                                    '&.Mui-checked': { color: '#007acc' }
                                                                }}
                                                            />
                                                        </ListItemIcon>
                                                        <ListItemText
                                                            primary={tool.name}
                                                            secondary={tool.description}
                                                            primaryTypographyProps={{ variant: 'body2', fontWeight: 500 }}
                                                            secondaryTypographyProps={{ variant: 'caption', color: '#888' }}
                                                        />
                                                        <Chip label={tool.tool_type} size="small" sx={{ height: 20, fontSize: '0.65rem', opacity: 0.7 }} />
                                                    </ListItem>
                                                );
                                            })
                                        ) : (
                                            <Box sx={{ p: 4, textAlign: 'center' }}>
                                                <Typography variant="body2" color="text.secondary">No tools available.</Typography>
                                                <Button size="small" sx={{ mt: 2 }} onClick={() => navigate('/tools')}>Create Tool</Button>
                                            </Box>
                                        )}
                                    </List>
                                </DialogContent>
                                <DialogActions sx={{ p: 2, borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                                    <Button onClick={() => setIsToolDialogOpen(false)} sx={{ color: '#888' }}>Close</Button>
                                    <Button variant="contained" onClick={() => setIsToolDialogOpen(false)}>Done</Button>
                                </DialogActions>
                            </Dialog>
                        </Grid>
                    </Grid>
                </TabPanel>

                <TabPanel value={activeTab} index={4}>
                    <Box sx={{ maxWidth: '800px', mx: 'auto' }}>
                        <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>Role-Based Access Control</Typography>

                        <Paper sx={{ p: 0, bgcolor: '#252526', border: '1px solid #2d2d30', overflow: 'hidden', mb: 3 }}>
                            {agentRoles && agentRoles.length > 0 ? (
                                <List>
                                    {agentRoles.map((ar: any, idx: number) => (
                                        <ListItem key={ar.role_id} divider={idx !== agentRoles.length - 1}>
                                            <ListItemIcon>
                                                <Security sx={{ color: '#007acc' }} />
                                            </ListItemIcon>
                                            <ListItemText
                                                primary={ar.role_name}
                                                secondary={`Access: ${ar.access_type.toUpperCase()}`}
                                                primaryTypographyProps={{ color: '#ccc' }}
                                                secondaryTypographyProps={{ color: '#888' }}
                                            />
                                            <IconButton
                                                onClick={() => revokeRoleMutation.mutate(ar.role_id)}
                                                disabled={revokeRoleMutation.isLoading}
                                                sx={{ color: '#f44336' }}
                                            >
                                                <Delete />
                                            </IconButton>
                                        </ListItem>
                                    ))}
                                </List>
                            ) : (
                                <Box sx={{ p: 3, textAlign: 'center', color: '#888' }}>
                                    No roles assigned to this agent.
                                </Box>
                            )}
                            <Box sx={{ p: 2, bgcolor: 'rgba(0,0,0,0.1)', borderTop: '1px solid #2d2d30' }}>
                                <Button
                                    startIcon={<AddIcon />}
                                    onClick={() => setAssignRoleDialogOpen(true)}
                                    variant="contained"
                                    sx={{ bgcolor: '#007acc' }}
                                >
                                    Assign Role
                                </Button>
                            </Box>
                        </Paper>

                        <Alert severity="info" sx={{ bgcolor: 'rgba(2, 136, 209, 0.1)', color: '#81d4fa' }}>
                            Users with "Super Admin" role have full access regardless of these settings.
                        </Alert>
                    </Box>
                </TabPanel>
            </Box>

            <Dialog open={assignRoleDialogOpen} onClose={() => setAssignRoleDialogOpen(false)}>
                <DialogTitle sx={{ bgcolor: '#252526', color: '#ccc' }}>Assign Role to Agent</DialogTitle>
                <DialogContent sx={{ bgcolor: '#1e1e1e', pt: 2, minWidth: 400 }}>
                    <FormControl fullWidth sx={{ mb: 2, mt: 1 }}>
                        <InputLabel>Role</InputLabel>
                        <Select
                            value={selectedRoleToAssign}
                            label="Role"
                            onChange={(e) => setSelectedRoleToAssign(e.target.value)}
                        >
                            {roles?.map((role: any) => (
                                <MenuItem key={role.id} value={role.id}>
                                    {role.name} ({role.description})
                                </MenuItem>
                            ))}
                        </Select>
                    </FormControl>
                    <FormControl fullWidth>
                        <InputLabel>Access Type</InputLabel>
                        <Select
                            value={selectedAccessType}
                            label="Access Type"
                            onChange={(e) => setSelectedAccessType(e.target.value)}
                        >
                            <MenuItem value="read">Read (View Only)</MenuItem>
                            <MenuItem value="write">Write (Edit & Execute)</MenuItem>
                            <MenuItem value="execute">Execute Only</MenuItem>
                        </Select>
                    </FormControl>
                </DialogContent>
                <DialogActions sx={{ bgcolor: '#252526' }}>
                    <Button onClick={() => setAssignRoleDialogOpen(false)} sx={{ color: '#888' }}>Cancel</Button>
                    <Button
                        onClick={handleAssignRole}
                        variant="contained"
                        disabled={!selectedRoleToAssign || assignRoleMutation.isLoading}
                        sx={{ bgcolor: '#007acc' }}
                    >
                        Assign
                    </Button>
                </DialogActions>
            </Dialog>

            {/* Knowledge Base Tab */}
            <TabPanel value={activeTab} index={5}>
                <Box sx={{ maxWidth: 900, mx: 'auto' }}>
                    <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Box>
                            <Typography variant="h6" sx={{ color: '#e1e1e1', mb: 1 }}>
                                Knowledge Base Sources
                            </Typography>
                            <Typography variant="body2" sx={{ color: '#969696' }}>
                                Assign specific RAG sources to this agent. If no sources are assigned, the agent will have access to all your knowledge base sources when using the knowledge_base tool.
                            </Typography>
                        </Box>
                        <Chip
                            label={capabilities.knowledge_base_retrieval ? 'Enabled' : 'Disabled'}
                            color={capabilities.knowledge_base_retrieval ? 'success' : 'default'}
                            size="small"
                        />
                    </Box>

                    {!capabilities.knowledge_base_retrieval && (
                        <Paper sx={{ p: 3, mb: 3, bgcolor: 'rgba(255, 193, 7, 0.1)', border: '1px solid rgba(255, 193, 7, 0.3)' }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                                <InfoOutlined sx={{ color: '#ffc107' }} />
                                <Box>
                                    <Typography variant="subtitle2" sx={{ color: '#ffc107', fontWeight: 600 }}>
                                        Knowledge Base Retrieval is Disabled
                                    </Typography>
                                    <Typography variant="body2" sx={{ color: '#e2c08d', mt: 0.5 }}>
                                        Enable it in the Configuration tab to allow this agent to use RAG sources.
                                    </Typography>
                                </Box>
                            </Box>
                        </Paper>
                    )}

                    <Card sx={{ bgcolor: 'rgba(255, 255, 255, 0.02)', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
                        <CardContent>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                                <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                                    Available Sources ({allRAGSources?.length || 0})
                                </Typography>
                                <Typography variant="caption" sx={{ color: '#569cd6' }}>
                                    {assignedRAGSources?.length || 0} assigned
                                </Typography>
                            </Box>

                            {(!allRAGSources || allRAGSources.length === 0) ? (
                                <Box sx={{ textAlign: 'center', py: 6 }}>
                                    <MenuBook sx={{ fontSize: 48, color: '#555', mb: 2 }} />
                                    <Typography variant="body2" sx={{ color: '#969696', mb: 2 }}>
                                        No RAG sources available
                                    </Typography>
                                    <Button
                                        variant="outlined"
                                        size="small"
                                        onClick={() => navigate('/knowledge-base')}
                                        sx={{ textTransform: 'none' }}
                                    >
                                        Go to Knowledge Base
                                    </Button>
                                </Box>
                            ) : (
                                <List sx={{ maxHeight: 500, overflow: 'auto' }}>
                                    {allRAGSources.map((source) => {
                                        const isAssigned = assignedRAGSources?.some(s => s.id === source.id)
                                        const isProcessing = assignRAGSourceMutation.isLoading || removeRAGSourceMutation.isLoading

                                        return (
                                            <ListItem
                                                key={source.id}
                                                sx={{
                                                    border: '1px solid rgba(255, 255, 255, 0.05)',
                                                    borderRadius: '8px',
                                                    mb: 1,
                                                    bgcolor: isAssigned ? 'rgba(0, 122, 204, 0.05)' : 'transparent',
                                                    '&:hover': { bgcolor: 'rgba(255, 255, 255, 0.02)' }
                                                }}
                                            >
                                                <ListItemIcon>
                                                    <Checkbox
                                                        edge="start"
                                                        checked={isAssigned}
                                                        onChange={() => handleToggleRAGSource(source.id)}
                                                        disabled={isProcessing}
                                                        icon={<CheckBoxOutlineBlank />}
                                                        checkedIcon={<CheckBox sx={{ color: '#007acc' }} />}
                                                    />
                                                </ListItemIcon>
                                                <ListItemText
                                                    primary={
                                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                                            <Typography variant="subtitle2" sx={{ color: '#e1e1e1' }}>
                                                                {source.name}
                                                            </Typography>
                                                            <Chip
                                                                label={source.source_type}
                                                                size="small"
                                                                sx={{
                                                                    height: 20,
                                                                    fontSize: '0.65rem',
                                                                    bgcolor: source.source_type === 'pdf' ? 'rgba(206, 145, 120, 0.2)' : 'rgba(78, 201, 176, 0.2)',
                                                                    color: source.source_type === 'pdf' ? '#ce9178' : '#4ec9b0'
                                                                }}
                                                            />
                                                            <Chip
                                                                label={source.status}
                                                                size="small"
                                                                color={source.status === 'completed' ? 'success' : source.status === 'failed' ? 'error' : 'default'}
                                                                sx={{ height: 20, fontSize: '0.65rem' }}
                                                            />
                                                        </Box>
                                                    }
                                                    secondary={
                                                        <Typography variant="caption" sx={{ color: '#969696', wordBreak: 'break-all' }}>
                                                            {source.content_source}
                                                        </Typography>
                                                    }
                                                />
                                            </ListItem>
                                        )
                                    })}
                                </List>
                            )}

                            <Divider sx={{ my: 2, borderColor: 'rgba(255, 255, 255, 0.05)' }} />

                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <InfoOutlined sx={{ fontSize: 16, color: '#569cd6' }} />
                                <Typography variant="caption" sx={{ color: '#969696' }}>
                                    <strong>Tip:</strong> If no sources are assigned, the agent can access all your knowledge base sources. Assign specific sources to restrict access.
                                </Typography>
                            </Box>
                        </CardContent>
                    </Card>
                </Box>
            </TabPanel>

            {/* Snackbar for notifications */}

            <Snackbar
                open={snackbar.open}
                autoHideDuration={4000}
                onClose={() => setSnackbar({ ...snackbar, open: false })}
                anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
            >
                <Alert
                    onClose={() => setSnackbar({ ...snackbar, open: false })}
                    severity={snackbar.severity}
                    sx={{
                        width: '100%',
                        borderRadius: '8px',
                        boxShadow: '0 8px 16px rgba(0,0,0,0.4)',
                        bgcolor: snackbar.severity === 'success' ? '#2e7d32' : '#d32f2f',
                        color: '#fff',
                        '& .MuiAlert-icon': { color: '#fff' }
                    }}
                >
                    {snackbar.message}
                </Alert>
            </Snackbar>
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
                                setHasUnsavedChanges(true)
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
        </Box>
    )
}

export default AgentDetailWorkspace
