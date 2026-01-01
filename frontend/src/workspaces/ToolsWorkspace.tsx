import React from 'react'
import { Box, Typography, Button, Card, CardContent, Grid, Chip } from '@mui/material'
import { 
  Add as AddIcon, 
  Code as CodeIcon,
  Extension as ExtensionIcon,
  CloudDownload as DownloadIcon
} from '@mui/icons-material'

const ToolsWorkspace: React.FC = () => {
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
                  Connect and configure Model Context Protocol servers
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
          Custom Tools
        </Typography>
        <Grid container spacing={2}>
          {[
            { 
              name: 'Email Sender', 
              type: 'Python', 
              status: 'Active', 
              description: 'Send emails via SMTP with templates',
              usageCount: 45
            },
            { 
              name: 'Database Query', 
              type: 'SQL', 
              status: 'Active', 
              description: 'Execute SQL queries with safety checks',
              usageCount: 23
            },
            { 
              name: 'File Processor', 
              type: 'Python', 
              status: 'Inactive', 
              description: 'Process and transform various file formats',
              usageCount: 12
            },
          ].map((tool, index) => (
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
                      {tool.name}
                    </Typography>
                    <Box
                      sx={{
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        backgroundColor: tool.status === 'Active' ? '#4ec9b0' : '#969696',
                      }}
                    />
                  </Box>
                  
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <Chip
                      label={tool.type}
                      size="small"
                      sx={{
                        height: 20,
                        fontSize: '10px',
                        backgroundColor: '#007acc',
                        color: '#ffffff',
                      }}
                    />
                    <Typography variant="caption" sx={{ color: '#969696' }}>
                      Used {tool.usageCount} times
                    </Typography>
                  </Box>
                  
                  <Typography variant="body2" sx={{ color: '#969696' }}>
                    {tool.description}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Box>

      {/* MCP Servers */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h6" sx={{ color: '#cccccc', mb: 2 }}>
          MCP Servers
        </Typography>
        <Grid container spacing={2}>
          {[
            { 
              name: 'GitHub Integration', 
              status: 'Connected', 
              tools: 5, 
              description: 'Access GitHub repositories and issues',
              version: 'v1.2.0'
            },
            { 
              name: 'Slack Bot', 
              status: 'Connected', 
              tools: 3, 
              description: 'Send messages and manage Slack channels',
              version: 'v2.1.1'
            },
            { 
              name: 'Weather API', 
              status: 'Disconnected', 
              tools: 2, 
              description: 'Get weather data and forecasts',
              version: 'v1.0.5'
            },
          ].map((server, index) => (
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
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="subtitle1" sx={{ color: '#cccccc' }}>
                      {server.name}
                    </Typography>
                    <Box
                      sx={{
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        backgroundColor: server.status === 'Connected' ? '#4ec9b0' : '#f48771',
                      }}
                    />
                  </Box>
                  
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <Chip
                      label={`${server.tools} tools`}
                      size="small"
                      sx={{
                        height: 20,
                        fontSize: '10px',
                        backgroundColor: '#4ec9b0',
                        color: '#000000',
                      }}
                    />
                    <Chip
                      label={server.version}
                      size="small"
                      sx={{
                        height: 20,
                        fontSize: '10px',
                        backgroundColor: '#969696',
                        color: '#ffffff',
                      }}
                    />
                  </Box>
                  
                  <Typography variant="body2" sx={{ color: '#969696', mb: 2 }}>
                    {server.description}
                  </Typography>
                  
                  <Typography 
                    variant="caption" 
                    sx={{ 
                      color: server.status === 'Connected' ? '#4ec9b0' : '#f48771',
                      fontWeight: 'bold'
                    }}
                  >
                    {server.status}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Box>

      {/* Tool Registry */}
      <Box>
        <Typography variant="h6" sx={{ color: '#cccccc', mb: 2 }}>
          Tool Registry
        </Typography>
        <Grid container spacing={2}>
          {[
            { name: 'Web Scraper', category: 'Data Collection', downloads: 1250 },
            { name: 'PDF Generator', category: 'Document Processing', downloads: 890 },
            { name: 'Image Processor', category: 'Media', downloads: 567 },
            { name: 'API Client', category: 'Integration', downloads: 2100 },
          ].map((tool, index) => (
            <Grid item xs={12} md={6} lg={3} key={index}>
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
                      {tool.name}
                    </Typography>
                    <DownloadIcon sx={{ color: '#569cd6', fontSize: 20 }} />
                  </Box>
                  <Typography variant="body2" sx={{ color: '#969696', mb: 1 }}>
                    {tool.category}
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#969696' }}>
                    {tool.downloads.toLocaleString()} downloads
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

export default ToolsWorkspace