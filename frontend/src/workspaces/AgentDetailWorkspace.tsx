import React, { useState, useEffect, useRef, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
    Box, Typography, Tabs, Tab, TextField, Button, Card, CardContent,
    IconButton, Chip, Select, MenuItem, FormControl, InputLabel, Snackbar,
    Alert, CircularProgress, Paper, Divider, List, ListItem, Tooltip,
    Avatar, Fade, Zoom, Breadcrumbs, Link, Switch, FormControlLabel,
    InputAdornment, Grid
} from '@mui/material'
import {
    ArrowBack, Save, PlayArrow, Stop, Send, Settings as SettingsIcon,
    AutoGraph, Code, Description, Psychology, History, Extension,
    ContentCopy, Delete, Share, OpenInNew, MoreVert, InfoOutlined,
    Done, Refresh, Bolt
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
    const [name, setName] = useState('')
    const [description, setDescription] = useState('')
    const [systemPrompt, setSystemPrompt] = useState('')
    const [model, setModel] = useState('gpt-4')
    const [temperature, setTemperature] = useState(0.7)
    const [maxTokens, setMaxTokens] = useState(2000)
    const [capabilities, setCapabilities] = useState({
        context_memory_enabled: true,
        knowledge_base_retrieval: true,
        internet_search_access: false,
        code_interpreter: true,
    })
    const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
    const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' })

    // Chat state
    const [chatMessages, setChatMessages] = useState<Array<{ role: string, content: string, status?: string }>>([])
    const [chatInput, setChatInput] = useState('')
    const [isExecuting, setIsExecuting] = useState(false)
    const [currentExecutionId, setCurrentExecutionId] = useState<string | null>(null)

    const { data: configuredModels, isLoading: isLoadingConfigured } = useQuery<LLMModel[]>('llm_models', getModels)
    const { data: ollamaModels, isLoading: isLoadingOllama } = useQuery<OllamaModel[]>('discovered_ollama_models', discoverOllamaModels, {
        retry: 1,
        refetchOnWindowFocus: false,
        staleTime: 1000 * 60 * 5 // 5 minutes
    })

    const { data: agent, isLoading, isError } = useQuery(
        ['agent', agentId],
        () => getAgent(agentId!),
        {
            enabled: !!agentId,
            onSuccess: (data) => {
                setName(data.name)
                setDescription(data.description || '')
                setSystemPrompt(data.system_prompt || '')
                // Use model from config or fallback
                setModel(data.config?.model || data.config?.model_name || 'gpt-4')
                setTemperature(data.config?.temperature || 0.7)
                setMaxTokens(data.config?.max_tokens || 2000)
                setCapabilities(data.config?.capabilities || {
                    context_memory_enabled: true,
                    knowledge_base_retrieval: true,
                    internet_search_access: false,
                    code_interpreter: true,
                })
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
            // Try to determine provider from existing config or default to unknown
            const currentProvider = agent?.config?.llm_provider || 'unknown';
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
            system_prompt: systemPrompt,
            config: {
                ...agent?.config,
                model: selectedModelName,     // Frontend state often uses 'model'
                model_name: selectedModelName, // Backend executor uses 'model_name'
                llm_provider: selectedProvider,
                temperature,
                max_tokens: maxTokens,
                capabilities,
            }
        })
    }

    const scrollToBottom = () => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }


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
            }, 1000);
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
                                    <Chip label={`Status: ${agent.status}`} size="small" variant="outlined" sx={{ borderColor: agent.status === 'active' ? '#4caf50' : '#888', color: agent.status === 'active' ? '#4caf50' : '#888' }} />
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

                            <Box sx={{ p: 2, borderRadius: '8px', border: '1px dashed rgba(255, 255, 255, 0.1)', textAlign: 'center' }}>
                                <Typography variant="body2" sx={{ color: '#666', mb: 1.5 }}>No custom tools connected to this agent.</Typography>
                                <Button variant="text" size="small" startIcon={<Bolt />} sx={{ textTransform: 'none', color: '#007acc' }}>Add Tool</Button>
                            </Box>
                        </Grid>
                    </Grid>
                </TabPanel>
            </Box>

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
        </Box>
    )
}

export default AgentDetailWorkspace
