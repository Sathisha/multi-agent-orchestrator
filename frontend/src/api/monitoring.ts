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

export const acknowledgeAlert = async (alertId: string): Promise<void> => {
  await apiClient.post(`/monitoring/alerts/${alertId}/acknowledge`)
}
