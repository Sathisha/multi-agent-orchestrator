import React from 'react'
import { Box, IconButton, Tooltip } from '@mui/material'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  SmartToy as AgentIcon,
  AccountTree as WorkflowIcon,
  Build as ToolsIcon,
  Monitor as MonitoringIcon,
  Settings as SettingsIcon,
  Menu as MenuIcon,
  Dns as LLMIcon,
  Link as ChainIcon,
  Visibility as VisionIcon,
  People as PeopleIcon,
  Extension as MCPIcon,
  Chat as ChatIcon,
} from '@mui/icons-material'
import { PermissionGuard } from '../PermissionGuard'

interface ActivityBarProps {
  onViewChange: (view: string) => void
  onToggleSidePanel: () => void
}

interface MenuItem {
  id: string
  icon: React.ElementType
  label: string
  path: string
  role?: string
  permission?: string
  requireSuperAdmin?: boolean
}

const ActivityBar: React.FC<ActivityBarProps> = ({
  onViewChange,
  onToggleSidePanel
}) => {
  const navigate = useNavigate()
  const location = useLocation()

  const menuItems: MenuItem[] = [
    { id: 'agents', icon: AgentIcon, label: 'Agents', path: '/agents' },
    { id: 'workflows', icon: WorkflowIcon, label: 'Workflows', path: '/chains' },
    { id: 'tools', icon: ToolsIcon, label: 'Tools', path: '/tools' },
    { id: 'models', icon: LLMIcon, label: 'LLM Models', path: '/models' },
    { id: 'mcp', icon: MCPIcon, label: 'MCP Servers', path: '/mcp' },
    { id: 'chat', icon: ChatIcon, label: 'Chat', path: '/chat' },
    { id: 'vision-test', icon: VisionIcon, label: 'Vision Test', path: '/vision-test', role: 'standard_user' },
    { id: 'monitoring', icon: MonitoringIcon, label: 'Monitoring', path: '/monitoring', role: 'standard_user' },
    { id: 'users', icon: PeopleIcon, label: 'Users', path: '/users', requireSuperAdmin: true },
  ]

  const handleItemClick = (item: MenuItem) => {
    onViewChange(item.id)
    navigate(item.path)
  }

  const isActive = (path: string) => {
    return location.pathname.startsWith(path)
  }

  return (
    <Box
      sx={{
        width: 48,
        backgroundColor: '#333333',
        borderRight: '1px solid #2d2d30',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        py: 1,
      }}
    >
      {/* Menu toggle button */}
      <Tooltip title="Toggle Side Panel" placement="right">
        <IconButton
          onClick={onToggleSidePanel}
          sx={{
            color: '#cccccc',
            mb: 2,
            '&:hover': {
              backgroundColor: '#2a2d2e',
            },
          }}
        >
          <MenuIcon />
        </IconButton>
      </Tooltip>

      {/* Main navigation items */}
      {menuItems.map((item) => {
        const Icon = item.icon
        const active = isActive(item.path)

        const button = (
          <Tooltip key={item.id} title={item.label} placement="right">
            <IconButton
              onClick={() => handleItemClick(item)}
              sx={{
                color: active ? '#ffffff' : '#cccccc',
                backgroundColor: active ? '#007acc' : 'transparent',
                mb: 1,
                '&:hover': {
                  backgroundColor: active ? '#007acc' : '#2a2d2e',
                },
                position: 'relative',
                '&::before': {
                  content: '""',
                  position: 'absolute',
                  left: 0,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  height: active ? '70%' : 0,
                  width: '2px',
                  backgroundColor: '#ffffff',
                  transition: 'height 0.2s ease',
                },
              }}
            >
              <Icon />
            </IconButton>
          </Tooltip>
        )

        // Wrap in PermissionGuard if permissions are specified
        if (item.requireSuperAdmin || item.role || item.permission) {
          return (
            <PermissionGuard
              key={item.id}
              requireSuperAdmin={item.requireSuperAdmin}
              role={item.role}
              permission={item.permission}
            >
              {button}
            </PermissionGuard>
          )
        }

        return button
      })}

      {/* Settings at bottom */}
      <Box sx={{ mt: 'auto' }}>
        <Tooltip title="Settings" placement="right">
          <IconButton
            sx={{
              color: '#cccccc',
              '&:hover': {
                backgroundColor: '#2a2d2e',
              },
            }}
          >
            <SettingsIcon />
          </IconButton>
        </Tooltip>
      </Box>
    </Box>
  )
}

export default ActivityBar
