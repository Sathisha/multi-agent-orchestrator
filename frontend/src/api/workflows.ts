import apiClient from './client'

export interface WorkflowRequest {
    name: string
    description?: string
    version?: string
    bpmn_xml: string
    // ... other fields
}

export interface WorkflowResponse {
    id: string
    name: string
    description?: string
    status: string
    execution_count: number
    updated_at: string
}

export interface WorkflowExecutionResponse {
    id: string
    workflow_id: string
    workflow_name?: string
    status: string
    started_at: string
    progress_percentage?: number
}

export const getWorkflows = async (): Promise<WorkflowResponse[]> => {
    const response = await apiClient.get<WorkflowResponse[]>('/workflows')
    return response.data
}

export const createWorkflow = async (data: WorkflowRequest): Promise<WorkflowResponse> => {
    const response = await apiClient.post<WorkflowResponse>('/workflows', data)
    return response.data
}

export const getExecutions = async (limit: number = 100): Promise<WorkflowExecutionResponse[]> => {
    const response = await apiClient.get<WorkflowExecutionResponse[]>(`/workflows/executions?limit=${limit}`)
    return response.data
}
