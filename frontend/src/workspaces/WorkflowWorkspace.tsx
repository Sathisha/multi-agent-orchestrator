import React from 'react'
import { Box, Typography, Button, Card, CardContent, Grid } from '@mui/material'
import { Add as AddIcon, AccountTree as WorkflowIcon, PlayArrow as PlayIcon } from '@mui/icons-material'

const WorkflowWorkspace: React.FC = () => {
  return (
    <Box sx={{ p: 3, height: '100%', overflow: 'auto' }}>
      {/* Header */}
      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Box>
          <Typography variant="h4" sx={{ color: '#cccccc', mb: 1 }}>
            Workflows
          </Typography>
          <Typography variant="body2" sx={{ color: '#969696' }}>
            Design and orchestrate multi-agent workflows using BPMN
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
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

      {/* BPMN Designer Section */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h6" sx={{ color: '#cccccc', mb: 2 }}>
          BPMN Designer
        </Typography>
        <Card
          sx={{
            backgroundColor: '#252526',
            border: '1px solid #2d2d30',
            minHeight: 300,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            '&:hover': {
              backgroundColor: '#2a2d2e',
              borderColor: '#007acc',
            },
          }}
        >
          <CardContent sx={{ textAlign: 'center' }}>
            <WorkflowIcon sx={{ fontSize: 64, color: '#569cd6', mb: 2 }} />
            <Typography variant="h6" sx={{ color: '#cccccc', mb: 1 }}>
              Visual Workflow Designer
            </Typography>
            <Typography variant="body2" sx={{ color: '#969696', mb: 2 }}>
              Drag and drop agents to create complex workflows
            </Typography>
            <Button
              variant="outlined"
              sx={{
                borderColor: '#007acc',
                color: '#007acc',
                '&:hover': {
                  borderColor: '#005a9e',
                  backgroundColor: 'rgba(0, 122, 204, 0.1)',
                },
              }}
            >
              Open Designer
            </Button>
          </CardContent>
        </Card>
      </Box>

      {/* Active Workflows */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h6" sx={{ color: '#cccccc', mb: 2 }}>
          Active Workflows
        </Typography>
        <Grid container spacing={2}>
          {[
            { 
              name: 'Customer Onboarding', 
              agents: 3, 
              status: 'Running', 
              progress: 75,
              executions: 12 
            },
            { 
              name: 'Content Review Pipeline', 
              agents: 2, 
              status: 'Paused', 
              progress: 45,
              executions: 8 
            },
          ].map((workflow, index) => (
            <Grid item xs={12} md={6} key={index}>
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
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                    <Typography variant="subtitle1" sx={{ color: '#cccccc' }}>
                      {workflow.name}
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Box
                        sx={{
                          width: 8,
                          height: 8,
                          borderRadius: '50%',
                          backgroundColor: workflow.status === 'Running' ? '#4ec9b0' : '#ffcc02',
                        }}
                      />
                      <Typography variant="caption" sx={{ color: '#969696' }}>
                        {workflow.status}
                      </Typography>
                    </Box>
                  </Box>
                  
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                    <Typography variant="body2" sx={{ color: '#969696' }}>
                      {workflow.agents} agents
                    </Typography>
                    <Typography variant="body2" sx={{ color: '#969696' }}>
                      {workflow.executions} executions
                    </Typography>
                  </Box>

                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Box
                      sx={{
                        flex: 1,
                        height: 4,
                        backgroundColor: '#2d2d30',
                        borderRadius: 2,
                        overflow: 'hidden',
                      }}
                    >
                      <Box
                        sx={{
                          width: `${workflow.progress}%`,
                          height: '100%',
                          backgroundColor: '#4ec9b0',
                        }}
                      />
                    </Box>
                    <Typography variant="caption" sx={{ color: '#969696' }}>
                      {workflow.progress}%
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Box>

      {/* Recent Workflows */}
      <Box>
        <Typography variant="h6" sx={{ color: '#cccccc', mb: 2 }}>
          Recent Workflows
        </Typography>
        <Grid container spacing={2}>
          {[
            { name: 'Data Processing Flow', agents: 4, lastRun: '2 hours ago', status: 'Completed' },
            { name: 'Email Campaign', agents: 2, lastRun: '1 day ago', status: 'Failed' },
            { name: 'Report Generation', agents: 3, lastRun: '3 days ago', status: 'Completed' },
          ].map((workflow, index) => (
            <Grid item xs={12} md={4} key={index}>
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
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="subtitle1" sx={{ color: '#cccccc' }}>
                      {workflow.name}
                    </Typography>
                    <PlayIcon sx={{ color: '#569cd6', fontSize: 20 }} />
                  </Box>
                  <Typography variant="body2" sx={{ color: '#969696', mb: 1 }}>
                    {workflow.agents} agents
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Typography variant="caption" sx={{ color: '#969696' }}>
                      {workflow.lastRun}
                    </Typography>
                    <Typography 
                      variant="caption" 
                      sx={{ 
                        color: workflow.status === 'Completed' ? '#4ec9b0' : '#f48771',
                        fontWeight: 'bold'
                      }}
                    >
                      {workflow.status}
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Box>
    </Box>
  )
}

export default WorkflowWorkspace