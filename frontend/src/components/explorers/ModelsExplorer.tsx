
import React from 'react'
import {
    Box,
    Typography,
    List,
    ListItem,
    ListItemButton,
    ListItemIcon,
    ListItemText,
    CircularProgress,
    IconButton,
    Tooltip,
} from '@mui/material'
import {
    Dns as LLMIcon,
    Add as AddIcon,
} from '@mui/icons-material'
import { useQuery } from 'react-query'
import { getModels } from '../../api/llmModels'
import { useNavigate } from 'react-router-dom'

const ModelsExplorer: React.FC = () => {
    const navigate = useNavigate()
    const { data: models, isLoading } = useQuery('llm_models', getModels)

    return (
        <Box sx={{ p: 1, userSelect: 'none' }}>
            <ListItem
                disablePadding
                sx={{
                    mb: 1,
                    px: 1,
                }}
            >
                <Box sx={{ display: 'flex', alignItems: 'center', width: '100%', justifyContent: 'space-between' }}>
                    <Typography
                        variant="caption"
                        sx={{
                            color: '#cccccc',
                            fontWeight: 'bold',
                            fontSize: '11px',
                            letterSpacing: '0.5px',
                        }}
                    >
                        CONFIGURED MODELS
                    </Typography>
                    <Tooltip title="Create New Model">
                        <IconButton
                            size="small"
                            onClick={() => navigate('/models')}
                            sx={{
                                color: '#cccccc',
                                opacity: 0.7,
                                '&:hover': {
                                    opacity: 1,
                                    backgroundColor: '#37373d',
                                },
                            }}
                        >
                            <AddIcon sx={{ fontSize: 14 }} />
                        </IconButton>
                    </Tooltip>
                </Box>
            </ListItem>

            {isLoading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', py: 1 }}>
                    <CircularProgress size={16} sx={{ color: '#444' }} />
                </Box>
            ) : (
                <List sx={{ pl: 0 }} disablePadding>
                    {models && models.length > 0 ? (
                        models.map((model) => (
                            <ListItem
                                key={model.id}
                                disablePadding
                                sx={{
                                    '&:hover': {
                                        backgroundColor: '#2a2d2e',
                                    },
                                }}
                            >
                                <ListItemButton
                                    onClick={() => navigate('/models')} // TODO: maybe navigate to specific model edit? For now, just /models
                                    sx={{
                                        py: 0.5,
                                        px: 1,
                                        minHeight: 'auto',
                                    }}
                                >
                                    <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
                                        <LLMIcon sx={{ fontSize: 16, color: '#569cd6' }} />
                                    </ListItemIcon>
                                    <ListItemText
                                        primary={model.name}
                                        secondary={model.provider}
                                        primaryTypographyProps={{
                                            fontSize: '13px',
                                            color: '#cccccc',
                                            noWrap: true
                                        }}
                                        secondaryTypographyProps={{
                                            fontSize: '11px',
                                            color: '#888888',
                                            noWrap: true
                                        }}
                                    />
                                    {model.is_default && (
                                        <Typography variant="caption" sx={{ color: '#4ec9b0', fontSize: '10px', ml: 1 }}>
                                            Default
                                        </Typography>
                                    )}
                                </ListItemButton>
                            </ListItem>
                        ))
                    ) : (
                        <Typography variant="caption" sx={{ pl: 2, py: 1, color: '#666', fontStyle: 'italic', display: 'block' }}>
                            No models configured
                        </Typography>
                    )}
                </List>
            )}
        </Box>
    )
}

export default ModelsExplorer
