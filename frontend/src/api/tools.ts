import apiClient from './client'

export interface Tool {
    id: string
    name: string
    description?: string
    version: string
    tool_type: string
    status: string
    category?: string
    tags: string[]
    capabilities: string[]
    usage_count: number
    created_at: string
    updated_at: string
    // New fields for tool details
    code?: string
    entry_point?: string
    input_schema?: Record<string, any>
    output_schema?: Record<string, any>
    timeout_seconds?: number
}

export interface CreateToolRequest {
    name: string
    description?: string
    version?: string
    tool_type?: 'custom' | 'mcp_server'
    code?: string
    input_schema?: Record<string, any>
    output_schema?: Record<string, any>
    category?: string
    tags?: string[]
    capabilities?: string[]
    timeout_seconds?: number
    entry_point?: string // Added entry_point
}

export const getTools = async (): Promise<Tool[]> => {
    const response = await apiClient.get<Tool[]>('/tools')
    return response.data
}

export const getTool = async (id: string): Promise<Tool> => {
    const response = await apiClient.get<Tool>(`/tools/${id}`)
    return response.data
}

export const createTool = async (data: CreateToolRequest): Promise<Tool> => {
    const response = await apiClient.post<Tool>('/tools', data)
    return response.data
}

export const updateTool = async (id: string, data: Partial<CreateToolRequest>): Promise<Tool> => {
    const response = await apiClient.put<Tool>(`/tools/${id}`, data)
    return response.data
}

export const deleteTool = async (id: string): Promise<void> => {
    await apiClient.delete(`/tools/${id}`)
}

export const validateTool = async (id: string): Promise<{ is_valid: boolean; errors: string[] }> => {
    const response = await apiClient.post(`/tools/${id}/validate`)
    return response.data
}

export const executeTool = async (
    id: string, 
    inputs: Record<string, any>, 
    context: Record<string, any> = {}, 
    timeout_override?: number
): Promise<any> => {
    const response = await apiClient.post(`/tools/${id}/execute`, { inputs, context, timeout_override })
    return response.data
}

export const getToolTemplates = async (): Promise<any[]> => {
    const response = await apiClient.get('/tools/templates/')
    return response.data
}
