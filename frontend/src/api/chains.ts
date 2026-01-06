/**
 * API client for Chain Orchestration endpoints.
 */

import apiClient from './client'
import {
    Chain,
    ChainListItem,
    ChainCreateRequest,
    ChainUpdateRequest,
    ChainExecuteRequest,
    ChainExecution,
    ChainExecutionListItem,
    ChainExecutionLog,
    ChainValidationResult,
    ChainExecutionStatusResponse,
} from '../types/chain'

// ============================================================================
// Chain CRUD
// ============================================================================

export const listChains = async (params?: {
    skip?: number
    limit?: number
    status?: string
    category?: string
}): Promise<ChainListItem[]> => {
    const response = await apiClient.get('/chains', { params })
    return response.data
}

export const getChain = async (chainId: string): Promise<Chain> => {
    const response = await apiClient.get(`/chains/${chainId}`)
    return response.data
}

export const createChain = async (request: ChainCreateRequest): Promise<Chain> => {
    const response = await apiClient.post('/chains', request)
    return response.data
}

export const updateChain = async (
    chainId: string,
    request: ChainUpdateRequest
): Promise<Chain> => {
    const response = await apiClient.put(`/chains/${chainId}`, request)
    return response.data
}

export const deleteChain = async (chainId: string): Promise<void> => {
    await apiClient.delete(`/chains/${chainId}`)
}

// ============================================================================
// Chain Validation
// ============================================================================

export const validateChain = async (chainId: string): Promise<ChainValidationResult> => {
    const response = await apiClient.post(`/chains/${chainId}/validate`)
    return response.data
}

// ============================================================================
// Chain Execution
// ============================================================================

export const executeChain = async (
    chainId: string,
    request: ChainExecuteRequest
): Promise<ChainExecution> => {
    const response = await apiClient.post(
        `/chains/${chainId}/execute`,
        request
    )
    return response.data
}

export const getChainExecutions = async (
    chainId: string,
    params?: { skip?: number; limit?: number }
): Promise<ChainExecutionListItem[]> => {
    const response = await apiClient.get(
        `/chains/${chainId}/executions`,
        { params }
    )
    return response.data
}

export const getExecution = async (executionId: string): Promise<ChainExecution> => {
    const response = await apiClient.get(`/chains/executions/${executionId}`)
    return response.data
}

export const getExecutionStatus = async (
    executionId: string
): Promise<ChainExecutionStatusResponse> => {
    const response = await apiClient.get(
        `/chains/executions/${executionId}/status`
    )
    return response.data
}

export const cancelExecution = async (executionId: string): Promise<void> => {
    await apiClient.post(`/chains/executions/${executionId}/cancel`)
}

export const getExecutionLogs = async (
    executionId: string,
    params?: { skip?: number; limit?: number; level?: string }
): Promise<ChainExecutionLog[]> => {
    const response = await apiClient.get(
        `/chains/executions/${executionId}/logs`,
        { params }
    )
    return response.data
}
