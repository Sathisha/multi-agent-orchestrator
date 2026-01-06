import apiClient from './client'

export interface User {
    id: string
    email: string
    username: string
    full_name: string
    avatar_url?: string
    status: string
    is_active: boolean
    is_system_admin: boolean
    created_at: string
    updated_at: string
    last_login_at?: string
}

export interface UserDetail extends User {
    roles: Role[]
}

export interface Role {
    id: string
    name: string
    description: string
    permissions?: Permission[]
    is_system_role?: boolean
    created_at: string
    updated_at: string
}

export interface Permission {
    id: string
    name: string
    description: string
    resource: string
    action: string
    created_at: string
}

export interface CreateUserRequest {
    email: string
    password: string
    full_name: string
    status?: string
    role_ids?: string[]
}

export interface UpdateUserRequest {
    full_name?: string
    email?: string
    status?: string
    is_active?: boolean
    role_ids?: string[]
}

export interface CreateRoleRequest {
    name: string
    description: string
    permissions?: string[]
}

export interface UpdateRoleRequest {
    name?: string
    description?: string
    permissions?: string[]
}

/**
 * Get all users (admin only)
 */
export const getUsers = async (): Promise<User[]> => {
    const response = await apiClient.get('/api/v1/auth/users')
    return response.data
}

/**
 * Get user details with roles (admin only)
 */
export const getUser = async (userId: string): Promise<UserDetail> => {
    const response = await apiClient.get(`/api/v1/auth/users/${userId}`)
    return response.data
}

/**
 * Create a new user (admin only)
 */
export const createUser = async (userData: CreateUserRequest): Promise<UserDetail> => {
    const response = await apiClient.post('/api/v1/auth/users', userData)
    return response.data
}

/**
 * Update user (admin only)
 */
export const updateUser = async (
    userId: string,
    userData: UpdateUserRequest
): Promise<UserDetail> => {
    const response = await apiClient.put(`/api/v1/auth/users/${userId}`, userData)
    return response.data
}

/**
 * Delete/deactivate user (admin only)
 */
export const deleteUser = async (userId: string): Promise<void> => {
    await apiClient.delete(`/api/v1/auth/users/${userId}`)
}

/**
 * Get all available roles (admin only)
 */
export const getRoles = async (): Promise<Role[]> => {
    const response = await apiClient.get('/api/v1/auth/roles')
    return response.data
}

/**
 * Get roles for a specific user (admin only)
 */
export const getUserRoles = async (userId: string): Promise<Role[]> => {
    const response = await apiClient.get(`/api/v1/auth/users/${userId}/roles`)
    return response.data
}

/**
 * Assign a role to a user (admin only)
 */
export const assignRole = async (userId: string, roleId: string): Promise<void> => {
    await apiClient.post(`/api/v1/auth/users/${userId}/roles/${roleId}`)
}

/**
 * Remove a role from a user (admin only)
 */
export const removeRole = async (userId: string, roleId: string): Promise<void> => {
    await apiClient.delete(`/api/v1/auth/users/${userId}/roles/${roleId}`)
}

/**
 * Create a new role (admin only)
 */
export const createRole = async (roleData: CreateRoleRequest): Promise<Role> => {
    const response = await apiClient.post('/api/v1/auth/roles', roleData)
    return response.data
}

/**
 * Update a role (admin only)
 */
export const updateRole = async (
    roleId: string,
    roleData: UpdateRoleRequest
): Promise<Role> => {
    const response = await apiClient.put(`/api/v1/auth/roles/${roleId}`, roleData)
    return response.data
}

/**
 * Delete a role (admin only)
 */
export const deleteRole = async (roleId: string): Promise<void> => {
    await apiClient.delete(`/api/v1/auth/roles/${roleId}`)
}

/**
 * Get all available permissions (admin only)
 */
export const getPermissions = async (): Promise<Permission[]> => {
    const response = await apiClient.get('/api/v1/auth/permissions')
    return response.data
}
