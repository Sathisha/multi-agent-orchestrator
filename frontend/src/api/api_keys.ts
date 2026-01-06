import client from './client'

export interface APIKey {
    id: string
    user_id: string
    name: string
    description?: string
    key_prefix: string
    permissions: string[]
    expires_at?: string
    last_used_at?: string
    is_active: boolean
    created_at: string
}

export interface CreateAPIKeyRequest {
    name: string
    description?: string
    permissions?: string[]
    expires_at?: string
}

export interface CreateAPIKeyResponse {
    api_key: APIKey
    key: string // The plain text key, returned only once
}

export interface APIKeyListResponse {
    api_keys: APIKey[]
    total_count: number
    skip: number
    limit: number
}

export const getAPIKeys = async (skip = 0, limit = 100): Promise<APIKeyListResponse> => {
    const response = await client.get(`/api-keys/`, {
        params: { skip, limit }
    })
    return response.data
}

export const createAPIKey = async (data: CreateAPIKeyRequest): Promise<CreateAPIKeyResponse> => {
    const response = await client.post(`/api-keys/`, data)
    return response.data
}

export const revokeAPIKey = async (apiKeyId: string): Promise<void> => {
    await client.delete(`/api-keys/${apiKeyId}`)
}
