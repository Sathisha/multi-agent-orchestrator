"""
Create Enhanced Enterprise Architecture Planner workflow.
6 specialized agents with conversational multi-agent reasoning.
"""

import asyncio
import sys
import os
import uuid

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.database.connection import get_database_session
from shared.models.agent import Agent, AgentType, AgentStatus
from shared.models.chain import Chain, ChainNode, ChainEdge, ChainNodeType, ChainStatus
from sqlalchemy import select


async def create_enterprise_architecture_planner(admin_id: uuid.UUID):
    """Create enhanced Enterprise Architecture Planner with 6 specialized agents."""
    async with get_database_session() as session:
        print("Creating Enhanced Enterprise Architecture Planner...")
        
        # Check if already exists
        result = await session.execute(
            select(Agent).where(Agent.name == "Architecture Requirements Gatherer")
        )
        if result.scalar_one_or_none():
            print("  ✓ Architecture agents already exist")
            return
        
        model_config = {
            "model_name": "llama3.2",
            "llm_provider": "ollama",
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        # 1. Requirements Gatherer
        requirements_gatherer = Agent(
            name="Architecture Requirements Gatherer",
            description="Gathers project requirements for architecture planning",
            type=AgentType.CONVERSATIONAL,
            status=AgentStatus.ACTIVE,
            system_prompt="""You are a friendly software architecture consultant. Have a natural conversation to understand the project requirements.

Ask questions ONE AT A TIME in a professional but approachable way:

1. Start: "Hi! I'd love to help design your software architecture. What type of application are you building? (e.g., web app, mobile app, API service, enterprise system)"
2. After type: "Great! What's the expected scale? (number of users, requests per second, data volume)"
3. After scale: "Got it! Do you have any technology preferences or constraints? (programming languages, cloud providers, existing systems to integrate with)"
4. After tech: "Perfect! What are your main concerns? (performance, security, cost, scalability, maintainability)"

CRITICAL: Ask ONLY ONE question per message. Keep it professional yet friendly.

When you have enough info (after 4 questions), output this JSON ONLY:
{
  "app_type": "web application",
  "scale": "10000 concurrent users",
  "tech_preferences": "Python, AWS, PostgreSQL",
  "main_concerns": ["scalability", "cost"],
  "ready_for_routing": true
}""",
            config=model_config.copy(),
            created_by=admin_id
        )
        session.add(requirements_gatherer)
        
        # 2. Architecture Router
        architecture_router = Agent(
            name="Architecture Router",
            description="Routes to appropriate architecture specialist",
            type=AgentType.CONVERSATIONAL,
            status=AgentStatus.ACTIVE,
            system_prompt="""You are a routing agent. Analyze project requirements and route to the appropriate specialist.

Input: Project requirements JSON
Output: ONLY this JSON (no explanation):

{
  "route_to": "microservices_architect",
  "project_summary": "Web app, 10K users, Python/AWS, needs scalability"
}

Routing rules:
- "microservices_architect" if scale > 1000 users OR mentions "microservices" OR distributed system
- "cloud_architect" if mentions cloud (AWS/Azure/GCP) OR serverless OR high scalability
- "devops_architect" if mentions CI/CD, deployment, monitoring, or DevOps

Default to "cloud_architect" for modern web applications.
Keep project_summary brief and technical.""",
            config={**model_config, "temperature": 0.3, "max_tokens": 300},
            created_by=admin_id
        )
        session.add(architecture_router)
        
        # 3. Microservices Architect
        microservices_architect = Agent(
            name="Microservices Architect",
            description="Designs microservices architecture",
            type=AgentType.CONVERSATIONAL,
            status=AgentStatus.ACTIVE,
            system_prompt="""You are a microservices architecture expert. Design a comprehensive microservices architecture based on the requirements.

You'll receive: Project requirements and scale

Your response should be detailed and actionable:

"Based on your requirements, here's a microservices architecture design:

**Service Decomposition**
I recommend breaking your application into these core services:
1. **[Service Name]** - Handles [responsibility]
2. **[Service Name]** - Manages [responsibility]
3. **[Service Name]** - Processes [responsibility]

**Communication Patterns**
- **API Gateway**: [Technology] for routing and authentication
- **Service-to-Service**: [REST/gRPC/Message Queue] for [reason]
- **Event Bus**: [Technology] for asynchronous events

**Data Management**
- **Database per Service**: Each service has its own [database type]
- **Data Consistency**: [Saga pattern/Event sourcing] for distributed transactions

**Key Benefits for Your Project:**
✓ [Benefit 1 specific to their needs]
✓ [Benefit 2 specific to their needs]
✓ [Benefit 3 specific to their needs]

**Implementation Roadmap:**
1. Start with [service] as your foundation
2. Add [service] for [functionality]
3. Scale with [additional services]"

Keep it technical but understandable. No follow-up questions.""",
            config={**model_config, "max_tokens": 1200},
            available_tools=["web_search"],
            created_by=admin_id
        )
        session.add(microservices_architect)
        
        # 4. Cloud Infrastructure Architect
        cloud_architect = Agent(
            name="Cloud Infrastructure Architect",
            description="Designs cloud infrastructure and deployment",
            type=AgentType.CONVERSATIONAL,
            status=AgentStatus.ACTIVE,
            system_prompt="""You are a cloud infrastructure expert. Design optimal cloud architecture based on requirements.

You'll receive: Project requirements, scale, and tech preferences

Your response should be comprehensive:

"Based on your requirements, here's your cloud infrastructure design:

**Cloud Platform Recommendation: [AWS/Azure/GCP]**
I recommend [platform] because [specific reasons for their use case].

**Core Infrastructure**
- **Compute**: [ECS/EKS/Lambda/App Service] - [why this choice]
- **Database**: [RDS/DynamoDB/CosmosDB] - [why this choice]
- **Caching**: [ElastiCache/Redis] for [performance benefit]
- **Storage**: [S3/Blob Storage] for [use case]

**Scalability Strategy**
- **Auto-scaling**: [Configuration] to handle [their scale]
- **Load Balancing**: [ALB/Application Gateway] across [regions/zones]
- **CDN**: [CloudFront/Azure CDN] for [performance]

**Cost Optimization**
- Estimated monthly cost: $[range] for [their scale]
- **Savings**: Use [Reserved Instances/Spot/Serverless] to reduce costs by [%]

**Security & Compliance**
- [VPC/VNet] with [security groups/NSGs]
- [IAM/RBAC] for access control
- [Encryption] at rest and in transit

**Why This Works for You:**
✓ Handles [their scale] with room to grow
✓ Optimized for [their main concern]
✓ [Cost-effective/Highly available/Secure] solution"

Be specific with service names and configurations. No follow-up questions.""",
            config={**model_config, "max_tokens": 1200},
            available_tools=["web_search"],
            created_by=admin_id
        )
        session.add(cloud_architect)
        
        # 5. DevOps & CI/CD Architect
        devops_architect = Agent(
            name="DevOps & CI/CD Architect",
            description="Designs DevOps pipelines and deployment strategies",
            type=AgentType.CONVERSATIONAL,
            status=AgentStatus.ACTIVE,
            system_prompt="""You are a DevOps and CI/CD expert. Design comprehensive deployment and operations strategy.

You'll receive: Project requirements and infrastructure

Your response should cover the full DevOps lifecycle:

"Based on your architecture, here's your DevOps and CI/CD strategy:

**CI/CD Pipeline**
- **Source Control**: [GitHub/GitLab/Bitbucket] with [branching strategy]
- **Build**: [GitHub Actions/Jenkins/GitLab CI] for automated builds
- **Testing**: Automated tests at [unit/integration/e2e] levels
- **Deployment**: [Blue-Green/Canary/Rolling] deployment to [environment]

**Pipeline Stages**
1. **Code Commit** → Trigger build
2. **Build & Test** → Run tests, security scans
3. **Deploy to Staging** → Automated deployment
4. **Integration Tests** → Validate staging
5. **Deploy to Production** → [Deployment strategy]

**Infrastructure as Code**
- **Tool**: [Terraform/CloudFormation/Pulumi]
- **Benefits**: Version control, reproducibility, disaster recovery

**Monitoring & Observability**
- **Metrics**: [Prometheus/CloudWatch/DataDog] for system health
- **Logging**: [ELK Stack/CloudWatch Logs] for debugging
- **Tracing**: [Jaeger/X-Ray] for distributed tracing
- **Alerting**: [PagerDuty/Opsgenie] for incidents

**Security in Pipeline**
- **SAST**: Static code analysis
- **DAST**: Dynamic security testing
- **Dependency Scanning**: Vulnerability detection
- **Secrets Management**: [Vault/AWS Secrets Manager]

**Deployment Frequency**: Aim for [daily/weekly] deployments with [rollback strategy]"

Be practical and specific to their tech stack. No follow-up questions.""",
            config={**model_config, "max_tokens": 1200},
            available_tools=["web_search"],
            created_by=admin_id
        )
        session.add(devops_architect)
        
        # 6. Architecture Synthesizer
        architecture_synthesizer = Agent(
            name="Architecture Synthesizer",
            description="Compiles comprehensive architecture document",
            type=AgentType.CONVERSATIONAL,
            status=AgentStatus.ACTIVE,
            system_prompt="""You are creating the final, comprehensive architecture document.

You'll receive: Specialist recommendations (microservices/cloud/devops)

Your job: Synthesize everything into a complete, actionable architecture plan:

"Perfect! Here's your complete software architecture plan:

## Executive Summary
[2-3 sentence overview of the architecture]

## Architecture Overview
**Type**: [Microservices/Monolith/Serverless/Hybrid]
**Scale**: Designed for [their scale] with [growth potential]
**Tech Stack**: [Key technologies]

## System Design
[Incorporate microservices design if provided]
- Service breakdown
- Communication patterns
- Data management

## Infrastructure
[Incorporate cloud architecture]
- Cloud platform and services
- Scalability strategy
- Cost estimates

## DevOps & Deployment
[Incorporate DevOps strategy]
- CI/CD pipeline
- Monitoring and observability
- Security measures

## Implementation Roadmap

**Phase 1 (Weeks 1-4): Foundation**
1. [Task 1]
2. [Task 2]
3. [Task 3]

**Phase 2 (Weeks 5-8): Core Services**
1. [Task 1]
2. [Task 2]

**Phase 3 (Weeks 9-12): Scale & Optimize**
1. [Task 1]
2. [Task 2]

## Key Benefits
✓ [Benefit 1 specific to their requirements]
✓ [Benefit 2 specific to their requirements]
✓ [Benefit 3 specific to their requirements]

## Next Steps
1. Review this architecture with your team
2. Set up development environment
3. Begin Phase 1 implementation

## Resources
- [Relevant documentation links]
- [Best practices guides]
- [Community resources]

Ready to start building? Let me know if you need clarification on any part!"

Make it comprehensive, well-structured, and actionable.""",
            config={**model_config, "max_tokens": 1500},
            created_by=admin_id
        )
        session.add(architecture_synthesizer)
        
        await session.flush()
        
        # Get agent IDs for workflow
        result = await session.execute(
            select(Agent).where(Agent.name.in_([
                "Architecture Requirements Gatherer", "Architecture Router",
                "Microservices Architect", "Cloud Infrastructure Architect",
                "DevOps & CI/CD Architect", "Architecture Synthesizer"
            ]))
        )
        agents_dict = {agent.name: agent for agent in result.scalars().all()}
        
        # Create the workflow
        chain = Chain(
            name="Enterprise Architecture Planner Pro",
            description="Interactive architecture planning with specialized experts for microservices, cloud, and DevOps",
            status=ChainStatus.ACTIVE,
            category="Software Architecture",
            tags=["architecture", "enterprise", "cloud", "devops", "microservices"],
            input_schema={
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Project description"}
                }
            },
            created_by=admin_id
        )
        session.add(chain)
        await session.flush()
        
        # Create nodes
        positions = {
            "start": (100, 300), "gatherer": (300, 300), "router": (500, 300),
            "microservices": (700, 150), "cloud": (700, 300), "devops": (700, 450),
            "synthesizer": (900, 300), "end": (1100, 300)
        }
        
        node_configs = [
            ("start", ChainNodeType.START, None, "Start", 0),
            ("gatherer", ChainNodeType.AGENT, agents_dict["Architecture Requirements Gatherer"].id, "Gather Requirements", 1),
            ("router", ChainNodeType.AGENT, agents_dict["Architecture Router"].id, "Route to Specialist", 2),
            ("microservices", ChainNodeType.AGENT, agents_dict["Microservices Architect"].id, "Microservices Design", 3),
            ("cloud", ChainNodeType.AGENT, agents_dict["Cloud Infrastructure Architect"].id, "Cloud Architecture", 3),
            ("devops", ChainNodeType.AGENT, agents_dict["DevOps & CI/CD Architect"].id, "DevOps Strategy", 3),
            ("synthesizer", ChainNodeType.AGENT, agents_dict["Architecture Synthesizer"].id, "Compile Plan", 4),
            ("end", ChainNodeType.END, None, "End", 5)
        ]
        
        for node_id, node_type, agent_id, label, order in node_configs:
            node = ChainNode(
                chain_id=chain.id,
                node_id=node_id,
                node_type=node_type,
                agent_id=agent_id,
                label=label,
                position_x=positions[node_id][0],
                position_y=positions[node_id][1],
                order_index=order,
                created_by=admin_id
            )
            session.add(node)
        
        await session.flush()
        
        # Create edges
        edges = [
            ("start_to_gatherer", "start", "gatherer", "Begin", None),
            ("gatherer_to_router", "gatherer", "router", "Requirements Ready",
             {"type": "json_contains", "field": "ready_for_routing", "value": True}),
            ("router_to_microservices", "router", "microservices", "Microservices Path",
             {"type": "json_contains", "field": "route_to", "value": "microservices_architect"}),
            ("router_to_cloud", "router", "cloud", "Cloud Path",
             {"type": "json_contains", "field": "route_to", "value": "cloud_architect"}),
            ("router_to_devops", "router", "devops", "DevOps Path",
             {"type": "json_contains", "field": "route_to", "value": "devops_architect"}),
            ("microservices_to_synthesizer", "microservices", "synthesizer", "Design Complete", None),
            ("cloud_to_synthesizer", "cloud", "synthesizer", "Architecture Complete", None),
            ("devops_to_synthesizer", "devops", "synthesizer", "Strategy Complete", None),
            ("synthesizer_to_end", "synthesizer", "end", "Final Plan", None)
        ]
        
        for edge_id, source, target, label, condition in edges:
            edge = ChainEdge(
                chain_id=chain.id,
                edge_id=edge_id,
                source_node_id=source,
                target_node_id=target,
                label=label,
                condition=condition,
                created_by=admin_id
            )
            session.add(edge)
        
        await session.commit()
        print("  ✓ Created 6 architecture agents and enhanced workflow")


if __name__ == "__main__":
    # For testing - use admin user ID
    admin_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(create_enterprise_architecture_planner(admin_id))
