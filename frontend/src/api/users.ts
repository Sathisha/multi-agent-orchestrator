import apiClient from './client'

// Role types
export interface Role {
    id: string
    name: string
    display_name: string
    description?: string
    permission_level: number
    is_system_role: boolean
    permissions?: Permission[]
}

export interface UserRole {
    role_id: string
    role_name: string
    assigned_at?: string
    expires_at?: string
}

// User types
export interface User {
    id: string
    email: string
    username: string
    full_name: string
    is_active: boolean
    is_superuser: boolean
    is_system_admin: boolean
    status: string
    roles: Role[]
    created_at?: string
    last_login_at?: string
    updated_at?: string
}

export interface UserDetail extends User {
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
    const response = await apiClient.get('/auth/users')
    return response.data
}

/**
 * Get user details with roles (admin only)
 */
export const getUser = async (userId: string): Promise<UserDetail> => {
    const response = await apiClient.get(`/auth/users/${userId}`)
    return response.data
}

/**
 * Create a new user (admin only)
 */
export const createUser = async (userData: CreateUserRequest): Promise<UserDetail> => {
    const response = await apiClient.post('/auth/users', userData)
    return response.data
}

/**
 * Update user (admin only)
 */
export const updateUser = async (
    userId: string,
    userData: UpdateUserRequest
): Promise<UserDetail> => {
    const response = await apiClient.put(`/auth/users/${userId}`, userData)
    return response.data
}

/**
 * Delete/deactivate user (admin only)
 */
export const deleteUser = async (userId: string): Promise<void> => {
    await apiClient.delete(`/auth/users/${userId}`)
}

/**
 * Get all available roles (admin only)
 */
export const getRoles = async (): Promise<Role[]> => {
    const response = await apiClient.get('/auth/roles')
    return response.data
}

/**
 * Get roles for a specific user (admin only)
 */
export const getUserRoles = async (userId: string): Promise<Role[]> => {
    const response = await apiClient.get(`/auth/users/${userId}/roles`)
    return response.data
}

/**
 * Assign a role to a user (admin only)
 */
export const assignRole = async (userId: string, roleId: string): Promise<void> => {
    await apiClient.post(`/auth/users/${userId}/roles/${roleId}`)
}

/**
 * Remove a role from a user (admin only)
 */
export const removeRole = async (userId: string, roleId: string): Promise<void> => {
    await apiClient.delete(`/auth/users/${userId}/roles/${roleId}`)
}

/**
 * Create a new role (admin only)
 */
export const createRole = async (roleData: CreateRoleRequest): Promise<Role> => {
    const response = await apiClient.post('/auth/roles', roleData)
    return response.data
}

/**
 * Update a role (admin only)
 */
export const updateRole = async (
    roleId: string,
    roleData: UpdateRoleRequest
): Promise<Role> => {
    const response = await apiClient.put(`/auth/roles/${roleId}`, roleData)
    return response.data
}

/**
 * Delete a role (admin only)
 */
export const deleteRole = async (roleId: string): Promise<void> => {
    await apiClient.delete(`/auth/roles/${roleId}`)
}

/**
 * Get all available permissions (admin only)
 */
export const getPermissions = async (): Promise<Permission[]> => {
    const response = await apiClient.get('/auth/permissions')
    return response.data
}
