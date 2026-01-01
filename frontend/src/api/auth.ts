import apiClient from './client'

export interface User {
    id: string
    email: string
    full_name?: string
    username?: string // Optional if backend doesn't enforce it
    firstName?: string
    lastName?: string
    isActive?: boolean // CamelCase vs snake_case depends on UserResponse?
    // Backend UserResponse (Step 783) returns UserResponse.from_orm(user).
    // Usually API returns snake_case unless configured otherwise.
    // I will assume snake_case from Pydantic default.
    is_active?: boolean
    is_system_admin?: boolean
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
