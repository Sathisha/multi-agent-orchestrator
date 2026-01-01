import { Routes, Route } from 'react-router-dom'
import VSCodeLayout from './components/layout/VSCodeLayout'
import AgentWorkspace from './workspaces/AgentWorkspace'
import WorkflowWorkspace from './workspaces/WorkflowWorkspace'
import ToolsWorkspace from './workspaces/ToolsWorkspace'
import MonitoringWorkspace from './workspaces/MonitoringWorkspace'
import AgentDetailWorkspace from './workspaces/AgentDetailWorkspace'
import LoginPage from './components/auth/LoginPage'
import ProtectedRoute from './routes/ProtectedRoute'

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route element={<ProtectedRoute />}>
        <Route path="/*" element={
          <VSCodeLayout>
            <Routes>
              <Route path="/" element={<AgentWorkspace />} />
              <Route path="/agents" element={<AgentWorkspace />} />
              <Route path="/agents/:agentId" element={<AgentDetailWorkspace />} />
              <Route path="/workflows" element={<WorkflowWorkspace />} />
              <Route path="/tools" element={<ToolsWorkspace />} />
              <Route path="/monitoring" element={<MonitoringWorkspace />} />
            </Routes>
          </VSCodeLayout>
        } />
      </Route>
    </Routes>
  )
}

export default App