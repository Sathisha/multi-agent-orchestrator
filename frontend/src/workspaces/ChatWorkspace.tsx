import React, { useState, useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import {
    Box,
    Typography,
    Paper,
    TextField,
    IconButton,
    List,
    ListItem,
    ListItemText,
    ListItemButton,
    Divider,
    Avatar,
    CircularProgress,
    Drawer,
    Button,
    Select,
    MenuItem,
    FormControl,
    InputLabel,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    useTheme,
    Chip
} from '@mui/material'
import {
    Send as SendIcon,
    Add as AddIcon,
    Chat as ChatIcon,
    Person as PersonIcon,
    SmartToy as BotIcon,
    Menu as MenuIcon,
    Delete as DeleteIcon,
    ArrowBack as ArrowBackIcon
} from '@mui/icons-material'
import ReactMarkdown from 'react-markdown'
import { listSessions, createSession, getSession, sendMessage } from '../api/chat'
import { listChains } from '../api/chains'
import { ChatSession, ChatMessage } from '../types/chat'
import { ChainListItem } from '../types/chain'

const ChatWorkspace: React.FC = () => {
    const theme = useTheme()
    const navigate = useNavigate()
    const queryClient = useQueryClient()
    const [searchParams, setSearchParams] = useSearchParams()

    // State
    const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null)
    const [inputMessage, setInputMessage] = useState('')
    const [isSidebarOpen, setIsSidebarOpen] = useState(true)
    const [createDialogOpen, setCreateDialogOpen] = useState(false)
    const [selectedChainId, setSelectedChainId] = useState<string>('')
    const messagesEndRef = useRef<HTMLDivElement | null>(null)

    // Queries
    const { data: sessions = [], isLoading: isLoadingSessions } = useQuery(
        'chatSessions',
        () => listSessions()
    )

    const { data: chains = [] } = useQuery(
        'chains',
        () => listChains()
    )

    const { data: currentSession, isLoading: isLoadingSession } = useQuery(
        ['chatSession', selectedSessionId],
        () => selectedSessionId ? getSession(selectedSessionId) : Promise.resolve(null),
        {
            enabled: !!selectedSessionId,
            refetchInterval: 5000 // Poll for updates? Maybe not needed if we wait for response
        }
    )

    // Mutations
    const createSessionMutation = useMutation(
        (chainId: string) => createSession({ chain_id: chainId }),
        {
            onSuccess: (newSession) => {
                queryClient.invalidateQueries('chatSessions')
                setSelectedSessionId(newSession.id)
                setCreateDialogOpen(false)
            }
        }
    )

    const sendMessageMutation = useMutation(
        (content: string) => sendMessage(selectedSessionId!, { content, role: 'user' }), // Valid role
        {
            onSuccess: (newMessage) => {
                queryClient.invalidateQueries(['chatSession', selectedSessionId])
                setInputMessage('')
            }
        }
    )

    // Effect to scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [currentSession?.messages, sendMessageMutation.isLoading])

    // Effect to check URL param
    useEffect(() => {
        const sid = searchParams.get('session_id')
        if (sid) {
            setSelectedSessionId(sid)
        }
    }, [searchParams])

    useEffect(() => {
        if (selectedSessionId) {
            setSearchParams({ session_id: selectedSessionId })
        }
    }, [selectedSessionId, setSearchParams])

    const handleSendMessage = () => {
        if (!inputMessage.trim() || !selectedSessionId) return
        sendMessageMutation.mutate(inputMessage)
    }

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSendMessage()
        }
    }

    const handleCreateSession = () => {
        if (selectedChainId) {
            createSessionMutation.mutate(selectedChainId)
        }
    }

    return (
        <Box sx={{ display: 'flex', height: '100vh', overflow: 'hidden', bgcolor: 'background.default' }}>
            {/* Sidebar */}
            <Box
                sx={{
                    width: isSidebarOpen ? 300 : 0,
                    flexShrink: 0,
                    transition: 'width 0.3s',
                    overflow: 'hidden',
                    borderRight: 1,
                    borderColor: 'divider',
                    display: 'flex',
                    flexDirection: 'column',
                    bgcolor: 'background.paper'
                }}
            >
                <Box sx={{ p: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Typography variant="h6" fontWeight="bold">Chats</Typography>
                    <IconButton size="small" onClick={() => setCreateDialogOpen(true)} color="primary">
                        <AddIcon />
                    </IconButton>
                </Box>
                <Divider />

                <List sx={{ flex: 1, overflow: 'auto' }}>
                    {isLoadingSessions ? (
                        <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
                            <CircularProgress size={24} />
                        </Box>
                    ) : sessions.length === 0 ? (
                        <Typography variant="body2" color="text.secondary" sx={{ p: 2, textAlign: 'center' }}>
                            No chats yet
                        </Typography>
                    ) : (
                        sessions.map((session) => (
                            <ListItemButton
                                key={session.id}
                                selected={selectedSessionId === session.id}
                                onClick={() => setSelectedSessionId(session.id)}
                            >
                                <ListItemText
                                    primary={session.title}
                                    secondary={new Date(session.updated_at || session.created_at).toLocaleDateString()}
                                    primaryTypographyProps={{ noWrap: true }}
                                />
                            </ListItemButton>
                        ))
                    )}
                </List>
            </Box>

            {/* Main Chat Area */}
            <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%', position: 'relative' }}>
                {/* Header */}
                <Box sx={{
                    p: 2,
                    borderBottom: 1,
                    borderColor: 'divider',
                    display: 'flex',
                    alignItems: 'center',
                    bgcolor: 'background.paper'
                }}>
                    <IconButton onClick={() => setIsSidebarOpen(!isSidebarOpen)} sx={{ mr: 2 }}>
                        {isSidebarOpen ? <ArrowBackIcon /> : <MenuIcon />}
                    </IconButton>
                    <Typography variant="h6">
                        {currentSession?.title || 'Select a chat'}
                    </Typography>
                </Box>

                {/* Messages */}
                {selectedSessionId ? (
                    <Box sx={{ flex: 1, overflow: 'auto', p: 3, display: 'flex', flexDirection: 'column', gap: 2 }}>
                        {/* Render existing messages */}
                        {currentSession?.messages.map((msg) => (
                            <Box
                                key={msg.id}
                                sx={{
                                    display: 'flex',
                                    justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                                    alignItems: 'flex-start',
                                    gap: 1
                                }}
                            >
                                {msg.role !== 'user' && (
                                    <Avatar sx={{ bgcolor: theme.palette.primary.main, width: 32, height: 32 }}>
                                        <BotIcon fontSize="small" />
                                    </Avatar>
                                )}
                                <Paper
                                    elevation={1}
                                    sx={{
                                        p: 2,
                                        maxWidth: '70%',
                                        bgcolor: msg.role === 'user' ? theme.palette.primary.dark : theme.palette.background.paper,
                                        color: msg.role === 'user' ? '#fff' : 'text.primary',
                                        borderRadius: 2
                                    }}
                                >
                                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                                </Paper>
                                {msg.role === 'user' && (
                                    <Avatar sx={{ bgcolor: theme.palette.secondary.main, width: 32, height: 32 }}>
                                        <PersonIcon fontSize="small" />
                                    </Avatar>
                                )}
                            </Box>
                        ))}

                        {/* Optimistic / Loading State */}
                        {sendMessageMutation.isLoading && (
                            <Box sx={{ display: 'flex', justifyContent: 'flex-start', gap: 1 }}>
                                <Avatar sx={{ bgcolor: theme.palette.primary.main, width: 32, height: 32 }}>
                                    <BotIcon fontSize="small" />
                                </Avatar>
                                <Paper sx={{ p: 2, bgcolor: theme.palette.background.paper, borderRadius: 2 }}>
                                    <Box sx={{ display: 'flex', gap: 1 }}>
                                        <CircularProgress size={16} />
                                        <Typography variant="body2">Thinking...</Typography>
                                    </Box>
                                </Paper>
                            </Box>
                        )}
                        <div ref={messagesEndRef} />
                    </Box>
                ) : (
                    <Box sx={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', opacity: 0.5 }}>
                        <ChatIcon sx={{ fontSize: 64, mb: 2 }} />
                        <Typography variant="h5">Select a conversation or start a new one</Typography>
                    </Box>
                )}

                {/* Input Area */}
                {selectedSessionId && (
                    <Box sx={{ p: 2, bgcolor: 'background.paper', borderTop: 1, borderColor: 'divider' }}>
                        <Box sx={{ display: 'flex', gap: 1 }}>
                            <TextField
                                fullWidth
                                variant="outlined"
                                placeholder="Type your message..."
                                value={inputMessage}
                                onChange={(e) => setInputMessage(e.target.value)}
                                onKeyDown={handleKeyPress}
                                disabled={sendMessageMutation.isLoading}
                                multiline
                                maxRows={4}
                            />
                            <Button
                                variant="contained"
                                color="primary"
                                onClick={handleSendMessage}
                                disabled={!inputMessage.trim() || sendMessageMutation.isLoading}
                                sx={{ minWidth: 'auto', px: 3 }}
                            >
                                <SendIcon />
                            </Button>
                        </Box>
                    </Box>
                )}
            </Box>

            {/* Create Dialog */}
            <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="sm" fullWidth>
                <DialogTitle>Start New Chat</DialogTitle>
                <DialogContent>
                    <Typography variant="body2" sx={{ mb: 2 }}>
                        Select a workflow to start chatting with. The workflow must be capable of handling chat input.
                    </Typography>
                    <FormControl fullWidth>
                        <InputLabel>Workflow</InputLabel>
                        <Select
                            value={selectedChainId}
                            label="Workflow"
                            onChange={(e) => setSelectedChainId(e.target.value)}
                        >
                            {chains.map((chain) => (
                                <MenuItem key={chain.id} value={chain.id}>
                                    {chain.name} ({chain.status})
                                </MenuItem>
                            ))}
                        </Select>
                    </FormControl>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
                    <Button
                        onClick={handleCreateSession}
                        variant="contained"
                        disabled={!selectedChainId || createSessionMutation.isLoading}
                    >
                        Start Chat
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    )
}

export default ChatWorkspace
