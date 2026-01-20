import { Routes, Route, Navigate } from 'react-router-dom'
import VSCodeLayout from './components/layout/VSCodeLayout'
import AgentWorkspace from './workspaces/AgentWorkspace'
// import WorkflowWorkspace from './workspaces/WorkflowWorkspace'
import ToolsWorkspace from './workspaces/ToolsWorkspace'
import ToolDetailWorkspace from './workspaces/ToolDetailWorkspace'
import MonitoringWorkspace from './workspaces/MonitoringWorkspace'
import AgentDetailWorkspace from './workspaces/AgentDetailWorkspace'
// import WorkflowDetailWorkspace from './workspaces/WorkflowDetailWorkspace'
import ChainWorkspace from './workspaces/ChainWorkspace'
import ChainDetailWorkspace from './workspaces/ChainDetailWorkspace'
import LLMModelsWorkspace from './workspaces/LLMModelsWorkspace'
import VisionTestWorkspace from './workspaces/VisionTestWorkspace'
import UserManagementWorkspace from './workspaces/UserManagementWorkspace'
import MCPServerListWorkspace from './workspaces/MCPServerListWorkspace'
import MCPServerDetailWorkspace from './workspaces/MCPServerDetailWorkspace'
import ChatWorkspace from './workspaces/ChatWorkspace'
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
          <Route path="/" element={<Navigate to="/agents" replace />} />
          <Route path="/agents" element={<AgentWorkspace />} />
          <Route path="/agents/:agentId" element={<AgentDetailWorkspace />} />
          {/* <Route path="/workflows" element={<WorkflowWorkspace />} />
          <Route path="/workflows/:workflowId" element={<WorkflowDetailWorkspace />} /> */}
          <Route path="/chains" element={<ChainWorkspace />} />
          <Route path="/chains/:chainId" element={<ChainDetailWorkspace />} />
          <Route path="/tools" element={<ToolsWorkspace />} />
          <Route path="/tools/:toolId" element={<ToolDetailWorkspace />} />
          <Route path="/monitoring" element={<MonitoringWorkspace />} />
          <Route path="/models" element={<LLMModelsWorkspace />} />
          <Route path="/vision-test" element={<VisionTestWorkspace />} />
          <Route path="/mcp" element={<MCPServerListWorkspace />} />
          <Route path="/mcp/:serverId" element={<MCPServerDetailWorkspace />} />
          <Route path="/chat" element={<ChatWorkspace />} />
          <Route path="/users" element={<UserManagementWorkspace />} />
        </Route>
      </Route>

      {/* Catch-all redirect to agents */}
      <Route path="*" element={<Navigate to="/agents" replace />} />
    </Routes>
  )
}

export default App