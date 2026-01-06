/**
 * TypeScript types for Chain Orchestration.
 */

export enum ChainNodeType {
    AGENT = 'agent',
    CONDITION = 'condition',
    AGGREGATOR = 'aggregator',
    PARALLEL_SPLIT = 'parallel_split',
    PARALLEL_JOIN = 'parallel_join',
    START = 'start',
    END = 'end',
}

export enum ChainStatus {
    DRAFT = 'draft',
    ACTIVE = 'active',
    ARCHIVED = 'archived',
}

export enum ChainExecutionStatus {
    PENDING = 'pending',
    RUNNING = 'running',
    COMPLETED = 'completed',
    FAILED = 'failed',
    CANCELLED = 'cancelled',
    PAUSED = 'paused',
}

// ============================================================================
// Node & Edge Types for React Flow
// ============================================================================

export interface ChainNodeData {
    label: string
    agentId?: string
    agentName?: string
    nodeType: ChainNodeType
    config?: Record<string, any>
}

export interface ChainNode {
    id: string  // node_id
    type: string  // 'agentNode' | 'conditionNode' | etc. (React Flow node type)
    data: ChainNodeData
    position: { x: number; y: number }
}

export interface ChainEdge {
    id: string  // edge_id
    source: string  // source node_id
    target: string  // target node_id
    label?: string
    condition?: Record<string, any>
    type?: string  // Edge type for React Flow
}

// ============================================================================
// API Types (matching backend Pydantic schemas)
// ============================================================================

export interface ChainNodeSchema {
    node_id: string
    node_type: ChainNodeType
    agent_id?: string
    label: string
    position_x: number
    position_y: number
    config?: Record<string, any>
    order_index?: number
}

export interface ChainEdgeSchema {
    edge_id: string
    source_node_id: string
    target_node_id: string
    condition?: Record<string, any>
    label?: string
}

export interface ChainNodeResponse extends ChainNodeSchema {
    id: string
    chain_id: string
    created_at: string
    updated_at: string
}

export interface ChainEdgeResponse extends ChainEdgeSchema {
    id: string
    chain_id: string
    created_at: string
    updated_at: string
}

export interface Chain {
    id: string
    name: string
    description?: string
    status: ChainStatus
    version: string
    category?: string
    tags: string[]
    nodes: ChainNodeResponse[]
    edges: ChainEdgeResponse[]
    input_schema?: Record<string, any>
    output_schema?: Record<string, any>
    execution_count: number
    last_executed_at?: string
    created_at: string
    updated_at: string
    chain_metadata?: Record<string, any>
}

export interface ChainListItem {
    id: string
    name: string
    description?: string
    status: ChainStatus
    version: string
    category?: string
    tags: string[]
    node_count: number
    execution_count: number
    last_executed_at?: string
    created_at: string
    updated_at: string
}

export interface ChainCreateRequest {
    name: string
    description?: string
    category?: string
    tags?: string[]
    nodes: ChainNodeSchema[]
    edges: ChainEdgeSchema[]
    input_schema?: Record<string, any>
    output_schema?: Record<string, any>
    status?: ChainStatus
    metadata?: Record<string, any>
}

export interface ChainUpdateRequest {
    name?: string
    description?: string
    category?: string
    tags?: string[]
    nodes?: ChainNodeSchema[]
    edges?: ChainEdgeSchema[]
    input_schema?: Record<string, any>
    output_schema?: Record<string, any>
    status?: ChainStatus
    metadata?: Record<string, any>
}

export interface ChainExecuteRequest {
    input_data: Record<string, any>
    execution_name?: string
    variables?: Record<string, any>
    correlation_id?: string
}

export interface ChainExecution {
    id: string
    chain_id: string
    execution_name?: string
    status: ChainExecutionStatus
    input_data: Record<string, any>
    output_data?: Record<string, any>
    variables: Record<string, any>
    node_results: Record<string, any>
    started_at?: string
    completed_at?: string
    duration_seconds?: number
    current_node_id?: string
    completed_nodes: string[]
    active_edges?: string[]
    edge_results?: Record<string, any>
    error_message?: string
    error_details?: Record<string, any>
    correlation_id?: string
    created_at: string
    updated_at: string
}

export interface ChainExecutionListItem {
    id: string
    chain_id: string
    execution_name?: string
    status: ChainExecutionStatus
    started_at?: string
    completed_at?: string
    duration_seconds?: number
    error_message?: string
    created_at: string
}

export interface ChainExecutionLog {
    id: string
    execution_id: string
    node_id?: string
    event_type: string
    message: string
    level: string
    timestamp: string
    metadata?: Record<string, any>
}

export interface ChainValidationResult {
    is_valid: boolean
    errors: string[]
    warnings: string[]
    details: Record<string, any>
}

export interface ChainExecutionStatusResponse {
    execution_id: string
    status: ChainExecutionStatus
    current_node_id?: string
    active_edges?: string[]
    completed_nodes: string[]
    node_states?: Record<string, string>
    progress_percentage: number
    error_message?: string
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Convert backend ChainNodeResponse to React Flow node format.
 */
export function toReactFlowNode(node: ChainNodeResponse): ChainNode {
    return {
        id: node.node_id,
        type: getNodeTypeForReactFlow(node.node_type),
        data: {
            label: node.label,
            agentId: node.agent_id,
            nodeType: node.node_type,
            config: node.config || {},
        },
        position: {
            x: node.position_x,
            y: node.position_y,
        },
    }
}

/**
 * Convert backend ChainEdgeResponse to React Flow edge format.
 */
export function toReactFlowEdge(edge: ChainEdgeResponse): ChainEdge {
    return {
        id: edge.edge_id,
        source: edge.source_node_id,
        target: edge.target_node_id,
        label: edge.label,
        condition: edge.condition,
        type: 'smoothstep',  // or 'default', 'step', 'straight'
    }
}

/**
 * Convert React Flow node to backend ChainNodeSchema.
 */
export function toChainNodeSchema(node: ChainNode, index: number): ChainNodeSchema {
    return {
        node_id: node.id,
        node_type: node.data.nodeType,
        agent_id: node.data.agentId,
        label: node.data.label,
        position_x: node.position.x,
        position_y: node.position.y,
        config: node.data.config || {},
        order_index: index,
    }
}

/**
 * Convert React Flow edge to backend ChainEdgeSchema.
 */
export function toChainEdgeSchema(edge: ChainEdge): ChainEdgeSchema {
    return {
        edge_id: edge.id,
        source_node_id: edge.source,
        target_node_id: edge.target,
        condition: edge.condition,
        label: edge.label,
    }
}

/**
 * Get React Flow node type based on chain node type.
 */
function getNodeTypeForReactFlow(nodeType: ChainNodeType): string {
    switch (nodeType) {
        case ChainNodeType.AGENT:
            return 'agentNode'
        case ChainNodeType.CONDITION:
            return 'conditionNode'
        case ChainNodeType.AGGREGATOR:
            return 'aggregatorNode'
        case ChainNodeType.PARALLEL_SPLIT:
            return 'parallelSplitNode'
        case ChainNodeType.PARALLEL_JOIN:
            return 'parallelJoinNode'
        case ChainNodeType.START:
            return 'startNode'
        case ChainNodeType.END:
            return 'endNode'
        default:
            return 'default'
    }
}

// Type aliases for consistency
export type ChainNodeRequest = ChainNodeSchema
export type ChainEdgeRequest = ChainEdgeSchema
