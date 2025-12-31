import React, { useState } from 'react'
import { 
  Box, 
  Typography, 
  IconButton, 
  Collapse, 
  List, 
  ListItem, 
  ListItemIcon, 
  ListItemText,
  ListItemButton,
} from '@mui/material'
import {
  ExpandMore as ExpandMoreIcon,
  ChevronRight as ChevronRightIcon,
  Build as ToolIcon,
  Add as AddIcon,
  Folder as FolderIcon,
  FolderOpen as FolderOpenIcon,
  Extension as ExtensionIcon,
  Code as CodeIcon,
} from '@mui/icons-material'

const ToolsExplorer: React.FC = () => {
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set(['custom-tools']))

  const toggleFolder = (folderId: string) => {
    const newExpanded = new Set(expandedFolders)
    if (newExpanded.has(folderId)) {
      newExpanded.delete(folderId)
    } else {
      newExpanded.add(folderId)
    }
    setExpandedFolders(newExpanded)
  }

  const mockCustomTools = [
    { id: '1', name: 'Email Sender', type: 'python', status: 'active' },
    { id: '2', name: 'Database Query', type: 'sql', status: 'active' },
    { id: '3', name: 'File Processor', type: 'python', status: 'inactive' },
  ]

  const mockMCPServers = [
    { id: '1', name: 'GitHub Integration', status: 'connected', tools: 5 },
    { id: '2', name: 'Slack Bot', status: 'connected', tools: 3 },
    { id: '3', name: 'Weather API', status: 'disconnected', tools: 2 },
  ]

  return (
    <Box sx={{ p: 1 }}>
      {/* Custom Tools folder */}
      <ListItem
        disablePadding
        sx={{
          '&:hover': {
            backgroundColor: '#2a2d2e',
          },
        }}
      >
        <ListItemButton
          onClick={() => toggleFolder('custom-tools')}
          sx={{
            py: 0.5,
            px: 1,
            minHeight: 'auto',
          }}
        >
          <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
            {expandedFolders.has('custom-tools') ? (
              <ExpandMoreIcon sx={{ fontSize: 16, color: '#cccccc' }} />
            ) : (
              <ChevronRightIcon sx={{ fontSize: 16, color: '#cccccc' }} />
            )}
          </ListItemIcon>
          <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
            {expandedFolders.has('custom-tools') ? (
              <FolderOpenIcon sx={{ fontSize: 16, color: '#dcb67a' }} />
            ) : (
              <FolderIcon sx={{ fontSize: 16, color: '#dcb67a' }} />
            )}
          </ListItemIcon>
          <ListItemText
            primary="Custom Tools"
            primaryTypographyProps={{
              fontSize: '13px',
              color: '#cccccc',
            }}
          />
          <IconButton
            size="small"
            sx={{
              color: '#cccccc',
              opacity: 0.7,
              '&:hover': {
                opacity: 1,
                backgroundColor: '#2a2d2e',
              },
            }}
          >
            <AddIcon sx={{ fontSize: 14 }} />
          </IconButton>
        </ListItemButton>
      </ListItem>

      {/* Custom Tools list */}
      <Collapse in={expandedFolders.has('custom-tools')}>
        <List sx={{ pl: 2 }}>
          {mockCustomTools.map((tool) => (
            <ListItem
              key={tool.id}
              disablePadding
              sx={{
                '&:hover': {
                  backgroundColor: '#2a2d2e',
                },
              }}
            >
              <ListItemButton
                sx={{
                  py: 0.5,
                  px: 1,
                  minHeight: 'auto',
                }}
              >
                <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
                  <CodeIcon 
                    sx={{ 
                      fontSize: 16, 
                      color: tool.status === 'active' ? '#4ec9b0' : '#969696' 
                    }} 
                  />
                </ListItemIcon>
                <ListItemText
                  primary={tool.name}
                  secondary={tool.type}
                  primaryTypographyProps={{
                    fontSize: '13px',
                    color: '#cccccc',
                  }}
                  secondaryTypographyProps={{
                    fontSize: '11px',
                    color: '#969696',
                  }}
                />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      </Collapse>

      {/* MCP Servers folder */}
      <ListItem
        disablePadding
        sx={{
          '&:hover': {
            backgroundColor: '#2a2d2e',
          },
        }}
      >
        <ListItemButton
          onClick={() => toggleFolder('mcp-servers')}
          sx={{
            py: 0.5,
            px: 1,
            minHeight: 'auto',
          }}
        >
          <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
            {expandedFolders.has('mcp-servers') ? (
              <ExpandMoreIcon sx={{ fontSize: 16, color: '#cccccc' }} />
            ) : (
              <ChevronRightIcon sx={{ fontSize: 16, color: '#cccccc' }} />
            )}
          </ListItemIcon>
          <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
            {expandedFolders.has('mcp-servers') ? (
              <FolderOpenIcon sx={{ fontSize: 16, color: '#dcb67a' }} />
            ) : (
              <FolderIcon sx={{ fontSize: 16, color: '#dcb67a' }} />
            )}
          </ListItemIcon>
          <ListItemText
            primary="MCP Servers"
            primaryTypographyProps={{
              fontSize: '13px',
              color: '#cccccc',
            }}
          />
          <IconButton
            size="small"
            sx={{
              color: '#cccccc',
              opacity: 0.7,
              '&:hover': {
                opacity: 1,
                backgroundColor: '#2a2d2e',
              },
            }}
          >
            <AddIcon sx={{ fontSize: 14 }} />
          </IconButton>
        </ListItemButton>
      </ListItem>

      {/* MCP Servers list */}
      <Collapse in={expandedFolders.has('mcp-servers')}>
        <List sx={{ pl: 2 }}>
          {mockMCPServers.map((server) => (
            <ListItem
              key={server.id}
              disablePadding
              sx={{
                '&:hover': {
                  backgroundColor: '#2a2d2e',
                },
              }}
            >
              <ListItemButton
                sx={{
                  py: 0.5,
                  px: 1,
                  minHeight: 'auto',
                }}
              >
                <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
                  <ExtensionIcon 
                    sx={{ 
                      fontSize: 16, 
                      color: server.status === 'connected' ? '#4ec9b0' : '#f48771' 
                    }} 
                  />
                </ListItemIcon>
                <ListItemText
                  primary={server.name}
                  secondary={`${server.tools} tools • ${server.status}`}
                  primaryTypographyProps={{
                    fontSize: '13px',
                    color: '#cccccc',
                  }}
                  secondaryTypographyProps={{
                    fontSize: '11px',
                    color: '#969696',
                  }}
                />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      </Collapse>

      {/* Tool Registry folder */}
      <ListItem
        disablePadding
        sx={{
          '&:hover': {
            backgroundColor: '#2a2d2e',
          },
        }}
      >
        <ListItemButton
          onClick={() => toggleFolder('registry')}
          sx={{
            py: 0.5,
            px: 1,
            minHeight: 'auto',
          }}
        >
          <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
            {expandedFolders.has('registry') ? (
              <ExpandMoreIcon sx={{ fontSize: 16, color: '#cccccc' }} />
            ) : (
              <ChevronRightIcon sx={{ fontSize: 16, color: '#cccccc' }} />
            )}
          </ListItemIcon>
          <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
            {expandedFolders.has('registry') ? (
              <FolderOpenIcon sx={{ fontSize: 16, color: '#dcb67a' }} />
            ) : (
              <FolderIcon sx={{ fontSize: 16, color: '#dcb67a' }} />
            )}
          </ListItemIcon>
          <ListItemText
            primary="Tool Registry"
            primaryTypographyProps={{
              fontSize: '13px',
              color: '#cccccc',
            }}
          />
        </ListItemButton>
      </ListItem>

      {/* Registry list */}
      <Collapse in={expandedFolders.has('registry')}>
        <List sx={{ pl: 2 }}>
          {['Web Scraper', 'PDF Generator', 'Image Processor', 'API Client'].map((tool) => (
            <ListItem
              key={tool}
              disablePadding
              sx={{
                '&:hover': {
                  backgroundColor: '#2a2d2e',
                },
              }}
            >
              <ListItemButton
                sx={{
                  py: 0.5,
                  px: 1,
                  minHeight: 'auto',
                }}
              >
                <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
                  <ToolIcon sx={{ fontSize: 16, color: '#569cd6' }} />
                </ListItemIcon>
                <ListItemText
                  primary={tool}
                  primaryTypographyProps={{
                    fontSize: '13px',
                    color: '#cccccc',
                  }}
                />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      </Collapse>
    </Box>
  )
}

export default ToolsExplorer