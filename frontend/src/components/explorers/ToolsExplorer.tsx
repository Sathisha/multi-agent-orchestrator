import React, { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  IconButton,
  Collapse,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemButton,
  CircularProgress,
} from '@mui/material'
import {
  ExpandMore as ExpandMoreIcon,
  ChevronRight as ChevronRightIcon,
  Build as ToolIcon,
  Add as AddIcon,
  Folder as FolderIcon,
  FolderOpen as FolderOpenIcon,
  Extension as ExtensionIcon,
  Code as CodeIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material'
import { getTools, getMCPServers, Tool, MCPServer } from '../../api/tools'

const ToolsExplorer: React.FC = () => {
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set(['custom-tools', 'mcp-servers']))
  const [tools, setTools] = useState<Tool[]>([])
  const [mcpServers, setMCPServers] = useState<MCPServer[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [toolsData, mcpData] = await Promise.all([
        getTools(),
        getMCPServers().catch(err => {
          console.warn("Failed to fetch MCP servers", err);
          return [] as MCPServer[];
        })
      ])
      setTools(toolsData)
      setMCPServers(mcpData)
    } catch (err: any) {
      console.error('Failed to fetch tools:', err)
      setError('Failed to load tools')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const toggleFolder = (folderId: string) => {
    const newExpanded = new Set(expandedFolders)
    if (newExpanded.has(folderId)) {
      newExpanded.delete(folderId)
    } else {
      newExpanded.add(folderId)
    }
    setExpandedFolders(newExpanded)
  }

  // Filter custom tools (assuming anything not MCP is custom for now, or check tool_type)
  const customTools = tools.filter(t => t.tool_type === 'custom' || !t.tool_type)

  if (loading && tools.length === 0) {
    return (
      <Box sx={{ p: 2, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress size={20} color="secondary" />
      </Box>
    )
  }

  return (
    <Box sx={{ p: 1 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1, px: 1 }}>
        <Typography variant="overline" sx={{ color: '#969696', fontWeight: 'bold' }}>
          Explorer
        </Typography>
        <IconButton size="small" onClick={fetchData} sx={{ color: '#969696' }}>
          <RefreshIcon fontSize="small" />
        </IconButton>
      </Box>

      {/* Custom Tools folder */}
      <ListItem
        disablePadding
        sx={{
          '&:hover': {
            backgroundColor: '#2a2d2e',
          },
        }}
      >
        <ListItemButton
          onClick={() => toggleFolder('custom-tools')}
          sx={{
            py: 0.5,
            px: 1,
            minHeight: 'auto',
          }}
        >
          <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
            {expandedFolders.has('custom-tools') ? (
              <ExpandMoreIcon sx={{ fontSize: 16, color: '#cccccc' }} />
            ) : (
              <ChevronRightIcon sx={{ fontSize: 16, color: '#cccccc' }} />
            )}
          </ListItemIcon>
          <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
            {expandedFolders.has('custom-tools') ? (
              <FolderOpenIcon sx={{ fontSize: 16, color: '#dcb67a' }} />
            ) : (
              <FolderIcon sx={{ fontSize: 16, color: '#dcb67a' }} />
            )}
          </ListItemIcon>
          <ListItemText
            primary={`Custom Tools (${customTools.length})`}
            primaryTypographyProps={{
              fontSize: '13px',
              color: '#cccccc',
            }}
          />
          <IconButton
            size="small"
            sx={{
              color: '#cccccc',
              opacity: 0.7,
              '&:hover': {
                opacity: 1,
                backgroundColor: '#2a2d2e',
              },
            }}
          >
            <AddIcon sx={{ fontSize: 14 }} />
          </IconButton>
        </ListItemButton>
      </ListItem>

      {/* Custom Tools list */}
      <Collapse in={expandedFolders.has('custom-tools')}>
        <List sx={{ pl: 2 }}>
          {customTools.map((tool) => (
            <ListItem
              key={tool.id}
              disablePadding
              sx={{
                '&:hover': {
                  backgroundColor: '#2a2d2e',
                },
              }}
            >
              <ListItemButton
                sx={{
                  py: 0.5,
                  px: 1,
                  minHeight: 'auto',
                }}
              >
                <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
                  <CodeIcon
                    sx={{
                      fontSize: 16,
                      color: tool.status === 'active' ? '#4ec9b0' : '#969696'
                    }}
                  />
                </ListItemIcon>
                <ListItemText
                  primary={tool.name}
                  secondary={tool.category || 'Utility'}
                  primaryTypographyProps={{
                    fontSize: '13px',
                    color: '#cccccc',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                  secondaryTypographyProps={{
                    fontSize: '11px',
                    color: '#969696',
                  }}
                />
              </ListItemButton>
            </ListItem>
          ))}
          {customTools.length === 0 && (
            <Typography sx={{ px: 4, py: 1, fontSize: '12px', color: '#666', fontStyle: 'italic' }}>
              No custom tools found
            </Typography>
          )}
        </List>
      </Collapse>

      {/* MCP Servers folder */}
      <ListItem
        disablePadding
        sx={{
          '&:hover': {
            backgroundColor: '#2a2d2e',
          },
        }}
      >
        <ListItemButton
          onClick={() => toggleFolder('mcp-servers')}
          sx={{
            py: 0.5,
            px: 1,
            minHeight: 'auto',
          }}
        >
          <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
            {expandedFolders.has('mcp-servers') ? (
              <ExpandMoreIcon sx={{ fontSize: 16, color: '#cccccc' }} />
            ) : (
              <ChevronRightIcon sx={{ fontSize: 16, color: '#cccccc' }} />
            )}
          </ListItemIcon>
          <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
            {expandedFolders.has('mcp-servers') ? (
              <FolderOpenIcon sx={{ fontSize: 16, color: '#dcb67a' }} />
            ) : (
              <FolderIcon sx={{ fontSize: 16, color: '#dcb67a' }} />
            )}
          </ListItemIcon>
          <ListItemText
            primary={`MCP Servers (${mcpServers.length})`}
            primaryTypographyProps={{
              fontSize: '13px',
              color: '#cccccc',
            }}
          />
          <IconButton
            size="small"
            sx={{
              color: '#cccccc',
              opacity: 0.7,
              '&:hover': {
                opacity: 1,
                backgroundColor: '#2a2d2e',
              },
            }}
          >
            <AddIcon sx={{ fontSize: 14 }} />
          </IconButton>
        </ListItemButton>
      </ListItem>

      {/* MCP Servers list */}
      <Collapse in={expandedFolders.has('mcp-servers')}>
        <List sx={{ pl: 2 }}>
          {mcpServers.map((server) => (
            <ListItem
              key={server.id}
              disablePadding
              sx={{
                '&:hover': {
                  backgroundColor: '#2a2d2e',
                },
              }}
            >
              <ListItemButton
                sx={{
                  py: 0.5,
                  px: 1,
                  minHeight: 'auto',
                }}
              >
                <ListItemIcon sx={{ minWidth: 20, mr: 1 }}>
                  <ExtensionIcon
                    sx={{
                      fontSize: 16,
                      color: server.status === 'connected' ? '#4ec9b0' : '#f48771'
                    }}
                  />
                </ListItemIcon>
                <ListItemText
                  primary={server.name}
                  secondary={`${server.tool_count || 0} tools • ${server.status}`}
                  primaryTypographyProps={{
                    fontSize: '13px',
                    color: '#cccccc',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                  secondaryTypographyProps={{
                    fontSize: '11px',
                    color: '#969696',
                  }}
                />
              </ListItemButton>
            </ListItem>
          ))}
          {mcpServers.length === 0 && (
            <Typography sx={{ px: 4, py: 1, fontSize: '12px', color: '#666', fontStyle: 'italic' }}>
              No MCP servers connected
            </Typography>
          )}
        </List>
      </Collapse>
    </Box>
  )
}

export default ToolsExplorer