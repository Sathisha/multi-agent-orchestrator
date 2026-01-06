import React, { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
    Box,
    Typography,
    Button,
    Card,
    CardContent,
    TextField,
    CircularProgress,
    Chip,
    Paper,
    Alert,
    Tabs,
    Tab,
    IconButton,
    Divider
} from '@mui/material'
import {
    ArrowBack as ArrowBackIcon,
    PlayArrow as PlayArrowIcon,
    Code as CodeIcon,
    Edit as EditIcon,
    Save as SaveIcon,
    Cancel as CancelIcon
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { getTool, executeTool, updateTool, Tool, CreateToolRequest } from '../api/tools'

interface TabPanelProps {
    children?: React.ReactNode
    index: number
    value: number
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => {
    return (
        <div role="tabpanel" hidden={value !== index}>
            {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
        </div>
    )
}

const ToolDetailWorkspace: React.FC = () => {
    const { toolId } = useParams<{ toolId: string }>()
    const navigate = useNavigate()
    const queryClient = useQueryClient()

    const [tabValue, setTabValue] = useState(0)
    const [isEditing, setIsEditing] = useState(false)
    const [editedTool, setEditedTool] = useState<Tool | null>(null)

    // Test execution state
    const [testInputs, setTestInputs] = useState('{}')
    const [testContext, setTestContext] = useState('{}')
    const [testResult, setTestResult] = useState<any>(null)
    const [testError, setTestError] = useState<string | null>(null)
    const [isExecuting, setIsExecuting] = useState(false)

    const { data: tool, isLoading } = useQuery(
        ['tool', toolId],
        () => getTool(toolId!),
        {
            enabled: !!toolId,
            onSuccess: (data) => {
                setEditedTool(data)
            }
        }
    )

    const updateMutation = useMutation(
        (data: { id: string; tool_request: Partial<CreateToolRequest> }) =>
            updateTool(data.id, data.tool_request),
        {
            onSuccess: () => {
                queryClient.invalidateQueries(['tool', toolId])
                setIsEditing(false)
            }
        }
    )

    const handleExecuteTest = async () => {
        if (!tool) return

        setIsExecuting(true)
        setTestError(null)
        setTestResult(null)

        try {
            const parsedInputs = JSON.parse(testInputs)
            const parsedContext = JSON.parse(testContext)
            const result = await executeTool(
                tool.id,
                parsedInputs,
                parsedContext,
                tool.timeout_seconds
            )
            setTestResult(result)
        } catch (e: any) {
            setTestError(e.response?.data?.detail || e.message || 'An unknown error occurred')
        } finally {
            setIsExecuting(false)
        }
    }

    const handleSave = () => {
        if (!editedTool) return

        updateMutation.mutate({
            id: editedTool.id,
            tool_request: {
                name: editedTool.name,
                description: editedTool.description,
                code: editedTool.code,
                input_schema: editedTool.input_schema,
                output_schema: editedTool.output_schema,
                entry_point: editedTool.entry_point,
                timeout_seconds: editedTool.timeout_seconds
            }
        })
    }

    const handleCancelEdit = () => {
        setEditedTool(tool || null)
        setIsEditing(false)
    }

    if (isLoading) {
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                <CircularProgress />
            </Box>
        )
    }

    if (!tool || !editedTool) {
        return (
            <Box sx={{ p: 3 }}>
                <Alert severity="error">Tool not found</Alert>
            </Box>
        )
    }

    return (
        <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            {/* Header */}
            <Box sx={{ p: 3, borderBottom: '1px solid #2d2d30' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <IconButton onClick={() => navigate('/tools')} sx={{ mr: 2, color: '#cccccc' }}>
                        <ArrowBackIcon />
                    </IconButton>
                    <Box sx={{ flex: 1 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                            <Typography variant="h4" sx={{ color: '#cccccc' }}>
                                {tool.name}
                            </Typography>
                            <Chip
                                label={tool.tool_type}
                                size="small"
                                sx={{
                                    backgroundColor: '#007acc',
                                    color: '#ffffff',
                                }}
                            />
                            <Box
                                sx={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 1,
                                }}
                            >
                                <Box
                                    sx={{
                                        width: 8,
                                        height: 8,
                                        borderRadius: '50%',
                                        backgroundColor: tool.status === 'active' ? '#4ec9b0' : '#969696',
                                    }}
                                />
                                <Typography variant="caption" sx={{ color: '#969696' }}>
                                    {tool.status}
                                </Typography>
                            </Box>
                        </Box>
                        <Typography variant="body2" sx={{ color: '#969696', mt: 1 }}>
                            {tool.description || 'No description'}
                        </Typography>
                        <Typography variant="caption" sx={{ color: '#969696', display: 'block', mt: 0.5 }}>
                            Used {tool.usage_count} times
                        </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', gap: 1 }}>
                        {isEditing ? (
                            <>
                                <Button
                                    variant="outlined"
                                    startIcon={<CancelIcon />}
                                    onClick={handleCancelEdit}
                                    sx={{
                                        borderColor: '#969696',
                                        color: '#969696',
                                    }}
                                >
                                    Cancel
                                </Button>
                                <Button
                                    variant="contained"
                                    startIcon={<SaveIcon />}
                                    onClick={handleSave}
                                    disabled={updateMutation.isLoading}
                                    sx={{
                                        backgroundColor: '#007acc',
                                        '&:hover': {
                                            backgroundColor: '#005a9e',
                                        },
                                    }}
                                >
                                    Save Changes
                                </Button>
                            </>
                        ) : (
                            <Button
                                variant="outlined"
                                startIcon={<EditIcon />}
                                onClick={() => setIsEditing(true)}
                                sx={{
                                    borderColor: '#007acc',
                                    color: '#007acc',
                                }}
                            >
                                Edit Tool
                            </Button>
                        )}
                    </Box>
                </Box>

                {/* Tabs */}
                <Tabs
                    value={tabValue}
                    onChange={(_, newValue) => setTabValue(newValue)}
                    sx={{
                        '& .MuiTab-root': {
                            color: '#969696',
                            '&.Mui-selected': {
                                color: '#007acc',
                            },
                        },
                        '& .MuiTabs-indicator': {
                            backgroundColor: '#007acc',
                        },
                    }}
                >
                    <Tab label="Overview" />
                    <Tab label="Code" />
                    <Tab label="Test" />
                </Tabs>
            </Box>

            {/* Content */}
            <Box sx={{ flex: 1, overflow: 'auto', p: 3 }}>
                <TabPanel value={tabValue} index={0}>
                    {/* Overview Tab */}
                    <Card sx={{ backgroundColor: '#252526', border: '1px solid #2d2d30', mb: 2 }}>
                        <CardContent>
                            <Typography variant="h6" sx={{ color: '#cccccc', mb: 2 }}>
                                Tool Details
                            </Typography>
                            <Box sx={{ display: 'grid', gridTemplateColumns: '200px 1fr', gap: 2 }}>
                                <Typography sx={{ color: '#969696' }}>Name:</Typography>
                                {isEditing ? (
                                    <TextField
                                        fullWidth
                                        size="small"
                                        value={editedTool.name}
                                        onChange={(e) => setEditedTool({ ...editedTool, name: e.target.value })}
                                    />
                                ) : (
                                    <Typography sx={{ color: '#cccccc' }}>{tool.name}</Typography>
                                )}

                                <Typography sx={{ color: '#969696' }}>Description:</Typography>
                                {isEditing ? (
                                    <TextField
                                        fullWidth
                                        size="small"
                                        multiline
                                        rows={2}
                                        value={editedTool.description || ''}
                                        onChange={(e) => setEditedTool({ ...editedTool, description: e.target.value })}
                                    />
                                ) : (
                                    <Typography sx={{ color: '#cccccc' }}>{tool.description || 'No description'}</Typography>
                                )}

                                <Typography sx={{ color: '#969696' }}>Entry Point:</Typography>
                                {isEditing ? (
                                    <TextField
                                        fullWidth
                                        size="small"
                                        value={editedTool.entry_point || 'execute'}
                                        onChange={(e) => setEditedTool({ ...editedTool, entry_point: e.target.value })}
                                    />
                                ) : (
                                    <Typography sx={{ color: '#cccccc' }}>{tool.entry_point || 'execute'}</Typography>
                                )}

                                <Typography sx={{ color: '#969696' }}>Timeout:</Typography>
                                {isEditing ? (
                                    <TextField
                                        fullWidth
                                        size="small"
                                        type="number"
                                        value={editedTool.timeout_seconds || 60}
                                        onChange={(e) => setEditedTool({ ...editedTool, timeout_seconds: parseInt(e.target.value) })}
                                    />
                                ) : (
                                    <Typography sx={{ color: '#cccccc' }}>{tool.timeout_seconds || 60} seconds</Typography>
                                )}

                                <Typography sx={{ color: '#969696' }}>Version:</Typography>
                                <Typography sx={{ color: '#cccccc' }}>{tool.version}</Typography>

                                <Typography sx={{ color: '#969696' }}>Created:</Typography>
                                <Typography sx={{ color: '#cccccc' }}>
                                    {new Date(tool.created_at).toLocaleString()}
                                </Typography>

                                <Typography sx={{ color: '#969696' }}>Updated:</Typography>
                                <Typography sx={{ color: '#cccccc' }}>
                                    {new Date(tool.updated_at).toLocaleString()}
                                </Typography>
                            </Box>
                        </CardContent>
                    </Card>

                    {/* Schemas */}
                    <Card sx={{ backgroundColor: '#252526', border: '1px solid #2d2d30', mb: 2 }}>
                        <CardContent>
                            <Typography variant="h6" sx={{ color: '#cccccc', mb: 2 }}>
                                Input Schema
                            </Typography>
                            {isEditing ? (
                                <TextField
                                    fullWidth
                                    multiline
                                    rows={6}
                                    value={JSON.stringify(editedTool.input_schema, null, 2)}
                                    onChange={(e) => {
                                        try {
                                            setEditedTool({ ...editedTool, input_schema: JSON.parse(e.target.value) })
                                        } catch {
                                            // Invalid JSON, ignore
                                        }
                                    }}
                                    sx={{
                                        '& .MuiInputBase-input': {
                                            fontFamily: 'monospace',
                                        },
                                    }}
                                />
                            ) : (
                                <Paper
                                    sx={{
                                        backgroundColor: '#1e1e1e',
                                        p: 2,
                                        overflow: 'auto',
                                    }}
                                >
                                    <pre style={{ margin: 0, color: '#d4d4d4', fontFamily: 'monospace' }}>
                                        {JSON.stringify(tool.input_schema, null, 2)}
                                    </pre>
                                </Paper>
                            )}
                        </CardContent>
                    </Card>

                    <Card sx={{ backgroundColor: '#252526', border: '1px solid #2d2d30' }}>
                        <CardContent>
                            <Typography variant="h6" sx={{ color: '#cccccc', mb: 2 }}>
                                Output Schema
                            </Typography>
                            {isEditing ? (
                                <TextField
                                    fullWidth
                                    multiline
                                    rows={6}
                                    value={JSON.stringify(editedTool.output_schema, null, 2)}
                                    onChange={(e) => {
                                        try {
                                            setEditedTool({ ...editedTool, output_schema: JSON.parse(e.target.value) })
                                        } catch {
                                            // Invalid JSON, ignore
                                        }
                                    }}
                                    sx={{
                                        '& .MuiInputBase-input': {
                                            fontFamily: 'monospace',
                                        },
                                    }}
                                />
                            ) : (
                                <Paper
                                    sx={{
                                        backgroundColor: '#1e1e1e',
                                        p: 2,
                                        overflow: 'auto',
                                    }}
                                >
                                    <pre style={{ margin: 0, color: '#d4d4d4', fontFamily: 'monospace' }}>
                                        {JSON.stringify(tool.output_schema, null, 2)}
                                    </pre>
                                </Paper>
                            )}
                        </CardContent>
                    </Card>
                </TabPanel>

                <TabPanel value={tabValue} index={1}>
                    {/* Code Tab */}
                    <Card sx={{ backgroundColor: '#252526', border: '1px solid #2d2d30' }}>
                        <CardContent>
                            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                                <CodeIcon sx={{ color: '#4ec9b0', mr: 1 }} />
                                <Typography variant="h6" sx={{ color: '#cccccc' }}>
                                    Tool Code
                                </Typography>
                            </Box>
                            {isEditing ? (
                                <TextField
                                    fullWidth
                                    multiline
                                    rows={20}
                                    value={editedTool.code || ''}
                                    onChange={(e) => setEditedTool({ ...editedTool, code: e.target.value })}
                                    sx={{
                                        '& .MuiInputBase-input': {
                                            fontFamily: 'monospace',
                                            fontSize: '14px',
                                        },
                                    }}
                                />
                            ) : (
                                <Paper
                                    sx={{
                                        backgroundColor: '#1e1e1e',
                                        p: 2,
                                        overflow: 'auto',
                                        maxHeight: '600px',
                                    }}
                                >
                                    <pre style={{ margin: 0, color: '#d4d4d4', fontFamily: 'monospace', fontSize: '14px' }}>
                                        {tool.code || 'No code available'}
                                    </pre>
                                </Paper>
                            )}
                        </CardContent>
                    </Card>
                </TabPanel>

                <TabPanel value={tabValue} index={2}>
                    {/* Test Tab */}
                    <Card sx={{ backgroundColor: '#252526', border: '1px solid #2d2d30', mb: 2 }}>
                        <CardContent>
                            <Typography variant="h6" sx={{ color: '#cccccc', mb: 2 }}>
                                Test Tool Execution
                            </Typography>

                            <Typography variant="body2" sx={{ color: '#969696', mb: 1 }}>
                                Inputs (JSON):
                            </Typography>
                            <TextField
                                fullWidth
                                multiline
                                rows={8}
                                value={testInputs}
                                onChange={(e) => setTestInputs(e.target.value)}
                                sx={{
                                    mb: 2,
                                    '& .MuiInputBase-input': {
                                        fontFamily: 'monospace',
                                    },
                                }}
                                placeholder='{"param1": "value1", "param2": "value2"}'
                            />

                            <Typography variant="body2" sx={{ color: '#969696', mb: 1 }}>
                                Context (JSON, Optional):
                            </Typography>
                            <TextField
                                fullWidth
                                multiline
                                rows={4}
                                value={testContext}
                                onChange={(e) => setTestContext(e.target.value)}
                                sx={{
                                    mb: 2,
                                    '& .MuiInputBase-input': {
                                        fontFamily: 'monospace',
                                    },
                                }}
                                placeholder='{"user_id": "123", "session_id": "abc"}'
                            />

                            <Button
                                variant="contained"
                                startIcon={isExecuting ? <CircularProgress size={20} /> : <PlayArrowIcon />}
                                onClick={handleExecuteTest}
                                disabled={isExecuting}
                                sx={{
                                    backgroundColor: '#007acc',
                                    '&:hover': {
                                        backgroundColor: '#005a9e',
                                    },
                                }}
                            >
                                {isExecuting ? 'Executing...' : 'Execute Test'}
                            </Button>
                        </CardContent>
                    </Card>

                    {/* Results */}
                    {testError && (
                        <Alert severity="error" sx={{ mb: 2 }}>
                            <Typography variant="h6" sx={{ mb: 1 }}>Error:</Typography>
                            <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
                                {testError}
                            </pre>
                        </Alert>
                    )}

                    {testResult && (
                        <Card sx={{ backgroundColor: '#252526', border: '1px solid #4ec9b0' }}>
                            <CardContent>
                                <Typography variant="h6" sx={{ color: '#4ec9b0', mb: 2 }}>
                                    ✓ Execution Successful
                                </Typography>
                                <Divider sx={{ mb: 2, borderColor: '#4ec9b0' }} />
                                <Paper
                                    sx={{
                                        backgroundColor: '#1e1e1e',
                                        p: 2,
                                        overflow: 'auto',
                                    }}
                                >
                                    <pre style={{ margin: 0, color: '#d4d4d4', fontFamily: 'monospace' }}>
                                        {JSON.stringify(testResult, null, 2)}
                                    </pre>
                                </Paper>
                            </CardContent>
                        </Card>
                    )}
                </TabPanel>
            </Box>
        </Box>
    )
}

export default ToolDetailWorkspace
