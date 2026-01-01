import React, { useState } from 'react'
import { Box, Typography, Button, Card, CardContent, Grid, Dialog, DialogTitle, DialogContent, DialogActions, TextField, CircularProgress, IconButton, Menu, MenuItem } from '@mui/material'
import { Add as AddIcon, SmartToy as AgentIcon, MoreVert as MoreVertIcon, Delete as DeleteIcon } from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { getAgents, createAgent, deleteAgent, CreateAgentRequest } from '../api/agents'
import { useNavigate } from 'react-router-dom'

const AgentWorkspace: React.FC = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [newAgentName, setNewAgentName] = useState('')
  const [newAgentDesc, setNewAgentDesc] = useState('')

  const { data: agents, isLoading } = useQuery('agents', getAgents)

  const createMutation = useMutation(createAgent, {
    onSuccess: () => {
      queryClient.invalidateQueries('agents')
      setCreateDialogOpen(false)
      setNewAgentName('')
      setNewAgentDesc('')
    },
  })

  const deleteMutation = useMutation(deleteAgent, {
    onSuccess: () => {
      queryClient.invalidateQueries('agents')
    }
  })

  const handleCreate = () => {
    createMutation.mutate({
      name: newAgentName,
      description: newAgentDesc,
      type: 'conversational' // default
    })
  }

  const handleDelete = (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (window.confirm('Are you sure you want to delete this agent?')) {
      deleteMutation.mutate(id)
    }
  }

  return (
    <Box sx={{ p: 3, height: '100%', overflow: 'auto' }}>
      {/* Header */}
      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Box>
          <Typography variant="h4" sx={{ color: '#cccccc', mb: 1 }}>
            AI Agents
          </Typography>
          <Typography variant="body2" sx={{ color: '#969696' }}>
            Create, configure, and manage your AI agents
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
          Create Agent
        </Button>
      </Box>

      {/* Main Content */}
      <Box>
        <Typography variant="h6" sx={{ color: '#cccccc', mb: 2 }}>
          Your Agents
        </Typography>

        {isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          <Grid container spacing={2}>
            {agents?.map((agent) => (
              <Grid item xs={12} md={6} lg={4} key={agent.id}>
                <Card
                  sx={{
                    backgroundColor: '#252526',
                    border: '1px solid #2d2d30',
                    cursor: 'pointer',
                    '&:hover': {
                      backgroundColor: '#2a2d2e',
                      borderColor: '#007acc',
                    },
                    position: 'relative'
                  }}
                  onClick={() => navigate(`/agents/${agent.id}`)} // Navigate to detail
                >
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                      <Typography variant="subtitle1" sx={{ color: '#cccccc' }}>
                        {agent.name}
                      </Typography>
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <Box
                          sx={{
                            width: 8,
                            height: 8,
                            borderRadius: '50%',
                            backgroundColor: agent.status === 'active' ? '#4ec9b0' : '#969696',
                            mr: 1
                          }}
                        />
                        <IconButton size="small" onClick={(e) => handleDelete(agent.id, e)}>
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Box>
                    </Box>
                    <Typography variant="body2" sx={{ color: '#969696', mb: 1, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                      {agent.description || 'No description'}
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#969696' }}>
                      Type: {agent.type}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
            {agents?.length === 0 && (
              <Typography sx={{ color: 'text.secondary', mt: 2, ml: 2 }}>No agents found. Create one to get started.</Typography>
            )}
          </Grid>
        )}
      </Box>

      {/* Create Dialog */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)}>
        <DialogTitle>Create New Agent</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Name"
            fullWidth
            value={newAgentName}
            onChange={(e) => setNewAgentName(e.target.value)}
          />
          <TextField
            margin="dense"
            label="Description"
            fullWidth
            multiline
            rows={3}
            value={newAgentDesc}
            onChange={(e) => setNewAgentDesc(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleCreate} disabled={!newAgentName || createMutation.isLoading}>Create</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default AgentWorkspace