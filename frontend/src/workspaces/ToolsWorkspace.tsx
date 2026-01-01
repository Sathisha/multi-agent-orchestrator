import React, { useState } from 'react'
import { Box, Typography, Button, Card, CardContent, Grid, Chip, Dialog, DialogTitle, DialogContent, DialogActions, TextField, CircularProgress, IconButton } from '@mui/material'
import {
  Add as AddIcon,
  Code as CodeIcon,
  Extension as ExtensionIcon,
  Delete as DeleteIcon
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { getTools, createTool, deleteTool, getToolTemplates } from '../api/tools'
import { useNavigate } from 'react-router-dom'

const ToolsWorkspace: React.FC = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [newToolName, setNewToolName] = useState('')
  const [newToolDesc, setNewToolDesc] = useState('')

  const { data: tools, isLoading } = useQuery('tools', getTools)
  const { data: templates } = useQuery('tool-templates', getToolTemplates)

  const createMutation = useMutation(createTool, {
    onSuccess: () => {
      queryClient.invalidateQueries('tools')
      setCreateDialogOpen(false)
      setNewToolName('')
      setNewToolDesc('')
    },
  })

  const deleteMutation = useMutation(deleteTool, {
    onSuccess: () => {
      queryClient.invalidateQueries('tools')
    }
  })

  const handleCreate = () => {
    // Use first template as default
    const defaultCode = templates?.[0]?.code || 'def execute(inputs, context=None):\\n    return {"result": "Hello World"}'
    createMutation.mutate({
      name: newToolName,
      description: newToolDesc,
      tool_type: 'custom',
      code: defaultCode
    })
  }

  const handleDelete = (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (window.confirm('Are you sure you want to delete this tool?')) {
      deleteMutation.mutate(id)
    }
  }

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
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)}>
        <DialogTitle>Create New Tool</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Name"
            fullWidth
            value={newToolName}
            onChange={(e) => setNewToolName(e.target.value)}
          />
          <TextField
            margin="dense"
            label="Description"
            fullWidth
            multiline
            rows={3}
            value={newToolDesc}
            onChange={(e) => setNewToolDesc(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleCreate} disabled={!newToolName || createMutation.isLoading}>Create</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default ToolsWorkspace