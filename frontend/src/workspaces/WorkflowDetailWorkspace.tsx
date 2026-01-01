import React from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Box, Typography, IconButton, CircularProgress } from '@mui/material'
import { ArrowBack } from '@mui/icons-material'
import { useQuery } from 'react-query'
import { getWorkflow } from '../api/workflows'

const WorkflowDetailWorkspace: React.FC = () => {
    const { workflowId } = useParams<{ workflowId: string }>()
    const navigate = useNavigate()

    const { data: workflow, isLoading } = useQuery(
        ['workflow', workflowId],
        () => getWorkflow(workflowId!),
        { enabled: !!workflowId }
    )

    if (isLoading) {
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                <CircularProgress />
            </Box>
        )
    }

    if (!workflow) {
        return (
            <Box sx={{ p: 3 }}>
                <Typography color="error">Workflow not found</Typography>
            </Box>
        )
    }

    return (
        <Box sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
                <IconButton onClick={() => navigate('/workflows')} size="small">
                    <ArrowBack />
                </IconButton>
                <Typography variant="h5">{workflow.name}</Typography>
            </Box>

            <Typography variant="body1" sx={{ mb: 2 }}>
                {workflow.description || 'No description'}
            </Typography>

            <Typography variant="caption" color="text.secondary">
                Status: {workflow.status} | Version: {workflow.version} | Executions: {workflow.execution_count}
            </Typography>

            <Box sx={{ mt: 4 }}>
                <Typography variant="h6" gutterBottom>BPMN Diagram</Typography>
                <Typography color="text.secondary">
                    BPMN designer integration coming soon...
                </Typography>
            </Box>
        </Box>
    )
}

export default WorkflowDetailWorkspace
