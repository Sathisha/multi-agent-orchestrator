export interface ChatMessage {
    id: string
    session_id: string
    role: 'user' | 'assistant' | 'system'
    content: string
    execution_id?: string
    created_at: string
    message_metadata?: Record<string, any>
}

export interface ChatSession {
    id: string
    user_id: string
    chain_id: string
    title: string
    created_at: string
    updated_at: string
    messages: ChatMessage[]
}

export interface ChatSessionCreateRequest {
    chain_id: string
    title?: string
}

export interface ChatMessageCreateRequest {
    role: 'user' | 'assistant' | 'system'
    content: string
    message_metadata?: Record<string, any>
}
