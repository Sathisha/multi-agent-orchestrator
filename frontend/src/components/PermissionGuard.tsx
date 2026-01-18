import React from 'react'
import { useAuth } from '../context/AuthContext'

interface PermissionGuardProps {
    permission?: string
    role?: string
    requireSuperAdmin?: boolean
    fallback?: React.ReactNode
    children: React.ReactNode
}

/**
 * PermissionGuard - Component that conditionally renders children based on user permissions
 * 
 * Usage:
 * <PermissionGuard permission="agent.create">
 *   <Button>Create Agent</Button>
 * </PermissionGuard>
 * 
 * <PermissionGuard role="super_admin">
 *   <MenuItem>Admin Settings</MenuItem>
 * </PermissionGuard>
 * 
 * <PermissionGuard requireSuperAdmin fallback={<AccessDenied />}>
 *   <AdminPanel />
 * </PermissionGuard>
 */
export const PermissionGuard: React.FC<PermissionGuardProps> = ({
    permission,
    role,
    requireSuperAdmin,
    fallback = null,
    children
}) => {
    const { hasPermission, hasRole, isSuperAdmin, isAuthenticated } = useAuth()

    // If not authenticated, show fallback
    if (!isAuthenticated) {
        return <>{fallback}</>
    }

    // Check super admin requirement
    if (requireSuperAdmin && !isSuperAdmin()) {
        return <>{fallback}</>
    }

    // Check specific permission
    if (permission && !hasPermission(permission)) {
        return <>{fallback}</>
    }

    // Check specific role
    if (role && !hasRole(role)) {
        return <>{fallback}</>
    }

    // All checks passed, render children
    return <>{children}</>
}

export default PermissionGuard
