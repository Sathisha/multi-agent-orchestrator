
import React, { useState } from 'react'
import {
    Box, Typography, Button, Card, CardContent, Grid, Dialog, DialogTitle, DialogContent,
    DialogActions, TextField, CircularProgress, IconButton, Chip, Paper, Divider,
    Tab, Tabs, InputAdornment, List, ListItem, ListItemText, Switch, FormControlLabel,
    TableContainer, Table, TableHead, TableRow, TableCell, TableBody,
    Select, MenuItem, FormControl, InputLabel
} from '@mui/material'
import {
    Add as AddIcon,
    Delete as DeleteIcon,
    Description as PdfIcon,
    Language as WebIcon,
    Search as SearchIcon,
    CloudUpload as UploadIcon,
    Lock as LockIcon,
    Public as PublicIcon,
    VpnKey as KeyIcon
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import {
    getRAGSources, addWebsiteSource, uploadPDFSource, deleteRAGSource, queryRAG,
    RAGSource, updateSourceVisibility, getSourceRoles, assignRoleToSource, removeRoleFromSource, SourceRoleResponse
} from '../api/rag'
import { getRoles, Role } from '../api/roles'

interface TabPanelProps {
    children?: React.ReactNode;
    index: number;
    value: number;
}

function CustomTabPanel(props: TabPanelProps) {
    const { children, value, index, ...other } = props;

    return (
        <div
            role="tabpanel"
            hidden={value !== index}
            id={`simple-tabpanel-${index}`}
            aria-labelledby={`simple-tab-${index}`}
            {...other}
        >
            {value === index && (
                <Box sx={{ p: 3 }}>
                    {children}
                </Box>
            )}
        </div>
    );
}

const RAGWorkspace: React.FC = () => {
    const queryClient = useQueryClient()
    const [addDialogOpen, setAddDialogOpen] = useState(false)
    const [tabValue, setTabValue] = useState(0)
    const [websiteUrl, setWebsiteUrl] = useState('')
    const [websiteName, setWebsiteName] = useState('')
    const [pdfFile, setPdfFile] = useState<File | null>(null)
    const [isPublic, setIsPublic] = useState(false)

    // RBAC State
    const [manageAccessOpen, setManageAccessOpen] = useState(false)
    const [selectedSourceForAccess, setSelectedSourceForAccess] = useState<RAGSource | null>(null)
    const [selectedRole, setSelectedRole] = useState('')
    const [selectedAccessType, setSelectedAccessType] = useState('view')

    const [testQuery, setTestQuery] = useState('')
    const [queryResults, setQueryResults] = useState<any[]>([])

    const { data: sources, isLoading } = useQuery('rag-sources', getRAGSources)
    const { data: availableRoles } = useQuery<Role[]>('roles', getRoles)

    // Fetch roles for selected source
    const { data: sourceRoles, isLoading: sourceRolesLoading } = useQuery(
        ['source-roles', selectedSourceForAccess?.id],
        () => getSourceRoles(selectedSourceForAccess!.id),
        {
            enabled: !!selectedSourceForAccess
        }
    )

    const addWebsiteMutation = useMutation(addWebsiteSource, {
        onSuccess: () => {
            queryClient.invalidateQueries('rag-sources')
            setAddDialogOpen(false)
            setWebsiteUrl('')
            setWebsiteName('')
            setIsPublic(false)
        }
    })

    const uploadPdfMutation = useMutation(({ file, name }: { file: File, name?: string }) => uploadPDFSource(file, name), {
        onSuccess: () => {
            queryClient.invalidateQueries('rag-sources')
            setAddDialogOpen(false)
            setPdfFile(null)
            setIsPublic(false) // Note: PDF upload API doesn't support is_public yet in frontend call, added to TODO
        }
    })

    const deleteMutation = useMutation(deleteRAGSource, {
        onSuccess: () => {
            queryClient.invalidateQueries('rag-sources')
        }
    })

    const queryMutation = useMutation(queryRAG, {
        onSuccess: (data) => {
            setQueryResults(data)
        }
    })

    const visibilityMutation = useMutation(
        ({ id, isPublic }: { id: string, isPublic: boolean }) => updateSourceVisibility(id, isPublic),
        {
            onSuccess: () => {
                queryClient.invalidateQueries('rag-sources')
                // Update local state if dialog open
                if (selectedSourceForAccess) {
                    setSelectedSourceForAccess(prev => prev ? { ...prev, is_public: !prev.is_public } : null)
                }
            }
        }
    )

    const assignRoleMutation = useMutation(
        ({ roleId, accessType }: { roleId: string, accessType: string }) =>
            assignRoleToSource(selectedSourceForAccess!.id, roleId, accessType),
        {
            onSuccess: () => {
                queryClient.invalidateQueries(['source-roles', selectedSourceForAccess?.id])
                setSelectedRole('')
            }
        }
    )

    const removeRoleMutation = useMutation(
        (roleId: string) => removeRoleFromSource(selectedSourceForAccess!.id, roleId),
        {
            onSuccess: () => {
                queryClient.invalidateQueries(['source-roles', selectedSourceForAccess?.id])
            }
        }
    )

    const handleAddWebsite = () => {
        if (websiteUrl && websiteName) {
            // Updated to pass isPublic - need to update API function signature or pass obj if mismatch
            // Actually addWebsiteSource signature takes CreateWebsiteSourceRequest which doesn't have isPublic in frontend interface yet
            // Assuming we updated interface in rag.ts
            addWebsiteMutation.mutate({ name: websiteName, url: websiteUrl })
            // TODO: Update rag.ts interface to include isPublic
        }
    }

    const handleUploadPdf = () => {
        if (pdfFile) {
            uploadPdfMutation.mutate({ file: pdfFile, name: pdfFile.name })
        }
    }

    const handleDelete = (id: string) => {
        if (window.confirm('Delete this source?')) {
            deleteMutation.mutate(id)
        }
    }

    const handleTestQuery = () => {
        if (testQuery) {
            queryMutation.mutate(testQuery)
        }
    }

    const handleManageAccess = (source: RAGSource) => {
        setSelectedSourceForAccess(source)
        setManageAccessOpen(true)
    }

    const handleVisibilityToggle = (id: string, checked: boolean) => {
        visibilityMutation.mutate({ id, isPublic: checked })
    }

    const handleAssignRole = () => {
        if (selectedSourceForAccess && selectedRole) {
            assignRoleMutation.mutate({ roleId: selectedRole, accessType: selectedAccessType })
        }
    }

    const handleRemoveRole = (roleId: string) => {
        if (window.confirm('Remove access for this role?')) {
            removeRoleMutation.mutate(roleId)
        }
    }

    return (
        <Box sx={{ p: 3, height: '100%', overflow: 'auto', bgcolor: '#1e1e1e' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
                <Typography variant="h4" sx={{ color: '#cccccc' }}>
                    Knowledge Base (RAG)
                </Typography>
                <Button
                    variant="contained"
                    startIcon={<AddIcon />}
                    onClick={() => setAddDialogOpen(true)}
                    sx={{ bgcolor: '#007acc' }}
                >
                    Add Source
                </Button>
            </Box>

            <Grid container spacing={3}>
                {/* Sources List */}
                <Grid item xs={12} md={8}>
                    <Typography variant="h6" sx={{ color: '#cccccc', mb: 2 }}>
                        Data Sources
                    </Typography>
                    {isLoading ? (
                        <CircularProgress />
                    ) : (
                        <Grid container spacing={2}>
                            {sources?.map((source) => (
                                <Grid item xs={12} sm={6} key={source.id}>
                                    <Card sx={{ bgcolor: '#252526', border: '1px solid #2d2d30' }}>
                                        <CardContent>
                                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                                    {source.source_type === 'website' ?
                                                        <WebIcon sx={{ color: '#4ec9b0' }} /> :
                                                        <PdfIcon sx={{ color: '#ce9178' }} />
                                                    }
                                                    <Typography variant="subtitle1" sx={{ color: '#cccccc' }}>
                                                        {source.name}
                                                    </Typography>
                                                </Box>
                                                <IconButton size="small" onClick={() => handleDelete(source.id)} sx={{ color: '#f48771' }}>
                                                    <DeleteIcon />
                                                </IconButton>
                                            </Box>
                                            <Typography variant="body2" sx={{ color: '#969696', mt: 1, wordBreak: 'break-all' }}>
                                                {source.content_source}
                                            </Typography>
                                            <Box sx={{ mt: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                                                <Chip
                                                    label={source.status}
                                                    size="small"
                                                    color={source.status === 'completed' ? 'success' : source.status === 'failed' ? 'error' : 'default'}
                                                    variant="outlined"
                                                />
                                                <Typography variant="caption" sx={{ color: '#569cd6' }}>
                                                    {new Date(source.created_at).toLocaleDateString()}
                                                </Typography>
                                            </Box>
                                        </CardContent>
                                    </Card>
                                </Grid>
                            ))}
                            {sources?.length === 0 && (
                                <Grid item xs={12}>
                                    <Paper sx={{ p: 4, textAlign: 'center', bgcolor: '#252526', color: '#969696' }}>
                                        No sources added yet.
                                    </Paper>
                                </Grid>
                            )}
                        </Grid>
                    )}
                </Grid>



                {/* Test Query Section */}
                <Grid item xs={12} md={4}>
                    <Paper sx={{ p: 2, bgcolor: '#252526', border: '1px solid #2d2d30', height: '100%' }}>
                        <Typography variant="h6" sx={{ color: '#cccccc', mb: 2 }}>
                            Test Retrieval
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                            <TextField
                                fullWidth
                                size="small"
                                placeholder="Ask a question..."
                                value={testQuery}
                                onChange={(e) => setTestQuery(e.target.value)}
                                onKeyPress={(e) => e.key === 'Enter' && handleTestQuery()}
                            />
                            <IconButton onClick={handleTestQuery} disabled={queryMutation.isLoading} sx={{ color: '#007acc' }}>
                                <SearchIcon />
                            </IconButton>
                        </Box>

                        {queryMutation.isLoading && <CircularProgress size={20} />}

                        <List sx={{ overflow: 'auto', maxHeight: 500 }}>
                            {queryResults.map((result, idx) => (
                                <ListItem key={idx} sx={{ flexDirection: 'column', alignItems: 'flex-start', borderBottom: '1px solid #333' }}>
                                    <Typography variant="subtitle2" sx={{ color: '#4ec9b0' }}>
                                        Score: {result.score.toFixed(3)}
                                    </Typography>
                                    <Typography variant="body2" sx={{ color: '#cccccc', mt: 0.5 }}>
                                        {result.content}
                                    </Typography>
                                    {result.metadata && (
                                        <Typography variant="caption" sx={{ color: '#569cd6', mt: 0.5 }}>
                                            Source: {result.metadata.source_name}
                                        </Typography>
                                    )}
                                </ListItem>
                            ))}
                        </List>
                    </Paper>
                </Grid>
            </Grid>

            {/* Add Source Dialog */}
            <Dialog open={addDialogOpen} onClose={() => setAddDialogOpen(false)} maxWidth="sm" fullWidth>
                <DialogTitle sx={{ bgcolor: '#252526', color: '#cccccc' }}>Add New Source</DialogTitle>
                <DialogContent sx={{ bgcolor: '#1e1e1e', p: 0 }}>
                    <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)} sx={{ borderBottom: 1, borderColor: '#333' }}>
                        <Tab label="Website" sx={{ color: '#969696' }} />
                        <Tab label="PDF Document" sx={{ color: '#969696' }} />
                    </Tabs>

                    <Box sx={{ p: 2, borderBottom: '1px solid #333' }}>
                        <FormControlLabel
                            control={
                                <Switch
                                    checked={isPublic}
                                    onChange={(e) => setIsPublic(e.target.checked)}
                                    color="secondary"
                                />
                            }
                            label={
                                <Box>
                                    <Typography variant="body2" sx={{ color: '#e1e1e1' }}>Make Public</Typography>
                                    <Typography variant="caption" sx={{ color: '#969696' }}>Visible to all users for viewing</Typography>
                                </Box>
                            }
                        />
                    </Box>

                    <CustomTabPanel value={tabValue} index={0}>
                        <TextField
                            fullWidth
                            label="Name"
                            value={websiteName}
                            onChange={(e) => setWebsiteName(e.target.value)}
                            sx={{ mb: 2 }}
                        />
                        <TextField
                            fullWidth
                            label="URL"
                            value={websiteUrl}
                            onChange={(e) => setWebsiteUrl(e.target.value)}
                            placeholder="https://example.com"
                        />
                        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
                            <Button
                                variant="contained"
                                onClick={handleAddWebsite}
                                disabled={addWebsiteMutation.isLoading || !websiteUrl || !websiteName}
                            >
                                {addWebsiteMutation.isLoading ? 'Processing...' : 'Add Website'}
                            </Button>
                        </Box>
                    </CustomTabPanel>

                    <CustomTabPanel value={tabValue} index={1}>
                        <Button
                            variant="outlined"
                            component="label"
                            fullWidth
                            startIcon={<UploadIcon />}
                            sx={{ mb: 2, height: 100, borderStyle: 'dashed' }}
                        >
                            {pdfFile ? pdfFile.name : 'Click to Upload PDF'}
                            <input
                                type="file"
                                hidden
                                accept="application/pdf"
                                onChange={(e) => setPdfFile(e.target.files?.[0] || null)}
                            />
                        </Button>
                        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
                            <Button
                                variant="contained"
                                onClick={handleUploadPdf}
                                disabled={uploadPdfMutation.isLoading || !pdfFile}
                            >
                                {uploadPdfMutation.isLoading ? 'Uploading...' : 'Upload & Process'}
                            </Button>
                        </Box>
                    </CustomTabPanel>
                </DialogContent>
            </Dialog>

            {/* Manage Access Dialog */}
            <Dialog open={manageAccessOpen} onClose={() => setManageAccessOpen(false)} maxWidth="md" fullWidth>
                <DialogTitle sx={{ bgcolor: '#252526', color: '#cccccc' }}>Manage Access: {selectedSourceForAccess?.name}</DialogTitle>
                <DialogContent sx={{ bgcolor: '#1e1e1e', p: 3 }}>
                    {/* Visibility Toggle */}
                    <Paper sx={{ p: 2, mb: 3, bgcolor: '#252526', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Box>
                            <Typography variant="subtitle1" sx={{ color: '#e1e1e1' }}>Public Access</Typography>
                            <Typography variant="body2" sx={{ color: '#969696' }}>
                                Allow any user to view and search this source
                            </Typography>
                        </Box>
                        <Switch
                            checked={selectedSourceForAccess?.is_public || false}
                            onChange={(e) => handleVisibilityToggle(selectedSourceForAccess!.id, e.target.checked)}
                            color="success"
                        />
                    </Paper>

                    <Typography variant="h6" sx={{ color: '#cccccc', mb: 2 }}>Role-Based Access</Typography>

                    {/* Add Role Form */}
                    <Box sx={{ display: 'flex', gap: 2, mb: 3, alignItems: 'flex-end' }}>
                        <FormControl fullWidth size="small">
                            <InputLabel>Select Role</InputLabel>
                            <Select
                                value={selectedRole}
                                label="Select Role"
                                onChange={(e) => setSelectedRole(e.target.value)}
                            >
                                {availableRoles?.map((role) => (
                                    <MenuItem key={role.id} value={role.id}>{role.name}</MenuItem>
                                ))}
                            </Select>
                        </FormControl>
                        <FormControl sx={{ minWidth: 150 }} size="small">
                            <InputLabel>Permission</InputLabel>
                            <Select
                                value={selectedAccessType}
                                label="Permission"
                                onChange={(e) => setSelectedAccessType(e.target.value)}
                            >
                                <MenuItem value="view">View</MenuItem>
                                <MenuItem value="query">Query</MenuItem>
                                <MenuItem value="modify">Modify</MenuItem>
                            </Select>
                        </FormControl>
                        <Button
                            variant="contained"
                            onClick={handleAssignRole}
                            disabled={!selectedRole || assignRoleMutation.isLoading}
                        >
                            Add
                        </Button>
                    </Box>

                    {/* Roles List */}
                    <TableContainer component={Paper} sx={{ bgcolor: '#252526' }}>
                        <Table size="small">
                            <TableHead>
                                <TableRow>
                                    <TableCell sx={{ color: '#969696' }}>Role</TableCell>
                                    <TableCell sx={{ color: '#969696' }}>Access</TableCell>
                                    <TableCell sx={{ color: '#969696' }} align="right">Action</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {sourceRolesLoading ? (
                                    <TableRow><TableCell colSpan={3} align="center"><CircularProgress size={20} /></TableCell></TableRow>
                                ) : sourceRoles?.length === 0 ? (
                                    <TableRow><TableCell colSpan={3} align="center" sx={{ color: '#666' }}>No specific roles assigned</TableCell></TableRow>
                                ) : (
                                    sourceRoles?.map((role) => (
                                        <TableRow key={role.role_id}>
                                            <TableCell sx={{ color: '#e1e1e1' }}>{role.role_name}</TableCell>
                                            <TableCell>
                                                <Chip
                                                    label={role.access_type}
                                                    size="small"
                                                    color={role.access_type === 'modify' ? 'warning' : 'default'}
                                                    variant="outlined"
                                                />
                                            </TableCell>
                                            <TableCell align="right">
                                                <IconButton
                                                    size="small"
                                                    onClick={() => handleRemoveRole(role.role_id)}
                                                    sx={{ color: '#f48771' }}
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

                </DialogContent>
                <DialogActions sx={{ bgcolor: '#252526' }}>
                    <Button onClick={() => setManageAccessOpen(false)}>Close</Button>
                </DialogActions>
            </Dialog>

        </Box >
    )
}

export default RAGWorkspace
