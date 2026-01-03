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
  CircularProgress,
  Tooltip,
} from '@mui/material'
import {
  ExpandMore as ExpandMoreIcon,
  ChevronRight as ChevronRightIcon,
  AccountTree as WorkflowIcon,
  Add as AddIcon,
  Folder as FolderIcon,
  FolderOpen as FolderOpenIcon,
} from '@mui/icons-material'
import { useQuery } from 'react-query'
import { getWorkflows, WorkflowResponse } from '../../api/workflows'
import { useNavigate, useParams } from 'react-router-dom'

const WorkflowExplorer: React.FC = () => {
  const navigate = useNavigate()
  const { workflowId: currentWorkflowId } = useParams<{ workflowId: string }>()
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set(['workflows']))

  const { data: workflows, isLoading } = useQuery('workflows', getWorkflows)

  const toggleFolder = (folderId: string) => {
    const newExpanded = new Set(expandedFolders)
    if (newExpanded.has(folderId)) {
      newExpanded.delete(folderId)
    } else {
      newExpanded.add(folderId)
    }
    setExpandedFolders(newExpanded)
  }

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'active':
        return '#4ec9b0'
      case 'draft':
        return '#969696'
      default:
        return '#969696'
    }
  }

  return (
    <Box sx={{ p: 1, userSelect: 'none' }}>
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
              fontWeight: 600
            }}
          />
          <Tooltip title="Create New Workflow">
            <IconButton
              size="small"
              onClick={(e) => { e.stopPropagation(); navigate('/chains') }}
              sx={{
                color: '#cccccc',
                opacity: 0.7,
                '&:hover': {
                  opacity: 1,
                  backgroundColor: '#37373d',
                },
              }}
            >
              <AddIcon sx={{ fontSize: 14 }} />
            </IconButton>
          </Tooltip>
        </ListItemButton>
      </ListItem>

      {/* Workflow list */}
      <Collapse in={expandedFolders.has('workflows')}>
        <List sx={{ pl: 0 }} disablePadding>
          {isLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 1 }}>
              <CircularProgress size={16} sx={{ color: '#444' }} />
            </Box>
          ) : workflows && workflows.length > 0 ? (
            workflows.map((workflow) => (
              <ListItem
                key={workflow.id}
                disablePadding
                sx={{
                  backgroundColor: currentWorkflowId === workflow.id ? '#37373d' : 'transparent',
                  '&:hover': {
                    backgroundColor: currentWorkflowId === workflow.id ? '#37373d' : '#2a2d2e',
                  },
                }}
              >
                <ListItemButton
                  onClick={() => navigate(`/chains/${workflow.id}`)}
                  sx={{
                    py: 0.5,
                    pl: 4,
                    minHeight: 'auto',
                    borderLeft: currentWorkflowId === workflow.id ? '2px solid #007acc' : '2px solid transparent'
                  }}
                >
                  <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
                    <WorkflowIcon
                      sx={{
                        fontSize: 16,
                        color: getStatusColor(workflow.status)
                      }}
                    />
                  </ListItemIcon>
                  <ListItemText
                    primary={workflow.name}
                    primaryTypographyProps={{
                      fontSize: '13px',
                      color: currentWorkflowId === workflow.id ? '#ffffff' : '#cccccc',
                      noWrap: true
                    }}
                  />
                </ListItemButton>
              </ListItem>
            ))
          ) : (
            <Typography variant="caption" sx={{ pl: 6, py: 1, color: '#666', fontStyle: 'italic', display: 'block' }}>
              No workflows yet
            </Typography>
          )}
        </List>
      </Collapse>
    </Box>
  )
}

export default WorkflowExplorer