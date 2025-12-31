import React, { useState } from 'react'
import { Box, Typography, IconButton, Tabs, Tab } from '@mui/material'
import { Close as CloseIcon, Terminal as TerminalIcon } from '@mui/icons-material'

interface TerminalPanelProps {
  onClose: () => void
}

const TerminalPanel: React.FC<TerminalPanelProps> = ({ onClose }) => {
  const [activeTab, setActiveTab] = useState(0)

  const tabs = [
    { label: 'Terminal', icon: TerminalIcon },
    { label: 'Logs', icon: TerminalIcon },
    { label: 'Debug', icon: TerminalIcon },
  ]

  return (
    <Box
      sx={{
        height: '100%',
        backgroundColor: '#1e1e1e',
        borderTop: '1px solid #2d2d30',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* Terminal header with tabs */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          backgroundColor: '#2d2d30',
          borderBottom: '1px solid #2d2d30',
          minHeight: 35,
        }}
      >
        <Tabs
          value={activeTab}
          onChange={(_, newValue) => setActiveTab(newValue)}
          sx={{
            flex: 1,
            minHeight: 35,
            '& .MuiTab-root': {
              color: '#cccccc',
              fontSize: '12px',
              minHeight: 35,
              textTransform: 'none',
            },
            '& .Mui-selected': {
              color: '#ffffff',
            },
            '& .MuiTabs-indicator': {
              backgroundColor: '#007acc',
            },
          }}
        >
          {tabs.map((tab, index) => (
            <Tab
              key={index}
              label={tab.label}
              icon={<tab.icon fontSize="small" />}
              iconPosition="start"
            />
          ))}
        </Tabs>
        
        <IconButton
          size="small"
          onClick={onClose}
          sx={{
            color: '#cccccc',
            mr: 1,
            '&:hover': {
              backgroundColor: '#2a2d2e',
            },
          }}
        >
          <CloseIcon fontSize="small" />
        </IconButton>
      </Box>

      {/* Terminal content */}
      <Box
        sx={{
          flex: 1,
          backgroundColor: '#1e1e1e',
          p: 2,
          fontFamily: '"Consolas", "Monaco", "Courier New", monospace',
          fontSize: '13px',
          color: '#cccccc',
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
        {activeTab === 0 && (
          <Box>
            <Typography variant="body2" sx={{ color: '#569cd6' }}>
              AI Agent Framework Terminal
            </Typography>
            <Typography variant="body2" sx={{ color: '#cccccc', mt: 1 }}>
              $ Ready for commands...
            </Typography>
            <Typography variant="body2" sx={{ color: '#6a9955', mt: 1 }}>
              # Use this terminal to monitor agent execution, view logs, and debug issues
            </Typography>
          </Box>
        )}
        
        {activeTab === 1 && (
          <Box>
            <Typography variant="body2" sx={{ color: '#569cd6' }}>
              System Logs
            </Typography>
            <Typography variant="body2" sx={{ color: '#cccccc', mt: 1 }}>
              [INFO] Frontend application started successfully
            </Typography>
            <Typography variant="body2" sx={{ color: '#cccccc' }}>
              [INFO] Connected to backend API at http://localhost:8000
            </Typography>
          </Box>
        )}
        
        {activeTab === 2 && (
          <Box>
            <Typography variant="body2" sx={{ color: '#569cd6' }}>
              Debug Console
            </Typography>
            <Typography variant="body2" sx={{ color: '#cccccc', mt: 1 }}>
              Debug information will appear here...
            </Typography>
          </Box>
        )}
      </Box>
    </Box>
  )
}

export default TerminalPanel