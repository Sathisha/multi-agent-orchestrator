import apiClient from './client'

export interface Agent {
    id: string
    name: string
    description?: string
    type: string
    status: string
    version: string
    config: Record<string, any>
    system_prompt?: string
    available_tools?: string[]
    capabilities?: string[]
    tags?: string[]
    execution_count: number
    created_at: string
    updated_at: string
}

export interface CreateAgentRequest {
    name: string
    description?: string
    type?: string // default CONVERSATIONAL
    config?: Record<string, any>
    system_prompt?: string
    llm_config?: Record<string, any>
    llm_model_id?: string;
    available_tools?: string[]
    capabilities?: string[]
    tags?: string[]
}

export interface UpdateAgentRequest extends CreateAgentRequest {
    status?: string
}

export interface ExecuteAgentRequest {
    input_data: Record<string, any>
    session_id?: string
    timeout_seconds?: number
}

export interface ExecuteAgentResponse {
    execution_id: string
    agent_id: string
    status: string
    message: string
}

export interface ExecutionStatusResponse {
    execution_id: string
    agent_id: string
    status: string
    started_at?: string
    completed_at?: string
    execution_time_ms?: number
    tokens_used?: number
    cost?: number
    error_message?: string
    is_active: boolean
    progress?: Record<string, any>
    output_data?: any
}

export const getAgents = async (): Promise<Agent[]> => {
    const response = await apiClient.get<Agent[]>('/agents')
    return response.data
}

export const getAgent = async (id: string): Promise<Agent> => {
    const response = await apiClient.get<Agent>(`/agents/${id}`)
    return response.data
}

export const createAgent = async (data: CreateAgentRequest): Promise<Agent> => {
    const response = await apiClient.post<Agent>('/agents', data)
    return response.data
}

export const updateAgent = async (id: string, data: Partial<UpdateAgentRequest>): Promise<Agent> => {
    const response = await apiClient.put<Agent>(`/agents/${id}`, data)
    return response.data
}

export const deleteAgent = async (id: string): Promise<void> => {
    await apiClient.delete(`/agents/${id}`)
}

export const executeAgent = async (agentId: string, data: ExecuteAgentRequest): Promise<ExecuteAgentResponse> => {
    const response = await apiClient.post<ExecuteAgentResponse>(`/agent-executor/${agentId}/execute`, data)
    return response.data
}


export interface AgentTemplate {
    id: string;
    name: string;
    description: string;
    type: string;
    system_prompt: string;
    icon: string;
    color: string;
    config?: Record<string, any>;
}

export const getExecutionStatus = async (executionId: string): Promise<ExecutionStatusResponse> => {
    const response = await apiClient.get<ExecutionStatusResponse>(`/agent-executor/executions/${executionId}/status`)
    return response.data
}

export const getAgentTemplates = async (): Promise<AgentTemplate[]> => {
    const response = await apiClient.get<AgentTemplate[]>('/agent-templates')
    return response.data
}
