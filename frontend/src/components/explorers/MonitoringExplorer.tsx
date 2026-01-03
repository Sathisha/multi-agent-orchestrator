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
  Chip,
} from '@mui/material'
import {
  ExpandMore as ExpandMoreIcon,
  ChevronRight as ChevronRightIcon,
  Monitor as MonitoringIcon,
  Refresh as RefreshIcon,
  Folder as FolderIcon,
  FolderOpen as FolderOpenIcon,
  Timeline as MetricsIcon,
  BugReport as LogsIcon,
  Security as AuditIcon,
  Speed as PerformanceIcon,
} from '@mui/icons-material'
import { useQuery } from 'react-query'
import { getDashboardStats, getHealthStatus } from '../../api/monitoring'

const MonitoringExplorer: React.FC = () => {
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set(['system-health']))

  const { data: dashboardStats } = useQuery('dashboard-stats-explorer', getDashboardStats, {
    refetchInterval: 30000
  })

  // We can fetch basic health for the CPU/Memory stats if we want them in the explorer too
  const { data: health } = useQuery('health-status-explorer', getHealthStatus, {
    refetchInterval: 60000
  })

  const systemResources = health?.health_checks?.system_resources?.details || {}

  const toggleFolder = (folderId: string) => {
    const newExpanded = new Set(expandedFolders)
    if (newExpanded.has(folderId)) {
      newExpanded.delete(folderId)
    } else {
      newExpanded.add(folderId)
    }
    setExpandedFolders(newExpanded)
  }

  const systemMetrics = [
    { name: 'CPU Usage', value: `${(systemResources.cpu_percent || 0).toFixed(0)}%`, status: (systemResources.cpu_percent || 0) > 80 ? 'error' : 'good' },
    { name: 'Memory Usage', value: `${(systemResources.memory_percent || 0).toFixed(0)}%`, status: (systemResources.memory_percent || 0) > 85 ? 'warning' : 'good' },
    { name: 'Active Agents', value: `${dashboardStats?.agents?.active || 0}`, status: 'good' },
    { name: 'Workflows', value: `${dashboardStats?.workflows?.total || 0}`, status: 'good' },
  ]

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'good':
        return '#4ec9b0'
      case 'warning':
        return '#ffcc02'
      case 'error':
        return '#f48771'
      default:
        return '#969696'
    }
  }

  return (
    <Box sx={{ p: 1 }}>
      {/* System Health folder */}
      <ListItem
        disablePadding
        sx={{
          '&:hover': {
            backgroundColor: '#2a2d2e',
          },
        }}
      >
        <ListItemButton
          onClick={() => toggleFolder('system-health')}
          sx={{
            py: 0.5,
            px: 1,
            minHeight: 'auto',
          }}
        >
          <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
            {expandedFolders.has('system-health') ? (
              <ExpandMoreIcon sx={{ fontSize: 16, color: '#cccccc' }} />
            ) : (
              <ChevronRightIcon sx={{ fontSize: 16, color: '#cccccc' }} />
            )}
          </ListItemIcon>
          <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
            {expandedFolders.has('system-health') ? (
              <FolderOpenIcon sx={{ fontSize: 16, color: '#dcb67a' }} />
            ) : (
              <FolderIcon sx={{ fontSize: 16, color: '#dcb67a' }} />
            )}
          </ListItemIcon>
          <ListItemText
            primary="System Health"
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
            <RefreshIcon sx={{ fontSize: 14 }} />
          </IconButton>
        </ListItemButton>
      </ListItem>

      {/* System Health metrics */}
      <Collapse in={expandedFolders.has('system-health')}>
        <List sx={{ pl: 2 }}>
          {systemMetrics.map((metric) => (
            <ListItem
              key={metric.name}
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
                  <MetricsIcon
                    sx={{
                      fontSize: 16,
                      color: getStatusColor(metric.status)
                    }}
                  />
                </ListItemIcon>
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <Typography sx={{ fontSize: '13px', color: '#cccccc' }}>
                        {metric.name}
                      </Typography>
                      <Chip
                        label={metric.value}
                        size="small"
                        sx={{
                          height: 16,
                          fontSize: '10px',
                          backgroundColor: getStatusColor(metric.status),
                          color: '#000000',
                          '& .MuiChip-label': {
                            px: 0.5,
                          },
                        }}
                      />
                    </Box>
                  }
                />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      </Collapse>

      {/* Logs folder */}
      <ListItem
        disablePadding
        sx={{
          '&:hover': {
            backgroundColor: '#2a2d2e',
          },
        }}
      >
        <ListItemButton
          onClick={() => toggleFolder('logs')}
          sx={{
            py: 0.5,
            px: 1,
            minHeight: 'auto',
          }}
        >
          <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
            {expandedFolders.has('logs') ? (
              <ExpandMoreIcon sx={{ fontSize: 16, color: '#cccccc' }} />
            ) : (
              <ChevronRightIcon sx={{ fontSize: 16, color: '#cccccc' }} />
            )}
          </ListItemIcon>
          <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
            {expandedFolders.has('logs') ? (
              <FolderOpenIcon sx={{ fontSize: 16, color: '#dcb67a' }} />
            ) : (
              <FolderIcon sx={{ fontSize: 16, color: '#dcb67a' }} />
            )}
          </ListItemIcon>
          <ListItemText
            primary="Logs"
            primaryTypographyProps={{
              fontSize: '13px',
              color: '#cccccc',
            }}
          />
        </ListItemButton>
      </ListItem>

      {/* Logs list */}
      <Collapse in={expandedFolders.has('logs')}>
        <List sx={{ pl: 2 }}>
          {['Application Logs', 'Agent Execution', 'API Requests', 'Error Logs'].map((logType) => (
            <ListItem
              key={logType}
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
                  <LogsIcon sx={{ fontSize: 16, color: '#569cd6' }} />
                </ListItemIcon>
                <ListItemText
                  primary={logType}
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

      {/* Performance folder */}
      <ListItem
        disablePadding
        sx={{
          '&:hover': {
            backgroundColor: '#2a2d2e',
          },
        }}
      >
        <ListItemButton
          onClick={() => toggleFolder('performance')}
          sx={{
            py: 0.5,
            px: 1,
            minHeight: 'auto',
          }}
        >
          <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
            {expandedFolders.has('performance') ? (
              <ExpandMoreIcon sx={{ fontSize: 16, color: '#cccccc' }} />
            ) : (
              <ChevronRightIcon sx={{ fontSize: 16, color: '#cccccc' }} />
            )}
          </ListItemIcon>
          <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
            {expandedFolders.has('performance') ? (
              <FolderOpenIcon sx={{ fontSize: 16, color: '#dcb67a' }} />
            ) : (
              <FolderIcon sx={{ fontSize: 16, color: '#dcb67a' }} />
            )}
          </ListItemIcon>
          <ListItemText
            primary="Performance"
            primaryTypographyProps={{
              fontSize: '13px',
              color: '#cccccc',
            }}
          />
        </ListItemButton>
      </ListItem>

      {/* Performance list */}
      <Collapse in={expandedFolders.has('performance')}>
        <List sx={{ pl: 2 }}>
          {['Response Times', 'Throughput', 'Resource Usage', 'Database Queries'].map((metric) => (
            <ListItem
              key={metric}
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
                  <PerformanceIcon sx={{ fontSize: 16, color: '#4ec9b0' }} />
                </ListItemIcon>
                <ListItemText
                  primary={metric}
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

      {/* Audit Trail folder */}
      <ListItem
        disablePadding
        sx={{
          '&:hover': {
            backgroundColor: '#2a2d2e',
          },
        }}
      >
        <ListItemButton
          onClick={() => toggleFolder('audit')}
          sx={{
            py: 0.5,
            px: 1,
            minHeight: 'auto',
          }}
        >
          <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
            {expandedFolders.has('audit') ? (
              <ExpandMoreIcon sx={{ fontSize: 16, color: '#cccccc' }} />
            ) : (
              <ChevronRightIcon sx={{ fontSize: 16, color: '#cccccc' }} />
            )}
          </ListItemIcon>
          <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
            {expandedFolders.has('audit') ? (
              <FolderOpenIcon sx={{ fontSize: 16, color: '#dcb67a' }} />
            ) : (
              <FolderIcon sx={{ fontSize: 16, color: '#dcb67a' }} />
            )}
          </ListItemIcon>
          <ListItemText
            primary="Audit Trail"
            primaryTypographyProps={{
              fontSize: '13px',
              color: '#cccccc',
            }}
          />
        </ListItemButton>
      </ListItem>

      {/* Audit list */}
      <Collapse in={expandedFolders.has('audit')}>
        <List sx={{ pl: 2 }}>
          {['User Actions', 'Agent Operations', 'System Changes', 'Security Events'].map((auditType) => (
            <ListItem
              key={auditType}
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
                  <AuditIcon sx={{ fontSize: 16, color: '#ffcc02' }} />
                </ListItemIcon>
                <ListItemText
                  primary={auditType}
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

export default MonitoringExplorer