import React from 'react'
import { Box, Typography, IconButton } from '@mui/material'
import { Close as CloseIcon } from '@mui/icons-material'
import AgentExplorer from '../explorers/AgentExplorer'
import WorkflowExplorer from '../explorers/WorkflowExplorer'
import ToolsExplorer from '../explorers/ToolsExplorer'
import MonitoringExplorer from '../explorers/MonitoringExplorer'

interface SidePanelProps {
  activeView: string
  onClose: () => void
}

const SidePanel: React.FC<SidePanelProps> = ({ activeView, onClose }) => {
  const getTitle = () => {
    switch (activeView) {
      case 'agents':
        return 'AGENTS'
      case 'workflows':
        return 'WORKFLOWS'
      case 'chains':
        return 'CHAINS'
      case 'tools':
        return 'TOOLS'
      case 'monitoring':
        return 'MONITORING'
      default:
        return 'EXPLORER'
    }
  }

  const renderExplorer = () => {
    switch (activeView) {
      case 'agents':
        return <AgentExplorer />
      case 'workflows':
        return <WorkflowExplorer />
      case 'chains':
        // For now, use a simple explorer - can create ChainExplorer later
        return <WorkflowExplorer />
      case 'tools':
        return <ToolsExplorer />
      case 'monitoring':
        return <MonitoringExplorer />
      default:
        return <AgentExplorer />
    }
  }

  return (
    <Box
      sx={{
        width: '100%',
        height: '100%',
        backgroundColor: '#252526',
        borderRight: '1px solid #2d2d30',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          px: 2,
          py: 1,
          borderBottom: '1px solid #2d2d30',
          minHeight: 35,
        }}
      >
        <Typography
          variant="caption"
          sx={{
            color: '#cccccc',
            fontWeight: 'bold',
            fontSize: '11px',
            letterSpacing: '0.5px',
          }}
        >
          {getTitle()}
        </Typography>
        <IconButton
          size="small"
          onClick={onClose}
          sx={{
            color: '#cccccc',
            '&:hover': {
              backgroundColor: '#2a2d2e',
            },
          }}
        >
          <CloseIcon fontSize="small" />
        </IconButton>
      </Box>

      {/* Explorer Content */}
      <Box
        sx={{
          flex: 1,
          overflow: 'auto',
          '&::-webkit-scrollbar': {
            width: '8px',
          },
          '&::-webkit-scrollbar-track': {
            backgroundColor: '#2b2b2b',
          },
          '&::-webkit-scrollbar-thumb': {
            backgroundColor: '#6b6b6b',
            borderRadius: '4px',
          },
          '&::-webkit-scrollbar-thumb:hover': {
            backgroundColor: '#959595',
          },
        }}
      >
        {renderExplorer()}
      </Box>
    </Box>
  )
}

export default SidePanel