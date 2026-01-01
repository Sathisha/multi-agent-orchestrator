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
} from '@mui/icons-material'

interface ActivityBarProps {
  onViewChange: (view: string) => void
  onToggleSidePanel: () => void
}

const ActivityBar: React.FC<ActivityBarProps> = ({ 
  onViewChange, 
  onToggleSidePanel 
}) => {
  const navigate = useNavigate()
  const location = useLocation()

  const menuItems = [
    { id: 'agents', icon: AgentIcon, label: 'Agents', path: '/agents' },
    { id: 'workflows', icon: WorkflowIcon, label: 'Workflows', path: '/workflows' },
    { id: 'tools', icon: ToolsIcon, label: 'Tools', path: '/tools' },
    { id: 'monitoring', icon: MonitoringIcon, label: 'Monitoring', path: '/monitoring' },
  ]

  const handleItemClick = (item: typeof menuItems[0]) => {
    onViewChange(item.id)
    navigate(item.path)
  }

  const isActive = (path: string) => {
    return location.pathname === path || (path === '/agents' && location.pathname === '/')
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
        
        return (
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
                '&:before': active ? {
                  content: '""',
                  position: 'absolute',
                  left: 0,
                  top: 0,
                  bottom: 0,
                  width: 2,
                  backgroundColor: '#007acc',
                } : undefined,
              }}
            >
              <Icon />
            </IconButton>
          </Tooltip>
        )
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