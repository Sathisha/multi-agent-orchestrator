import React, { useState } from 'react'
import {
    Box,
    Typography,
    IconButton,
    Collapse,
    List,
    ListItem,
    ListItemButton,
    ListItemIcon,
    ListItemText,
    CircularProgress,
    Tooltip,
} from '@mui/material'
import {
    ExpandMore as ExpandMoreIcon,
    ChevronRight as ChevronRightIcon,
    LibraryBooks as KnowledgeIcon,
    Add as AddIcon,
    Folder as FolderIcon,
    FolderOpen as FolderOpenIcon,
    Description as PdfIcon,
    Language as WebIcon,
    MenuBook,
} from '@mui/icons-material'
import { useQuery } from 'react-query'
import { getRAGSources } from '../../api/rag'
import { useNavigate } from 'react-router-dom'

const RAGExplorer: React.FC = () => {
    const navigate = useNavigate()
    const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set(['sources']))

    const { data: sources, isLoading } = useQuery('rag-sources', getRAGSources)

    const toggleFolder = (folderId: string) => {
        const newExpanded = new Set(expandedFolders)
        if (newExpanded.has(folderId)) {
            newExpanded.delete(folderId)
        } else {
            newExpanded.add(folderId)
        }
        setExpandedFolders(newExpanded)
    }

    const getSourceIcon = (type: string) => {
        if (type === 'pdf') return <PdfIcon sx={{ fontSize: 16, color: '#e09867' }} />
        if (type === 'website') return <WebIcon sx={{ fontSize: 16, color: '#4ec9b0' }} />
        return <KnowledgeIcon sx={{ fontSize: 16, color: '#969696' }} />
    }

    return (
        <Box sx={{ p: 1, userSelect: 'none' }}>
            {/* Sources folder */}
            <ListItem
                disablePadding
                sx={{
                    '&:hover': {
                        backgroundColor: '#2a2d2e',
                    },
                }}
            >
                <ListItemButton
                    onClick={() => toggleFolder('sources')}
                    sx={{
                        py: 0.5,
                        px: 1,
                        minHeight: 'auto',
                    }}
                >
                    <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
                        {expandedFolders.has('sources') ? (
                            <ExpandMoreIcon sx={{ fontSize: 16, color: '#cccccc' }} />
                        ) : (
                            <ChevronRightIcon sx={{ fontSize: 16, color: '#cccccc' }} />
                        )}
                    </ListItemIcon>
                    <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
                        {expandedFolders.has('sources') ? (
                            <FolderOpenIcon sx={{ fontSize: 16, color: '#dcb67a' }} />
                        ) : (
                            <FolderIcon sx={{ fontSize: 16, color: '#dcb67a' }} />
                        )}
                    </ListItemIcon>
                    <ListItemText
                        primary="Data Sources"
                        primaryTypographyProps={{
                            fontSize: '13px',
                            color: '#cccccc',
                            fontWeight: 600
                        }}
                    />
                    <Tooltip title="Add New Source">
                        <IconButton
                            size="small"
                            onClick={(e) => { e.stopPropagation(); navigate('/knowledge') }}
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
                </ListItemButton>
            </ListItem>

            {/* Sources list */}
            <Collapse in={expandedFolders.has('sources')}>
                <List sx={{ pl: 0 }} disablePadding>
                    {isLoading ? (
                        <Box sx={{ display: 'flex', justifyContent: 'center', py: 1 }}>
                            <CircularProgress size={16} sx={{ color: '#444' }} />
                        </Box>
                    ) : sources && sources.length > 0 ? (
                        sources.map((source) => (
                            <ListItem
                                key={source.id}
                                disablePadding
                                sx={{
                                    '&:hover': {
                                        backgroundColor: '#2a2d2e',
                                    },
                                }}
                            >
                                <ListItemButton
                                    onClick={() => navigate('/knowledge')}
                                    sx={{
                                        py: 0.5,
                                        pl: 4,
                                        minHeight: 'auto',
                                    }}
                                >
                                    <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
                                        {getSourceIcon(source.source_type)}
                                    </ListItemIcon>
                                    <ListItemText
                                        primary={source.name}
                                        secondary={source.status}
                                        primaryTypographyProps={{
                                            fontSize: '13px',
                                            color: '#cccccc',
                                            noWrap: true
                                        }}
                                        secondaryTypographyProps={{
                                            fontSize: '11px',
                                            color: source.status === 'completed' ? '#4caf50' : '#d16969'
                                        }}
                                    />
                                </ListItemButton>
                            </ListItem>
                        ))
                    ) : (
                        <Typography variant="caption" sx={{ pl: 6, py: 1, color: '#666', fontStyle: 'italic', display: 'block' }}>
                            No sources found
                        </Typography>
                    )}
                </List>
            </Collapse>
        </Box>
    )
}

export default RAGExplorer
