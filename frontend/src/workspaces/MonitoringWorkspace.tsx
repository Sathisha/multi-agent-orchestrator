import React from 'react'
import { Box, Typography, Card, CardContent, Grid, LinearProgress, Chip } from '@mui/material'
import { 
  Timeline as MetricsIcon,
  BugReport as LogsIcon,
  Security as AuditIcon,
  Speed as PerformanceIcon,
  Memory as MemoryIcon,
  Storage as StorageIcon
} from '@mui/icons-material'

const MonitoringWorkspace: React.FC = () => {
  const systemMetrics = [
    { name: 'CPU Usage', value: 45, unit: '%', status: 'good', icon: PerformanceIcon },
    { name: 'Memory Usage', value: 67, unit: '%', status: 'warning', icon: MemoryIcon },
    { name: 'Disk Usage', value: 23, unit: '%', status: 'good', icon: StorageIcon },
    { name: 'Active Agents', value: 3, unit: '', status: 'good', icon: MetricsIcon },
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
    <Box sx={{ p: 3, height: '100%', overflow: 'auto' }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" sx={{ color: '#cccccc', mb: 1 }}>
          System Monitoring
        </Typography>
        <Typography variant="body2" sx={{ color: '#969696' }}>
          Monitor system health, performance, and agent activities
        </Typography>
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
          Agent Activity
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
                  Execution Timeline
                </Typography>
                <Box
                  sx={{
                    height: 200,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    backgroundColor: '#1e1e1e',
                    borderRadius: 1,
                  }}
                >
                  <Typography variant="body2" sx={{ color: '#969696' }}>
                    Timeline chart will be implemented here
                  </Typography>
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
                  {[
                    { name: 'Customer Support Bot', status: 'Running', uptime: '2h 15m' },
                    { name: 'Data Analyzer', status: 'Running', uptime: '45m' },
                    { name: 'Content Generator', status: 'Idle', uptime: '1d 3h' },
                  ].map((agent, index) => (
                    <Box key={index} sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <Box>
                        <Typography variant="body2" sx={{ color: '#cccccc' }}>
                          {agent.name}
                        </Typography>
                        <Typography variant="caption" sx={{ color: '#969696' }}>
                          Uptime: {agent.uptime}
                        </Typography>
                      </Box>
                      <Chip
                        label={agent.status}
                        size="small"
                        sx={{
                          backgroundColor: agent.status === 'Running' ? '#4ec9b0' : '#969696',
                          color: '#000000',
                          fontSize: '10px',
                        }}
                      />
                    </Box>
                  ))}
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
                    Response Times
                  </Typography>
                </Box>
                <Typography variant="h5" sx={{ color: '#cccccc', mb: 1 }}>
                  127ms
                </Typography>
                <Typography variant="body2" sx={{ color: '#4ec9b0' }}>
                  ↓ 15ms from last hour
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
                    Throughput
                  </Typography>
                </Box>
                <Typography variant="h5" sx={{ color: '#cccccc', mb: 1 }}>
                  45 req/min
                </Typography>
                <Typography variant="body2" sx={{ color: '#4ec9b0' }}>
                  ↑ 8 req/min from last hour
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
                  <BugReport sx={{ color: '#f48771', mr: 1 }} />
                  <Typography variant="subtitle1" sx={{ color: '#cccccc' }}>
                    Error Rate
                  </Typography>
                </Box>
                <Typography variant="h5" sx={{ color: '#cccccc', mb: 1 }}>
                  0.02%
                </Typography>
                <Typography variant="body2" sx={{ color: '#4ec9b0' }}>
                  ↓ 0.01% from last hour
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>

      {/* Recent Logs and Alerts */}
      <Box>
        <Typography variant="h6" sx={{ color: '#cccccc', mb: 2 }}>
          Recent Activity
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <Card
              sx={{
                backgroundColor: '#252526',
                border: '1px solid #2d2d30',
                height: 300,
              }}
            >
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <LogsIcon sx={{ color: '#569cd6', mr: 1 }} />
                  <Typography variant="subtitle1" sx={{ color: '#cccccc' }}>
                    System Logs
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  {[
                    { time: '14:32:15', level: 'INFO', message: 'Agent "Customer Support Bot" started successfully' },
                    { time: '14:31:42', level: 'INFO', message: 'Workflow "Onboarding" completed execution' },
                    { time: '14:30:18', level: 'WARN', message: 'High memory usage detected (67%)' },
                    { time: '14:29:55', level: 'INFO', message: 'New tool "Email Sender" registered' },
                  ].map((log, index) => (
                    <Box key={index} sx={{ display: 'flex', gap: 1, fontSize: '12px' }}>
                      <Typography variant="caption" sx={{ color: '#969696', minWidth: 60 }}>
                        {log.time}
                      </Typography>
                      <Typography 
                        variant="caption" 
                        sx={{ 
                          color: log.level === 'WARN' ? '#ffcc02' : '#4ec9b0',
                          minWidth: 40,
                          fontWeight: 'bold'
                        }}
                      >
                        {log.level}
                      </Typography>
                      <Typography variant="caption" sx={{ color: '#cccccc' }}>
                        {log.message}
                      </Typography>
                    </Box>
                  ))}
                </Box>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} md={6}>
            <Card
              sx={{
                backgroundColor: '#252526',
                border: '1px solid #2d2d30',
                height: 300,
              }}
            >
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <AuditIcon sx={{ color: '#ffcc02', mr: 1 }} />
                  <Typography variant="subtitle1" sx={{ color: '#cccccc' }}>
                    Audit Trail
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  {[
                    { time: '14:30', user: 'admin', action: 'Created new agent "Data Processor"' },
                    { time: '14:25', user: 'developer', action: 'Modified workflow "Content Pipeline"' },
                    { time: '14:20', user: 'admin', action: 'Updated system configuration' },
                    { time: '14:15', user: 'developer', action: 'Deployed agent "Support Bot" to production' },
                  ].map((audit, index) => (
                    <Box key={index} sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                      <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                        <Typography variant="caption" sx={{ color: '#969696' }}>
                          {audit.time}
                        </Typography>
                        <Chip
                          label={audit.user}
                          size="small"
                          sx={{
                            height: 16,
                            fontSize: '9px',
                            backgroundColor: '#007acc',
                            color: '#ffffff',
                          }}
                        />
                      </Box>
                      <Typography variant="caption" sx={{ color: '#cccccc', fontSize: '11px' }}>
                        {audit.action}
                      </Typography>
                    </Box>
                  ))}
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>
    </Box>
  )
}

export default MonitoringWorkspace