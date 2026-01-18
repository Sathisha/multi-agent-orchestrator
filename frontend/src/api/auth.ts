import apiClient from './client'

export interface User {
    id: string
    email: string
    full_name?: string
    username?: string
    firstName?: string
    lastName?: string
    isActive?: boolean
    is_active?: boolean
    is_superuser?: boolean
    is_system_admin?: boolean
    roles?: Array<{
        id: string
        name: string
        permissions?: Array<{
            id: string
            name: string
            description?: string
        }>
    }>
}

export interface LoginRequest {
    email: string // or username?
    password: string
}

export interface RegisterRequest {
    email: string
    password: string
    full_name: string
}

export interface AuthResponse {
    access_token: string
    refresh_token: string
    token_type: string
    expires_in: number
}

// User Profile Response
// UserResponse schema (backend) includes fields.

export const login = async (data: LoginRequest): Promise<AuthResponse> => {
    const response = await apiClient.post<AuthResponse>('/auth/login', data)
    return response.data
}

export const register = async (data: RegisterRequest): Promise<User> => {
    const response = await apiClient.post<User>('/auth/register', data)
    return response.data
}

export const getCurrentUser = async (): Promise<User> => {
    const response = await apiClient.get<User>('/auth/me')
    return response.data
}

export const logout = async (): Promise<void> => {
    await apiClient.post('/auth/logout')
}

export const refreshAccessToken = async (refreshToken: string): Promise<AuthResponse> => {
    const response = await apiClient.post<AuthResponse>('/auth/refresh', { refresh_token: refreshToken })
    return response.data
}
