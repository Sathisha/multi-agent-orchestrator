import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import {
    Box,
    Button,
    Typography,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Paper,
    Chip,
    IconButton,
    TextField,
    InputAdornment,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
} from '@mui/material'
import {
    Add as AddIcon,
    Search as SearchIcon,
    Edit as EditIcon,
    Delete as DeleteIcon,
    PlayArrow as PlayArrowIcon,
    Visibility as VisibilityIcon,
} from '@mui/icons-material'
import { listChains, createChain, deleteChain } from '../api/chains'
import { ChainListItem, ChainStatus } from '../types/chain'

const ChainWorkspace: React.FC = () => {
    const navigate = useNavigate()
    const queryClient = useQueryClient()
    const [searchQuery, setSearchQuery] = useState('')
    const [createDialogOpen, setCreateDialogOpen] = useState(false)
    const [newChainName, setNewChainName] = useState('')
    const [newChainDescription, setNewChainDescription] = useState('')

    // Fetch chains
    const { data: chains = [], isLoading } = useQuery<ChainListItem[]>(
        'chains',
        () => listChains()
    )

    // Create chain mutation
    const createMutation = useMutation(
        () => createChain({
            name: newChainName,
            description: newChainDescription,
            nodes: [],
            edges: [],
            status: ChainStatus.DRAFT,
        }),
        {
            onSuccess: (newChain) => {
                queryClient.invalidateQueries('chains')
                setCreateDialogOpen(false)
                setNewChainName('')
                setNewChainDescription('')
                // Navigate to the new chain
                navigate(`/chains/${newChain.id}`)
            },
        }
    )

    // Delete chain mutation
    const deleteMutation = useMutation(
        (chainId: string) => deleteChain(chainId),
        {
            onSuccess: () => {
                queryClient.invalidateQueries('chains')
            },
        }
    )

    const filteredChains = chains.filter((chain) =>
        chain.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (chain.description?.toLowerCase().includes(searchQuery.toLowerCase()))
    )

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'active':
                return 'success'
            case 'draft':
                return 'default'
            case 'archived':
                return 'error'
            default:
                return 'default'
        }
    }

    const handleCreateChain = () => {
        if (newChainName.trim()) {
            createMutation.mutate()
        }
    }

    const handleDeleteChain = (chainId: string, chainName: string) => {
        if (window.confirm(`Are you sure you want to delete "${chainName}"?`)) {
            deleteMutation.mutate(chainId)
        }
    }

    return (
        <Box sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column' }}>
            {/* Header */}
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                <Box>
                    <Typography variant="h4" gutterBottom>
                        Agent Chains
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                        Create and manage agent orchestration chains
                    </Typography>
                </Box>
                <Button
                    variant="contained"
                    startIcon={<AddIcon />}
                    onClick={() => setCreateDialogOpen(true)}
                >
                    Create Chain
                </Button>
            </Box>

            {/* Search */}
            <TextField
                placeholder="Search chains..."
                variant="outlined"
                size="small"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                sx={{ mb: 2, maxWidth: 400 }}
                InputProps={{
                    startAdornment: (
                        <InputAdornment position="start">
                            <SearchIcon />
                        </InputAdornment>
                    ),
                }}
            />

            {/* Chains Table */}
            <TableContainer component={Paper} sx={{ flex: 1, overflow: 'auto' }}>
                <Table stickyHeader>
                    <TableHead>
                        <TableRow>
                            <TableCell>Name</TableCell>
                            <TableCell>Description</TableCell>
                            <TableCell>Status</TableCell>
                            <TableCell align="center">Nodes</TableCell>
                            <TableCell align="center">Executions</TableCell>
                            <TableCell>Last Executed</TableCell>
                            <TableCell align="right">Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {isLoading ? (
                            <TableRow>
                                <TableCell colSpan={7} align="center">
                                    Loading chains...
                                </TableCell>
                            </TableRow>
                        ) : filteredChains.length === 0 ? (
                            <TableRow>
                                <TableCell colSpan={7} align="center">
                                    <Box sx={{ py: 4 }}>
                                        <Typography variant="body1" color="text.secondary" gutterBottom>
                                            No chains found
                                        </Typography>
                                        <Typography variant="body2" color="text.secondary">
                                            {searchQuery
                                                ? 'Try adjusting your search'
                                                : 'Create your first chain to get started'}
                                        </Typography>
                                    </Box>
                                </TableCell>
                            </TableRow>
                        ) : (
                            filteredChains.map((chain) => (
                                <TableRow
                                    key={chain.id}
                                    hover
                                    sx={{ cursor: 'pointer' }}
                                    onClick={() => navigate(`/chains/${chain.id}`)}
                                >
                                    <TableCell>
                                        <Typography variant="body1" fontWeight="medium">
                                            {chain.name}
                                        </Typography>
                                    </TableCell>
                                    <TableCell>
                                        <Typography variant="body2" color="text.secondary" noWrap>
                                            {chain.description || '-'}
                                        </Typography>
                                    </TableCell>
                                    <TableCell>
                                        <Chip
                                            label={chain.status}
                                            size="small"
                                            color={getStatusColor(chain.status) as any}
                                        />
                                    </TableCell>
                                    <TableCell align="center">{chain.node_count}</TableCell>
                                    <TableCell align="center">{chain.execution_count}</TableCell>
                                    <TableCell>
                                        {chain.last_executed_at
                                            ? new Date(chain.last_executed_at).toLocaleString()
                                            : 'Never'}
                                    </TableCell>
                                    <TableCell align="right" onClick={(e) => e.stopPropagation()}>
                                        <IconButton
                                            size="small"
                                            onClick={() => navigate(`/chains/${chain.id}`)}
                                            title="View/Edit"
                                        >
                                            <EditIcon fontSize="small" />
                                        </IconButton>
                                        <IconButton
                                            size="small"
                                            onClick={() => handleDeleteChain(chain.id, chain.name)}
                                            title="Delete"
                                            color="error"
                                        >
                                            <DeleteIcon fontSize="small" />
                                        </IconButton>
                                    </TableCell>
                                </TableRow>
                            ))
                        )}
                    </TableBody>
                </Table>
            </TableContainer>

            {/* Create Chain Dialog */}
            <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="sm" fullWidth>
                <DialogTitle>Create New Chain</DialogTitle>
                <DialogContent>
                    <TextField
                        autoFocus
                        margin="dense"
                        label="Chain Name"
                        fullWidth
                        variant="outlined"
                        value={newChainName}
                        onChange={(e) => setNewChainName(e.target.value)}
                        sx={{ mb: 2 }}
                    />
                    <TextField
                        margin="dense"
                        label="Description (optional)"
                        fullWidth
                        variant="outlined"
                        multiline
                        rows={3}
                        value={newChainDescription}
                        onChange={(e) => setNewChainDescription(e.target.value)}
                    />
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
                    <Button
                        onClick={handleCreateChain}
                        variant="contained"
                        disabled={!newChainName.trim() || createMutation.isLoading}
                    >
                        {createMutation.isLoading ? 'Creating...' : 'Create'}
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    )
}

export default ChainWorkspace
