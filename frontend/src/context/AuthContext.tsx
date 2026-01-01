import React, { createContext, useState, useEffect, useContext } from 'react'
import { User, LoginRequest, RegisterRequest, login as apiLogin, register as apiRegister, getCurrentUser, logout as apiLogout } from '../api/auth'

interface AuthContextType {
    user: User | null
    isAuthenticated: boolean
    isLoading: boolean
    login: (data: LoginRequest) => Promise<void>
    register: (data: RegisterRequest) => Promise<void>
    logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<User | null>(null)
    const [isLoading, setIsLoading] = useState(true)

    useEffect(() => {
        const initAuth = async () => {
            const token = localStorage.getItem('token')
            console.log('[AuthContext] Initializing auth, token:', token ? 'exists' : 'none')
            if (token) {
                try {
                    const userData = await getCurrentUser()
                    console.log('[AuthContext] User loaded:', userData.email)
                    setUser(userData)
                } catch (error) {
                    console.error('[AuthContext] Failed to fetch user', error)
                    localStorage.removeItem('token')
                    localStorage.removeItem('refreshToken')
                }
            }
            setIsLoading(false)
            console.log('[AuthContext] Auth initialized, isAuthenticated:', !!token)
        }
        initAuth()
    }, [])

    const login = async (data: LoginRequest) => {
        setIsLoading(true)
        try {
            const response = await apiLogin(data)
            localStorage.setItem('token', response.access_token)
            localStorage.setItem('refreshToken', response.refresh_token)
            // Fetch user details immediately after login
            const userData = await getCurrentUser()
            setUser(userData)
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
            localStorage.removeItem('token')
            localStorage.removeItem('refreshToken')
            setUser(null)
        }
    }

    return (
        <AuthContext.Provider value={{ user, isAuthenticated: !!user, isLoading, login, register, logout }}>
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
