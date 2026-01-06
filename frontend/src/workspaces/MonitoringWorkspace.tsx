import React, { useMemo } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  LinearProgress,
  Chip,
  CircularProgress,
  useTheme,
  Alert,
  IconButton,
  Tooltip,
} from '@mui/material';
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
  AccountTree as WorkflowIcon,
  Refresh as RefreshIcon,
  Dns as DatabaseIcon,
  Cached as CacheIcon,
  Language as NetworkIcon,
  SmartToy as RobotIcon,
} from '@mui/icons-material';
import { useQuery } from 'react-query';
import {
  getHealthStatus,
  getPerformanceSummary,
  getAlerts,
  getDashboardStats,
  getMetricsHistory,
  Alert as AlertType,
} from '../api/monitoring';
import MetricChart from '../components/charts/MetricChart';

const POLLING_INTERVAL = 30000; // 30 seconds

// --- Helper Components ---

const StatusChip = ({ status }: { status: string }) => {
  const theme = useTheme();
  let color = theme.palette.text.secondary;
  let bgcolor = theme.palette.action.disabledBackground;

  const normalizedStatus = status.toLowerCase();

  if (normalizedStatus === 'healthy' || normalizedStatus === 'good' || normalizedStatus === 'up') {
    color = theme.palette.success.main;
    bgcolor = theme.palette.success.light + '20'; // Transparent background
  } else if (normalizedStatus === 'degraded' || normalizedStatus === 'warning') {
    color = theme.palette.warning.main;
    bgcolor = theme.palette.warning.light + '20';
  } else if (normalizedStatus === 'unhealthy' || normalizedStatus === 'error' || normalizedStatus === 'down' || normalizedStatus === 'critical') {
    color = theme.palette.error.main;
    bgcolor = theme.palette.error.light + '20';
  }

  return (
    <Chip
      label={status.toUpperCase()}
      size="small"
      sx={{
        color: color,
        bgcolor: bgcolor,
        fontWeight: 'bold',
        fontSize: '0.7rem',
        height: 20,
      }}
    />
  );
};

