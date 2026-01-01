import React, { useState } from 'react'
import { Box, Typography, Button, Card, CardContent, Grid, Chip, Dialog, DialogTitle, DialogContent, DialogActions, TextField, CircularProgress, IconButton } from '@mui/material'
import {
  Add as AddIcon,
  Code as CodeIcon,
  Extension as ExtensionIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  PlayArrow as PlayArrowIcon
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { getTools, createTool, deleteTool, updateTool, getToolTemplates, executeTool, Tool, CreateToolRequest } from '../api/tools'
import { useNavigate } from 'react-router-dom'

const ToolsWorkspace: React.FC = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [testDialogOpen, setTestDialogOpen] = useState(false)
  const [selectedTool, setSelectedTool] = useState<Tool | null>(null)

  const [newToolName, setNewToolName] = useState('')
  const [newToolDesc, setNewToolDesc] = useState('')
  const [newToolCode, setNewToolCode] = useState('')
  const [newToolInputSchema, setNewToolInputSchema] = useState('{}')
  const [newToolOutputSchema, setNewToolOutputSchema] = useState('{}')
  const [newToolEntryPoint, setNewToolEntryPoint] = useState('execute')
  const [newToolTimeout, setNewToolTimeout] = useState(60)

  const { data: tools, isLoading } = useQuery('tools', getTools)
  const { data: templates } = useQuery('tool-templates', getToolTemplates)

  const createMutation = useMutation(createTool, {
    onSuccess: () => {
      queryClient.invalidateQueries('tools')
      setCreateDialogOpen(false)
      setNewToolName('')
      setNewToolDesc('')
      setNewToolCode('')
      setNewToolInputSchema('{}')
      setNewToolOutputSchema('{}')
      setNewToolEntryPoint('execute')
      setNewToolTimeout(60)
    },
  })

  const deleteMutation = useMutation(deleteTool, {
    onSuccess: () => {
      queryClient.invalidateQueries('tools')
    }
  })

  const updateMutation = useMutation(
    (data: { id: string; tool_request: Partial<CreateToolRequest> }) => updateTool(data.id, data.tool_request),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('tools')
        setEditDialogOpen(false)
      }
    }
  )

  const handleCreate = () => {
    // Use first template as default or empty values
    createMutation.mutate({
      name: newToolName,
      description: newToolDesc,
      tool_type: 'custom', // Assuming custom for now
      code: newToolCode || 'def execute(inputs, context=None):\\n    return {"result": "Hello World"}',
      input_schema: JSON.parse(newToolInputSchema),
      output_schema: JSON.parse(newToolOutputSchema),
      entry_point: newToolEntryPoint,
      timeout_seconds: newToolTimeout
    })
  }

  const handleDelete = (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (window.confirm('Are you sure you want to delete this tool?')) {
      deleteMutation.mutate(id)
    }
  }

  const openEditDialog = (tool: Tool) => {
    setSelectedTool(tool);
    setEditDialogOpen(true);
  };

  const openTestDialog = (tool: Tool) => {
    setSelectedTool(tool);
    setTestDialogOpen(true);
  };

  return (
    <Box sx={{ p: 3, height: '100%', overflow: 'auto' }}>
      {/* Header */}
      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Box>
          <Typography variant="h4" sx={{ color: '#cccccc', mb: 1 }}>
            Tools & Extensions
          </Typography>
          <Typography variant="body2" sx={{ color: '#969696' }}>
            Create custom tools and integrate MCP servers to extend agent capabilities
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setCreateDialogOpen(true)}
          sx={{
            backgroundColor: '#007acc',
            '&:hover': {
              backgroundColor: '#005a9e',
            },
          }}
        >
          Create Tool
        </Button>
      </Box>

      {/* Tool Development Section */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h6" sx={{ color: '#cccccc', mb: 2 }}>
          Tool Development
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <Card
              sx={{
                backgroundColor: '#252526',
                border: '1px solid #2d2d30',
                cursor: 'pointer',
                '&:hover': {
                  backgroundColor: '#2a2d2e',
                  borderColor: '#007acc',
                },
              }}
              onClick={() => setCreateDialogOpen(true)}
            >
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <CodeIcon sx={{ color: '#4ec9b0', mr: 1 }} />
                  <Typography variant="h6" sx={{ color: '#cccccc' }}>
                    Custom Tool Editor
                  </Typography>
                </Box>
                <Typography variant="body2" sx={{ color: '#969696', mb: 2 }}>
                  Write custom Python functions with built-in templates and testing
                </Typography>
                <Button
                  variant="outlined"
                  size="small"
                  sx={{
                    borderColor: '#007acc',
                    color: '#007acc',
                    '&:hover': {
                      borderColor: '#005a9e',
                      backgroundColor: 'rgba(0, 122, 204, 0.1)',
                    },
                  }}
                >
                  Open Editor
                </Button>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card
              sx={{
                backgroundColor: '#252526',
                border: '1px solid #2d2d30',
                cursor: 'pointer',
                '&:hover': {
                  backgroundColor: '#2a2d2e',
                  borderColor: '#007acc',
                },
              }}
            >
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <ExtensionIcon sx={{ color: '#569cd6', mr: 1 }} />
                  <Typography variant="h6" sx={{ color: '#cccccc' }}>
                    MCP Server Manager
                  </Typography>
                </Box>
                <Typography variant="body2" sx={{ color: '#969696', mb: 2 }}>
                  Connect and configure Model Context Protocol servers (Coming Soon)
                </Typography>
                <Button
                  variant="outlined"
                  size="small"
                  disabled
                  sx={{
                    borderColor: '#007acc',
                    color: '#007acc',
                  }}
                >
                  Manage Servers
                </Button>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>

      {/* Custom Tools */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h6" sx={{ color: '#cccccc', mb: 2 }}>
          Your Custom Tools
        </Typography>
        {isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          <Grid container spacing={2}>
            {tools?.map((tool) => (
              <Grid item xs={12} md={6} lg={4} key={tool.id}>
                <Card
                  sx={{
                    backgroundColor: '#252526',
                    border: '1px solid #2d2d30',
                    cursor: 'pointer',
                    '&:hover': {
                      backgroundColor: '#2a2d2e',
                      borderColor: '#007acc',
                    },
                  }}
                  onClick={() => navigate(`/tools/${tool.id}`)}
                >
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                      <Typography variant="subtitle1" sx={{ color: '#cccccc' }}>
                        {tool.name}
                      </Typography>
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <Box
                          sx={{
                            width: 8,
                            height: 8,
                            borderRadius: '50%',
                            backgroundColor: tool.status === 'active' ? '#4ec9b0' : '#969696',
                            mr: 1
                          }}
                        />
                        <IconButton size="small" onClick={(e) => openEditDialog(tool)}>
                            <EditIcon fontSize="small" />
                        </IconButton>
                        <IconButton size="small" onClick={(e) => openTestDialog(tool)}>
                            <PlayArrowIcon fontSize="small" />
                        </IconButton>
                        <IconButton size="small" onClick={(e) => handleDelete(tool.id, e)}>
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Box>
                    </Box>

                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                      <Chip
                        label={tool.tool_type}
                        size="small"
                        sx={{
                          height: 20,
                          fontSize: '10px',
                          backgroundColor: '#007acc',
                          color: '#ffffff',
                        }}
                      />
                      <Typography variant="caption" sx={{ color: '#969696' }}>
                        Used {tool.usage_count} times
                      </Typography>
                    </Box>

                    <Typography variant="body2" sx={{ color: '#969696', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                      {tool.description || 'No description'}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
            {tools?.length === 0 && (
              <Typography sx={{ color: 'text.secondary', mt: 2, ml: 2 }}>No tools found. Create one to get started.</Typography>
            )}
          </Grid>
        )}
      </Box>

      {/* Create Dialog */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Create New Tool</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Name"
            fullWidth
            value={newToolName}
            onChange={(e) => setNewToolName(e.target.value)}
            sx={{ mb: 2 }}
          />
          <TextField
            margin="dense"
            label="Description"
            fullWidth
            multiline
            rows={2}
            value={newToolDesc}
            onChange={(e) => setNewToolDesc(e.target.value)}
            sx={{ mb: 2 }}
          />
          <TextField
            margin="dense"
            label="Entry Point"
            fullWidth
            value={newToolEntryPoint}
            onChange={(e) => setNewToolEntryPoint(e.target.value)}
            sx={{ mb: 2 }}
          />
          <TextField
            margin="dense"
            label="Code"
            fullWidth
            multiline
            rows={10}
            value={newToolCode}
            onChange={(e) => setNewToolCode(e.target.value)}
            sx={{ mb: 2 }}
          />
          <TextField
            margin="dense"
            label="Input Schema (JSON)"
            fullWidth
            multiline
            rows={4}
            value={newToolInputSchema}
            onChange={(e) => setNewToolInputSchema(e.target.value)}
            sx={{ mb: 2 }}
          />
          <TextField
            margin="dense"
            label="Output Schema (JSON)"
            fullWidth
            multiline
            rows={4}
            value={newToolOutputSchema}
            onChange={(e) => setNewToolOutputSchema(e.target.value)}
            sx={{ mb: 2 }}
          />
          <TextField
            margin="dense"
            label="Timeout Seconds"
            fullWidth
            type="number"
            value={newToolTimeout}
            onChange={(e) => setNewToolTimeout(parseInt(e.target.value))}
            sx={{ mb: 2 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleCreate} disabled={!newToolName || createMutation.isLoading}>Create</Button>
        </DialogActions>
      </Dialog>

      {/* Edit Dialog */}
      {selectedTool && (
        <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)} maxWidth="md" fullWidth>
          <DialogTitle>Edit Tool: {selectedTool.name}</DialogTitle>
          <DialogContent>
            <TextField
              autoFocus
              margin="dense"
              label="Name"
              fullWidth
              value={selectedTool.name}
              onChange={(e) => setSelectedTool(prev => prev ? { ...prev, name: e.target.value } : null)}
              sx={{ mb: 2 }}
            />
            <TextField
              margin="dense"
              label="Description"
              fullWidth
              multiline
              rows={2}
              value={selectedTool.description || ''}
              onChange={(e) => setSelectedTool(prev => prev ? { ...prev, description: e.target.value } : null)}
              sx={{ mb: 2 }}
            />
            <TextField
              margin="dense"
              label="Entry Point"
              fullWidth
              value={selectedTool.entry_point || ''}
              onChange={(e) => setSelectedTool(prev => prev ? { ...prev, entry_point: e.target.value } : null)}
              sx={{ mb: 2 }}
            />
            <TextField
              margin="dense"
              label="Code"
              fullWidth
              multiline
              rows={10}
              value={selectedTool.code || ''}
              onChange={(e) => setSelectedTool(prev => prev ? { ...prev, code: e.target.value } : null)}
              sx={{ mb: 2 }}
            />
            <TextField
              margin="dense"
              label="Input Schema (JSON)"
              fullWidth
              multiline
              rows={4}
              value={JSON.stringify(selectedTool.input_schema, null, 2)}
              onChange={(e) => {
                try {
                  setSelectedTool(prev => prev ? { ...prev, input_schema: JSON.parse(e.target.value) } : null)
                } catch {
                  // Handle invalid JSON
                }
              }}
              sx={{ mb: 2 }}
            />
            <TextField
              margin="dense"
              label="Output Schema (JSON)"
              fullWidth
              multiline
              rows={4}
              value={JSON.stringify(selectedTool.output_schema, null, 2)}
              onChange={(e) => {
                try {
                  setSelectedTool(prev => prev ? { ...prev, output_schema: JSON.parse(e.target.value) } : null)
                } catch {
                  // Handle invalid JSON
                }
              }}
              sx={{ mb: 2 }}
            />
            <TextField
              margin="dense"
              label="Timeout Seconds"
              fullWidth
              type="number"
              value={selectedTool.timeout_seconds || 60}
              onChange={(e) => setSelectedTool(prev => prev ? { ...prev, timeout_seconds: parseInt(e.target.value) } : null)}
              sx={{ mb: 2 }}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setEditDialogOpen(false)}>Cancel</Button>
            <Button
              onClick={() => {
                if (selectedTool) {
                  updateMutation.mutate({
                    id: selectedTool.id,
                    tool_request: {
                      name: selectedTool.name,
                      description: selectedTool.description,
                      code: selectedTool.code,
                      input_schema: selectedTool.input_schema,
                      output_schema: selectedTool.output_schema,
                      entry_point: selectedTool.entry_point,
                      timeout_seconds: selectedTool.timeout_seconds
                    }
                  })
                }
              }}
              disabled={updateMutation.isLoading}
            >
              Save
            </Button>
          </DialogActions>
        </Dialog>
      )}

      {/* Test Dialog */}
      {selectedTool && (
        <Dialog open={testDialogOpen} onClose={() => setTestDialogOpen(false)} maxWidth="md" fullWidth>
          <ToolTestDialog tool={selectedTool} onClose={() => setTestDialogOpen(false)} />
        </Dialog>
      )}
    </Box>
  )
}

interface ToolTestDialogProps {
  tool: Tool;
  onClose: () => void;
}

const ToolTestDialog: React.FC<ToolTestDialogProps> = ({ tool, onClose }) => {
  const [inputs, setInputs] = useState('{}');
  const [context, setContext] = useState('{}');
  const [response, setResponse] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleExecuteTest = async () => {
    setLoading(true);
    setError(null);
    setResponse(null);
    try {
      const parsedInputs = JSON.parse(inputs);
      const parsedContext = JSON.parse(context);
      const result = await executeTool(tool.id, parsedInputs, parsedContext, tool.timeout_seconds);
      setResponse(result);
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <DialogTitle>Test Tool: {tool.name}</DialogTitle>
      <DialogContent>
        <TextField
          margin="dense"
          label="Inputs (JSON)"
          fullWidth
          multiline
          rows={6}
          value={inputs}
          onChange={(e) => setInputs(e.target.value)}
          sx={{ mb: 2 }}
        />
        <TextField
          margin="dense"
          label="Context (JSON - Optional)"
          fullWidth
          multiline
          rows={4}
          value={context}
          onChange={(e) => setContext(e.target.value)}
          sx={{ mb: 2 }}
        />
        <Button
          variant="contained"
          onClick={handleExecuteTest}
          disabled={loading}
          startIcon={loading ? <CircularProgress size={20} /> : <PlayArrowIcon />}
          sx={{ mb: 2 }}
        >
          Execute Test
        </Button>

        {loading && <CircularProgress size={24} sx={{ mt: 2 }} />}

        {error && (
          <Box sx={{ mt: 2, p: 2, bgcolor: '#f4433620', color: '#f44336', borderRadius: 1 }}>
            <Typography variant="h6">Error:</Typography>
            <Typography sx={{ whiteSpace: 'pre-wrap' }}>{error}</Typography>
          </Box>
        )}

        {response && (
          <Box sx={{ mt: 2, p: 2, border: '1px solid #4ec9b0', borderRadius: 1, bgcolor: '#4ec9b020' }}>
            <Typography variant="h6" sx={{ color: '#4ec9b0' }}>Response:</Typography>
            <Typography sx={{ whiteSpace: 'pre-wrap', color: '#cccccc' }}>{JSON.stringify(response, null, 2)}</Typography>
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </>
  );
};

export default ToolsWorkspace