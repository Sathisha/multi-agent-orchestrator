import React, { useState, useMemo } from 'react'
import {
  Box, Typography, Button, Card, CardContent, Grid, Dialog, DialogTitle, DialogContent,
  DialogActions, TextField, CircularProgress, IconButton, Menu, MenuItem, Chip,
  InputAdornment, ToggleButtonGroup, ToggleButton, Tooltip, Paper, Divider,
  FormControl, InputLabel, Select, Checkbox, ListItemText, Badge, Avatar
} from '@mui/material'
import {
  Add as AddIcon,
  SmartToy as AgentIcon,
  MoreVert as MoreVertIcon,
  Delete as DeleteIcon,
  Search as SearchIcon,
  FilterList as FilterIcon,
  ViewModule as ViewModuleIcon,
  ViewList as ViewListIcon,
  ContentCopy as CopyIcon,
  GetApp as ExportIcon,
  PlayArrow as PlayIcon,
  Stop as StopIcon,
  Edit as EditIcon,
  Refresh as RefreshIcon,
  TrendingUp as TrendingUpIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Schedule as ScheduleIcon
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { getAgents, createAgent, deleteAgent, updateAgent, CreateAgentRequest, UpdateAgentRequest, Agent, getAgentTemplates, AgentTemplate } from '../api/agents'
import { useNavigate } from 'react-router-dom'

const AgentWorkspace: React.FC = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // State management
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [templateDialogOpen, setTemplateDialogOpen] = useState(false)
  const [newAgentName, setNewAgentName] = useState('')
  const [newAgentDesc, setNewAgentDesc] = useState('')
  const [newAgentType, setNewAgentType] = useState('conversational')
  const [searchQuery, setSearchQuery] = useState('')
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [filterStatus, setFilterStatus] = useState<string[]>(['active', 'inactive'])
  const [filterType, setFilterType] = useState<string[]>([])
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null)

  const { data: agents, isLoading, refetch } = useQuery('agents', getAgents)
  const { data: agentTemplates, isLoading: templatesLoading } = useQuery('agentTemplates', getAgentTemplates)

  const createMutation = useMutation(createAgent, {
    onSuccess: () => {
      queryClient.invalidateQueries('agents')
      setCreateDialogOpen(false)
      setTemplateDialogOpen(false)
      setNewAgentName('')
      setNewAgentDesc('')
      setNewAgentType('conversational')
    },
  })

  const deleteMutation = useMutation(deleteAgent, {
    onSuccess: () => {
      queryClient.invalidateQueries('agents')
    }
  })

  const updateMutation = useMutation(
    ({ id, data }: { id: string; data: Partial<UpdateAgentRequest> }) => updateAgent(id, data),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('agents')
      }
    }
  )

  // Filter and search logic
  const filteredAgents = useMemo(() => {
    if (!agents) return []

    return agents.filter(agent => {
      const matchesSearch = agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        agent.description?.toLowerCase().includes(searchQuery.toLowerCase())
      const matchesStatus = filterStatus.length === 0 || filterStatus.includes(agent.status)
      const matchesType = filterType.length === 0 || filterType.includes(agent.type)

      return matchesSearch && matchesStatus && matchesType
    })
  }, [agents, searchQuery, filterStatus, filterType])

  // Statistics
  const stats = useMemo(() => {
    if (!agents) return { total: 0, active: 0, inactive: 0 }

    return {
      total: agents.length,
      active: agents.filter(a => a.status === 'active').length,
      inactive: agents.filter(a => a.status === 'inactive').length
    }
  }, [agents])

  const handleCreate = () => {
    createMutation.mutate({
      name: newAgentName,
      description: newAgentDesc,
      type: newAgentType
    })
  }

  const handleCreateFromTemplate = (template: AgentTemplate) => {
    createMutation.mutate({
      name: template.name,
      description: template.description,
      type: template.type,
      system_prompt: template.system_prompt
    })
  }

  const handleDelete = (id: string, e?: React.MouseEvent) => {
    e?.stopPropagation()
    if (window.confirm('Are you sure you want to delete this agent?')) {
      deleteMutation.mutate(id)
    }
    handleCloseMenu()
  }

  const handleToggleStatus = (agent: Agent, e?: React.MouseEvent) => {
    e?.stopPropagation()
    const newStatus = agent.status === 'active' ? 'inactive' : 'active'
    updateMutation.mutate({
      id: agent.id,
      data: { status: newStatus }
    })
    handleCloseMenu()
  }

  const handleDuplicate = (agent: Agent, e?: React.MouseEvent) => {
    e?.stopPropagation()
    createMutation.mutate({
      name: `${agent.name} (Copy)`,
      description: agent.description,
      type: agent.type,
      system_prompt: agent.system_prompt,
      config: agent.config
    })
    handleCloseMenu()
  }

  const handleOpenMenu = (event: React.MouseEvent<HTMLElement>, agent: Agent) => {
    event.stopPropagation()
    setAnchorEl(event.currentTarget)
    setSelectedAgent(agent)
  }

  const handleCloseMenu = () => {
    setAnchorEl(null)
    setSelectedAgent(null)
  }

  const getAgentIcon = (type: string) => {
    const template = agentTemplates?.find(t => t.type === type)
    return template?.icon || '🤖'
  }

  const getAgentColor = (type: string) => {
    const template = agentTemplates?.find(t => t.type === type)
    return template?.color || '#569cd6'
  }

  return (
    <Box sx={{ p: 3, height: '100%', overflow: 'auto', bgcolor: '#1e1e1e' }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Box>
            <Typography variant="h4" sx={{ color: '#cccccc', mb: 1, fontWeight: 600 }}>
              AI Agents
            </Typography>
            <Typography variant="body2" sx={{ color: '#969696' }}>
              Create, configure, and manage your AI agents
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Tooltip title="Refresh">
              <IconButton onClick={() => refetch()} sx={{ color: '#cccccc' }}>
                <RefreshIcon />
              </IconButton>
            </Tooltip>
            <Button
              variant="outlined"
              startIcon={<AgentIcon />}
              onClick={() => setTemplateDialogOpen(true)}
              sx={{
                borderColor: '#569cd6',
                color: '#569cd6',
                '&:hover': {
                  borderColor: '#4a8cc7',
                  backgroundColor: 'rgba(86, 156, 214, 0.1)',
                },
              }}
            >
              Templates
            </Button>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => setCreateDialogOpen(true)}
              sx={{
                backgroundColor: '#007acc',
                '&:hover': {
                  backgroundColor: '#005a9e',
                },
              }}
            >
              Create Agent
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
                    Total Agents
                  </Typography>
                </Box>
                <Avatar sx={{ bgcolor: 'rgba(86, 156, 214, 0.2)', width: 56, height: 56 }}>
                  <AgentIcon sx={{ color: '#569cd6', fontSize: 32 }} />
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
                    Active Agents
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
                  <Typography variant="h3" sx={{ color: '#969696', fontWeight: 600 }}>
                    {stats.inactive}
                  </Typography>
                  <Typography variant="body2" sx={{ color: '#969696' }}>
                    Inactive Agents
                  </Typography>
                </Box>
                <Avatar sx={{ bgcolor: 'rgba(150, 150, 150, 0.2)', width: 56, height: 56 }}>
                  <ScheduleIcon sx={{ color: '#969696', fontSize: 32 }} />
                </Avatar>
              </Box>
            </Paper>
          </Grid>
        </Grid>

        {/* Search and Filters */}
        <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
          <TextField
            placeholder="Search agents..."
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
          Your Agents ({filteredAgents.length})
        </Typography>

        {isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
            <CircularProgress />
          </Box>
        ) : viewMode === 'grid' ? (
          <Grid container spacing={2}>
            {filteredAgents?.map((agent) => (
              <Grid item xs={12} md={6} lg={4} key={agent.id}>
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
                  onClick={() => navigate(`/agents/${agent.id}`)}
                >
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 2 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                        <Avatar
                          sx={{
                            bgcolor: `${getAgentColor(agent.type)}20`,
                            color: getAgentColor(agent.type),
                            width: 48,
                            height: 48,
                            fontSize: '24px'
                          }}
                        >
                          {getAgentIcon(agent.type)}
                        </Avatar>
                        <Box>
                          <Typography variant="subtitle1" sx={{ color: '#cccccc', fontWeight: 500 }}>
                            {agent.name}
                          </Typography>
                          <Chip
                            label={agent.status}
                            size="small"
                            sx={{
                              height: 20,
                              fontSize: '11px',
                              backgroundColor: agent.status === 'active' ? 'rgba(78, 201, 176, 0.2)' : 'rgba(150, 150, 150, 0.2)',
                              color: agent.status === 'active' ? '#4ec9b0' : '#969696',
                              border: `1px solid ${agent.status === 'active' ? '#4ec9b0' : '#969696'}`,
                            }}
                          />
                        </Box>
                      </Box>
                      <IconButton
                        size="small"
                        onClick={(e) => handleOpenMenu(e, agent)}
                        sx={{ color: '#969696' }}
                      >
                        <MoreVertIcon fontSize="small" />
                      </IconButton>
                    </Box>

                    <Typography
                      variant="body2"
                      sx={{
                        color: '#969696',
                        mb: 2,
                        display: '-webkit-box',
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: 'vertical',
                        overflow: 'hidden',
                        minHeight: 40
                      }}
                    >
                      {agent.description || 'No description'}
                    </Typography>

                    <Divider sx={{ my: 1.5, borderColor: '#2d2d30' }} />

                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Chip
                        label={agent.type}
                        size="small"
                        sx={{
                          fontSize: '10px',
                          height: 22,
                          backgroundColor: 'rgba(86, 156, 214, 0.1)',
                          color: '#569cd6',
                        }}
                      />
                      <Box sx={{ display: 'flex', gap: 0.5 }}>
                        <Tooltip title={agent.status === 'active' ? 'Stop' : 'Start'}>
                          <IconButton
                            size="small"
                            onClick={(e) => handleToggleStatus(agent, e)}
                            sx={{ color: agent.status === 'active' ? '#4ec9b0' : '#969696' }}
                          >
                            {agent.status === 'active' ? <StopIcon fontSize="small" /> : <PlayIcon fontSize="small" />}
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Edit">
                          <IconButton
                            size="small"
                            onClick={(e) => {
                              e.stopPropagation()
                              navigate(`/agents/${agent.id}`)
                            }}
                            sx={{ color: '#569cd6' }}
                          >
                            <EditIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </Box>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
            {filteredAgents?.length === 0 && (
              <Grid item xs={12}>
                <Paper sx={{ p: 4, textAlign: 'center', bgcolor: '#252526', border: '1px solid #2d2d30' }}>
                  <AgentIcon sx={{ fontSize: 64, color: '#969696', mb: 2 }} />
                  <Typography variant="h6" sx={{ color: '#cccccc', mb: 1 }}>
                    No agents found
                  </Typography>
                  <Typography variant="body2" sx={{ color: '#969696', mb: 2 }}>
                    {searchQuery ? 'Try adjusting your search or filters' : 'Create your first agent to get started'}
                  </Typography>
                  {!searchQuery && (
                    <Button
                      variant="contained"
                      startIcon={<AddIcon />}
                      onClick={() => setCreateDialogOpen(true)}
                      sx={{ backgroundColor: '#007acc' }}
                    >
                      Create Agent
                    </Button>
                  )}
                </Paper>
              </Grid>
            )}
          </Grid>
        ) : (
          // List View
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            {filteredAgents?.map((agent) => (
              <Paper
                key={agent.id}
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
                onClick={() => navigate(`/agents/${agent.id}`)}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flex: 1 }}>
                    <Avatar
                      sx={{
                        bgcolor: `${getAgentColor(agent.type)}20`,
                        color: getAgentColor(agent.type),
                        fontSize: '20px'
                      }}
                    >
                      {getAgentIcon(agent.type)}
                    </Avatar>
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="subtitle1" sx={{ color: '#cccccc', fontWeight: 500 }}>
                        {agent.name}
                      </Typography>
                      <Typography variant="body2" sx={{ color: '#969696', fontSize: '12px' }}>
                        {agent.description || 'No description'}
                      </Typography>
                    </Box>
                  </Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <Chip label={agent.type} size="small" sx={{ fontSize: '11px' }} />
                    <Chip
                      label={agent.status}
                      size="small"
                      sx={{
                        backgroundColor: agent.status === 'active' ? 'rgba(78, 201, 176, 0.2)' : 'rgba(150, 150, 150, 0.2)',
                        color: agent.status === 'active' ? '#4ec9b0' : '#969696',
                      }}
                    />
                    <IconButton size="small" onClick={(e) => handleOpenMenu(e, agent)}>
                      <MoreVertIcon />
                    </IconButton>
                  </Box>
                </Box>
              </Paper>
            ))}
          </Box>
        )}
      </Box>

      {/* Context Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleCloseMenu}
      >
        <MenuItem onClick={() => selectedAgent && navigate(`/agents/${selectedAgent.id}`)}>
          <EditIcon fontSize="small" sx={{ mr: 1 }} />
          Edit
        </MenuItem>
        <MenuItem onClick={() => selectedAgent && handleDuplicate(selectedAgent)}>
          <CopyIcon fontSize="small" sx={{ mr: 1 }} />
          Duplicate
        </MenuItem>
        <MenuItem onClick={() => selectedAgent && handleToggleStatus(selectedAgent)}>
          {selectedAgent?.status === 'active' ? <StopIcon fontSize="small" sx={{ mr: 1 }} /> : <PlayIcon fontSize="small" sx={{ mr: 1 }} />}
          {selectedAgent?.status === 'active' ? 'Deactivate' : 'Activate'}
        </MenuItem>
        <Divider />
        <MenuItem onClick={() => selectedAgent && handleDelete(selectedAgent.id)} sx={{ color: '#f48771' }}>
          <DeleteIcon fontSize="small" sx={{ mr: 1 }} />
          Delete
        </MenuItem>
      </Menu>

      {/* Create Dialog */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ bgcolor: '#252526', color: '#cccccc' }}>Create New Agent</DialogTitle>
        <DialogContent sx={{ bgcolor: '#1e1e1e', pt: 2 }}>
          <TextField
            autoFocus
            margin="dense"
            label="Name"
            fullWidth
            value={newAgentName}
            onChange={(e) => setNewAgentName(e.target.value)}
            sx={{ mb: 2 }}
          />
          <TextField
            margin="dense"
            label="Description"
            fullWidth
            multiline
            rows={3}
            value={newAgentDesc}
            onChange={(e) => setNewAgentDesc(e.target.value)}
            sx={{ mb: 2 }}
          />
          <FormControl fullWidth>
            <InputLabel>Type</InputLabel>
            <Select
              value={newAgentType}
              label="Type"
              onChange={(e) => setNewAgentType(e.target.value)}
            >
              <MenuItem value="conversational">Conversational</MenuItem>
              <MenuItem value="content-generation">Content Generation</MenuItem>
              <MenuItem value="data-analysis">Data Analysis</MenuItem>
              <MenuItem value="code-review">Code Review</MenuItem>
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions sx={{ bgcolor: '#252526' }}>
          <Button onClick={() => setCreateDialogOpen(false)} sx={{ color: '#969696' }}>Cancel</Button>
          <Button
            onClick={handleCreate}
            disabled={!newAgentName || createMutation.isLoading}
            variant="contained"
            sx={{ backgroundColor: '#007acc' }}
          >
            Create
          </Button>
        </DialogActions>
      </Dialog>

      {/* Template Dialog */}
      <Dialog open={templateDialogOpen} onClose={() => setTemplateDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle sx={{ bgcolor: '#252526', color: '#cccccc' }}>
          Choose Agent Template
        </DialogTitle>
        <DialogContent sx={{ bgcolor: '#1e1e1e', pt: 3 }}>
          <Grid container spacing={2}>
            {templatesLoading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', width: '100%', mt: 4 }}>
                <CircularProgress />
              </Box>
            ) : (
              agentTemplates?.map((template) => (
                <Grid item xs={12} sm={6} key={template.id}>
                  <Card
                    sx={{
                      bgcolor: '#252526',
                      border: '1px solid #2d2d30',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease',
                      '&:hover': {
                        borderColor: template.color,
                        transform: 'translateY(-2px)',
                        boxShadow: `0 4px 12px ${template.color}40`,
                      }
                    }}
                    onClick={() => handleCreateFromTemplate(template)}
                  >
                    <CardContent>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
                        <Avatar
                          sx={{
                            bgcolor: `${template.color}20`,
                            color: template.color,
                            fontSize: '24px'
                          }}
                        >
                          {template.icon}
                        </Avatar>
                        <Typography variant="h6" sx={{ color: '#cccccc' }}>
                          {template.name}
                        </Typography>
                      </Box>
                      <Typography variant="body2" sx={{ color: '#969696', mb: 1 }}>
                        {template.description}
                      </Typography>
                      <Chip
                        label={template.type}
                        size="small"
                        sx={{
                          fontSize: '10px',
                          backgroundColor: `${template.color}20`,
                          color: template.color,
                        }}
                      />
                    </CardContent>
                  </Card>
                </Grid>
              ))
            )}
          </Grid>
        </DialogContent>
        <DialogActions sx={{ bgcolor: '#252526' }}>
          <Button onClick={() => setTemplateDialogOpen(false)} sx={{ color: '#969696' }}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default AgentWorkspace