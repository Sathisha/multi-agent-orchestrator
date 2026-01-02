import React from 'react'
import {
    Box,
    Typography,
    List,
    ListItem,
    ListItemText,
    Chip,
    CircularProgress,
    IconButton
} from '@mui/material'
import {
    PlayArrow as PlayIcon,
    CheckCircle as CheckIcon,
    Error as ErrorIcon,
    Cancel as CancelIcon,
    Refresh as RefreshIcon
} from '@mui/icons-material'
import { ChainExecutionListItem } from '../../types/chain'

interface ExecutionHistoryProps {
    executions: ChainExecutionListItem[]
    selectedExecutionId?: string
    onSelectExecution: (executionId: string) => void
    isLoading?: boolean
    onRefresh: () => void
}

const getStatusIcon = (status: string) => {
    switch (status) {
        case 'completed': return <CheckIcon fontSize="small" color="success" />
        case 'failed': return <ErrorIcon fontSize="small" color="error" />
        case 'cancelled': return <CancelIcon fontSize="small" color="disabled" />
        case 'running': return <CircularProgress size={16} />
        default: return <PlayIcon fontSize="small" color="action" />
    }
}

const ExecutionHistory: React.FC<ExecutionHistoryProps> = ({
    executions,
    selectedExecutionId,
    onSelectExecution,
    isLoading,
    onRefresh
}) => {
    return (
        <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #eee' }}>
                <Typography variant="subtitle2" fontWeight="bold">
                    Execution History
                </Typography>
                <IconButton size="small" onClick={onRefresh} disabled={isLoading}>
                    <RefreshIcon fontSize="small" />
                </IconButton>
            </Box>

            {isLoading && executions.length === 0 ? (
                <Box sx={{ p: 2, textAlign: 'center' }}>
                    <CircularProgress size={24} />
                </Box>
            ) : executions.length === 0 ? (
                <Box sx={{ p: 2, textAlign: 'center' }}>
                    <Typography variant="body2" color="text.secondary">
                        No executions yet
                    </Typography>
                </Box>
            ) : (
                <List sx={{ overflow: 'auto', flex: 1, p: 0 }}>
                    {executions.map((exec) => (
                        <ListItem
                            key={exec.id}
                            button
                            selected={selectedExecutionId === exec.id}
                            onClick={() => onSelectExecution(exec.id)}
                            divider
                            sx={{
                                borderLeft: selectedExecutionId === exec.id ? '4px solid #007acc' : '4px solid transparent'
                            }}
                        >
                            <Box sx={{ mr: 1, display: 'flex', alignItems: 'center' }}>
                                {getStatusIcon(exec.status)}
                            </Box>
                            <ListItemText
                                primary={
                                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                        <Typography variant="body2" fontWeight="medium">
                                            {new Date(exec.started_at || exec.created_at).toLocaleString()}
                                        </Typography>
                                    </Box>
                                }
                                secondary={
                                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, mt: 0.5 }}>
                                        <Box sx={{ display: 'flex', gap: 1 }}>
                                            <Chip
                                                label={exec.status}
                                                size="small"
                                                color={exec.status === 'completed' ? 'success' : exec.status === 'failed' ? 'error' : 'default'}
                                                sx={{ height: 20, fontSize: '0.6rem' }}
                                            />
                                            {exec.duration_seconds != null && (
                                                <Typography variant="caption" color="text.secondary">
                                                    {Number(exec.duration_seconds).toFixed(2)}s
                                                </Typography>
                                            )}
                                        </Box>
                                        {exec.error_message && (
                                            <Typography variant="caption" color="error" noWrap title={exec.error_message}>
                                                {exec.error_message}
                                            </Typography>
                                        )}
                                    </Box>
                                }
                            />
                        </ListItem>
                    ))}
                </List>
            )}
        </Box>
    )
}

export default ExecutionHistory
