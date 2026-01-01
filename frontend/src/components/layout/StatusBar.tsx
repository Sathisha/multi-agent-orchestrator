import React from 'react'
import { Box, Typography, IconButton, Chip } from '@mui/material'
import {
  Terminal as TerminalIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
} from '@mui/icons-material'
import UserMenu from './UserMenu'

interface StatusBarProps {
  onToggleTerminal: () => void
  terminalOpen: boolean
}

const StatusBar: React.FC<StatusBarProps> = ({ onToggleTerminal, terminalOpen }) => {
  return (
    <Box
      sx={{
        height: 22,
        backgroundColor: '#007acc',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        px: 1,
        fontSize: '12px',
      }}
    >
      {/* Left side - System status */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <CheckIcon sx={{ fontSize: 14, color: '#ffffff' }} />
          <Typography variant="caption" sx={{ color: '#ffffff', fontSize: '11px' }}>
            Backend Connected
          </Typography>
        </Box>

        <Chip
          label="0 Agents Running"
          size="small"
          sx={{
            height: 16,
            fontSize: '10px',
            backgroundColor: 'rgba(255, 255, 255, 0.2)',
            color: '#ffffff',
            '& .MuiChip-label': {
              px: 1,
            },
          }}
        />
      </Box>

      {/* Right side - Actions and indicators */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        {/* Error/Warning indicators */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <ErrorIcon sx={{ fontSize: 14, color: '#ffffff' }} />
          <Typography variant="caption" sx={{ color: '#ffffff', fontSize: '11px' }}>
            0
          </Typography>
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <WarningIcon sx={{ fontSize: 14, color: '#ffffff' }} />
          <Typography variant="caption" sx={{ color: '#ffffff', fontSize: '11px' }}>
            0
          </Typography>
        </Box>

        {/* Terminal toggle */}
        <IconButton
          size="small"
          onClick={onToggleTerminal}
          sx={{
            color: '#ffffff',
            backgroundColor: terminalOpen ? 'rgba(255, 255, 255, 0.2)' : 'transparent',
            '&:hover': {
              backgroundColor: 'rgba(255, 255, 255, 0.3)',
            },
            width: 20,
            height: 20,
          }}
        >
          <TerminalIcon sx={{ fontSize: 14 }} />
        </IconButton>

        {/* Current branch/environment */}
        <Typography variant="caption" sx={{ color: '#ffffff', fontSize: '11px' }}>
          Development
        </Typography>

        {/* User Menu */}
        <UserMenu />
      </Box>
    </Box>
  )
}

export default StatusBar