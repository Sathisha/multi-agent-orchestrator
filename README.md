# AI Agent Framework

A comprehensive platform that enables developers to create, orchestrate, and deploy AI agents with minimal complexity while maintaining enterprise-grade capabilities.

## 🚀 Key Features

- **VS Code-Style Interface**: Familiar developer experience with workspaces for agents, workflows, tools, and monitoring
- **BPMN Workflow Orchestration**: Visual workflow design with AI-enhanced automation
- **Enterprise Security**: Built-in RBAC, guardrails, audit trails, and compliance features
- **Self-Hosting**: Complete data sovereignty with downloadable deployment packages
- **LLM Flexibility**: Support for OpenAI, Anthropic, Azure OpenAI, and local models
- **Extensible Architecture**: Plugin system for custom tools and MCP server integrations

## 🏗️ Architecture

- **Backend**: Python microservices with FastAPI, PostgreSQL, Redis
- **Frontend**: React 18+ with TypeScript and VS Code-style interface
- **Security**: Keycloak authentication, Casbin RBAC, comprehensive guardrails
- **Orchestration**: Camunda BPMN engine with Docker containerization
- **Monitoring**: Prometheus metrics with Apache Superset dashboards

## 📋 Project Status

This project is currently in the specification and design phase. See the `.kiro/specs/` directory for detailed requirements, design, and implementation tasks.

## 🛠️ Technology Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, PostgreSQL, Redis
- **Frontend**: React 18+, TypeScript, Material-UI, Monaco Editor, React Flow
- **Infrastructure**: Docker, Docker Compose, Kong Gateway, Camunda Platform 8
- **Security**: Keycloak, Casbin, Custom Guardrails Engine
- **Monitoring**: Prometheus, Apache Superset, Structured Logging

## 📁 Project Structure

```
ai-agent-framework/
├── .kiro/                          # Kiro configuration and specs
│   ├── specs/                      # Feature specifications
│   └── steering/                   # AI assistant guidance rules
├── backend/                        # Python microservices
├── frontend/                       # React TypeScript application
├── infrastructure/                 # Deployment and infrastructure
├── docs/                           # Documentation
└── config/                         # Configuration files
```

## 🚀 Getting Started

1. **Review Specifications**: Check `.kiro/specs/ai-agent-framework/` for requirements and design
2. **Implementation Plan**: See `tasks.md` for the complete implementation roadmap
3. **Development Setup**: Follow the infrastructure setup in the tasks

## 📄 License

This project uses only permissive licenses (MIT, Apache 2.0, BSD) that are safe for commercial use and monetization.

## 🤝 Contributing

This project is currently in active development. Please refer to the implementation tasks for current development priorities.