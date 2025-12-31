import React from 'react'
import { Box } from '@mui/material'

interface MainEditorProps {
  children: React.ReactNode
}

const MainEditor: React.FC<MainEditorProps> = ({ children }) => {
  return (
    <Box
      sx={{
        flex: 1,
        height: '100%',
        backgroundColor: '#1e1e1e',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Tab bar area - will be implemented later for multiple tabs */}
      <Box
        sx={{
          height: 35,
          backgroundColor: '#2d2d30',
          borderBottom: '1px solid #2d2d30',
          display: 'flex',
          alignItems: 'center',
          px: 1,
        }}
      >
        {/* Tabs will go here */}
      </Box>

      {/* Main content area */}
      <Box
        sx={{
          flex: 1,
          overflow: 'auto',
          backgroundColor: '#1e1e1e',
          '&::-webkit-scrollbar': {
            width: '8px',
            height: '8px',
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
        {children}
      </Box>
    </Box>
  )
}

export default MainEditor