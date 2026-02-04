import apiClient from './client'

export interface Role {
    id: string
    name: string
    description: string
    permissions: string[]
    created_at: string
    updated_at: string
}

export const getRoles = async (): Promise<Role[]> => {
    const response = await apiClient.get<Role[]>('/roles/')
    return response.data
}
