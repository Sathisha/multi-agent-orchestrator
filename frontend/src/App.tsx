import { Routes, Route } from 'react-router-dom'
import VSCodeLayout from './components/layout/VSCodeLayout'
import AgentWorkspace from './workspaces/AgentWorkspace'
import WorkflowWorkspace from './workspaces/WorkflowWorkspace'
import ToolsWorkspace from './workspaces/ToolsWorkspace'
import MonitoringWorkspace from './workspaces/MonitoringWorkspace'

function App() {
  return (
    <VSCodeLayout>
      <Routes>
        <Route path="/" element={<AgentWorkspace />} />
        <Route path="/agents" element={<AgentWorkspace />} />
        <Route path="/workflows" element={<WorkflowWorkspace />} />
        <Route path="/tools" element={<ToolsWorkspace />} />
        <Route path="/monitoring" element={<MonitoringWorkspace />} />
      </Routes>
    </VSCodeLayout>
  )
}

export default App