import { Routes, Route, Navigate } from 'react-router-dom'
import VSCodeLayout from './components/layout/VSCodeLayout'
import AgentWorkspace from './workspaces/AgentWorkspace'
import WorkflowWorkspace from './workspaces/WorkflowWorkspace'
import ToolsWorkspace from './workspaces/ToolsWorkspace'
import MonitoringWorkspace from './workspaces/MonitoringWorkspace'
import AgentDetailWorkspace from './workspaces/AgentDetailWorkspace'
import WorkflowDetailWorkspace from './workspaces/WorkflowDetailWorkspace'
import LLMModelsWorkspace from './workspaces/LLMModelsWorkspace'
import LoginPage from './components/auth/LoginPage'
import ProtectedRoute from './routes/ProtectedRoute'

function App() {
  return (
    <Routes>
      {/* Public route - Login page standalone */}
      <Route path="/login" element={<LoginPage />} />

      {/* Protected routes - All wrapped in VSCodeLayout */}
      <Route element={<ProtectedRoute />}>
        <Route element={<VSCodeLayout />}>
          <Route path="/" element={<Navigate to="/workflows" replace />} />
          <Route path="/agents" element={<AgentWorkspace />} />
          <Route path="/agents/:agentId" element={<AgentDetailWorkspace />} />
          <Route path="/workflows" element={<WorkflowWorkspace />} />
          <Route path="/workflows/:workflowId" element={<WorkflowDetailWorkspace />} />
          <Route path="/tools" element={<ToolsWorkspace />} />
          <Route path="/monitoring" element={<MonitoringWorkspace />} />
          <Route path="/models" element={<LLMModelsWorkspace />} />
        </Route>
      </Route>

      {/* Catch-all redirect to agents */}
      <Route path="*" element={<Navigate to="/workflows" replace />} />
    </Routes>
  )
}

export default App