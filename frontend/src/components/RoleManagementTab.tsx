import React, { useState, useMemo } from 'react'
import {
    Box, Typography, Button, Card, CardContent, Grid, Dialog, DialogTitle, DialogContent,
    DialogActions, TextField, CircularProgress, IconButton, Menu, MenuItem, Chip,
    Paper, Divider, FormGroup, FormControlLabel, Checkbox, Alert, Accordion,
    AccordionSummary, AccordionDetails
} from '@mui/material'
import {
    Add as AddIcon,
    Security as SecurityIcon,
    MoreVert as MoreVertIcon,
    Delete as DeleteIcon,
    Edit as EditIcon,
    ExpandMore as ExpandMoreIcon,
    Lock as LockIcon
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import {
    getRoles, createRole, updateRole, deleteRole, getPermissions,
    Role, Permission, CreateRoleRequest, UpdateRoleRequest
} from '../api/users'

const RoleManagementTab: React.FC = () => {
    const queryClient = useQueryClient()

    // State management
    const [createDialogOpen, setCreateDialogOpen] = useState(false)
    const [editDialogOpen, setEditDialogOpen] = useState(false)
    const [selectedRole, setSelectedRole] = useState<Role | null>(null)
    const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)

    // Form state
    const [roleName, setRoleName] = useState('')
    const [roleDescription, setRoleDescription] = useState('')
    const [selectedPermissions, setSelectedPermissions] = useState<string[]>([])

    // Queries
    const { data: roles, isLoading: rolesLoading } = useQuery('roles', getRoles)
    const { data: permissions, isLoading: permissionsLoading } = useQuery('permissions', getPermissions)

    // Mutations
    const createMutation = useMutation(createRole, {
        onSuccess: () => {
            queryClient.invalidateQueries('roles')
            setCreateDialogOpen(false)
            resetForm()
        },
    })

    const updateMutation = useMutation(
        ({ roleId, data }: { roleId: string; data: UpdateRoleRequest }) => updateRole(roleId, data),
        {
            onSuccess: () => {
                queryClient.invalidateQueries('roles')
                setEditDialogOpen(false)
                setSelectedRole(null)
            }
        }
    )

    const deleteMutation = useMutation(deleteRole, {
        onSuccess: () => {
            queryClient.invalidateQueries('roles')
        }
    })

    const resetForm = () => {
        setRoleName('')
        setRoleDescription('')
        setSelectedPermissions([])
    }

    // Group permissions by resource
    const groupedPermissions = useMemo(() => {
        if (!permissions) return {}

        const grouped: Record<string, Permission[]> = {}
        permissions.forEach(perm => {
            const resource = perm.resource || perm.name.split('.')[0]
            if (!grouped[resource]) {
                grouped[resource] = []
            }
            grouped[resource].push(perm)
        })
        return grouped
    }, [permissions])

    const handleCreate = () => {
        createMutation.mutate({
            name: roleName,
            description: roleDescription,
            permissions: selectedPermissions
        })
    }

    const handleEdit = () => {
        if (!selectedRole) return

        updateMutation.mutate({
            roleId: selectedRole.id,
            data: {
                name: roleName,
                description: roleDescription,
                permissions: selectedPermissions
            }
        })
    }

    const handleDelete = (roleId: string, e?: React.MouseEvent) => {
        e?.stopPropagation()
        if (window.confirm('Are you sure you want to delete this role? This action cannot be undone.')) {
            deleteMutation.mutate(roleId)
        }
        handleCloseMenu()
    }

    const handleOpenMenu = (event: React.MouseEvent<HTMLElement>, role: Role) => {
        event.stopPropagation()
        setAnchorEl(event.currentTarget)
        setSelectedRole(role)
    }

    const handleCloseMenu = () => {
        setAnchorEl(null)
    }

    const handleOpenEdit = (role: Role) => {
        setSelectedRole(role)
        setRoleName(role.name)
        setRoleDescription(role.description || '')
        setSelectedPermissions(role.permissions?.map(p => p.name) || [])
        setEditDialogOpen(true)
        handleCloseMenu()
    }

    const handleOpenCreate = () => {
        resetForm()
        setCreateDialogOpen(true)
    }

    const handlePermissionToggle = (permissionName: string) => {
        setSelectedPermissions(prev =>
            prev.includes(permissionName)
                ? prev.filter(p => p !== permissionName)
                : [...prev, permissionName]
        )
    }

    const handleSelectAllInResource = (resource: string) => {
        const resourcePerms = groupedPermissions[resource] || []
        const resourcePermNames = resourcePerms.map(p => p.name)
        const allSelected = resourcePermNames.every(p => selectedPermissions.includes(p))

        if (allSelected) {
            setSelectedPermissions(prev => prev.filter(p => !resourcePermNames.includes(p)))
        } else {
            setSelectedPermissions(prev => [...new Set([...prev, ...resourcePermNames])])
        }
    }

    if (rolesLoading || permissionsLoading) {
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
                <CircularProgress />
            </Box>
        )
    }

    return (
        <Box sx={{ p: 3 }}>
            {/* Header */}
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                <Box>
                    <Typography variant="h5" sx={{ color: '#cccccc', fontWeight: 600 }}>
                        Role Management
                    </Typography>
                    <Typography variant="body2" sx={{ color: '#969696' }}>
                        Create and manage roles with permission assignments
                    </Typography>
                </Box>
                <Button
                    variant="contained"
                    startIcon={<AddIcon />}
                    onClick={handleOpenCreate}
                    sx={{
                        backgroundColor: '#007acc',
                        '&:hover': { backgroundColor: '#005a9e' },
                    }}
                >
                    Create Role
                </Button>
            </Box>

            {/* Roles Grid */}
            <Grid container spacing={2}>
                {roles?.map((role) => (
                    <Grid item xs={12} md={6} key={role.id}>
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
                                },
                            }}
                            onClick={() => handleOpenEdit(role)}
                        >
                            <CardContent>
                                <Box sx={{ display: 'flex', justifyContent: 'between', alignItems: 'flex-start' }}>
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flex: 1 }}>
                                        <SecurityIcon sx={{ color: '#569cd6', fontSize: 32 }} />
                                        <Box sx={{ flex: 1 }}>
                                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                                <Typography variant="h6" sx={{ color: '#cccccc', fontWeight: 500 }}>
                                                    {role.name}
                                                </Typography>
                                                {role.is_system_role && (
                                                    <Chip
                                                        icon={<LockIcon sx={{ fontSize: 14 }} />}
                                                        label="System"
                                                        size="small"
                                                        sx={{
                                                            height: 20,
                                                            fontSize: '10px',
                                                            backgroundColor: 'rgba(220, 220, 170, 0.2)',
                                                            color: '#dcdcaa',
                                                        }}
                                                    />
                                                )}
                                            </Box>
                                            <Typography variant="body2" sx={{ color: '#969696', mt: 0.5 }}>
                                                {role.description || 'No description'}
                                            </Typography>
                                        </Box>
                                    </Box>
                                    <IconButton
                                        size="small"
                                        onClick={(e) => handleOpenMenu(e, role)}
                                        sx={{ color: '#969696' }}
                                    >
                                        <MoreVertIcon fontSize="small" />
                                    </IconButton>
                                </Box>

                                <Divider sx={{ my: 1.5, borderColor: '#2d2d30' }} />

                                <Box>
                                    <Typography variant="caption" sx={{ color: '#969696' }}>
                                        Permissions: {role.permissions?.length || 0}
                                    </Typography>
                                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 1 }}>
                                        {role.permissions?.slice(0, 5).map(perm => (
                                            <Chip
                                                key={perm.id}
                                                label={perm.name}
                                                size="small"
                                                sx={{
                                                    height: 20,
                                                    fontSize: '11px',
                                                    backgroundColor: 'rgba(78, 201, 176, 0.2)',
                                                    color: '#4ec9b0',
                                                }}
                                            />
                                        ))}
                                        {(role.permissions?.length || 0) > 5 && (
                                            <Chip
                                                label={`+${(role.permissions?.length || 0) - 5} more`}
                                                size="small"
                                                sx={{
                                                    height: 20,
                                                    fontSize: '11px',
                                                    backgroundColor: 'rgba(150, 150, 150, 0.2)',
                                                    color: '#969696',
                                                }}
                                            />
                                        )}
                                    </Box>
                                </Box>
                            </CardContent>
                        </Card>
                    </Grid>
                ))}

                {(!roles || roles.length === 0) && (
                    <Grid item xs={12}>
                        <Paper sx={{ p: 4, textAlign: 'center', bgcolor: '#252526', border: '1px solid #2d2d30' }}>
                            <SecurityIcon sx={{ fontSize: 64, color: '#969696', mb: 2 }} />
                            <Typography variant="h6" sx={{ color: '#cccccc', mb: 1 }}>
                                No roles found
                            </Typography>
                            <Typography variant="body2" sx={{ color: '#969696', mb: 2 }}>
                                Create your first role to get started
                            </Typography>
                            <Button
                                variant="contained"
                                startIcon={<AddIcon />}
                                onClick={handleOpenCreate}
                                sx={{ backgroundColor: '#007acc' }}
                            >
                                Create Role
                            </Button>
                        </Paper>
                    </Grid>
                )}
            </Grid>

            {/* Context Menu */}
            <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={handleCloseMenu}>
                <MenuItem onClick={() => selectedRole && handleOpenEdit(selectedRole)}>
                    <EditIcon fontSize="small" sx={{ mr: 1 }} />
                    Edit
                </MenuItem>
                {selectedRole && !selectedRole.is_system_role && (
                    <>
                        <Divider />
                        <MenuItem onClick={() => selectedRole && handleDelete(selectedRole.id)} sx={{ color: '#f48771' }}>
                            <DeleteIcon fontSize="small" sx={{ mr: 1 }} />
                            Delete
                        </MenuItem>
                    </>
                )}
            </Menu>

            {/* Create Dialog */}
            <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="md" fullWidth>
                <DialogTitle sx={{ bgcolor: '#252526', color: '#cccccc' }}>Create New Role</DialogTitle>
                <DialogContent sx={{ bgcolor: '#1e1e1e', pt: 2 }}>
                    <TextField
                        autoFocus
                        margin="dense"
                        label="Role Name"
                        fullWidth
                        value={roleName}
                        onChange={(e) => setRoleName(e.target.value)}
                        sx={{ mb: 2 }}
                    />
                    <TextField
                        margin="dense"
                        label="Description"
                        fullWidth
                        multiline
                        rows={2}
                        value={roleDescription}
                        onChange={(e) => setRoleDescription(e.target.value)}
                        sx={{ mb: 2 }}
                    />

                    <Typography variant="subtitle2" sx={{ color: '#cccccc', mt: 2, mb: 1 }}>
                        Permissions
                    </Typography>
                    {Object.entries(groupedPermissions).map(([resource, perms]) => (
                        <Accordion key={resource} sx={{ bgcolor: '#252526', mb: 1 }}>
                            <AccordionSummary expandIcon={<ExpandMoreIcon sx={{ color: '#969696' }} />}>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%', pr: 2 }}>
                                    <Typography sx={{ color: '#cccccc', textTransform: 'capitalize' }}>
                                        {resource}
                                    </Typography>
                                    <Typography variant="caption" sx={{ color: '#969696' }}>
                                        {perms.filter(p => selectedPermissions.includes(p.name)).length}/{perms.length} selected
                                    </Typography>
                                </Box>
                            </AccordionSummary>
                            <AccordionDetails>
                                <FormControlLabel
                                    control={
                                        <Checkbox
                                            checked={perms.every(p => selectedPermissions.includes(p.name))}
                                            indeterminate={
                                                perms.some(p => selectedPermissions.includes(p.name)) &&
                                                !perms.every(p => selectedPermissions.includes(p.name))
                                            }
                                            onChange={() => handleSelectAllInResource(resource)}
                                        />
                                    }
                                    label={<Typography sx={{ fontWeight: 600 }}>Select All</Typography>}
                                />
                                <FormGroup sx={{ pl: 3 }}>
                                    {perms.map(perm => (
                                        <FormControlLabel
                                            key={perm.id}
                                            control={
                                                <Checkbox
                                                    checked={selectedPermissions.includes(perm.name)}
                                                    onChange={() => handlePermissionToggle(perm.name)}
                                                />
                                            }
                                            label={
                                                <Box>
                                                    <Typography variant="body2" sx={{ color: '#cccccc' }}>
                                                        {perm.name}
                                                    </Typography>
                                                    {perm.description && (
                                                        <Typography variant="caption" sx={{ color: '#969696' }}>
                                                            {perm.description}
                                                        </Typography>
                                                    )}
                                                </Box>
                                            }
                                        />
                                    ))}
                                </FormGroup>
                            </AccordionDetails>
                        </Accordion>
                    ))}
                </DialogContent>
                <DialogActions sx={{ bgcolor: '#252526' }}>
                    <Button onClick={() => setCreateDialogOpen(false)} sx={{ color: '#969696' }}>Cancel</Button>
                    <Button
                        onClick={handleCreate}
                        disabled={!roleName || !roleDescription || createMutation.isLoading}
                        variant="contained"
                        sx={{ backgroundColor: '#007acc' }}
                    >
                        Create
                    </Button>
                </DialogActions>
            </Dialog>

            {/* Edit Dialog */}
            <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)} maxWidth="md" fullWidth>
                <DialogTitle sx={{ bgcolor: '#252526', color: '#cccccc' }}>
                    Edit Role
                    {selectedRole?.is_system_role && (
                        <Alert severity="warning" sx={{ mt: 1 }}>
                            This is a system role. You can modify permissions but cannot rename or delete it.
                        </Alert>
                    )}
                </DialogTitle>
                <DialogContent sx={{ bgcolor: '#1e1e1e', pt: 2 }}>
                    <TextField
                        margin="dense"
                        label="Role Name"
                        fullWidth
                        value={roleName}
                        onChange={(e) => setRoleName(e.target.value)}
                        disabled={selectedRole?.is_system_role}
                        sx={{ mb: 2 }}
                    />
                    <TextField
                        margin="dense"
                        label="Description"
                        fullWidth
                        multiline
                        rows={2}
                        value={roleDescription}
                        onChange={(e) => setRoleDescription(e.target.value)}
                        sx={{ mb: 2 }}
                    />

                    <Typography variant="subtitle2" sx={{ color: '#cccccc', mt: 2, mb: 1 }}>
                        Permissions
                    </Typography>
                    {Object.entries(groupedPermissions).map(([resource, perms]) => (
                        <Accordion key={resource} sx={{ bgcolor: '#252526', mb: 1 }}>
                            <AccordionSummary expandIcon={<ExpandMoreIcon sx={{ color: '#969696' }} />}>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%', pr: 2 }}>
                                    <Typography sx={{ color: '#cccccc', textTransform: 'capitalize' }}>
                                        {resource}
                                    </Typography>
                                    <Typography variant="caption" sx={{ color: '#969696' }}>
                                        {perms.filter(p => selectedPermissions.includes(p.name)).length}/{perms.length} selected
                                    </Typography>
                                </Box>
                            </AccordionSummary>
                            <AccordionDetails>
                                <FormControlLabel
                                    control={
                                        <Checkbox
                                            checked={perms.every(p => selectedPermissions.includes(p.name))}
                                            indeterminate={
                                                perms.some(p => selectedPermissions.includes(p.name)) &&
                                                !perms.every(p => selectedPermissions.includes(p.name))
                                            }
                                            onChange={() => handleSelectAllInResource(resource)}
                                        />
                                    }
                                    label={<Typography sx={{ fontWeight: 600 }}>Select All</Typography>}
                                />
                                <FormGroup sx={{ pl: 3 }}>
                                    {perms.map(perm => (
                                        <FormControlLabel
                                            key={perm.id}
                                            control={
                                                <Checkbox
                                                    checked={selectedPermissions.includes(perm.name)}
                                                    onChange={() => handlePermissionToggle(perm.name)}
                                                />
                                            }
                                            label={
                                                <Box>
                                                    <Typography variant="body2" sx={{ color: '#cccccc' }}>
                                                        {perm.name}
                                                    </Typography>
                                                    {perm.description && (
                                                        <Typography variant="caption" sx={{ color: '#969696' }}>
                                                            {perm.description}
                                                        </Typography>
                                                    )}
                                                </Box>
                                            }
                                        />
                                    ))}
                                </FormGroup>
                            </AccordionDetails>
                        </Accordion>
                    ))}
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

export default RoleManagementTab
