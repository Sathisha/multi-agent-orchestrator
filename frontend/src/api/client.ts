import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'

const apiClient = axios.create({
    baseURL: '/api/v1',
    headers: {
        'Content-Type': 'application/json',
    },
})

// Flag to prevent multiple refresh attempts
let isRefreshing = false
let failedQueue: Array<{
    resolve: (value?: any) => void
    reject: (reason?: any) => void
}> = []

const processQueue = (error: AxiosError | null, token: string | null = null) => {
    failedQueue.forEach(prom => {
        if (error) {
            prom.reject(error)
        } else {
            prom.resolve(token)
        }
    })
    failedQueue = []
}

// Request interceptor to add auth token
apiClient.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('token')
        if (token) {
            config.headers.Authorization = `Bearer ${token}`
        }
        return config
    },
    (error) => {
        return Promise.reject(error)
    }
)

// Response interceptor to handle errors and token refresh
apiClient.interceptors.response.use(
    (response) => {
        return response
    },
    async (error: AxiosError) => {
        const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

        // Handle 401 errors
        if (error.response && error.response.status === 401) {
            // Skip refresh for login and refresh endpoints
            if (originalRequest.url?.includes('/auth/login') ||
                originalRequest.url?.includes('/auth/refresh') ||
                originalRequest.url?.includes('/auth/register')) {
                return Promise.reject(error)
            }

            // If we haven't tried to refresh yet
            if (!originalRequest._retry) {
                if (isRefreshing) {
                    // If already refreshing, queue this request
                    return new Promise((resolve, reject) => {
                        failedQueue.push({ resolve, reject })
                    }).then(token => {
                        if (originalRequest.headers) {
                            originalRequest.headers.Authorization = `Bearer ${token}`
                        }
                        return apiClient(originalRequest)
                    }).catch(err => {
                        return Promise.reject(err)
                    })
                }

                originalRequest._retry = true
                isRefreshing = true

                const refreshToken = localStorage.getItem('refreshToken')

                if (!refreshToken) {
                    // No refresh token, redirect to login
                    localStorage.removeItem('token')
                    localStorage.removeItem('refreshToken')
                    window.location.href = '/login'
                    return Promise.reject(error)
                }

                try {
                    // Attempt to refresh the token
                    const response = await axios.post('/api/v1/auth/refresh', {
                        refresh_token: refreshToken
                    })

                    const { access_token, refresh_token: newRefreshToken } = response.data

                    // Update tokens
                    localStorage.setItem('token', access_token)
                    if (newRefreshToken) {
                        localStorage.setItem('refreshToken', newRefreshToken)
                    }

                    // Update authorization header
                    if (originalRequest.headers) {
                        originalRequest.headers.Authorization = `Bearer ${access_token}`
                    }

                    // Process queued requests
                    processQueue(null, access_token)
                    isRefreshing = false

                    // Retry the original request
                    return apiClient(originalRequest)
                } catch (refreshError) {
                    // Refresh failed, clear auth and redirect
                    processQueue(refreshError as AxiosError, null)
                    isRefreshing = false
                    localStorage.removeItem('token')
                    localStorage.removeItem('refreshToken')
                    window.location.href = '/login'
                    return Promise.reject(refreshError)
                }
            }
        }

        return Promise.reject(error)
    }
)

export default apiClient
