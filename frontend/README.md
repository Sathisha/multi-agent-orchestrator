# AI Agent Framework Frontend

A VS Code-style React application for managing AI agents, workflows, and tools.

## Features

- **VS Code-Style Interface**: Familiar layout with Activity Bar, Side Panel, Main Editor, and Terminal
- **Agent Management**: Create, configure, and monitor AI agents
- **Workflow Designer**: Visual BPMN workflow orchestration
- **Tool Development**: Custom tool creation and MCP server integration
- **System Monitoring**: Real-time performance and health monitoring

## Technology Stack

- **React 18+** with TypeScript
- **Material-UI** for components
- **Monaco Editor** for code editing
- **React Query** for state management
- **Vite** for build tooling

## Development

### Prerequisites

- Node.js 18+
- npm or yarn

### Local Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Docker Development

```bash
# Start development container with hot reload
docker-compose --profile dev up frontend-dev

# Start production container
docker-compose --profile frontend up frontend

# Start both backend and frontend for full development
docker-compose --profile dev up backend frontend-dev
```

## Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── layout/         # Layout components (ActivityBar, SidePanel, etc.)
│   └── explorers/      # Explorer components for each workspace
├── workspaces/         # Main workspace views
│   ├── AgentWorkspace.tsx
│   ├── WorkflowWorkspace.tsx
│   ├── ToolsWorkspace.tsx
│   └── MonitoringWorkspace.tsx
├── services/           # API client services
├── hooks/              # Custom React hooks
├── types/              # TypeScript type definitions
└── utils/              # Utility functions
```

## API Integration

The frontend connects to the backend API at `http://localhost:8000` by default. API calls are proxied through Vite during development and through Nginx in production.

## Styling

The application uses a VS Code-inspired dark theme with:
- Background: `#1e1e1e`
- Panels: `#252526`
- Borders: `#2d2d30`
- Primary: `#007acc`
- Text: `#cccccc`

## Contributing

1. Follow the existing code style and patterns
2. Use TypeScript for all new components
3. Add proper error handling and loading states
4. Test components in both light and dark themes
5. Ensure responsive design for different screen sizes