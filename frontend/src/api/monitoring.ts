import apiClient from './client'

export interface HealthCheckResult {
  overall_status: string
  timestamp: string
  health_checks: {
    [key: string]: {
      status: string
      duration_ms: number
      error: string | null
      details: any
    }
  }
}

export interface PerformanceSummary {
  timestamp: string
  overall_health: string
  metrics: {
    system?: {
      cpu_percent: number
      memory_percent: number
      disk_percent: number
    }
    database?: {
      query_time_ms: number
      active_connections: number
      pool_size: number
    }
    cache?: {
      ping_time_ms: number
      used_memory_mb: number
      connected_clients: number
    }
  }
}

export interface Alert {
  type: string
  severity: string
  message: string
  threshold: number
  timestamp: string
  acknowledged: string
  [key: string]: any
}


export interface DashboardStats {
  agents: {
    total: number
    active: number
    inactive: number
  }
  tools: {
    total: number
    available: number
  }
  workflows: {
    total: number
    active: number
    completed: number
  }
}

export const getHealthStatus = async (): Promise<HealthCheckResult> => {
  const response = await apiClient.get('/monitoring/health')
  return response.data
}

export const getPerformanceSummary = async (): Promise<PerformanceSummary> => {
  const response = await apiClient.get('/monitoring/performance/summary')
  return response.data
}

export const getAlerts = async (): Promise<{ alerts: Alert[], count: number }> => {
  const response = await apiClient.get('/monitoring/alerts')
  return response.data
}

export const getDashboardStats = async (): Promise<DashboardStats> => {
  const response = await apiClient.get('/monitoring/stats')
  return response.data
}

export const acknowledgeAlert = async (alertId: string): Promise<void> => {
  await apiClient.post(`/monitoring/alerts/${alertId}/acknowledge`)
}

export const getMetricsHistory = async (metric: string, durationStr: string = '1h'): Promise<{ timestamp: number; value: number }[]> => {
  // Calculate start/end based on duration
  const end = Math.floor(Date.now() / 1000);
  let start = end - 3600; // Default 1h

  if (durationStr === '30m') start = end - 1800;
  if (durationStr === '6h') start = end - 21600;
  if (durationStr === '24h') start = end - 86400;

  const response = await apiClient.get('/monitoring/metrics/history', {
    params: { metric, start, end, step: '30s' }
  })
  return response.data
}

