import React from 'react'
import { Box, Typography, Button, Card, CardContent, Grid } from '@mui/material'
import { Add as AddIcon, SmartToy as AgentIcon } from '@mui/icons-material'

const AgentWorkspace: React.FC = () => {
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

      {/* Quick Start Section */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h6" sx={{ color: '#cccccc', mb: 2 }}>
          Quick Start
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
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
                  <AgentIcon sx={{ color: '#4ec9b0', mr: 1 }} />
                  <Typography variant="h6" sx={{ color: '#cccccc' }}>
                    Chatbot Template
                  </Typography>
                </Box>
                <Typography variant="body2" sx={{ color: '#969696' }}>
                  Create a conversational AI agent with built-in guardrails and memory
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} md={4}>
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
                  <AgentIcon sx={{ color: '#569cd6', mr: 1 }} />
                  <Typography variant="h6" sx={{ color: '#cccccc' }}>
                    Content Generator
                  </Typography>
                </Box>
                <Typography variant="body2" sx={{ color: '#969696' }}>
                  Generate high-quality content with customizable templates and styles
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} md={4}>
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
                  <AgentIcon sx={{ color: '#ffcc02', mr: 1 }} />
                  <Typography variant="h6" sx={{ color: '#cccccc' }}>
                    Data Analyzer
                  </Typography>
                </Box>
                <Typography variant="body2" sx={{ color: '#969696' }}>
                  Analyze and process data with intelligent insights and reporting
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>

      {/* Recent Agents */}
      <Box>
        <Typography variant="h6" sx={{ color: '#cccccc', mb: 2 }}>
          Recent Agents
        </Typography>
        <Grid container spacing={2}>
          {[
            { name: 'Customer Support Bot', type: 'Chatbot', status: 'Active', lastUsed: '2 hours ago' },
            { name: 'Content Generator', type: 'Content Generation', status: 'Inactive', lastUsed: '1 day ago' },
            { name: 'Data Analyzer', type: 'Data Analysis', status: 'Active', lastUsed: '30 minutes ago' },
          ].map((agent, index) => (
            <Grid item xs={12} md={6} lg={4} key={index}>
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
                      {agent.name}
                    </Typography>
                    <Box
                      sx={{
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        backgroundColor: agent.status === 'Active' ? '#4ec9b0' : '#969696',
                      }}
                    />
                  </Box>
                  <Typography variant="body2" sx={{ color: '#969696', mb: 1 }}>
                    {agent.type}
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#969696' }}>
                    Last used: {agent.lastUsed}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Box>
    </Box>
  )
}

export default AgentWorkspace