const ResourceCard = ({
  title,
  value,
  unit,
  icon: Icon,
  color,
}: {
  title: string;
  value: number;
  unit: string;
  icon: any;
  color: string;
}) => {
  const theme = useTheme();

  return (
    <Card sx={{ height: '100%', position: 'relative', overflow: 'visible' }}>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
          <Box>
            <Typography variant="overline" color="text.secondary">
              {title}
            </Typography>
            <Typography variant="h4" sx={{ fontWeight: 'bold', my: 0.5 }}>
              {value.toFixed(1)}
              <Typography component="span" variant="body2" color="text.secondary" sx={{ ml: 0.5 }}>
                {unit}
              </Typography>
            </Typography>
          </Box>
          <Box
            sx={{
              p: 1,
              borderRadius: 2,
              bgcolor: `${color}20`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Icon sx={{ color: color }} />
          </Box>
        </Box>
        <LinearProgress
          variant="determinate"
          value={Math.min(value, 100)} // Ensure we don't exceed 100 for visual
          sx={{
            height: 6,
            borderRadius: 3,
            bgcolor: theme.palette.action.hover,
            '& .MuiLinearProgress-bar': {
              bgcolor: color,
            },
          }}
        />
      </CardContent>
    </Card>
  );
};

const MonitoringWorkspace: React.FC = () => {
  const theme = useTheme();

  // --- Data Fetching ---

  const { data: health, isLoading: healthLoading, refetch: refetchHealth } = useQuery(
    'health-status',
    getHealthStatus,
    { refetchInterval: POLLING_INTERVAL }
  );

  const { data: performance, isLoading: perfLoading } = useQuery(
    'performance-summary',
    getPerformanceSummary,
    { refetchInterval: POLLING_INTERVAL }
  );

  const { data: alertsData } = useQuery('active-alerts', getAlerts, {
    refetchInterval: POLLING_INTERVAL,
  });

  const { data: dashboardStats } = useQuery('dashboard-stats', getDashboardStats, {
    refetchInterval: POLLING_INTERVAL,
  });

  // History Metrics
  const { data: cpuHistory, isLoading: cpuHistoryLoading } = useQuery(
    ['metrics-history', 'cpu_usage'],
    () => getMetricsHistory('cpu_usage'),
    { refetchInterval: 60000 }
  );
  const { data: memHistory, isLoading: memHistoryLoading } = useQuery(
    ['metrics-history', 'memory_usage'],
    () => getMetricsHistory('memory_usage'),
    { refetchInterval: 60000 }
  );
  const { data: agentsHistory, isLoading: agentsHistoryLoading } = useQuery(
    ['metrics-history', 'active_agents'],
    () => getMetricsHistory('active_agents'),
    { refetchInterval: 60000 }
  );

  const systemResources = health?.health_checks?.system_resources?.details || {};

  // --- Alert Management ---
  const [dismissedAlerts, setDismissedAlerts] = React.useState<Set<string>>(new Set());

  // Deduplicate alerts - show only unique messages from recent alerts
  const deduplicatedAlerts = React.useMemo(() => {
    if (!alertsData?.alerts) return [];

    const seen = new Map<string, AlertType>();

    return alertsData.alerts
      .filter(alert => {
        // Skip dismissed alerts
        const alertKey = `${alert.message}-${alert.timestamp}`;
        if (dismissedAlerts.has(alertKey)) return false;

        // Check if we've seen this message before
        if (seen.has(alert.message)) {
          return false; // Hide duplicates
        }

        seen.set(alert.message, alert);
        return true;
      })
      .slice(0, 5); // Show max 5 alerts
  }, [alertsData, dismissedAlerts]);

  // Auto-dismiss alerts after 60 seconds
  React.useEffect(() => {
    if (deduplicatedAlerts.length === 0) return;

    const timer = setTimeout(() => {
      setDismissedAlerts(prev => {
        const newSet = new Set(prev);
        deduplicatedAlerts.forEach(alert => {
          newSet.add(`${alert.message}-${alert.timestamp}`);
        });
        return newSet;
      });
    }, 60000); // 60 seconds

    return () => clearTimeout(timer);
  }, [deduplicatedAlerts]);

  // --- Derived State ---

  const metrics = [
    {
      title: 'CPU Usage',
      value: systemResources.cpu_percent || 0,
      unit: '%',
      icon: PerformanceIcon,
      color: theme.palette.info.main,
    },
    {
      title: 'Memory Usage',
      value: systemResources.memory_percent || 0,
      unit: '%',
      icon: MemoryIcon,
      color: theme.palette.secondary.main,
    },
    {
      title: 'Disk Usage',
      value: systemResources.disk_percent || 0,
      unit: '%',
      icon: StorageIcon,
      color: theme.palette.warning.main,
    },
    {
      title: 'Active Agents',
      value: dashboardStats?.agents?.active || 0,
      unit: '',
      icon: RobotIcon,
      color: theme.palette.success.main,
    }
  ];

  const overallStatus = health?.overall_status || 'unknown';

  if (healthLoading || perfLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3, height: '100%', overflow: 'auto' }}>

      {/* Header Section */}
      <Box sx={{ mb: 4, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 'bold', mb: 1 }}>
            System Monitor
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Real-time insight into system performance and health.
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <Tooltip title="Refresh Data">
            <IconButton onClick={() => refetchHealth()}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          <Chip
            icon={overallStatus === 'healthy' ? <HealthyIcon /> : <WarningIcon />}
            label={`System Status: ${overallStatus.toUpperCase()}`}
            color={overallStatus === 'healthy' ? 'success' : 'error'}
            variant="outlined"
            sx={{ fontWeight: 'bold' }}
          />
        </Box>
      </Box>

      {/* Alerts Section - Only active if there are alerts */}
      {deduplicatedAlerts.length > 0 && (
        <Box sx={{ mb: 4 }}>
          {deduplicatedAlerts.map((alert: AlertType) => (
            <Alert
              key={`${alert.message}-${alert.timestamp}`}
              severity={alert.severity as any}
              sx={{ mb: 1 }}
              onClose={() => {
                const alertKey = `${alert.message}-${alert.timestamp}`;
                setDismissedAlerts(prev => new Set(prev).add(alertKey));
              }}
              action={
                <Typography variant="caption" sx={{ mr: 2 }}>
                  {new Date(alert.timestamp).toLocaleTimeString()}
                </Typography>
              }
            >
              {alert.message}
            </Alert>
          ))}
          {alertsData?.alerts && alertsData.alerts.length > deduplicatedAlerts.length && (
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', ml: 2, mt: 1 }}>
              ({alertsData.alerts.length - deduplicatedAlerts.length} duplicate alerts hidden)
            </Typography>
          )}
        </Box>
      )}

      {/* Key Resources Grid */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {metrics.map((metric, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <ResourceCard {...metric} />
          </Grid>
        ))}
      </Grid>

      {/* Main Content Grid */}
      <Grid container spacing={3}>

        {/* Left Column: Charts */}
        <Grid item xs={12} lg={8}>
          <Typography variant="h6" sx={{ mb: 2, fontWeight: 'bold' }}>
            Performance Trends
          </Typography>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <MetricChart
                title="CPU Load History"
                data={cpuHistory || []}
                color={theme.palette.info.main}
                unit="%"
                loading={cpuHistoryLoading}
                height={250}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <MetricChart
                title="Memory Usage History"
                data={memHistory || []}
                color={theme.palette.secondary.main}
                unit="%" // Assuming the backend now returns % or we treat it as unitless value if unknown
                loading={memHistoryLoading}
                height={250}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <MetricChart
                title="Active Agents History"
                data={agentsHistory || []}
                color={theme.palette.success.main}
                unit=""
                loading={agentsHistoryLoading}
                height={250}
              />
            </Grid>
          </Grid>
        </Grid>

        {/* Right Column: Detailed Health & Status */}
        <Grid item xs={12} lg={4}>
          <Typography variant="h6" sx={{ mb: 2, fontWeight: 'bold' }}>
            Component Status
          </Typography>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>

            {/* Database Health */}
            <Card variant="outlined">
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <DatabaseIcon sx={{ mr: 1, color: theme.palette.primary.main }} />
                  <Typography variant="subtitle1" fontWeight="bold">Database</Typography>
                  <Box sx={{ flexGrow: 1 }} />
                  <StatusChip status={health?.health_checks?.database?.status || 'Unknown'} />
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="body2" color="text.secondary">Pool Size</Typography>
                  <Typography variant="body2" fontWeight="medium">
                    {health?.health_checks?.database?.details?.pool_size || '-'}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="body2" color="text.secondary">Active Connections</Typography>
                  <Typography variant="body2" fontWeight="medium">
                    {health?.health_checks?.database?.details?.checked_out_connections || '-'}
                  </Typography>
                </Box>
              </CardContent>
            </Card>

            {/* Redis Health */}
            <Card variant="outlined">
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <CacheIcon sx={{ mr: 1, color: theme.palette.error.main }} />
                  <Typography variant="subtitle1" fontWeight="bold">Cache (Redis)</Typography>
                  <Box sx={{ flexGrow: 1 }} />
                  <StatusChip status={health?.health_checks?.redis?.status || 'Unknown'} />
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="body2" color="text.secondary">Memory Used</Typography>
                  <Typography variant="body2" fontWeight="medium">
                    {health?.health_checks?.redis?.details?.used_memory_human || '-'}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="body2" color="text.secondary">Connected Clients</Typography>
                  <Typography variant="body2" fontWeight="medium">
                    {health?.health_checks?.redis?.details?.connected_clients || '-'}
                  </Typography>
                </Box>
              </CardContent>
            </Card>

            {/* External Services */}
            <Card variant="outlined">
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <NetworkIcon sx={{ mr: 1, color: theme.palette.warning.main }} />
                  <Typography variant="subtitle1" fontWeight="bold">Services</Typography>
                  <Box sx={{ flexGrow: 1 }} />
                  <StatusChip status={health?.health_checks?.external_services?.status || 'Unknown'} />
                </Box>
                {health?.health_checks?.external_services?.details &&
                  Object.entries(health.health_checks.external_services.details).map(([service, status]: [string, any]) => (
                    <Box key={service} sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                      <Typography variant="body2" color="text.secondary" sx={{ textTransform: 'capitalize' }}>
                        {service}
                      </Typography>
                      <StatusChip status={status ? 'UP' : 'DOWN'} />
                    </Box>
                  ))
                }
              </CardContent>
            </Card>
          </Box>
        </Grid>
      </Grid>
    </Box>
  );
};

export default MonitoringWorkspace;