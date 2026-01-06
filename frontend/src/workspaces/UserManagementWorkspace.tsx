import React, { useState, useMemo } from 'react'
import {
    Box, Typography, Button, Card, CardContent, Grid, Dialog, DialogTitle, DialogContent,
    DialogActions, TextField, CircularProgress, IconButton, Menu, MenuItem, Chip,
    InputAdornment, ToggleButtonGroup, ToggleButton, Tooltip, Paper, Divider,
    FormControl, InputLabel, Select, Checkbox, ListItemText, Avatar, Alert
} from '@mui/material'
import {
    Add as AddIcon,
    People as PeopleIcon,
    MoreVert as MoreVertIcon,
    Delete as DeleteIcon,
    Search as SearchIcon,
    ViewModule as ViewModuleIcon,
    ViewList as ViewListIcon,
    Edit as EditIcon,
    Refresh as RefreshIcon,
    CheckCircle as CheckCircleIcon,
    Block as BlockIcon,
    AdminPanelSettings as AdminIcon,
    PersonAdd as PersonAddIcon
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import {
    getUsers, createUser, deleteUser, updateUser,
    getRoles, CreateUserRequest, UpdateUserRequest,
    User, UserDetail, Role
} from '../api/users'

const DEFAULT_ROLES = [
    { id: '5a9143c1-11d9-43c2-841f-846175654321', name: 'admin', description: 'Administrator' },
    { id: '5a9143c1-11d9-43c2-841f-846175654322', name: 'standard', description: 'Standard User' },
    { id: '5a9143c1-11d9-43c2-841f-846175654323', name: 'service', description: 'Service Account' }
]

const UserManagementWorkspace: React.FC = () => {
    const queryClient = useQueryClient()

    // State management
    const [createDialogOpen, setCreateDialogOpen] = useState(false)
    const [editDialogOpen, setEditDialogOpen] = useState(false)
    const [selectedUser, setSelectedUser] = useState<User | null>(null)
    const [searchQuery, setSearchQuery] = useState('')
    const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
    const [filterStatus, setFilterStatus] = useState<string[]>(['active', 'inactive'])
    const [filterRoles, setFilterRoles] = useState<string[]>([])
    const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)

    // Form state for create
    const [newUserEmail, setNewUserEmail] = useState('')
    const [newUserPassword, setNewUserPassword] = useState('')
    const [newUserFullName, setNewUserFullName] = useState('')
    const [newUserStatus, setNewUserStatus] = useState('active')
    const [newUserRoles, setNewUserRoles] = useState<string[]>([])

    // Form state for edit
    const [editUserFullName, setEditUserFullName] = useState('')
    const [editUserEmail, setEditUserEmail] = useState('')
    const [editUserStatus, setEditUserStatus] = useState('')
    const [editUserActive, setEditUserActive] = useState(true)
    const [editUserRoles, setEditUserRoles] = useState<string[]>([])

    // Queries
    const { data: roles, isLoading: rolesLoading } = useQuery('roles', getRoles)
    const availableRoles = (roles && roles.length > 0) ? roles : (DEFAULT_ROLES as unknown as Role[])
    const { data: users, isLoading, refetch } = useQuery('users', getUsers)

    // Mutations
    const createMutation = useMutation(createUser, {
        onSuccess: () => {
            queryClient.invalidateQueries('users')
            setCreateDialogOpen(false)
            resetCreateForm()
        },
    })

    const updateMutation = useMutation(
        ({ userId, data }: { userId: string; data: UpdateUserRequest }) => updateUser(userId, data),
        {
            onSuccess: () => {
                queryClient.invalidateQueries('users')
                setEditDialogOpen(false)
                setSelectedUser(null)
            }
        }
    )

    const deleteMutation = useMutation(deleteUser, {
        onSuccess: () => {
            queryClient.invalidateQueries('users')
        }
    })

    const resetCreateForm = () => {
        setNewUserEmail('')
        setNewUserPassword('')
        setNewUserFullName('')
        setNewUserStatus('active')
        setNewUserRoles([])
    }

    // Filter and search logic
    const filteredUsers = useMemo(() => {
        if (!users) return []

        return users.filter(user => {
            const matchesSearch = user.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                user.email.toLowerCase().includes(searchQuery.toLowerCase())
            const matchesStatus = filterStatus.length === 0 || filterStatus.includes(user.status)
            // Role filtering would require fetching each user's roles, skip for now or implement with detail endpoint
            return matchesSearch && matchesStatus
        })
    }, [users, searchQuery, filterStatus])

    // Statistics
    const stats = useMemo(() => {
        if (!users) return { total: 0, active: 0, admins: 0 }

        return {
            total: users.length,
            active: users.filter(u => u.is_active).length,
            admins: users.filter(u => u.is_system_admin).length
        }
    }, [users])

    const handleCreate = () => {
        createMutation.mutate({
            email: newUserEmail,
            password: newUserPassword,
            full_name: newUserFullName,
            status: newUserStatus,
            role_ids: newUserRoles
        })
    }

    const handleEdit = () => {
        if (!selectedUser) return

        updateMutation.mutate({
            userId: selectedUser.id,
            data: {
                full_name: editUserFullName,
                email: editUserEmail,
                status: editUserStatus,
                is_active: editUserActive,
                role_ids: editUserRoles
            }
        })
    }

    const handleDelete = (userId: string, e?: React.MouseEvent) => {
        e?.stopPropagation()
        if (window.confirm('Are you sure you want to deactivate this user?')) {
            deleteMutation.mutate(userId)
        }
        handleCloseMenu()
    }

    const handleToggleActive = (user: User, e?: React.MouseEvent) => {
        e?.stopPropagation()
        updateMutation.mutate({
            userId: user.id,
            data: { is_active: !user.is_active }
        })
        handleCloseMenu()
    }

    const handleOpenMenu = (event: React.MouseEvent<HTMLElement>, user: User) => {
        event.stopPropagation()
        setAnchorEl(event.currentTarget)
        setSelectedUser(user)
    }

    const handleCloseMenu = () => {
        setAnchorEl(null)
    }

    const handleOpenEditDialog = (user: User) => {
        setSelectedUser(user)
        setEditUserFullName(user.full_name)
        setEditUserEmail(user.email)
        setEditUserStatus(user.status)
        setEditUserActive(user.is_active)
        // Would need to fetch user roles here, for now using empty array
        setEditUserRoles([])
        setEditDialogOpen(true)
        handleCloseMenu()
    }

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'active':
                return { bg: 'rgba(78, 201, 176, 0.2)', color: '#4ec9b0', border: '#4ec9b0' }
            case 'inactive':
                return { bg: 'rgba(150, 150, 150, 0.2)', color: '#969696', border: '#969696' }
            case 'suspended':
                return { bg: 'rgba(244, 135, 113, 0.2)', color: '#f48771', border: '#f48771' }
            default:
                return { bg: 'rgba(150, 150, 150, 0.2)', color: '#969696', border: '#969696' }
        }
    }

    return (
        <Box sx={{ p: 3, height: '100%', overflow: 'auto', bgcolor: '#1e1e1e' }}>
            {/* Header */}
            <Box sx={{ mb: 4 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                    <Box>
                        <Typography variant="h4" sx={{ color: '#cccccc', mb: 1, fontWeight: 600 }}>
                            User Management
                        </Typography>
                        <Typography variant="body2" sx={{ color: '#969696' }}>
                            Manage users and their role assignments
                        </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', gap: 1 }}>
                        <Tooltip title="Refresh">
                            <IconButton onClick={() => refetch()} sx={{ color: '#cccccc' }}>
                                <RefreshIcon />
                            </IconButton>
                        </Tooltip>
                        <Button
                            variant="contained"
                            startIcon={<PersonAddIcon />}
                            onClick={() => setCreateDialogOpen(true)}
                            sx={{
                                backgroundColor: '#007acc',
                                '&:hover': {
                                    backgroundColor: '#005a9e',
                                },
                            }}
                        >
                            Create User
                        </Button>
                    </Box>
                </Box>

                {/* Statistics Cards */}
                <Grid container spacing={2} sx={{ mb: 3 }}>
                    <Grid item xs={12} md={4}>
                        <Paper sx={{ p: 2, bgcolor: '#252526', border: '1px solid #2d2d30' }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                <Box>
                                    <Typography variant="h3" sx={{ color: '#569cd6', fontWeight: 600 }}>
                                        {stats.total}
                                    </Typography>
                                    <Typography variant="body2" sx={{ color: '#969696' }}>
                                        Total Users
                                    </Typography>
                                </Box>
                                <Avatar sx={{ bgcolor: 'rgba(86, 156, 214, 0.2)', width: 56, height: 56 }}>
                                    <PeopleIcon sx={{ color: '#569cd6', fontSize: 32 }} />
                                </Avatar>
                            </Box>
                        </Paper>
                    </Grid>
                    <Grid item xs={12} md={4}>
                        <Paper sx={{ p: 2, bgcolor: '#252526', border: '1px solid #2d2d30' }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                <Box>
                                    <Typography variant="h3" sx={{ color: '#4ec9b0', fontWeight: 600 }}>
                                        {stats.active}
                                    </Typography>
                                    <Typography variant="body2" sx={{ color: '#969696' }}>
                                        Active Users
                                    </Typography>
                                </Box>
                                <Avatar sx={{ bgcolor: 'rgba(78, 201, 176, 0.2)', width: 56, height: 56 }}>
                                    <CheckCircleIcon sx={{ color: '#4ec9b0', fontSize: 32 }} />
                                </Avatar>
                            </Box>
                        </Paper>
                    </Grid>
                    <Grid item xs={12} md={4}>
                        <Paper sx={{ p: 2, bgcolor: '#252526', border: '1px solid #2d2d30' }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                <Box>
                                    <Typography variant="h3" sx={{ color: '#dcdcaa', fontWeight: 600 }}>
                                        {stats.admins}
                                    </Typography>
                                    <Typography variant="body2" sx={{ color: '#969696' }}>
                                        System Admins
                                    </Typography>
                                </Box>
                                <Avatar sx={{ bgcolor: 'rgba(220, 220, 170, 0.2)', width: 56, height: 56 }}>
                                    <AdminIcon sx={{ color: '#dcdcaa', fontSize: 32 }} />
                                </Avatar>
                            </Box>
                        </Paper>
                    </Grid>
                </Grid>

                {/* Search and Filters */}
                <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
                    <TextField
                        placeholder="Search users..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        sx={{ flex: 1, minWidth: 250 }}
                        InputProps={{
                            startAdornment: (
                                <InputAdornment position="start">
                                    <SearchIcon sx={{ color: '#969696' }} />
                                </InputAdornment>
                            ),
                        }}
                    />
                    <FormControl sx={{ minWidth: 150 }}>
                        <InputLabel>Status</InputLabel>
                        <Select
                            multiple
                            value={filterStatus}
                            onChange={(e) => setFilterStatus(e.target.value as string[])}
                            renderValue={(selected) => `${selected.length} selected`}
                        >
                            <MenuItem value="active">
                                <Checkbox checked={filterStatus.includes('active')} />
                                <ListItemText primary="Active" />
                            </MenuItem>
                            <MenuItem value="inactive">
                                <Checkbox checked={filterStatus.includes('inactive')} />
                                <ListItemText primary="Inactive" />
                            </MenuItem>
                            <MenuItem value="suspended">
                                <Checkbox checked={filterStatus.includes('suspended')} />
                                <ListItemText primary="Suspended" />
                            </MenuItem>
                        </Select>
                    </FormControl>
                    <ToggleButtonGroup
                        value={viewMode}
                        exclusive
                        onChange={(_, newMode) => newMode && setViewMode(newMode)}
                        size="small"
                    >
                        <ToggleButton value="grid">
                            <ViewModuleIcon />
                        </ToggleButton>
                        <ToggleButton value="list">
                            <ViewListIcon />
                        </ToggleButton>
                    </ToggleButtonGroup>
                </Box>
            </Box>

            {/* Main Content */}
            <Box>
                <Typography variant="h6" sx={{ color: '#cccccc', mb: 2, fontWeight: 500 }}>
                    Users ({filteredUsers.length})
                </Typography>

                {isLoading ? (
                    <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
                        <CircularProgress />
                    </Box>
                ) : viewMode === 'grid' ? (
                    <Grid container spacing={2}>
                        {filteredUsers?.map((user) => {
                            const statusStyle = getStatusColor(user.status)
                            return (
                                <Grid item xs={12} md={6} lg={4} key={user.id}>
                                    <Card
                                        sx={{
                                            backgroundColor: '#252526',
                                            border: '1px solid #2d2d30',
                                            cursor: 'pointer',
                                            transition: 'all 0.2s ease',
                                            '&:hover': {
                                                backgroundColor: '#2a2d2e',
                                                borderColor: '#007acc',
                                                transform: 'translateY(-2px)',
                                                boxShadow: '0 4px 12px rgba(0, 122, 204, 0.2)',
                                            },
                                            position: 'relative',
                                            height: '100%'
                                        }}
                                        onClick={() => handleOpenEditDialog(user)}
                                    >
                                        <CardContent>
                                            <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 2 }}>
                                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flex: 1 }}>
                                                    <Avatar
                                                        sx={{
                                                            bgcolor: user.is_system_admin ? 'rgba(220, 220, 170, 0.2)' : 'rgba(86, 156, 214, 0.2)',
                                                            color: user.is_system_admin ? '#dcdcaa' : '#569cd6',
                                                            width: 48,
                                                            height: 48,
                                                        }}
                                                    >
                                                        {user.is_system_admin ? <AdminIcon /> : <PeopleIcon />}
                                                    </Avatar>
                                                    <Box sx={{ flex: 1, minWidth: 0 }}>
                                                        <Typography variant="subtitle1" sx={{ color: '#cccccc', fontWeight: 500 }} noWrap>
                                                            {user.full_name}
                                                        </Typography>
                                                        <Typography variant="body2" sx={{ color: '#969696', fontSize: '12px' }} noWrap>
                                                            {user.email}
                                                        </Typography>
                                                    </Box>
                                                </Box>
                                                <IconButton
                                                    size="small"
                                                    onClick={(e) => handleOpenMenu(e, user)}
                                                    sx={{ color: '#969696' }}
                                                >
                                                    <MoreVertIcon fontSize="small" />
                                                </IconButton>
                                            </Box>

                                            <Divider sx={{ my: 1.5, borderColor: '#2d2d30' }} />

                                            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 1 }}>
                                                <Chip
                                                    label={user.status}
                                                    size="small"
                                                    sx={{
                                                        fontSize: '11px',
                                                        height: 22,
                                                        backgroundColor: statusStyle.bg,
                                                        color: statusStyle.color,
                                                        border: `1px solid ${statusStyle.border}`,
                                                    }}
                                                />
                                                {user.is_system_admin && (
                                                    <Chip
                                                        label="Admin"
                                                        size="small"
                                                        sx={{
                                                            fontSize: '11px',
                                                            height: 22,
                                                            backgroundColor: 'rgba(220, 220, 170, 0.2)',
                                                            color: '#dcdcaa',
                                                            border: '1px solid #dcdcaa',
                                                        }}
                                                    />
                                                )}
                                                {!user.is_active && (
                                                    <Chip
                                                        icon={<BlockIcon sx={{ fontSize: 14 }} />}
                                                        label="Inactive"
                                                        size="small"
                                                        sx={{
                                                            fontSize: '11px',
                                                            height: 22,
                                                            backgroundColor: 'rgba(244, 135, 113, 0.2)',
                                                            color: '#f48771',
                                                        }}
                                                    />
                                                )}
                                            </Box>

                                            {user.last_login_at && (
                                                <Typography variant="caption" sx={{ color: '#969696' }}>
                                                    Last login: {new Date(user.last_login_at).toLocaleDateString()}
                                                </Typography>
                                            )}
                                        </CardContent>
                                    </Card>
                                </Grid>
                            )
                        })}
                        {filteredUsers?.length === 0 && (
                            <Grid item xs={12}>
                                <Paper sx={{ p: 4, textAlign: 'center', bgcolor: '#252526', border: '1px solid #2d2d30' }}>
                                    <PeopleIcon sx={{ fontSize: 64, color: '#969696', mb: 2 }} />
                                    <Typography variant="h6" sx={{ color: '#cccccc', mb: 1 }}>
                                        No users found
                                    </Typography>
                                    <Typography variant="body2" sx={{ color: '#969696', mb: 2 }}>
                                        {searchQuery ? 'Try adjusting your search or filters' : 'Create your first user to get started'}
                                    </Typography>
                                    {!searchQuery && (
                                        <Button
                                            variant="contained"
                                            startIcon={<AddIcon />}
                                            onClick={() => setCreateDialogOpen(true)}
                                            sx={{ backgroundColor: '#007acc' }}
                                        >
                                            Create User
                                        </Button>
                                    )}
                                </Paper>
                            </Grid>
                        )}
                    </Grid>
                ) : (
                    // List View
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                        {filteredUsers?.map((user) => {
                            const statusStyle = getStatusColor(user.status)
                            return (
                                <Paper
                                    key={user.id}
                                    sx={{
                                        p: 2,
                                        bgcolor: '#252526',
                                        border: '1px solid #2d2d30',
                                        cursor: 'pointer',
                                        transition: 'all 0.2s ease',
                                        '&:hover': {
                                            bgcolor: '#2a2d2e',
                                            borderColor: '#007acc',
                                        }
                                    }}
                                    onClick={() => handleOpenEditDialog(user)}
                                >
                                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flex: 1 }}>
                                            <Avatar
                                                sx={{
                                                    bgcolor: user.is_system_admin ? 'rgba(220, 220, 170, 0.2)' : 'rgba(86, 156, 214, 0.2)',
                                                    color: user.is_system_admin ? '#dcdcaa' : '#569cd6',
                                                }}
                                            >
                                                {user.is_system_admin ? <AdminIcon /> : <PeopleIcon />}
                                            </Avatar>
                                            <Box sx={{ flex: 1 }}>
                                                <Typography variant="subtitle1" sx={{ color: '#cccccc', fontWeight: 500 }}>
                                                    {user.full_name}
                                                </Typography>
                                                <Typography variant="body2" sx={{ color: '#969696', fontSize: '12px' }}>
                                                    {user.email}
                                                </Typography>
                                            </Box>
                                        </Box>
                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                                            <Chip
                                                label={user.status}
                                                size="small"
                                                sx={{
                                                    fontSize: '11px',
                                                    backgroundColor: statusStyle.bg,
                                                    color: statusStyle.color,
                                                }}
                                            />
                                            {user.is_system_admin && (
                                                <Chip
                                                    label="Admin"
                                                    size="small"
                                                    sx={{ fontSize: '11px', backgroundColor: 'rgba(220, 220, 170, 0.2)', color: '#dcdcaa' }}
                                                />
                                            )}
                                            <IconButton size="small" onClick={(e) => handleOpenMenu(e, user)}>
                                                <MoreVertIcon />
                                            </IconButton>
                                        </Box>
                                    </Box>
                                </Paper>
                            )
                        })}
                    </Box>
                )}
            </Box>

            {/* Context Menu */}
            <Menu
                anchorEl={anchorEl}
                open={Boolean(anchorEl)}
                onClose={handleCloseMenu}
            >
                <MenuItem onClick={() => selectedUser && handleOpenEditDialog(selectedUser)}>
                    <EditIcon fontSize="small" sx={{ mr: 1 }} />
                    Edit
                </MenuItem>
                <MenuItem onClick={() => selectedUser && handleToggleActive(selectedUser)}>
                    {selectedUser?.is_active ? <BlockIcon fontSize="small" sx={{ mr: 1 }} /> : <CheckCircleIcon fontSize="small" sx={{ mr: 1 }} />}
                    {selectedUser?.is_active ? 'Deactivate' : 'Activate'}
                </MenuItem>
                <Divider />
                <MenuItem onClick={() => selectedUser && handleDelete(selectedUser.id)} sx={{ color: '#f48771' }}>
                    <DeleteIcon fontSize="small" sx={{ mr: 1 }} />
                    Delete
                </MenuItem>
            </Menu>

            {/* Create Dialog */}
            <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="sm" fullWidth>
                <DialogTitle sx={{ bgcolor: '#252526', color: '#cccccc' }}>Create New User</DialogTitle>
                <DialogContent sx={{ bgcolor: '#1e1e1e', pt: 2 }}>
                    <TextField
                        autoFocus
                        margin="dense"
                        label="Email"
                        type="email"
                        fullWidth
                        value={newUserEmail}
                        onChange={(e) => setNewUserEmail(e.target.value)}
                        sx={{ mb: 2 }}
                    />
                    <TextField
                        margin="dense"
                        label="Full Name"
                        fullWidth
                        value={newUserFullName}
                        onChange={(e) => setNewUserFullName(e.target.value)}
                        sx={{ mb: 2 }}
                    />
                    <TextField
                        margin="dense"
                        label="Password"
                        type="password"
                        fullWidth
                        value={newUserPassword}
                        onChange={(e) => setNewUserPassword(e.target.value)}
                        helperText="Minimum 8 characters with uppercase, lowercase, and digit"
                        sx={{ mb: 2 }}
                    />
                    <FormControl fullWidth sx={{ mb: 2 }}>
                        <InputLabel>Status</InputLabel>
                        <Select
                            value={newUserStatus}
                            label="Status"
                            onChange={(e) => setNewUserStatus(e.target.value)}
                        >
                            <MenuItem value="active">Active</MenuItem>
                            <MenuItem value="inactive">Inactive</MenuItem>
                            <MenuItem value="suspended">Suspended</MenuItem>
                        </Select>
                    </FormControl>
                    <FormControl fullWidth>
                        <InputLabel>Roles</InputLabel>
                        <Select
                            multiple
                            value={newUserRoles}
                            onChange={(e) => setNewUserRoles(e.target.value as string[])}
                            renderValue={(selected) => (
                                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                                    {selected.map((value) => {
                                        const role = availableRoles?.find(r => r.id === value)
                                        return <Chip key={value} label={role?.name || value} size="small" />
                                    })}
                                </Box>
                            )}
                        >
                            {availableRoles?.map((role) => (
                                <MenuItem key={role.id} value={role.id}>
                                    <Checkbox checked={newUserRoles.includes(role.id)} />
                                    <ListItemText primary={role.name} secondary={role.description} />
                                </MenuItem>
                            ))}
                        </Select>
                    </FormControl>
                </DialogContent>
                <DialogActions sx={{ bgcolor: '#252526' }}>
                    <Button onClick={() => setCreateDialogOpen(false)} sx={{ color: '#969696' }}>Cancel</Button>
                    <Button
                        onClick={handleCreate}
                        disabled={!newUserEmail || !newUserPassword || !newUserFullName || createMutation.isLoading}
                        variant="contained"
                        sx={{ backgroundColor: '#007acc' }}
                    >
                        Create
                    </Button>
                </DialogActions>
            </Dialog>

            {/* Edit Dialog */}
            <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)} maxWidth="sm" fullWidth>
                <DialogTitle sx={{ bgcolor: '#252526', color: '#cccccc' }}>Edit User</DialogTitle>
                <DialogContent sx={{ bgcolor: '#1e1e1e', pt: 2 }}>
                    <TextField
                        margin="dense"
                        label="Email"
                        type="email"
                        fullWidth
                        value={editUserEmail}
                        onChange={(e) => setEditUserEmail(e.target.value)}
                        sx={{ mb: 2 }}
                    />
                    <TextField
                        margin="dense"
                        label="Full Name"
                        fullWidth
                        value={editUserFullName}
                        onChange={(e) => setEditUserFullName(e.target.value)}
                        sx={{ mb: 2 }}
                    />
                    <FormControl fullWidth sx={{ mb: 2 }}>
                        <InputLabel>Status</InputLabel>
                        <Select
                            value={editUserStatus}
                            label="Status"
                            onChange={(e) => setEditUserStatus(e.target.value)}
                        >
                            <MenuItem value="active">Active</MenuItem>
                            <MenuItem value="inactive">Inactive</MenuItem>
                            <MenuItem value="suspended">Suspended</MenuItem>
                        </Select>
                    </FormControl>
                    <FormControl fullWidth sx={{ mb: 2 }}>
                        <InputLabel>Active</InputLabel>
                        <Select
                            value={editUserActive ? 'true' : 'false'}
                            label="Active"
                            onChange={(e) => setEditUserActive(e.target.value === 'true')}
                        >
                            <MenuItem value="true">Yes</MenuItem>
                            <MenuItem value="false">No</MenuItem>
                        </Select>
                    </FormControl>
                    <FormControl fullWidth>
                        <InputLabel>Roles</InputLabel>
                        <Select
                            multiple
                            value={editUserRoles}
                            onChange={(e) => setEditUserRoles(e.target.value as string[])}
                            renderValue={(selected) => (
                                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                                    {selected.map((value) => {
                                        const role = availableRoles?.find(r => r.id === value)
                                        return <Chip key={value} label={role?.name || value} size="small" />
                                    })}
                                </Box>
                            )}
                        >
                            {availableRoles?.map((role) => (
                                <MenuItem key={role.id} value={role.id}>
                                    <Checkbox checked={editUserRoles.includes(role.id)} />
                                    <ListItemText primary={role.name} secondary={role.description} />
                                </MenuItem>
                            ))}
                        </Select>
                    </FormControl>
                </DialogContent>
                <DialogActions sx={{ bgcolor: '#252526' }}>
                    <Button onClick={() => setEditDialogOpen(false)} sx={{ color: '#969696' }}>Cancel</Button>
                    <Button
                        onClick={handleEdit}
                        disabled={updateMutation.isLoading}
                        variant="contained"
                        sx={{ backgroundColor: '#007acc' }}
                    >
                        Save
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    )
}

export default UserManagementWorkspace
