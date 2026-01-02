import React, { useState, useEffect } from 'react'
import { Box, Typography, Card, CardContent, Grid, LinearProgress, Chip, CircularProgress } from '@mui/material'
import { 
  Timeline as MetricsIcon,
  BugReport as LogsIcon,
  Security as AuditIcon,
  Speed as PerformanceIcon,
  Memory as MemoryIcon,
  Storage as StorageIcon,
  CheckCircle as HealthyIcon,
  Warning as WarningIcon,
  Error as ErrorIcon
} from '@mui/icons-material'
import { useQuery } from 'react-query'
import { getHealthStatus, getPerformanceSummary, getAlerts } from '../api/monitoring'
import { getAgents } from '../api/agents'

const MonitoringWorkspace: React.FC = () => {
  // Poll data every 30 seconds
  const { data: health, isLoading: healthLoading } = useQuery('health-status', getHealthStatus, {
    refetchInterval: 30000
  })
  const { data: performance, isLoading: perfLoading } = useQuery('performance-summary', getPerformanceSummary, {
    refetchInterval: 30000
  })
  const { data: alertsData } = useQuery('active-alerts', getAlerts, {
    refetchInterval: 30000
  })
  const { data: agents } = useQuery('agents', getAgents)

  const systemResources = health?.health_checks?.system_resources?.details || {}
  
  const systemMetrics = [
    { name: 'CPU Usage', value: systemResources.cpu_percent || 0, unit: '%', status: getMetricStatus(systemResources.cpu_percent || 0, 80), icon: PerformanceIcon },
    { name: 'Memory Usage', value: systemResources.memory_percent || 0, unit: '%', status: getMetricStatus(systemResources.memory_percent || 0, 85), icon: MemoryIcon },
    { name: 'Disk Usage', value: systemResources.disk_percent || 0, unit: '%', status: getMetricStatus(systemResources.disk_percent || 0, 90), icon: StorageIcon },
    { name: 'Active Agents', value: agents?.length || 0, unit: '', status: 'good', icon: MetricsIcon },
  ]

  function getMetricStatus(value: number, threshold: number) {
    if (value > threshold) return 'error'
    if (value > threshold * 0.8) return 'warning'
    return 'good'
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'good':
      case 'healthy':
        return '#4ec9b0'
      case 'warning':
      case 'degraded':
        return '#ffcc02'
      case 'error':
      case 'unhealthy':
        return '#f48771'
      default:
        return '#969696'
    }
  }

  if (healthLoading || perfLoading) {
    return (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
            <CircularProgress />
        </Box>
    )
  }

  return (
    <Box sx={{ p: 3, height: '100%', overflow: 'auto' }}>
      {/* Header */}
      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Box>
            <Typography variant="h4" sx={{ color: '#cccccc', mb: 1 }}>
            System Monitoring
            </Typography>
            <Typography variant="body2" sx={{ color: '#969696' }}>
            Monitor system health, performance, and agent activities
            </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <Box sx={{ textAlign: 'right', mr: 2 }}>
                <Typography variant="caption" sx={{ color: '#969696', display: 'block' }}>
                    Overall Status
                </Typography>
                <Typography variant="subtitle2" sx={{ color: getStatusColor(health?.overall_status || '') }}>
                    {(health?.overall_status || 'Unknown').toUpperCase()}
                </Typography>
            </Box>
            {health?.overall_status === 'healthy' ? (
                <HealthyIcon sx={{ color: '#4ec9b0', fontSize: 32 }} />
            ) : health?.overall_status === 'degraded' ? (
                <WarningIcon sx={{ color: '#ffcc02', fontSize: 32 }} />
            ) : (
                <ErrorIcon sx={{ color: '#f48771', fontSize: 32 }} />
            )}
        </Box>
      </Box>

      {/* System Health Overview */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h6" sx={{ color: '#cccccc', mb: 2 }}>
          System Health
        </Typography>
        <Grid container spacing={2}>
          {systemMetrics.map((metric, index) => {
            const Icon = metric.icon
            return (
              <Grid item xs={12} sm={6} md={3} key={index}>
                <Card
                  sx={{
                    backgroundColor: '#252526',
                    border: '1px solid #2d2d30',
                    '&:hover': {
                      backgroundColor: '#2a2d2e',
                    },
                  }}
                >
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                      <Icon sx={{ color: getStatusColor(metric.status), mr: 1 }} />
                      <Typography variant="subtitle2" sx={{ color: '#cccccc' }}>
                        {metric.name}
                      </Typography>
                    </Box>
                    <Typography variant="h4" sx={{ color: '#cccccc', mb: 1 }}>
                      {metric.value}{metric.unit}
                    </Typography>
                    {metric.unit === '%' && (
                      <LinearProgress
                        variant="determinate"
                        value={metric.value}
                        sx={{
                          height: 4,
                          borderRadius: 2,
                          backgroundColor: '#2d2d30',
                          '& .MuiLinearProgress-bar': {
                            backgroundColor: getStatusColor(metric.status),
                          },
                        }}
                      />
                    )}
                  </CardContent>
                </Card>
              </Grid>
            )
          })}
        </Grid>
      </Box>

      {/* Agent Activity */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h6" sx={{ color: '#cccccc', mb: 2 }}>
          Component Status
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} md={8}>
            <Card
              sx={{
                backgroundColor: '#252526',
                border: '1px solid #2d2d30',
                height: 300,
              }}
            >
              <CardContent>
                <Typography variant="subtitle1" sx={{ color: '#cccccc', mb: 2 }}>
                  Health Check Details
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                    {health && Object.entries(health.health_checks).map(([name, check]) => (
                        <Box key={name} sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: getStatusColor(check.status), mr: 2 }} />
                                <Typography variant="body2" sx={{ color: '#cccccc', textTransform: 'capitalize' }}>
                                    {name.replace('_', ' ')}
                                </Typography>
                            </Box>
                            <Box sx={{ textAlign: 'right' }}>
                                <Typography variant="caption" sx={{ color: '#969696', display: 'block' }}>
                                    {check.duration_ms.toFixed(1)}ms
                                </Typography>
                                <Chip label={check.status} size="small" sx={{ height: 16, fontSize: '9px', bgcolor: getStatusColor(check.status), color: '#000' }} />
                            </Box>
                        </Box>
                    ))}
                </Box>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} md={4}>
            <Card
              sx={{
                backgroundColor: '#252526',
                border: '1px solid #2d2d30',
                height: 300,
              }}
            >
              <CardContent>
                <Typography variant="subtitle1" sx={{ color: '#cccccc', mb: 2 }}>
                  Active Agents
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  {(agents || []).slice(0, 5).map((agent, index) => (
                    <Box key={index} sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <Box>
                        <Typography variant="body2" sx={{ color: '#cccccc' }}>
                          {agent.name}
                        </Typography>
                        <Typography variant="caption" sx={{ color: '#969696' }}>
                          Status: {agent.status}
                        </Typography>
                      </Box>
                      <Chip
                        label={agent.status}
                        size="small"
                        sx={{
                          backgroundColor: agent.status === 'active' ? '#4ec9b0' : '#969696',
                          color: '#000000',
                          fontSize: '10px',
                        }}
                      />
                    </Box>
                  ))}
                  {(!agents || agents.length === 0) && (
                      <Typography variant="body2" sx={{ color: '#969696', textAlign: 'center', mt: 4 }}>
                          No agents found
                      </Typography>
                  )}
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>

      {/* Performance Metrics */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h6" sx={{ color: '#cccccc', mb: 2 }}>
          Performance Metrics
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
            <Card
              sx={{
                backgroundColor: '#252526',
                border: '1px solid #2d2d30',
              }}
            >
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <PerformanceIcon sx={{ color: '#4ec9b0', mr: 1 }} />
                  <Typography variant="subtitle1" sx={{ color: '#cccccc' }}>
                    DB Query Time
                  </Typography>
                </Box>
                <Typography variant="h5" sx={{ color: '#cccccc', mb: 1 }}>
                  {(performance?.metrics?.database?.query_time_ms || 0).toFixed(1)}ms
                </Typography>
                <Typography variant="body2" sx={{ color: getStatusColor(getMetricStatus(performance?.metrics?.database?.query_time_ms || 0, 500)) }}>
                   {performance?.metrics?.database?.query_time_ms && performance.metrics.database.query_time_ms < 100 ? 'Excellent performance' : 'Normal latency'}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} md={4}>
            <Card
              sx={{
                backgroundColor: '#252526',
                border: '1px solid #2d2d30',
              }}
            >
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <MetricsIcon sx={{ color: '#569cd6', mr: 1 }} />
                  <Typography variant="subtitle1" sx={{ color: '#cccccc' }}>
                    DB Pool Utilization
                  </Typography>
                </Box>
                <Typography variant="h5" sx={{ color: '#cccccc', mb: 1 }}>
                  {performance?.metrics?.database?.active_connections || 0} / {performance?.metrics?.database?.pool_size || 0}
                </Typography>
                <Typography variant="body2" sx={{ color: '#969696' }}>
                   Active connections
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} md={4}>
            <Card
              sx={{
                backgroundColor: '#252526',
                border: '1px solid #2d2d30',
              }}
            >
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <LogsIcon sx={{ color: '#f48771', mr: 1 }} />
                  <Typography variant="subtitle1" sx={{ color: '#cccccc' }}>
                    Cache Latency
                  </Typography>
                </Box>
                <Typography variant="h5" sx={{ color: '#cccccc', mb: 1 }}>
                  {(performance?.metrics?.cache?.ping_time_ms || 0).toFixed(1)}ms
                </Typography>
                <Typography variant="body2" sx={{ color: '#4ec9b0' }}>
                   Redis responsive
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>

      {/* Recent Alerts */}
      <Box>
        <Typography variant="h6" sx={{ color: '#cccccc', mb: 2 }}>
          Active Alerts
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12}>
            <Card
              sx={{
                backgroundColor: '#252526',
                border: '1px solid #2d2d30',
                minHeight: 150,
              }}
            >
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <WarningIcon sx={{ color: '#ffcc02', mr: 1 }} />
                  <Typography variant="subtitle1" sx={{ color: '#cccccc' }}>
                    System Alerts ({alertsData?.count || 0})
                  </Typography>
                </Box>
                {alertsData?.alerts && alertsData.alerts.length > 0 ? (
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                    {alertsData.alerts.map((alert, index) => (
                        <Box key={index} sx={{ p: 1.5, bgcolor: '#1e1e1e', borderRadius: 1, borderLeft: `4px solid ${alert.severity === 'critical' ? '#f48771' : '#ffcc02'}` }}>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                                <Typography variant="subtitle2" sx={{ color: '#cccccc' }}>
                                    {alert.message}
                                </Typography>
                                <Typography variant="caption" sx={{ color: '#969696' }}>
                                    {new Date(alert.timestamp).toLocaleTimeString()}
                                </Typography>
                            </Box>
                            <Box sx={{ display: 'flex', gap: 1 }}>
                                <Chip label={alert.type} size="small" sx={{ height: 16, fontSize: '9px' }} />
                                <Chip label={alert.severity} size="small" sx={{ height: 16, fontSize: '9px', bgcolor: alert.severity === 'critical' ? '#f4877120' : '#ffcc0220', color: alert.severity === 'critical' ? '#f48771' : '#ffcc02' }} />
                            </Box>
                        </Box>
                    ))}
                    </Box>
                ) : (
                    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', py: 4 }}>
                        <HealthyIcon sx={{ color: '#4ec9b020', fontSize: 48, mb: 1 }} />
                        <Typography variant="body2" sx={{ color: '#969696' }}>
                            No active alerts. All systems operational.
                        </Typography>
                    </Box>
                )}
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>
    </Box>
  )
}

export default MonitoringWorkspace