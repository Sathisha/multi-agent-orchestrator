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
  AccountTree as WorkflowIcon,
  Add as AddIcon,
  Folder as FolderIcon,
  FolderOpen as FolderOpenIcon,
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
} from '@mui/icons-material'

const WorkflowExplorer: React.FC = () => {
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set(['workflows']))

  const toggleFolder = (folderId: string) => {
    const newExpanded = new Set(expandedFolders)
    if (newExpanded.has(folderId)) {
      newExpanded.delete(folderId)
    } else {
      newExpanded.add(folderId)
    }
    setExpandedFolders(newExpanded)
  }

  const mockWorkflows = [
    { id: '1', name: 'Customer Onboarding', status: 'running', agents: 3 },
    { id: '2', name: 'Content Review Pipeline', status: 'paused', agents: 2 },
    { id: '3', name: 'Data Processing Flow', status: 'stopped', agents: 4 },
  ]

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <PlayIcon sx={{ fontSize: 12, color: '#4ec9b0' }} />
      case 'paused':
        return <PauseIcon sx={{ fontSize: 12, color: '#ffcc02' }} />
      default:
        return null
    }
  }

  return (
    <Box sx={{ p: 1 }}>
      {/* Workflows folder */}
      <ListItem
        disablePadding
        sx={{
          '&:hover': {
            backgroundColor: '#2a2d2e',
          },
        }}
      >
        <ListItemButton
          onClick={() => toggleFolder('workflows')}
          sx={{
            py: 0.5,
            px: 1,
            minHeight: 'auto',
          }}
        >
          <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
            {expandedFolders.has('workflows') ? (
              <ExpandMoreIcon sx={{ fontSize: 16, color: '#cccccc' }} />
            ) : (
              <ChevronRightIcon sx={{ fontSize: 16, color: '#cccccc' }} />
            )}
          </ListItemIcon>
          <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
            {expandedFolders.has('workflows') ? (
              <FolderOpenIcon sx={{ fontSize: 16, color: '#dcb67a' }} />
            ) : (
              <FolderIcon sx={{ fontSize: 16, color: '#dcb67a' }} />
            )}
          </ListItemIcon>
          <ListItemText
            primary="Workflows"
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

      {/* Workflow list */}
      <Collapse in={expandedFolders.has('workflows')}>
        <List sx={{ pl: 2 }}>
          {mockWorkflows.map((workflow) => (
            <ListItem
              key={workflow.id}
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
                  <WorkflowIcon 
                    sx={{ 
                      fontSize: 16, 
                      color: workflow.status === 'running' ? '#4ec9b0' : '#969696' 
                    }} 
                  />
                </ListItemIcon>
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <Typography sx={{ fontSize: '13px', color: '#cccccc' }}>
                        {workflow.name}
                      </Typography>
                      {getStatusIcon(workflow.status)}
                    </Box>
                  }
                  secondary={`${workflow.agents} agents`}
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

      {/* BPMN Diagrams folder */}
      <ListItem
        disablePadding
        sx={{
          '&:hover': {
            backgroundColor: '#2a2d2e',
          },
        }}
      >
        <ListItemButton
          onClick={() => toggleFolder('bpmn')}
          sx={{
            py: 0.5,
            px: 1,
            minHeight: 'auto',
          }}
        >
          <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
            {expandedFolders.has('bpmn') ? (
              <ExpandMoreIcon sx={{ fontSize: 16, color: '#cccccc' }} />
            ) : (
              <ChevronRightIcon sx={{ fontSize: 16, color: '#cccccc' }} />
            )}
          </ListItemIcon>
          <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
            {expandedFolders.has('bpmn') ? (
              <FolderOpenIcon sx={{ fontSize: 16, color: '#dcb67a' }} />
            ) : (
              <FolderIcon sx={{ fontSize: 16, color: '#dcb67a' }} />
            )}
          </ListItemIcon>
          <ListItemText
            primary="BPMN Diagrams"
            primaryTypographyProps={{
              fontSize: '13px',
              color: '#cccccc',
            }}
          />
        </ListItemButton>
      </ListItem>

      {/* BPMN list */}
      <Collapse in={expandedFolders.has('bpmn')}>
        <List sx={{ pl: 2 }}>
          {['onboarding.bpmn', 'review-pipeline.bpmn', 'data-flow.bpmn'].map((file) => (
            <ListItem
              key={file}
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
                  <WorkflowIcon sx={{ fontSize: 16, color: '#569cd6' }} />
                </ListItemIcon>
                <ListItemText
                  primary={file}
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

export default WorkflowExplorer