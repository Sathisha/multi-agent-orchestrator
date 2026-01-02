import React, { createContext, useContext, useState, useCallback } from 'react'
import { Snackbar, Alert, AlertColor } from '@mui/material'

interface Notification {
    message: string
    severity: AlertColor
    id: number
}

interface NotificationContextType {
    showNotification: (message: string, severity?: AlertColor) => void
    showError: (message: string) => void
    showSuccess: (message: string) => void
    showWarning: (message: string) => void
    showInfo: (message: string) => void
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined)

export const useNotification = () => {
    const context = useContext(NotificationContext)
    if (!context) {
        throw new Error('useNotification must be used within NotificationProvider')
    }
    return context
}

export const NotificationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [notification, setNotification] = useState<Notification | null>(null)

    const showNotification = useCallback((message: string, severity: AlertColor = 'info') => {
        setNotification({
            message,
            severity,
            id: Date.now()
        })
    }, [])

    const showError = useCallback((message: string) => {
        showNotification(message, 'error')
    }, [showNotification])

    const showSuccess = useCallback((message: string) => {
        showNotification(message, 'success')
    }, [showNotification])

    const showWarning = useCallback((message: string) => {
        showNotification(message, 'warning')
    }, [showNotification])

    const showInfo = useCallback((message: string) => {
        showNotification(message, 'info')
    }, [showNotification])

    const handleClose = () => {
        setNotification(null)
    }

    return (
        <NotificationContext.Provider value={{ showNotification, showError, showSuccess, showWarning, showInfo }}>
            {children}
            <Snackbar
                open={!!notification}
                autoHideDuration={6000}
                onClose={handleClose}
                anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
            >
                {notification && (
                    <Alert onClose={handleClose} severity={notification.severity} sx={{ width: '100%' }}>
                        {notification.message}
                    </Alert>
                )}
            </Snackbar>
        </NotificationContext.Provider>
    )
}
