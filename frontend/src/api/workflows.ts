import apiClient from './client'

export interface WorkflowRequest {
    name: string
    description?: string
    version?: string
    bpmn_xml: string
    category?: string
    tags?: string[]
    input_schema?: Record<string, any>
    output_schema?: Record<string, any>
    timeout_minutes?: number
    max_concurrent_executions?: number
}

export interface WorkflowResponse {
    id: string
    name: string
    description?: string
    version: string
    status: string
    execution_count: number
    created_at: string
    updated_at: string
    category?: string
    tags?: string[]
    bpmn_xml?: string
}

export interface WorkflowExecutionRequest {
    input_data: Record<string, any>
    variables?: Record<string, any>
    priority?: number
    correlation_id?: string
}

export interface WorkflowExecutionResponse {
    id: string
    workflow_id: string
    workflow_name?: string
    status: string
    started_at: string
    completed_at?: string
    progress_percentage?: number
    input_data?: Record<string, any>
    output_data?: Record<string, any>
    error_message?: string
}

export const getWorkflows = async (): Promise<WorkflowResponse[]> => {
    const response = await apiClient.get<WorkflowResponse[]>('/workflows')
    return response.data
}

export const getWorkflow = async (id: string): Promise<WorkflowResponse> => {
    const response = await apiClient.get<WorkflowResponse>(`/workflows/${id}`)
    return response.data
}

export const createWorkflow = async (data: WorkflowRequest): Promise<WorkflowResponse> => {
    const response = await apiClient.post<WorkflowResponse>('/workflows', data)
    return response.data
}

export const updateWorkflow = async (id: string, data: Partial<WorkflowRequest>): Promise<WorkflowResponse> => {
    const response = await apiClient.put<WorkflowResponse>(`/workflows/${id}`, data)
    return response.data
}

export const deleteWorkflow = async (id: string): Promise<void> => {
    await apiClient.delete(`/workflows/${id}`)
}

export const getExecutions = async (limit: number = 100): Promise<WorkflowExecutionResponse[]> => {
    const response = await apiClient.get<WorkflowExecutionResponse[]>(`/workflows/executions?limit=${limit}`)
    return response.data
}

export const executeWorkflow = async (id: string, data: WorkflowExecutionRequest): Promise<WorkflowExecutionResponse> => {
    const response = await apiClient.post<WorkflowExecutionResponse>(`/workflows/${id}/execute`, data)
    return response.data
}

export const getExecutionStatus = async (executionId: string): Promise<WorkflowExecutionResponse> => {
    const response = await apiClient.get<WorkflowExecutionResponse>(`/workflows/executions/${executionId}`)
    return response.data
}
