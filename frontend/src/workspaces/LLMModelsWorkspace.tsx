import React, { useState } from 'react';
import {
    Box,
    Typography,
    Button,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Paper,
    IconButton,
    Dialog,
    DialogActions,
    DialogContent,
    DialogTitle,
    TextField,
    Checkbox,
    FormControlLabel,
    Select,
    MenuItem,
    CircularProgress,
    List,
    ListItem,
    ListItemText
} from '@mui/material';
import { Add as AddIcon, Edit as EditIcon, Delete as DeleteIcon, Refresh as RefreshIcon, PlayArrow as PlayArrowIcon } from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { getModels, createModel, updateModel, deleteModel, discoverOllamaModels, testLLMModel, getTestStatus, LLMModel, LLMModelCreate, LLMModelUpdate, OllamaModel } from '../api/llmModels';


const LLMModelsWorkspace: React.FC = () => {
    const queryClient = useQueryClient();
    const [createDialogOpen, setCreateDialogOpen] = useState(false);
    const [editDialogOpen, setEditDialogOpen] = useState(false);
    const [testDialogOpen, setTestDialogOpen] = useState(false);
    const [selectedModel, setSelectedModel] = useState<LLMModel | null>(null);
    const [discoveredOllamaModels, setDiscoveredOllamaModels] = useState<OllamaModel[]>([]);
    const [ollamaDiscoveryLoading, setOllamaDiscoveryLoading] = useState(false);

    const { data: models, isLoading } = useQuery('llm_models', getModels);

    const createMutation = useMutation((newData: LLMModelCreate) => createModel(newData), {
        onSuccess: () => {
            queryClient.invalidateQueries('llm_models');
            setCreateDialogOpen(false);
        },
    });

    const updateMutation = useMutation((updateData: LLMModelUpdate) => updateModel(selectedModel!.id, updateData), {
        onSuccess: () => {
            queryClient.invalidateQueries('llm_models');
            setEditDialogOpen(false);
        },
    });

    const deleteMutation = useMutation(deleteModel, {
        onSuccess: () => {
            queryClient.invalidateQueries('llm_models');
        },
    });

    const handleCreateModel = (data: LLMModelCreate) => {
        createMutation.mutate(data);
    };

    const handleUpdateModel = (data: LLMModelUpdate) => {
        updateMutation.mutate(data);
    };

    const handleDeleteModel = (id: string) => {
        if (window.confirm('Are you sure you want to delete this model?')) {
            deleteMutation.mutate(id);
        }
    };

    const handleDiscoverOllamaModels = async () => {
        setOllamaDiscoveryLoading(true);
        try {
            const models = await discoverOllamaModels();
            setDiscoveredOllamaModels(models);
        } catch (error) {
            console.error("Error discovering Ollama models:", error);
            // Optionally, show an error message to the user
        } finally {
            setOllamaDiscoveryLoading(false);
        }
    };

    const handleImportOllamaModel = (ollamaModel: OllamaModel) => {
        const newModel: LLMModelCreate = {
            name: ollamaModel.name,
            provider: 'ollama',
            api_base: 'http://localhost:11434',
            api_key: 'ollama',
            description: `Imported from Ollama discovery. Size: ${(ollamaModel.size / (1024 * 1024 * 1024)).toFixed(2)} GB`,
            is_default: false
        };
        createMutation.mutate(newModel);
    };

    const openCreateDialog = () => {
        setSelectedModel(null);
        setCreateDialogOpen(true);
    }

    const openEditDialog = (model: LLMModel) => {
        setSelectedModel(model);
        setEditDialogOpen(true);
    };

    const openTestDialog = (model: LLMModel) => {
        setSelectedModel(model);
        setTestDialogOpen(true);
    };

    return (
        <Box sx={{ p: 3 }}>
            <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Typography variant="h4">LLM Models</Typography>
                <Box>
                    <Button
                        variant="outlined"
                        startIcon={ollamaDiscoveryLoading ? <CircularProgress size={20} /> : <RefreshIcon />}
                        onClick={handleDiscoverOllamaModels}
                        disabled={ollamaDiscoveryLoading}
                        sx={{ mr: 2 }}
                    >
                        Discover Ollama Models
                    </Button>
                    <Button variant="contained" startIcon={<AddIcon />} onClick={openCreateDialog}>
                        Create Model
                    </Button>
                </Box>
            </Box>

            {discoveredOllamaModels.length > 0 && (
                <Box sx={{ mb: 3 }}>
                    <Typography variant="h5">Discovered Ollama Models</Typography>
                    <List component={Paper} sx={{ mt: 1 }}>
                        {discoveredOllamaModels.map((ollamaModel) => (
                            <ListItem key={ollamaModel.name}
                                secondaryAction={
                                    <Button size="small" variant="outlined" startIcon={<AddIcon />} onClick={() => handleImportOllamaModel(ollamaModel)}>
                                        Import
                                    </Button>
                                }
                            >
                                <ListItemText
                                    primary={ollamaModel.name}
                                    secondary={`Size: ${(ollamaModel.size / (1024 * 1024 * 1024)).toFixed(2)} GB, Modified: ${new Date(ollamaModel.modified_at).toLocaleString()}`}
                                />
                            </ListItem>
                        ))}
                    </List>
                </Box>
            )}

            <Typography variant="h5" sx={{ mb: 2 }}>Configured Models</Typography>
            {isLoading ? (
                <CircularProgress />
            ) : (
                <TableContainer component={Paper}>
                    <Table>
                        <TableHead>
                            <TableRow>
                                <TableCell>Name</TableCell>
                                <TableCell>Provider</TableCell>
                                <TableCell>Description</TableCell>
                                <TableCell>Default</TableCell>
                                <TableCell>Actions</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {models?.map((model) => (
                                <TableRow key={model.id}>
                                    <TableCell>{model.name}</TableCell>
                                    <TableCell>{model.provider}</TableCell>
                                    <TableCell>{model.description}</TableCell>
                                    <TableCell>{model.is_default ? 'Yes' : 'No'}</TableCell>
                                    <TableCell>
                                        <IconButton onClick={() => openEditDialog(model)}><EditIcon /></IconButton>
                                        <IconButton onClick={() => handleDeleteModel(model.id)}><DeleteIcon /></IconButton>
                                        <IconButton onClick={() => openTestDialog(model)}><PlayArrowIcon /></IconButton>
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </TableContainer>
            )}

            <ModelDialog
                open={createDialogOpen || editDialogOpen}
                onClose={() => { setCreateDialogOpen(false); setEditDialogOpen(false); }}
                onSubmit={selectedModel ? handleUpdateModel : handleCreateModel}
                model={selectedModel}
            />

            {selectedModel && (
                <ModelTestDialog
                    open={testDialogOpen}
                    onClose={() => setTestDialogOpen(false)}
                    model={selectedModel}
                />
            )}
        </Box>
    );
};

interface ModelDialogProps {
    open: boolean;
    onClose: () => void;
    onSubmit: (data: any) => void;
    model: LLMModel | null;
}

const ModelDialog: React.FC<ModelDialogProps> = ({ open, onClose, onSubmit, model }) => {
    const [formData, setFormData] = useState<LLMModelUpdate>({});

    React.useEffect(() => {
        if (model) {
            setFormData(model);
        } else {
            setFormData({
                name: '',
                provider: 'OpenAI',
                api_key: '',
                api_base: '',
                description: '',
                is_default: false,
            })
        }
    }, [model, open]);


    const handleChange = (e: React.ChangeEvent<HTMLInputElement | { name?: string; value: unknown }>) => {
        const { name, value, type, checked } = e.target as HTMLInputElement;
        setFormData(prev => ({ ...prev, [name as string]: type === 'checkbox' ? checked : value }));
    };

    const handleSelectChange = (e: any) => {
        setFormData(prev => ({ ...prev, provider: e.target.value }));
    }

    const handleSubmit = () => {
        const submissionData = { ...formData };
        if (submissionData.api_key === '') {
            delete submissionData.api_key;
        }
        onSubmit(submissionData);
        onClose();
    };

    return (
        <Dialog open={open} onClose={onClose}>
            <DialogTitle>{model ? 'Edit LLM Model' : 'Create LLM Model'}</DialogTitle>
            <DialogContent>
                <TextField name="name" label="Name" value={formData.name || ''} onChange={handleChange} fullWidth margin="dense" />
                <Select name="provider" value={formData.provider || 'OpenAI'} onChange={handleSelectChange} fullWidth>
                    <MenuItem value="openai">OpenAI</MenuItem>
                    <MenuItem value="anthropic">Anthropic</MenuItem>
                    <MenuItem value="google">Google Gemini</MenuItem>
                    <MenuItem value="vertex_ai">Vertex AI</MenuItem>
                    <MenuItem value="ollama">Ollama</MenuItem>
                    <MenuItem value="huggingface">HuggingFace</MenuItem>
                </Select>
                <TextField name="api_key" label="API Key" value={formData.api_key || ''} onChange={handleChange} fullWidth margin="dense" type="password" />
                <TextField name="api_base" label="API Base" value={formData.api_base || ''} onChange={handleChange} fullWidth margin="dense" />
                <TextField name="description" label="Description" value={formData.description || ''} onChange={handleChange} fullWidth margin="dense" multiline rows={3} />
                <FormControlLabel
                    control={<Checkbox name="is_default" checked={formData.is_default || false} onChange={handleChange} />}
                    label="Default Model"
                />
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose}>Cancel</Button>
                <Button onClick={handleSubmit}>Submit</Button>
            </DialogActions>
        </Dialog>
    );
}

interface ModelTestDialogProps {
    open: boolean;
    onClose: () => void;
    model: LLMModel;
}

const ModelTestDialog: React.FC<ModelTestDialogProps> = ({ open, onClose, model }) => {
    const [prompt, setPrompt] = useState<string>('');
    const [systemPrompt, setSystemPrompt] = useState<string>('');
    const [testResponse, setTestResponse] = useState<string>('');
    const [testingLoading, setTestingLoading] = useState(false);
    const [jobId, setJobId] = useState<string | null>(null);
    const [startTime, setStartTime] = useState<number | null>(null);

    React.useEffect(() => {
        if (open) {
            setPrompt('');
            setSystemPrompt('');
            setTestResponse('');
            setJobId(null);
            setTestingLoading(false);
            setStartTime(null);
        }
    }, [open, model]);

    React.useEffect(() => {
        let pollInterval: NodeJS.Timeout | null = null;
        if (jobId && testingLoading && startTime) {
            pollInterval = setInterval(async () => {
                // Check for 60-second timeout
                const elapsed = (Date.now() - startTime) / 1000;
                if (elapsed >= 60) {
                    setTestResponse(`Error: Test timed out after 60 seconds. The model may be slow, overloaded, or experiencing issues.`);
                    setTestingLoading(false);
                    setJobId(null);
                    if (pollInterval) clearInterval(pollInterval);
                    return;
                }

                try {
                    const statusData = await getTestStatus(jobId);
                    if (statusData.status === 'completed') {
                        setTestResponse(statusData.result);
                        setTestingLoading(false);
                        setJobId(null);
                        if (pollInterval) clearInterval(pollInterval);
                    } else if (statusData.status === 'failed') {
                        // Improve error message formatting
                        const errorMsg = statusData.error || 'Unknown error occurred';
                        setTestResponse(`Error: ${errorMsg}`);
                        setTestingLoading(false);
                        setJobId(null);
                        if (pollInterval) clearInterval(pollInterval);
                    }
                } catch (error) {
                    console.error("Polling error", error);
                    setTestResponse("Error: Failed to get test status. The test might have timed out or the server may have restarted.");
                    setTestingLoading(false);
                    setJobId(null);
                    if (pollInterval) clearInterval(pollInterval);
                }
            }, 5000); // Changed from 2000ms to 5000ms (5 seconds)
        }
        return () => {
            if (pollInterval) clearInterval(pollInterval);
        }
    }, [jobId, testingLoading, startTime]);

    const handleTestModel = async () => {
        setTestingLoading(true);
        setTestResponse('');
        setJobId(null);
        setStartTime(Date.now()); // Track start time for timeout
        try {
            const response = await testLLMModel(model.id, prompt, systemPrompt);
            setJobId(response.job_id);
        } catch (error: any) {
            setTestingLoading(false);
            const errorMsg = error.response?.data?.detail || error.message || 'Unknown error';
            setTestResponse(`Error: ${errorMsg}`);
        }
    };

    return (
        <Dialog open={open} onClose={onClose} fullWidth maxWidth="md">
            <DialogTitle>Test LLM Model: {model.name}</DialogTitle>
            <DialogContent>
                <TextField
                    label="System Prompt (Optional)"
                    value={systemPrompt}
                    onChange={(e) => setSystemPrompt(e.target.value)}
                    fullWidth
                    margin="dense"
                    multiline
                    rows={2}
                />
                <TextField
                    label="User Prompt"
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    fullWidth
                    margin="dense"
                    multiline
                    rows={4}
                />
                <Button
                    variant="contained"
                    onClick={handleTestModel}
                    disabled={testingLoading || !prompt}
                    startIcon={testingLoading ? <CircularProgress size={20} /> : <PlayArrowIcon />}
                    sx={{ mt: 2 }}
                >
                    Send Test Request
                </Button>
                {testResponse && (
                    <Box sx={{
                        mt: 2,
                        p: 3,
                        border: '2px solid #1976d2',
                        borderRadius: '8px',
                        bgcolor: '#ffffff',
                        boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
                    }}>
                        <Typography variant="h6" sx={{ mb: 2, color: '#1976d2', fontWeight: 600 }}>
                            Model Response:
                        </Typography>
                        <Typography sx={{
                            whiteSpace: 'pre-wrap',
                            color: '#000000',
                            fontSize: '0.95rem',
                            lineHeight: 1.6,
                            fontFamily: 'monospace'
                        }}>
                            {testResponse}
                        </Typography>
                    </Box>
                )}
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose}>Close</Button>
            </DialogActions>
        </Dialog>
    );
};


export default LLMModelsWorkspace;
