import { useQuery } from 'react-query'
import { getCurrentUser } from '../api/auth'

/**
 * Custom hook to check user permissions
 * 
 * Usage:
 * const { hasPermission, isAdmin, isLoading } = usePermissions()
 * 
 * if (hasPermission('agent.create')) {
 *   // Show create button
 * }
 */
export const usePermissions = () => {
    const { data: currentUser, isLoading } = useQuery('currentUser', getCurrentUser, {
        staleTime: 5 * 60 * 1000, // 5 minutes
        retry: false
    })

    const isAdmin = currentUser?.is_system_admin || false

    /**
     * Check if current user has a specific permission
     * @param permission - Permission string in format "resource.action" (e.g., "agent.view")
     * @returns true if user has permission or is admin, false otherwise
     */
    const hasPermission = (permission: string): boolean => {
        // Admins have all permissions
        if (isAdmin) return true

        // If no user or user has no roles, deny
        if (!currentUser || !currentUser.roles) return false

        // Check if any of user's roles has the required permission
        return currentUser.roles.some(role =>
            role.permissions?.some(perm => perm.name === permission)
        )
    }

    /**
     * Check if user has ANY of the provided permissions
     * @param permissions - Array of permission strings
     * @returns true if user has at least one permission
     */
    const hasAnyPermission = (...permissions: string[]): boolean => {
        if (isAdmin) return true
        return permissions.some(perm => hasPermission(perm))
    }

    /**
     * Check if user has ALL of the provided permissions
     * @param permissions - Array of permission strings
     * @returns true if user has all permissions
     */
    const hasAllPermissions = (...permissions: string[]): boolean => {
        if (isAdmin) return true
        return permissions.every(perm => hasPermission(perm))
    }

    return {
        hasPermission,
        hasAnyPermission,
        hasAllPermissions,
        isAdmin,
        isLoading,
        currentUser
    }
}
