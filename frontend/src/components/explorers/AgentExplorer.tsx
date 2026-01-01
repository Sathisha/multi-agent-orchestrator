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
  SmartToy as AgentIcon,
  Add as AddIcon,
  Folder as FolderIcon,
  FolderOpen as FolderOpenIcon,
  Psychology,
  AutoGraph,
  Bolt,
  Description
} from '@mui/icons-material'
import { useQuery } from 'react-query'
import { getAgents, Agent } from '../../api/agents'
import { useNavigate, useParams } from 'react-router-dom'

const AgentExplorer: React.FC = () => {
  const navigate = useNavigate()
  const { agentId: currentAgentId } = useParams<{ agentId: string }>()
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set(['agents']))

  const { data: agents, isLoading } = useQuery('agents', getAgents)

  const toggleFolder = (folderId: string) => {
    const newExpanded = new Set(expandedFolders)
    if (newExpanded.has(folderId)) {
      newExpanded.delete(folderId)
    } else {
      newExpanded.add(folderId)
    }
    setExpandedFolders(newExpanded)
  }

  const getAgentIcon = (type: string, status: string) => {
    const color = status === 'active' ? '#4ec9b0' : '#969696'
    switch (type?.toUpperCase()) {
      case 'CONVERSATIONAL': return <Psychology sx={{ fontSize: 16, color }} />;
      case 'TASK': return <Bolt sx={{ fontSize: 16, color }} />;
      default: return <AgentIcon sx={{ fontSize: 16, color }} />;
    }
  }

  return (
    <Box sx={{ p: 1, userSelect: 'none' }}>
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
            primary="Registered Agents"
            primaryTypographyProps={{
              fontSize: '13px',
              color: '#cccccc',
              fontWeight: 600
            }}
          />
          <Tooltip title="Create New Agent">
            <IconButton
              size="small"
              onClick={(e) => { e.stopPropagation(); navigate('/agents') }}
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

      {/* Agent list */}
      <Collapse in={expandedFolders.has('agents')}>
        <List sx={{ pl: 0 }} disablePadding>
          {isLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 1 }}>
              <CircularProgress size={16} sx={{ color: '#444' }} />
            </Box>
          ) : agents && agents.length > 0 ? (
            agents.map((agent) => (
              <ListItem
                key={agent.id}
                disablePadding
                sx={{
                  backgroundColor: currentAgentId === agent.id ? '#37373d' : 'transparent',
                  '&:hover': {
                    backgroundColor: currentAgentId === agent.id ? '#37373d' : '#2a2d2e',
                  },
                }}
              >
                <ListItemButton
                  onClick={() => navigate(`/agents/${agent.id}`)}
                  sx={{
                    py: 0.5,
                    pl: 4,
                    minHeight: 'auto',
                    borderLeft: currentAgentId === agent.id ? '2px solid #007acc' : '2px solid transparent'
                  }}
                >
                  <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
                    {getAgentIcon(agent.type, agent.status)}
                  </ListItemIcon>
                  <ListItemText
                    primary={agent.name}
                    primaryTypographyProps={{
                      fontSize: '13px',
                      color: currentAgentId === agent.id ? '#ffffff' : '#cccccc',
                      noWrap: true
                    }}
                  />
                </ListItemButton>
              </ListItem>
            ))
          ) : (
            <Typography variant="caption" sx={{ pl: 6, py: 1, color: '#666', fontStyle: 'italic', display: 'block' }}>
              No agents yet
            </Typography>
          )}
        </List>
      </Collapse>

      {/* Templates folder - Visual only for now */}
      <ListItem
        disablePadding
        sx={{
          mt: 1,
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
            primary="Standard Templates"
            primaryTypographyProps={{
              fontSize: '13px',
              color: '#cccccc',
              fontWeight: 600
            }}
          />
        </ListItemButton>
      </ListItem>

      <Collapse in={expandedFolders.has('templates')}>
        <List sx={{ pl: 0 }} disablePadding>
          {['Customer Support', 'Content Writer', 'Data Analyst', 'Code Reviewer'].map((template) => (
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
                  pl: 4,
                  minHeight: 'auto',
                }}
              >
                <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
                  <Description sx={{ fontSize: 14, color: '#569cd6' }} />
                </ListItemIcon>
                <ListItemText
                  primary={template}
                  primaryTypographyProps={{
                    fontSize: '13px',
                    color: '#969696',
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