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
    available_tools?: string[]
    capabilities?: string[]
    tags?: string[]
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

export const updateAgent = async (id: string, data: Partial<CreateAgentRequest>): Promise<Agent> => {
    const response = await apiClient.put<Agent>(`/agents/${id}`, data)
    return response.data
}

export const deleteAgent = async (id: string): Promise<void> => {
    await apiClient.delete(`/agents/${id}`)
}
