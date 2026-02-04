
import apiClient from './client'

export interface RAGSource {
    id: string
    name: string
    source_type: 'website' | 'pdf' | 'text' // as defined in backend enum
    content_source: string
    status: 'pending' | 'processing' | 'completed' | 'failed'
    owner_id: string
    is_public: boolean
    processing_metadata?: Record<string, any>
    created_at: string
    updated_at: string
}

export interface CreateWebsiteSourceRequest {
    name: string
    url: string
}

export const getRAGSources = async (): Promise<RAGSource[]> => {
    const response = await apiClient.get<RAGSource[]>('/rag/sources')
    return response.data
}

export const addWebsiteSource = async (data: CreateWebsiteSourceRequest): Promise<RAGSource> => {
    const response = await apiClient.post<RAGSource>('/rag/sources/website', data)
    return response.data
}

export const uploadPDFSource = async (file: File, name?: string): Promise<RAGSource> => {
    const formData = new FormData()
    formData.append('file', file)
    if (name) {
        formData.append('name', name)
    }
    const response = await apiClient.post<RAGSource>('/rag/sources/pdf', formData, {
        headers: {
            'Content-Type': 'multipart/form-data'
        }
    })
    return response.data
}

export const deleteRAGSource = async (id: string): Promise<void> => {
    await apiClient.delete(`/rag/sources/${id}`)
}

export interface QueryResponse {
    content: string
    score: number
    metadata: Record<string, any>
}

export const queryRAG = async (query: string, limit: number = 5): Promise<QueryResponse[]> => {
    const response = await apiClient.post<QueryResponse[]>('/rag/query', { query, limit })
    return response.data
}

// Agent-Source Assignment APIs
export const getAgentSources = async (agentId: string): Promise<RAGSource[]> => {
    const response = await apiClient.get<RAGSource[]>(`/rag/agents/${agentId}/sources`)
    return response.data
}

export const assignSourceToAgent = async (agentId: string, sourceId: string): Promise<void> => {
    await apiClient.post(`/rag/agents/${agentId}/sources/${sourceId}`)
}

export const removeSourceFromAgent = async (agentId: string, sourceId: string): Promise<void> => {
    await apiClient.delete(`/rag/agents/${agentId}/sources/${sourceId}`)
}

// RBAC APIs
export interface SourceRoleResponse {
    role_id: string
    role_name: string
    access_type: 'view' | 'query' | 'modify'
}

export const updateSourceVisibility = async (sourceId: string, isPublic: boolean): Promise<RAGSource> => {
    const response = await apiClient.patch<RAGSource>(`/rag/sources/${sourceId}/visibility`, null, {
        params: { is_public: isPublic }
    })
    return response.data
}

export const getSourceRoles = async (sourceId: string): Promise<SourceRoleResponse[]> => {
    const response = await apiClient.get<SourceRoleResponse[]>(`/rag/sources/${sourceId}/roles`)
    return response.data
}

export const assignRoleToSource = async (sourceId: string, roleId: string, accessType: string): Promise<void> => {
    await apiClient.post(`/rag/sources/${sourceId}/roles/${roleId}`, null, {
        params: { access_type: accessType }
    })
}

export const removeRoleFromSource = async (sourceId: string, roleId: string): Promise<void> => {
    await apiClient.delete(`/rag/sources/${sourceId}/roles/${roleId}`)
}
