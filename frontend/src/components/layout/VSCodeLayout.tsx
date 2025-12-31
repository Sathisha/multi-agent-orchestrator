import React, { useState } from 'react'
import { Box } from '@mui/material'
import SplitPane from 'react-split-pane'
import ActivityBar from './ActivityBar'
import SidePanel from './SidePanel'
import MainEditor from './MainEditor'
import TerminalPanel from './TerminalPanel'
import StatusBar from './StatusBar'

interface VSCodeLayoutProps {
  children: React.ReactNode
}

const VSCodeLayout: React.FC<VSCodeLayoutProps> = ({ children }) => {
  const [activeView, setActiveView] = useState('agents')
  const [sidePanelOpen, setSidePanelOpen] = useState(true)
  const [terminalOpen, setTerminalOpen] = useState(false)

  return (
    <Box
      sx={{
        height: '100vh',
        width: '100vw',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        backgroundColor: '#1e1e1e',
      }}
    >
      {/* Main content area */}
      <Box sx={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* Activity Bar */}
        <ActivityBar 
          activeView={activeView} 
          onViewChange={setActiveView}
          onToggleSidePanel={() => setSidePanelOpen(!sidePanelOpen)}
        />
        
        {/* Main workspace area */}
        <Box sx={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
          <SplitPane
            split="horizontal"
            minSize={200}
            defaultSize={terminalOpen ? '70%' : '100%'}
            resizerStyle={{
              background: '#007acc',
              opacity: 0.2,
              zIndex: 1,
              MozUserSelect: 'none',
              WebkitUserSelect: 'none',
              msUserSelect: 'none',
              userSelect: 'none',
            }}
          >
            {/* Top pane: Side panel + Main editor */}
            <Box sx={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
              <SplitPane
                split="vertical"
                minSize={200}
                maxSize={600}
                defaultSize={sidePanelOpen ? 300 : 0}
                resizerStyle={{
                  background: '#007acc',
                  opacity: 0.2,
                  zIndex: 1,
                  MozUserSelect: 'none',
                  WebkitUserSelect: 'none',
                  msUserSelect: 'none',
                  userSelect: 'none',
                }}
              >
                {/* Side Panel */}
                {sidePanelOpen && (
                  <SidePanel 
                    activeView={activeView}
                    onClose={() => setSidePanelOpen(false)}
                  />
                )}
                
                {/* Main Editor Area */}
                <MainEditor>
                  {children}
                </MainEditor>
              </SplitPane>
            </Box>
            
            {/* Bottom pane: Terminal */}
            {terminalOpen && (
              <TerminalPanel 
                onClose={() => setTerminalOpen(false)}
              />
            )}
          </SplitPane>
        </Box>
      </Box>
      
      {/* Status Bar */}
      <StatusBar 
        onToggleTerminal={() => setTerminalOpen(!terminalOpen)}
        terminalOpen={terminalOpen}
      />
    </Box>
  )
}

export default VSCodeLayout