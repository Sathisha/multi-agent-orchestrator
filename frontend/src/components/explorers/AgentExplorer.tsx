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
  SmartToy as AgentIcon,
  Add as AddIcon,
  Folder as FolderIcon,
  FolderOpen as FolderOpenIcon,
} from '@mui/icons-material'

const AgentExplorer: React.FC = () => {
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set(['agents']))

  const toggleFolder = (folderId: string) => {
    const newExpanded = new Set(expandedFolders)
    if (newExpanded.has(folderId)) {
      newExpanded.delete(folderId)
    } else {
      newExpanded.add(folderId)
    }
    setExpandedFolders(newExpanded)
  }

  const mockAgents = [
    { id: '1', name: 'Customer Support Bot', type: 'chatbot', status: 'active' },
    { id: '2', name: 'Content Generator', type: 'content-generation', status: 'inactive' },
    { id: '3', name: 'Data Analyzer', type: 'data-analysis', status: 'active' },
  ]

  return (
    <Box sx={{ p: 1 }}>
      {/* Agents folder */}
      <ListItem
        disablePadding
        sx={{
          '&:hover': {
            backgroundColor: '#2a2d2e',
          },
        }}
      >
        <ListItemButton
          onClick={() => toggleFolder('agents')}
          sx={{
            py: 0.5,
            px: 1,
            minHeight: 'auto',
          }}
        >
          <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
            {expandedFolders.has('agents') ? (
              <ExpandMoreIcon sx={{ fontSize: 16, color: '#cccccc' }} />
            ) : (
              <ChevronRightIcon sx={{ fontSize: 16, color: '#cccccc' }} />
            )}
          </ListItemIcon>
          <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
            {expandedFolders.has('agents') ? (
              <FolderOpenIcon sx={{ fontSize: 16, color: '#dcb67a' }} />
            ) : (
              <FolderIcon sx={{ fontSize: 16, color: '#dcb67a' }} />
            )}
          </ListItemIcon>
          <ListItemText
            primary="Agents"
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

      {/* Agent list */}
      <Collapse in={expandedFolders.has('agents')}>
        <List sx={{ pl: 2 }}>
          {mockAgents.map((agent) => (
            <ListItem
              key={agent.id}
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
                  <AgentIcon 
                    sx={{ 
                      fontSize: 16, 
                      color: agent.status === 'active' ? '#4ec9b0' : '#969696' 
                    }} 
                  />
                </ListItemIcon>
                <ListItemText
                  primary={agent.name}
                  secondary={agent.type}
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

      {/* Templates folder */}
      <ListItem
        disablePadding
        sx={{
          '&:hover': {
            backgroundColor: '#2a2d2e',
          },
        }}
      >
        <ListItemButton
          onClick={() => toggleFolder('templates')}
          sx={{
            py: 0.5,
            px: 1,
            minHeight: 'auto',
          }}
        >
          <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
            {expandedFolders.has('templates') ? (
              <ExpandMoreIcon sx={{ fontSize: 16, color: '#cccccc' }} />
            ) : (
              <ChevronRightIcon sx={{ fontSize: 16, color: '#cccccc' }} />
            )}
          </ListItemIcon>
          <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
            {expandedFolders.has('templates') ? (
              <FolderOpenIcon sx={{ fontSize: 16, color: '#dcb67a' }} />
            ) : (
              <FolderIcon sx={{ fontSize: 16, color: '#dcb67a' }} />
            )}
          </ListItemIcon>
          <ListItemText
            primary="Templates"
            primaryTypographyProps={{
              fontSize: '13px',
              color: '#cccccc',
            }}
          />
        </ListItemButton>
      </ListItem>

      {/* Template list */}
      <Collapse in={expandedFolders.has('templates')}>
        <List sx={{ pl: 2 }}>
          {['Chatbot', 'Content Generation', 'Data Analysis'].map((template) => (
            <ListItem
              key={template}
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
                  <AgentIcon sx={{ fontSize: 16, color: '#569cd6' }} />
                </ListItemIcon>
                <ListItemText
                  primary={template}
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

export default AgentExplorer