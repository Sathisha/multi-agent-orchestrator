import React, { useState } from 'react'
import { Box, Typography, Button, Card, CardContent, Grid, CircularProgress, Chip, Dialog, DialogTitle, DialogContent, DialogActions, TextField } from '@mui/material'
import { Add as AddIcon, AccountTree as WorkflowIcon, PlayArrow as PlayIcon } from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { getWorkflows, getExecutions, createWorkflow } from '../api/workflows'
import { useNavigate } from 'react-router-dom'

const WorkflowWorkspace: React.FC = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [newItemName, setNewItemName] = useState('')

  const { data: workflows, isLoading: loadingWorkflows } = useQuery('workflows', getWorkflows)
  const { data: executions, isLoading: loadingExecutions } = useQuery('executions', () => getExecutions(50))

  // Derived states
  const activeExecutions = executions?.filter(ex => ['running', 'pending'].includes(ex.status.toLowerCase())) || []
  const recentExecutions = executions?.slice(0, 6) || []

  const createMutation = useMutation(createWorkflow, {
    onSuccess: () => {
      queryClient.invalidateQueries('workflows')
      setCreateDialogOpen(false)
      setNewItemName('')
    }
  })

  const handleCreate = () => {
    // Simple XML placeholder
    const placeholderXML = `<?xml version="1.0" encoding="UTF-8"?><bpmn:definitions ...>`
    createMutation.mutate({
      name: newItemName,
      bpmn_xml: placeholderXML,
      description: "Created via Quick Start"
    })
  }

  return (
    <Box sx={{ p: 3, height: '100%', overflow: 'auto' }}>
      {/* Header */}
      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Box>
          <Typography variant="h4" sx={{ color: '#cccccc', mb: 1 }}>
            Workflows
          </Typography>
          <Typography variant="body2" sx={{ color: '#969696' }}>
            Design and orchestrate multi-agent workflows
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
          Create Workflow
        </Button>
      </Box>

      {/* BPMN Designer Section (Action Card) */}
      <Box sx={{ mb: 4 }}>
        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
            <Card sx={{ bgcolor: '#252526', border: '1px solid #2d2d30', height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', p: 3, cursor: 'pointer', '&:hover': { borderColor: '#007acc' } }}>
              <WorkflowIcon sx={{ fontSize: 48, color: '#569cd6', mb: 2 }} />
              <Typography variant="h6" color="#cccccc">BPMN Designer</Typography>
              <Typography variant="body2" color="#969696" align="center" sx={{ mb: 2 }}>Launch the visual workflow editor</Typography>
              <Button variant="outlined" onClick={() => alert("Designer integration coming soon")}>Open</Button>
            </Card>
          </Grid>
          {/* Stats Card */}
          <Grid item xs={12} md={8}>
            <Card sx={{ bgcolor: '#252526', border: '1px solid #2d2d30', height: '100%', p: 2 }}>
              <Typography variant="h6" color="#cccccc" gutterBottom>Overview</Typography>
              <Grid container spacing={2}>
                <Grid item xs={4}>
                  <Typography variant="h3" color="#4ec9b0">{workflows?.length || 0}</Typography>
                  <Typography variant="caption" color="#969696">Definitions</Typography>
                </Grid>
                <Grid item xs={4}>
                  <Typography variant="h3" color="#569cd6">{activeExecutions.length}</Typography>
                  <Typography variant="caption" color="#969696">Active Runs</Typography>
                </Grid>
                <Grid item xs={4}>
                  <Typography variant="h3" color="#ce9178">{executions?.length || 0}</Typography>
                  <Typography variant="caption" color="#969696">Total Runs</Typography>
                </Grid>
              </Grid>
            </Card>
          </Grid>
        </Grid>
      </Box>

      {/* Active Workflows (Running) */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h6" sx={{ color: '#cccccc', mb: 2 }}>
          Active Executions
        </Typography>
        {loadingExecutions ? <CircularProgress /> : (
          <Grid container spacing={2}>
            {activeExecutions.length === 0 ? <Typography sx={{ ml: 2, color: '#969696' }}>No active executions.</Typography> :
              activeExecutions.map((ex) => (
                <Grid item xs={12} md={6} key={ex.id}>
                  <Card sx={{ bgcolor: '#252526', border: '1px solid #2d2d30' }}>
                    <CardContent>
                      <Typography variant="subtitle1" color="#cccccc">{ex.workflow_name || 'Workflow'}</Typography>
                      <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                        <Chip label={ex.status} size="small" color={ex.status === 'running' ? 'success' : 'warning'} />
                        <Typography variant="caption" color="#969696">Started: {new Date(ex.started_at).toLocaleTimeString()}</Typography>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
          </Grid>
        )}
      </Box>

      {/* Recent Workflows (All Definitions) */}
      <Box>
        <Typography variant="h6" sx={{ color: '#cccccc', mb: 2 }}>
          Workflow Definitions
        </Typography>
        {loadingWorkflows ? <CircularProgress /> : (
          <Grid container spacing={2}>
            {workflows?.map((wf) => (
              <Grid item xs={12} md={4} key={wf.id}>
                <Card
                  sx={{ bgcolor: '#252526', border: '1px solid #2d2d30', cursor: 'pointer', '&:hover': { borderColor: '#007acc' } }}
                  onClick={() => navigate(`/workflows/${wf.id}`)}
                >
                  <CardContent>
                    <Typography variant="subtitle1" color="#cccccc">{wf.name}</Typography>
                    <Typography variant="body2" color="#969696" noWrap>{wf.description || 'No description'}</Typography>
                    <Box sx={{ mt: 2, display: 'flex', justifyContent: 'space-between' }}>
                      <Chip label={wf.status} size="small" variant="outlined" sx={{ color: '#969696', borderColor: '#4caf50' }} />
                      <Typography variant="caption" color="#969696">{wf.execution_count} runs</Typography>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        )}
      </Box>

      {/* Create Dialog */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)}>
        <DialogTitle>Create Workflow</DialogTitle>
        <DialogContent>
          <TextField autoFocus margin="dense" label="Name" fullWidth value={newItemName} onChange={(e) => setNewItemName(e.target.value)} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleCreate}>Create</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default WorkflowWorkspace