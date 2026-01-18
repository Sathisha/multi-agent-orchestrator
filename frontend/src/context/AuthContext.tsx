import React, { createContext, useState, useEffect, useContext, useRef, useCallback } from 'react'
import { jwtDecode } from 'jwt-decode'
import { User, LoginRequest, RegisterRequest, login as apiLogin, register as apiRegister, getCurrentUser, logout as apiLogout, refreshAccessToken } from '../api/auth'

interface Role {
    id: string
    name: string
    permission_level: number
}

interface JWTPayload {
    sub: string
    email: string
    is_superuser: boolean
    roles: Role[]
    permissions: string[]
    exp: number
}

interface AuthContextType {
    user: User | null
    isAuthenticated: boolean
    isLoading: boolean
    jwtPayload: JWTPayload | null
    login: (data: LoginRequest) => Promise<void>
    register: (data: RegisterRequest) => Promise<void>
    logout: () => Promise<void>
    refreshToken: () => Promise<void>
    hasPermission: (permission: string) => boolean
    hasRole: (roleName: string) => boolean
    isSuperAdmin: () => boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<User | null>(null)
    const [jwtPayload, setJwtPayload] = useState<JWTPayload | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const refreshTimeoutRef = useRef<NodeJS.Timeout | null>(null)

    // Token refresh function
    const refreshToken = useCallback(async () => {
        const refresh = localStorage.getItem('refreshToken')
        if (!refresh) {
            console.log('[AuthContext] No refresh token available')
            return
        }

        try {
            console.log('[AuthContext] Refreshing access token...')
            const response = await refreshAccessToken(refresh)
            localStorage.setItem('token', response.access_token)

            if (response.refresh_token) {
                localStorage.setItem('refreshToken', response.refresh_token)
            }

            const decoded = jwtDecode<JWTPayload>(response.access_token)
            setJwtPayload(decoded)

            console.log('[AuthContext] Token refreshed successfully')
            scheduleTokenRefresh(decoded.exp)
        } catch (error) {
            console.error('[AuthContext] Token refresh failed:', error)
            // Clear auth state on refresh failure
            localStorage.removeItem('token')
            localStorage.removeItem('refreshToken')
            setUser(null)
            setJwtPayload(null)
        }
    }, [])

    // Schedule automatic token refresh before expiration
    const scheduleTokenRefresh = useCallback((expirationTime: number) => {
        // Clear any existing timeout
        if (refreshTimeoutRef.current) {
            clearTimeout(refreshTimeoutRef.current)
        }

        const now = Math.floor(Date.now() / 1000)
        const timeUntilExpiry = expirationTime - now

        // Refresh 5 minutes (300 seconds) before expiration
        const refreshIn = Math.max(0, (timeUntilExpiry - 300) * 1000)

        console.log(`[AuthContext] Scheduling token refresh in ${Math.floor(refreshIn / 1000)} seconds`)

        refreshTimeoutRef.current = setTimeout(() => {
            refreshToken()
        }, refreshIn)
    }, [refreshToken])

    useEffect(() => {
        const initAuth = async () => {
            const token = localStorage.getItem('token')
            console.log('[AuthContext] Initializing auth, token:', token ? 'exists' : 'none')
            if (token) {
                try {
                    // Decode JWT to get roles and permissions
                    const decoded = jwtDecode<JWTPayload>(token)

                    // Check if token is expired
                    const now = Math.floor(Date.now() / 1000)
                    if (decoded.exp && decoded.exp < now) {
                        console.log('[AuthContext] Token expired, attempting refresh...')
                        await refreshToken()
                    } else {
                        setJwtPayload(decoded)

                        // Fetch full user details
                        const userData = await getCurrentUser()
                        console.log('[AuthContext] User loaded:', userData.email)
                        setUser(userData)

                        // Schedule automatic refresh
                        if (decoded.exp) {
                            scheduleTokenRefresh(decoded.exp)
                        }
                    }
                } catch (error) {
                    console.error('[AuthContext] Failed to fetch user or decode token', error)
                    localStorage.removeItem('token')
                    localStorage.removeItem('refreshToken')
                    setJwtPayload(null)
                }
            }
            setIsLoading(false)
            console.log('[AuthContext] Auth initialized, isAuthenticated:', !!token)
        }
        initAuth()

        // Cleanup timeout on unmount
        return () => {
            if (refreshTimeoutRef.current) {
                clearTimeout(refreshTimeoutRef.current)
            }
        }
    }, [refreshToken, scheduleTokenRefresh])

    const login = async (data: LoginRequest) => {
        setIsLoading(true)
        try {
            const response = await apiLogin(data)
            localStorage.setItem('token', response.access_token)
            localStorage.setItem('refreshToken', response.refresh_token)

            // Decode JWT to get roles and permissions
            const decoded = jwtDecode<JWTPayload>(response.access_token)
            setJwtPayload(decoded)

            // Fetch user details immediately after login
            const userData = await getCurrentUser()
            setUser(userData)

            // Schedule automatic token refresh
            if (decoded.exp) {
                scheduleTokenRefresh(decoded.exp)
            }
        } finally {
            setIsLoading(false)
        }
    }

    const register = async (data: RegisterRequest) => {
        setIsLoading(true)
        try {
            await apiRegister(data)
            // Auto login after register? Or redirect?
            // Usually register just creates account.
            // But typically we want to auto-login.
            // However, the register endpoint returns User, not Token.
            // So we must Login explicitly or ask user to login.
            // For now, we'll just let the caller handle redirection to Login.
        } finally {
            setIsLoading(false)
        }
    }

    const logout = async () => {
        try {
            await apiLogout()
        } catch (e) {
            console.error(e)
        } finally {
            // Clear refresh timeout
            if (refreshTimeoutRef.current) {
                clearTimeout(refreshTimeoutRef.current)
            }

            localStorage.removeItem('token')
            localStorage.removeItem('refreshToken')
            setUser(null)
            setJwtPayload(null)
        }
    }

    const hasPermission = (permission: string): boolean => {
        if (!jwtPayload) return false
        if (jwtPayload.is_superuser) return true
        return jwtPayload.permissions.includes(permission)
    }

    const hasRole = (roleName: string): boolean => {
        if (!jwtPayload) return false
        return jwtPayload.roles.some(r => r.name === roleName)
    }

    const isSuperAdmin = (): boolean => {
        if (!jwtPayload) return false
        return jwtPayload.is_superuser || hasRole('super_admin')
    }

    return (
        <AuthContext.Provider value={{
            user,
            isAuthenticated: !!user,
            isLoading,
            jwtPayload,
            login,
            register,
            logout,
            refreshToken,
            hasPermission,
            hasRole,
            isSuperAdmin
        }}>
            {children}
        </AuthContext.Provider>
    )
}

export const useAuth = () => {
    const context = useContext(AuthContext)
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider')
    }
    return context
}
