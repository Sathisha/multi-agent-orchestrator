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
  Error as ErrorIcon,
  Build as ToolsIcon,
  AccountTree as WorkflowIcon
} from '@mui/icons-material'
import { useQuery } from 'react-query'
import { getHealthStatus, getPerformanceSummary, getAlerts, getDashboardStats, getMetricsHistory } from '../api/monitoring'
import { getAgents } from '../api/agents'
import MetricChart from '../components/charts/MetricChart'

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
  const { data: dashboardStats } = useQuery('dashboard-stats', getDashboardStats, {
    refetchInterval: 30000
  })

  // History Metrics
  const { data: cpuHistory, isLoading: cpuLoading } = useQuery(
    ['metrics-history', 'cpu_usage'],
    () => getMetricsHistory('cpu_usage'),
    { refetchInterval: 60000 }
  )
  const { data: memHistory, isLoading: memLoading } = useQuery(
    ['metrics-history', 'memory_usage'],
    () => getMetricsHistory('memory_usage'),
    { refetchInterval: 60000 }
  )
  const { data: agentsHistory, isLoading: agentsLoading } = useQuery(
    ['metrics-history', 'active_agents'],
    () => getMetricsHistory('active_agents'),
    { refetchInterval: 60000 }
  )

  const systemResources = health?.health_checks?.system_resources?.details || {}

  const systemMetrics = [
    { name: 'CPU Usage', value: systemResources.cpu_percent || 0, unit: '%', status: getMetricStatus(systemResources.cpu_percent || 0, 80), icon: PerformanceIcon },
    { name: 'Memory Usage', value: systemResources.memory_percent || 0, unit: '%', status: getMetricStatus(systemResources.memory_percent || 0, 85), icon: MemoryIcon },
    { name: 'Disk Usage', value: systemResources.disk_percent || 0, unit: '%', status: getMetricStatus(systemResources.disk_percent || 0, 90), icon: StorageIcon },
    { name: 'Active Agents', value: dashboardStats?.agents?.active || 0, unit: '', status: 'good', icon: MetricsIcon },
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

      {/* Real-time Metrics */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h6" sx={{ color: '#cccccc', mb: 2 }}>
          Real-time Metrics
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
            <MetricChart
              title="CPU Usage"
              data={cpuHistory || []}
              color="#4ec9b0"
              unit="%"
              loading={cpuLoading}
            />
          </Grid>
          <Grid item xs={12} md={4}>
            <MetricChart
              title="Memory Usage"
              data={memHistory || []}
              color="#569cd6"
              unit="MB" // Using Memory Bytes converted to meaningful unit in chart or passing raw? Backend sends bytes usually. 
              // Wait, backend query for memory is 'process_resident_memory_bytes'. 
              // Let's assume bytes, but the chart formatter might need adjustment or we adjust here.
              // Actually for simplicity let's stick to the raw value or assume the backend sends % if we changed query. 
              // I used 'process_resident_memory_bytes' in backend. So unit is Bytes.
              // MetricChart might need better formatting for bytes, but let's stick to simple number for now or update MetricChart to handle bytes.
              // Re-reading backend: 'avg(rate(process_cpu_seconds_total[1m])) * 100' -> Percent.
              // 'process_resident_memory_bytes' -> Bytes.
              loading={memLoading}
            />
          </Grid>
          <Grid item xs={12} md={4}>
            <MetricChart
              title="Active Agents"
              data={agentsHistory || []}
              color="#ffcc02"
              unit=""
              loading={agentsLoading}
            />
          </Grid>
        </Grid>
      </Box>

      {/* Component Status */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h6" sx={{ color: '#cccccc', mb: 2 }}>
          Component Status
        </Typography>
        <Grid container spacing={2}>
          {/* Detailed Health Checks */}
          <Grid item xs={12} md={6}>
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

          {/* Agent/Tool/Workflow Stats */}
          <Grid item xs={12} md={6}>
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <Card sx={{ backgroundColor: '#252526', border: '1px solid #2d2d30' }}>
                  <CardContent>
                    <Typography variant="subtitle1" sx={{ color: '#cccccc', mb: 2 }}>
                      Component Statistics
                    </Typography>
                    <Grid container spacing={2}>
                      {/* Agents */}
                      <Grid item xs={4}>
                        <Box sx={{ textAlign: 'center', p: 1, border: '1px solid #3e3e42', borderRadius: 1 }}>
                          <MetricsIcon sx={{ color: '#4ec9b0', mb: 1 }} />
                          <Typography variant="h4" sx={{ color: '#cccccc' }}>{dashboardStats?.agents?.total || 0}</Typography>
                          <Typography variant="caption" sx={{ color: '#969696' }}>Total Agents</Typography>
                          <Typography variant="caption" sx={{ color: '#4ec9b0', display: 'block' }}>{dashboardStats?.agents?.active || 0} Active</Typography>
                        </Box>
                      </Grid>
                      {/* Tools */}
                      <Grid item xs={4}>
                        <Box sx={{ textAlign: 'center', p: 1, border: '1px solid #3e3e42', borderRadius: 1 }}>
                          <ToolsIcon sx={{ color: '#569cd6', mb: 1 }} />
                          <Typography variant="h4" sx={{ color: '#cccccc' }}>{dashboardStats?.tools?.total || 0}</Typography>
                          <Typography variant="caption" sx={{ color: '#969696' }}>Available Tools</Typography>
                        </Box>
                      </Grid>
                      {/* Workflows */}
                      <Grid item xs={4}>
                        <Box sx={{ textAlign: 'center', p: 1, border: '1px solid #3e3e42', borderRadius: 1 }}>
                          <WorkflowIcon sx={{ color: '#ffcc02', mb: 1 }} />
                          <Typography variant="h4" sx={{ color: '#cccccc' }}>{dashboardStats?.workflows?.total || 0}</Typography>
                          <Typography variant="caption" sx={{ color: '#969696' }}>Total Workflows</Typography>
                          <Typography variant="caption" sx={{ color: '#ffcc02', display: 'block' }}>{dashboardStats?.workflows?.active || 0} Active</Typography>
                        </Box>
                      </Grid>
                    </Grid>
                  </CardContent>
                </Card>
              </Grid>

              {/* Active Alerts (Mini) */}
              <Grid item xs={12}>
                <Card sx={{ backgroundColor: '#252526', border: '1px solid #2d2d30', minHeight: 140 }}>
                  <CardContent>
                    <Typography variant="subtitle1" sx={{ color: '#cccccc', mb: 1 }}>
                      Active Alerts
                    </Typography>
                    {alertsData?.alerts && alertsData.alerts.length > 0 ? (
                      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                        {alertsData.alerts.slice(0, 2).map((alert, index) => (
                          <Box key={index} sx={{ p: 1, bgcolor: '#1e1e1e', borderRadius: 1, borderLeft: `3px solid ${alert.severity === 'critical' ? '#f48771' : '#ffcc02'}` }}>
                            <Typography variant="body2" sx={{ color: '#cccccc', fontSize: '12px' }}>
                              {alert.message}
                            </Typography>
                          </Box>
                        ))}
                      </Box>
                    ) : (
                      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', py: 2 }}>
                        <HealthyIcon sx={{ color: '#4ec9b020', fontSize: 32, mb: 1 }} />
                        <Typography variant="caption" sx={{ color: '#969696' }}>
                          No active alerts
                        </Typography>
                      </Box>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          </Grid>
        </Grid>
      </Box>
    </Box>
  )
}

export default MonitoringWorkspace