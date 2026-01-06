import React, { useState, useEffect } from 'react'
import { Box } from '@mui/material'
import { Outlet, useLocation } from 'react-router-dom'
import { Allotment } from 'allotment'
import 'allotment/dist/style.css'
import '../../styles/allotment-theme.css'
import ActivityBar from './ActivityBar'
import SidePanel from './SidePanel'
import MainEditor from './MainEditor'
import TerminalPanel from './TerminalPanel'
import StatusBar from './StatusBar'

const VSCodeLayout: React.FC = () => {
  const location = useLocation()

  const getInitialView = () => {
    const path = location.pathname
    if (path.startsWith('/agents')) return 'agents'
    if (path.startsWith('/chains') || path.startsWith('/workflows')) return 'workflows'
    if (path.startsWith('/tools')) return 'tools'
    if (path.startsWith('/models')) return 'models'
    if (path.startsWith('/vision-test')) return 'vision-test'
    if (path.startsWith('/monitoring')) return 'monitoring'
    if (path.startsWith('/users')) return 'users'
    return 'agents'
  }

  const [activeView, setActiveView] = useState(getInitialView())
  const [sidePanelOpen, setSidePanelOpen] = useState(true)
  const [terminalOpen, setTerminalOpen] = useState(false)

  // Sync active view with location changes (e.g. browser back button)
  useEffect(() => {
    setActiveView(getInitialView())
  }, [location.pathname])

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
          onViewChange={setActiveView}
          onToggleSidePanel={() => setSidePanelOpen(!sidePanelOpen)}
        />

        {/* Main workspace area */}
        <Box sx={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
          <Allotment vertical={true}>
            {/* Main content area */}
            <Allotment.Pane>
              <Box sx={{ display: 'flex', height: '100%' }}>
                <Allotment vertical={false}>
                  {/* Side Panel */}
                  {sidePanelOpen && (
                    <Allotment.Pane minSize={200} maxSize={600} preferredSize={300}>
                      <SidePanel
                        activeView={activeView}
                        onClose={() => setSidePanelOpen(false)}
                      />
                    </Allotment.Pane>
                  )}

                  {/* Main Editor Area */}
                  <Allotment.Pane>
                    <MainEditor>
                      <Outlet />
                    </MainEditor>
                  </Allotment.Pane>
                </Allotment>
              </Box>
            </Allotment.Pane>

            {/* Terminal Panel */}
            {terminalOpen && (
              <Allotment.Pane minSize={200} preferredSize="30%">
                <TerminalPanel
                  onClose={() => setTerminalOpen(false)}
                />
              </Allotment.Pane>
            )}
          </Allotment>
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