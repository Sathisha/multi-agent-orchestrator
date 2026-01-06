import React, { useState, useEffect } from 'react';
import {
    Box,
    Typography,
    Paper,
    TextField,
    Button,
    Select,
    MenuItem,
    FormControl,
    InputLabel,
    CircularProgress,
    Card,
    CardMedia,
    Alert,
} from '@mui/material';
import { CloudUpload as CloudUploadIcon, Send as SendIcon } from '@mui/icons-material';
import { useQuery } from 'react-query';
import { getModels, getTestStatus, LLMModel } from '../api/llmModels';
import { testVisionModel } from '../api/visionTest';

const VisionTestWorkspace: React.FC = () => {
    const [selectedModelId, setSelectedModelId] = useState<string>('');
    const [prompt, setPrompt] = useState<string>('Describe this image');
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [response, setResponse] = useState<string>('');
    const [error, setError] = useState<string>('');
    const [jobId, setJobId] = useState<string | null>(null);

    const { data: models } = useQuery('llm_models', getModels);

    // Filter for probable vision models (those with "vision" in name or description, or just allow all for flexibility)
    // For now, let's show all and let the user pick, but ideally we'd flag them.
    // Given the prompt "llama3.2-vision" is pulled, we specifically look for it.
    const visionModels = models?.filter(m =>
        m.name.toLowerCase().includes('vision') ||
        m.name.toLowerCase().includes('gpt-4o') ||
        m.name.toLowerCase().includes('claude-3')
    ) || [];

    useEffect(() => {
        if (!selectedModelId && visionModels.length > 0) {
            setSelectedModelId(visionModels[0].id);
        }
    }, [visionModels, selectedModelId]);

    useEffect(() => {
        let pollInterval: NodeJS.Timeout | null = null;
        if (jobId && loading) {
            pollInterval = setInterval(async () => {
                try {
                    const statusData = await getTestStatus(jobId);
                    if (statusData.status === 'completed') {
                        setResponse(statusData.result);
                        setLoading(false);
                        setJobId(null);
                        if (pollInterval) clearInterval(pollInterval);
                    } else if (statusData.status === 'failed') {
                        setError(statusData.error || 'Test failed');
                        setLoading(false);
                        setJobId(null);
                        if (pollInterval) clearInterval(pollInterval);
                    }
                } catch (err: any) {
                    setError(err.message || 'Polling failed');
                    setLoading(false);
                    setJobId(null);
                    if (pollInterval) clearInterval(pollInterval);
                }
            }, 2000);
        }
        return () => {
            if (pollInterval) clearInterval(pollInterval);
        };
    }, [jobId, loading]);

    const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
        if (event.target.files && event.target.files[0]) {
            const file = event.target.files[0];
            setSelectedFile(file);

            const reader = new FileReader();
            reader.onloadend = () => {
                setPreviewUrl(reader.result as string);
            };
            reader.readAsDataURL(file);
        }
    };

    const handleSubmit = async () => {
        if (!selectedFile || !selectedModelId) return;

        setLoading(true);
        setError('');
        setResponse('');
        setJobId(null);

        try {
            const res = await testVisionModel(selectedModelId, prompt, selectedFile);
            setJobId(res.job_id);
        } catch (err: any) {
            setError(err.response?.data?.detail || err.message || 'Failed to start test');
            setLoading(false);
        }
    };

    return (
        <Box sx={{ p: 3, maxWidth: 1200, margin: '0 auto' }}>
            <Typography variant="h4" gutterBottom>
                Vision Model Playground
            </Typography>
            <Typography variant="body1" color="text.secondary" paragraph>
                Upload an image and test it with vision-capable models like Llama 3.2 Vision.
            </Typography>

            <Paper sx={{ p: 3, mb: 3 }}>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>

                    {/* Model Selection */}
                    <FormControl fullWidth>
                        <InputLabel>Select Model</InputLabel>
                        <Select
                            value={selectedModelId}
                            label="Select Model"
                            onChange={(e) => setSelectedModelId(e.target.value)}
                        >
                            {visionModels.map((model) => (
                                <MenuItem key={model.id} value={model.id}>
                                    {model.name} ({model.provider})
                                </MenuItem>
                            ))}
                            {visionModels.length === 0 && (
                                <MenuItem disabled>No vision models found (add one with 'vision' in name)</MenuItem>
                            )}
                        </Select>
                    </FormControl>

                    {/* Image Upload Area */}
                    <Box sx={{
                        border: '2px dashed #ccc',
                        borderRadius: 2,
                        p: 4,
                        textAlign: 'center',
                        bgcolor: '#fafafa',
                        cursor: 'pointer',
                        '&:hover': { bgcolor: '#f0f0f0' }
                    }}>
                        <input
                            accept="image/*"
                            style={{ display: 'none' }}
                            id="raised-button-file"
                            type="file"
                            onChange={handleFileSelect}
                        />
                        <label htmlFor="raised-button-file">
                            <Button variant="contained" component="span" startIcon={<CloudUploadIcon />}>
                                Upload Image
                            </Button>
                        </label>
                        {selectedFile && (
                            <Typography variant="body2" sx={{ mt: 1 }}>
                                {selectedFile.name}
                            </Typography>
                        )}
                    </Box>

                    {/* Image Preview */}
                    {previewUrl && (
                        <Card sx={{ maxWidth: '100%', maxHeight: 600, overflow: 'hidden', display: 'flex', justifyContent: 'center', bgcolor: '#000' }}>
                            <CardMedia
                                component="img"
                                image={previewUrl}
                                alt="Preview"
                                sx={{ maxHeight: 600, objectFit: 'contain' }}
                            />
                        </Card>
                    )}

                    {/* Prompt Input */}
                    <TextField
                        label="Prompt"
                        multiline
                        rows={3}
                        value={prompt}
                        onChange={(e) => setPrompt(e.target.value)}
                        placeholder="Ask something about the image..."
                        fullWidth
                    />

                    {/* Submit Button */}
                    <Button
                        variant="contained"
                        size="large"
                        onClick={handleSubmit}
                        disabled={loading || !selectedFile || !selectedModelId}
                        startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <SendIcon />}
                    >
                        {loading ? 'Analyzing...' : 'Send Request'}
                    </Button>
                </Box>
            </Paper>

            {/* Error Display */}
            {error && (
                <Alert severity="error" sx={{ mb: 3 }}>
                    {error}
                </Alert>
            )}

            {/* Response Display */}
            {response && (
                <Paper sx={{ p: 3, bgcolor: '#f5f9ff', border: '1px solid #e0e0e0' }}>
                    <Typography variant="h6" gutterBottom color="primary">
                        Model Response
                    </Typography>
                    <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                        {response}
                    </Typography>
                </Paper>
            )}
        </Box>
    );
};

export default VisionTestWorkspace;
