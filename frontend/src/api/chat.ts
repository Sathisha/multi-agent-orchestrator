import apiClient from './client'
import {
    ChatSession,
    ChatMessage,
    ChatSessionCreateRequest,
    ChatMessageCreateRequest
} from '../types/chat'

export const listSessions = async (params?: {
    skip?: number
    limit?: number
}): Promise<ChatSession[]> => {
    const response = await apiClient.get('/chat/sessions', { params })
    return response.data
}

export const createSession = async (request: ChatSessionCreateRequest): Promise<ChatSession> => {
    const response = await apiClient.post('/chat/sessions', request)
    return response.data
}

export const getSession = async (sessionId: string): Promise<ChatSession> => {
    const response = await apiClient.get(`/chat/sessions/${sessionId}`)
    return response.data
}

export const sendMessage = async (
    sessionId: string,
    request: ChatMessageCreateRequest
): Promise<ChatMessage> => {
    const response = await apiClient.post(`/chat/sessions/${sessionId}/messages`, request)
    return response.data
}
