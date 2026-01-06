import React from 'react'
import { Box, Typography, IconButton } from '@mui/material'
import { Close as CloseIcon } from '@mui/icons-material'
import AgentExplorer from '../explorers/AgentExplorer'
import WorkflowExplorer from '../explorers/WorkflowExplorer'
import ToolsExplorer from '../explorers/ToolsExplorer'
import MonitoringExplorer from '../explorers/MonitoringExplorer'
import ModelsExplorer from '../explorers/ModelsExplorer'

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
      case 'tools':
        return 'TOOLS'
      case 'models':
        return 'LLM MODELS'
      case 'monitoring':
        return 'MONITORING'
      case 'users':
        return 'USERS'
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
      case 'tools':
        return <ToolsExplorer />
      case 'models':
        return <ModelsExplorer />
      case 'monitoring':
        return <MonitoringExplorer />
      case 'users':
        return (
          <Box sx={{ p: 2 }}>
            <Typography variant="body2" sx={{ color: '#969696', textAlign: 'center', mt: 4 }}>
              User management is shown in the main panel
            </Typography>
          </Box>
        )
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