"""
Seed script to create admin user and sample data for testing.
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from shared.database.connection import AsyncSessionLocal
from shared.models.user import User
from shared.models.agent import Agent, AgentType, AgentStatus
from shared.models.workflow import Workflow, WorkflowStatus
from shared.models.workflow import Workflow, WorkflowStatus
from shared.models.tool import Tool, ToolType, ToolStatus, MCPServer, MCPServerStatus
from shared.models.chain import Chain, ChainNode, ChainEdge, ChainNodeType, ChainStatus
from shared.services.auth import AuthService
import uuid


async def create_admin_user():
    """Create admin user: admin/admin"""
    async with AsyncSessionLocal() as session:
        auth_service = AuthService(session)
        
        # Check if admin exists
        result = await session.execute(select(User).where(User.email == "admin@example.com"))
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print("✓ Admin user already exists")
            return existing_user
        
        # Create admin user
        user = await auth_service.register_user(
            email="admin@example.com",
            password="admin",
            full_name="Admin User"
        )
        
        # Set as system admin
        user.is_superuser = True
        await session.commit()
        
        print("✓ Created admin user: admin@example.com / admin")
        return user


async def create_sample_agents(user_id: uuid.UUID):
    """Create sample agents"""
    async with AsyncSessionLocal() as session:
        # Check if agents exist
        result = await session.execute(select(Agent))
        if result.scalars().first():
            print("✓ Sample agents already exist")
            return
        
        agents = [
            Agent(
                id=uuid.uuid4(),
                name="Customer Support Bot",
                description="AI assistant for handling customer inquiries and support tickets",
                type=AgentType.CONVERSATIONAL,
                status=AgentStatus.ACTIVE,
                version="1.0",
                system_prompt="""You are a helpful customer support assistant. 
You are NOT a general conversational chatbot.
You look for a specific topic in the user's request.
If a valid support topic is found, you provide helpful information or route the request.
If no clear topic is found, or the request is irrelevant, you politely decline.""",
                config={
                    "model": "gpt-4",
                    "temperature": 0.5,
                    "max_tokens": 2000,
                    "use_standard_response_format": True,
                    "success_criteria": "The user's inquiry matches a known support topic (billing, technical issue, account management) and you have provided a relevant helpful response.",
                    "failure_criteria": "The user's inquiry is gibberish, offensive, or completely unrelated to customer support topics."
                },
                available_tools=["Weather Checker", "Wikipedia Search", "Internet Search", "Time & Date"],
                created_by=user_id,
                updated_by=user_id
            ),
            Agent(
                id=uuid.uuid4(),
                name="Research Assistant",
                description="Helps with research tasks, finding information, and data analysis",
                type=AgentType.TASK,
                status=AgentStatus.ACTIVE,
                version="1.0",
                system_prompt="""You are a research assistant.
You are part of an agent workflow.
You receive a topic for research.
You shall only respond with the research material in valid JSON format.
You do not add other conversation text or next steps outside the JSON data.""",
                config={
                    "model": "gpt-4",
                    "temperature": 0.3,
                    "max_tokens": 3000,
                    "use_standard_response_format": True,
                    "success_criteria": "You have successfully successfully retrieved factual information about the requested topic using the available tools.",
                    "failure_criteria": "You could not find any relevant information about the topic after searching."
                },
                available_tools=["Wikipedia Search", "Internet Search", "Calculator", "JSON Parser"],
                capabilities=["research", "data_analysis", "fact_checking"],
                tags=["research", "information"],
                created_by=user_id,
                updated_by=user_id
            ),
            Agent(
                id=uuid.uuid4(),
                name="Content Writer",
                description="Creates engaging blog posts and marketing content",
                type=AgentType.CONVERSATIONAL,
                status=AgentStatus.DRAFT,
                version="1.0",
                system_prompt="You are a creative content writer. Write engaging, SEO-optimized content.",
                config={
                    "model": "gpt-3.5-turbo",
                    "temperature": 0.9,
                    "max_tokens": 2500
                },
                available_tools=["Wikipedia Search", "Internet Search", "Text Transformer"],
                capabilities=["writing", "seo", "marketing"],
                tags=["content", "marketing"],
                created_by=user_id,
                updated_by=user_id
            ),
            Agent(
                id=uuid.uuid4(),
                name="Data Analyst",
                description="Analyzes datasets and generates insights",
                type=AgentType.TASK,
                status=AgentStatus.ACTIVE,
                version="1.0",
                system_prompt="You are a data analyst. Analyze data, identify patterns, and provide actionable insights.",
                config={
                    "model": "gpt-4",
                    "temperature": 0.2,
                    "max_tokens": 2000
                },
                available_tools=["Calculator", "JSON Parser", "HTTP Request", "File Hash Calculator"],
                capabilities=["data_analysis", "visualization", "reporting"],
                tags=["analytics", "data"],
                created_by=user_id,
                updated_by=user_id
            ),
            # --- Scenario 1: Smartphone Recommendation Agents ---
            Agent(
                id=uuid.uuid4(),
                name="Tech Trends Researcher",
                description="Specializes in finding the latest smartphone specifications, reviews, and market trends.",
                type=AgentType.TASK,
                status=AgentStatus.ACTIVE,
                version="1.0",
                system_prompt="You are a Tech Trends Researcher. Your goal is to fetch the latest data on smartphones, matching specific user criteria like camera quality, battery life, and ecosystem.",
                config={"model": "gpt-4", "temperature": 0.3},
                available_tools=["Internet Search", "Wikipedia Search"],
                tags=["tech", "research", "smartphones"],
                created_by=user_id,
                updated_by=user_id
            ),
            Agent(
                id=uuid.uuid4(),
                name="Consumer Advisor",
                description="Interacts with the user to understand their lifestyle, preferences, and budget for a new phone.",
                type=AgentType.CONVERSATIONAL,
                status=AgentStatus.ACTIVE,
                version="1.0",
                system_prompt="""You are a Consumer Advisor. Your goal is to help users find the perfect smartphone.
Ask targeted questions about the user's current ecosystem (iOS/Android), usage patterns (gaming, photography), and budget to build a profile.

### RESPONSE FORMAT
You MUST respond in valid JSON format using the Standard Agent Communication Protocol.

{
    "thought": "Reasoning about what to ask or say next...",
    "status": "success",
    "message": "The user-friendly message you want the user to see. e.g. 'What is your budget?'",
    "data": {
        // Any structured data collected so far
        "budget": 1000,
        "use_case": "gaming",
        "ready_for_routing": false 
    }
}

CRITICAL: 
- Put the text you want the user to read in the "message" field.
- Do NOT output raw JSON to the user directly as continuous text. The system will parse your JSON and show only the "message" field to the user.
- If you have collected all necessary information (Budget, Use Case, Brand, Features), set "ready_for_routing": true in "data" and provide a summary in "message".
""",
                config={"model": "gpt-4", "temperature": 0.7, "use_standard_response_format": True},
                tags=["advisory", "consumer", "smartphones"],
                created_by=user_id,
                updated_by=user_id
            ),
            Agent(
                id=uuid.uuid4(),
                name="Deal Finder",
                description="Searches for the best current pricing and deals for specific smartphone models.",
                type=AgentType.TASK,
                status=AgentStatus.ACTIVE,
                version="1.0",
                system_prompt="You are a Deal Finder. Given a list of smartphone models, find the best current prices and active deals.",
                config={"model": "gpt-3.5-turbo", "temperature": 0.2},
                available_tools=["Internet Search", "Calculator"],
                tags=["shopping", "deals", "smartphones"],
                created_by=user_id,
                updated_by=user_id
            ),
            
            # --- Scenario 2: Software Architecture Advisory Agents ---
            Agent(
                id=uuid.uuid4(),
                name="System Architect",
                description="Designs high-level system architecture based on requirements.",
                type=AgentType.TASK,
                status=AgentStatus.ACTIVE,
                version="1.0",
                system_prompt="You are a System Architect. Analyze requirements for scale, users, and complexity. output high-level design patterns (Microservices, Monolith, Serverless) and technology stacks.",
                config={"model": "gpt-4", "temperature": 0.4},
                tags=["architecture", "design", "software"],
                created_by=user_id,
                updated_by=user_id
            ),
            Agent(
                id=uuid.uuid4(),
                name="Cloud Infrastructure Specialist",
                description="Recommends cloud services and infrastructure configurations (AWS, Azure, GCP).",
                type=AgentType.TASK,
                status=AgentStatus.ACTIVE,
                version="1.0",
                system_prompt="You are a Cloud Infrastructure Specialist. Suggest specific cloud services (e.g., AWS Lambda, K8s, DynamoDB) that fit the proposed system architecture.",
                config={"model": "gpt-4", "temperature": 0.3},
                available_tools=["Internet Search"],
                tags=["cloud", "infrastructure", "aws", "azure"],
                created_by=user_id,
                updated_by=user_id
            ),
            Agent(
                id=uuid.uuid4(),
                name="Database Expert",
                description="Advises on data storage solutions (SQL vs NoSQL, specific technologies).",
                type=AgentType.TASK,
                status=AgentStatus.ACTIVE,
                version="1.0",
                system_prompt="You are a Database Expert. Recommend the optimal database technologies (Postgres, MongoDB, Redis) based on data structure and access patterns.",
                config={"model": "gpt-4", "temperature": 0.3},
                tags=["database", "storage", "sql", "nosql"],
                created_by=user_id,
                updated_by=user_id
            ),
            Agent(
                id=uuid.uuid4(),
                name="DevOps Engineer",
                description="Outlines CI/CD pipelines and deployment strategies.",
                type=AgentType.TASK,
                status=AgentStatus.ACTIVE,
                version="1.0",
                system_prompt="You are a DevOps Engineer. Define the deployment strategy, CI/CD pipelines, and observability tools for the proposed system.",
                config={"model": "gpt-3.5-turbo", "temperature": 0.3},
                tags=["devops", "deployment", "cicd"],
                created_by=user_id,
                updated_by=user_id
            ),

            # --- Scenario 3: Career Counseling Agents ---
            Agent(
                id=uuid.uuid4(),
                name="Career Coach",
                description="Helps users identify career goals and paths.",
                type=AgentType.CONVERSATIONAL,
                status=AgentStatus.ACTIVE,
                version="1.0",
                system_prompt="You are a Career Coach. specific questions to understand the user's background, strengths, and aspirations.",
                config={"model": "gpt-4", "temperature": 0.8},
                tags=["career", "coaching", "hr"],
                created_by=user_id,
                updated_by=user_id
            ),
            Agent(
                id=uuid.uuid4(),
                name="Job Market Analyst",
                description="Analyzes current job market trends and demand.",
                type=AgentType.TASK,
                status=AgentStatus.ACTIVE,
                version="1.0",
                system_prompt="You are a Job Market Analyst. Provide data on growing roles, salary ranges, and industry trends for a specific career path.",
                config={"model": "gpt-4", "temperature": 0.2},
                available_tools=["Internet Search", "Wikipedia Search"],
                tags=["market-analysis", "jobs", "trends"],
                created_by=user_id,
                updated_by=user_id
            ),
            Agent(
                id=uuid.uuid4(),
                name="Skill Assessor",
                description="Identifies skill gaps and recommends learning resources.",
                type=AgentType.TASK,
                status=AgentStatus.ACTIVE,
                version="1.0",
                system_prompt="You are a Skill Assessor. Compare the user's current skills against the requirements for their target role and list specific gaps.",
                config={"model": "gpt-4", "temperature": 0.3},
                tags=["skills", "learning", "development"],
                created_by=user_id,
                updated_by=user_id
            ),
            Agent(
                id=uuid.uuid4(),
                name="Resume Polisher",
                description="Optimizes resumes and LinkedIn profiles for specific roles.",
                type=AgentType.TASK,
                status=AgentStatus.ACTIVE,
                version="1.0",
                system_prompt="You are a Resume Polisher. Suggest improvements to the user's resume summary and experience points to align with the target role.",
                config={"model": "gpt-3.5-turbo", "temperature": 0.5},
                tags=["resume", "writing", "career"],
                created_by=user_id,
                updated_by=user_id
            ),
        ]
        
        for agent in agents:
            session.add(agent)
        
        await session.commit()
        print(f"✓ Created {len(agents)} sample agents")


async def create_sample_workflows(user_id: uuid.UUID):
    """Create sample workflows"""
    async with AsyncSessionLocal() as session:
        # Check if workflows exist
        result = await session.execute(select(Workflow))
        if result.scalars().first():
            print("✓ Sample workflows already exist")
            return
        
        workflows = [
            Workflow(
                id=uuid.uuid4(),
                name="Customer Onboarding",
                description="Automated workflow for onboarding new customers",
                version="1.0",
                status=WorkflowStatus.ACTIVE,
                category="customer_management",
                tags=["onboarding", "automation"],
                input_schema={"type": "object", "properties": {"customer_email": {"type": "string"}}},
                output_schema={"type": "object", "properties": {"status": {"type": "string"}}},
                created_by=user_id,
                updated_by=user_id
            ),
            Workflow(
                id=uuid.uuid4(),
                name="Content Review Pipeline",
                description="Multi-stage content review and approval workflow",
                version="1.0",
                status=WorkflowStatus.DRAFT,
                category="content",
                tags=["review", "content"],
                created_by=user_id,
                updated_by=user_id
            ),
            Workflow(
                id=uuid.uuid4(),
                name="Data Processing Pipeline",
                description="ETL workflow for processing and analyzing data",
                version="1.0",
                status=WorkflowStatus.ACTIVE,
                category="data",
                tags=["etl", "analytics"],
                created_by=user_id,
                updated_by=user_id
            ),
        ]
        
        for workflow in workflows:
            session.add(workflow)
        
        await session.commit()
        print(f"✓ Created {len(workflows)} sample workflows")


async def create_sample_chains(user_id: uuid.UUID):
    """Create sample chains (multi-agent workflows)"""
    async with AsyncSessionLocal() as session:
        # Check if chains exist
        result = await session.execute(select(Chain))
        if result.scalars().first():
            print("✓ Sample chains already exist")
            return

        # Fetch agents by name to link them
        agent_names = [
            "Tech Trends Researcher", "Consumer Advisor", "Deal Finder",
            "System Architect", "Cloud Infrastructure Specialist", "Database Expert", "DevOps Engineer",
            "Career Coach", "Job Market Analyst", "Skill Assessor", "Resume Polisher",
            "Research Assistant" # reusing one existing agent
        ]
        
        agents_result = await session.execute(select(Agent).where(Agent.name.in_(agent_names)))
        agents_map = {agent.name: agent.id for agent in agents_result.scalars().all()}
        
        # Verify we have all agents
        if len(agents_map) < len(agent_names):
            print(f"⚠️ Warning: Some agents not found. Creating chains with available agents only.")
            
        chains_data = []
        
        # --- Chain 1: SmartPhone Buying Guide ---
        if all(k in agents_map for k in ["Consumer Advisor", "Tech Trends Researcher", "Deal Finder"]):
            chain_id = uuid.uuid4()
            chain = Chain(
                id=chain_id,
                name="Smartphone Buying Guide",
                description="Interactive guide to help users choose the perfect smartphone, researching trends and finding deals.",
                status=ChainStatus.ACTIVE,
                category="shopping",
                tags=["consumer", "mobile", "guide"],
                input_schema={"type": "object", "properties": {"user_query": {"type": "string"}}},
                created_by=user_id,
                updated_by=user_id
            )
            
            nodes = [
                ChainNode(chain_id=chain_id, node_id="start", node_type=ChainNodeType.START, label="Start", position_x=100, position_y=300, order_index=0),
                ChainNode(chain_id=chain_id, node_id="advisor", node_type=ChainNodeType.AGENT, agent_id=agents_map["Consumer Advisor"], label="Consumer Advisor", position_x=300, position_y=300, order_index=1),
                ChainNode(chain_id=chain_id, node_id="researcher", node_type=ChainNodeType.AGENT, agent_id=agents_map["Tech Trends Researcher"], label="Tech Trends Researcher", position_x=500, position_y=300, order_index=2),
                ChainNode(chain_id=chain_id, node_id="deal_finder", node_type=ChainNodeType.AGENT, agent_id=agents_map["Deal Finder"], label="Deal Finder", position_x=700, position_y=300, order_index=3),
                ChainNode(chain_id=chain_id, node_id="end", node_type=ChainNodeType.END, label="End", position_x=900, position_y=300, order_index=4)
            ]
            
            edges = [
                ChainEdge(chain_id=chain_id, edge_id="e1", source_node_id="start", target_node_id="advisor"),
                ChainEdge(chain_id=chain_id, edge_id="e2", source_node_id="advisor", target_node_id="researcher"),
                ChainEdge(chain_id=chain_id, edge_id="e3", source_node_id="researcher", target_node_id="deal_finder"),
                ChainEdge(chain_id=chain_id, edge_id="e4", source_node_id="deal_finder", target_node_id="end")
            ]
            
            chains_data.append((chain, nodes, edges))

        # --- Chain 2: Enterprise Architecture Planner ---
        if all(k in agents_map for k in ["System Architect", "Cloud Infrastructure Specialist", "Database Expert", "DevOps Engineer"]):
            chain_id = uuid.uuid4()
            chain = Chain(
                id=chain_id,
                name="Enterprise Architecture Planner",
                description="End-to-end software architecture planning, from high-level design to cloud infra and DevOps strategy.",
                status=ChainStatus.ACTIVE,
                category="engineering",
                tags=["architecture", "design", "enterprise"],
                input_schema={"type": "object", "properties": {"requirements": {"type": "string"}}},
                created_by=user_id,
                updated_by=user_id
            )
            
            nodes = [
                ChainNode(chain_id=chain_id, node_id="start", node_type=ChainNodeType.START, label="Start", position_x=100, position_y=300, order_index=0),
                ChainNode(chain_id=chain_id, node_id="architect", node_type=ChainNodeType.AGENT, agent_id=agents_map["System Architect"], label="System Architect", position_x=300, position_y=300, order_index=1),
                ChainNode(chain_id=chain_id, node_id="cloud_spec", node_type=ChainNodeType.AGENT, agent_id=agents_map["Cloud Infrastructure Specialist"], label="Cloud Specialist", position_x=500, position_y=200, order_index=2),
                ChainNode(chain_id=chain_id, node_id="db_expert", node_type=ChainNodeType.AGENT, agent_id=agents_map["Database Expert"], label="DB Expert", position_x=500, position_y=400, order_index=2),
                ChainNode(chain_id=chain_id, node_id="devops", node_type=ChainNodeType.AGENT, agent_id=agents_map["DevOps Engineer"], label="DevOps Engineer", position_x=700, position_y=300, order_index=3),
                ChainNode(chain_id=chain_id, node_id="end", node_type=ChainNodeType.END, label="End", position_x=900, position_y=300, order_index=4)
            ]
            
            edges = [
                ChainEdge(chain_id=chain_id, edge_id="e1", source_node_id="start", target_node_id="architect"),
                ChainEdge(chain_id=chain_id, edge_id="e2", source_node_id="architect", target_node_id="cloud_spec"),
                ChainEdge(chain_id=chain_id, edge_id="e3", source_node_id="architect", target_node_id="db_expert"),
                ChainEdge(chain_id=chain_id, edge_id="e4", source_node_id="cloud_spec", target_node_id="devops"),
                ChainEdge(chain_id=chain_id, edge_id="e5", source_node_id="db_expert", target_node_id="devops"),
                ChainEdge(chain_id=chain_id, edge_id="e6", source_node_id="devops", target_node_id="end")
            ]
            
            chains_data.append((chain, nodes, edges))
            
        # --- Chain 3: Career Path Optimizer ---
        if all(k in agents_map for k in ["Career Coach", "Skill Assessor", "Job Market Analyst", "Resume Polisher"]):
            chain_id = uuid.uuid4()
            chain = Chain(
                id=chain_id,
                name="Career Path Optimizer",
                description="Comprehensive career guidance analyzing skills, market trends, and resume optimization.",
                status=ChainStatus.ACTIVE,
                category="career",
                tags=["career", "growth", "hr"],
                input_schema={"type": "object", "properties": {"user_profile": {"type": "string"}}},
                created_by=user_id,
                updated_by=user_id
            )
            
            nodes = [
                ChainNode(chain_id=chain_id, node_id="start", node_type=ChainNodeType.START, label="Start", position_x=100, position_y=300, order_index=0),
                ChainNode(chain_id=chain_id, node_id="coach", node_type=ChainNodeType.AGENT, agent_id=agents_map["Career Coach"], label="Career Coach", position_x=300, position_y=300, order_index=1),
                ChainNode(chain_id=chain_id, node_id="assessor", node_type=ChainNodeType.AGENT, agent_id=agents_map["Skill Assessor"], label="Skill Assessor", position_x=500, position_y=200, order_index=2),
                ChainNode(chain_id=chain_id, node_id="analyst", node_type=ChainNodeType.AGENT, agent_id=agents_map["Job Market Analyst"], label="Market Analyst", position_x=500, position_y=400, order_index=2),
                ChainNode(chain_id=chain_id, node_id="polisher", node_type=ChainNodeType.AGENT, agent_id=agents_map["Resume Polisher"], label="Resume Polisher", position_x=700, position_y=300, order_index=3),
                ChainNode(chain_id=chain_id, node_id="end", node_type=ChainNodeType.END, label="End", position_x=900, position_y=300, order_index=4)
            ]
            
            edges = [
                ChainEdge(chain_id=chain_id, edge_id="e1", source_node_id="start", target_node_id="coach"),
                ChainEdge(chain_id=chain_id, edge_id="e2", source_node_id="coach", target_node_id="assessor"),
                ChainEdge(chain_id=chain_id, edge_id="e3", source_node_id="coach", target_node_id="analyst"),
                ChainEdge(chain_id=chain_id, edge_id="e4", source_node_id="assessor", target_node_id="polisher"),
                ChainEdge(chain_id=chain_id, edge_id="e5", source_node_id="analyst", target_node_id="polisher"),
                ChainEdge(chain_id=chain_id, edge_id="e6", source_node_id="polisher", target_node_id="end")
            ]
            
            chains_data.append((chain, nodes, edges))

        # Commit all chains
        for chain, nodes, edges in chains_data:
            session.add(chain)
            for node in nodes:
                session.add(node)
            for edge in edges:
                session.add(edge)
                
        await session.commit()
        print(f"✓ Created {len(chains_data)} sample chains")


async def create_sample_tools(user_id: uuid.UUID):
    """Create sample tools"""
    async with AsyncSessionLocal() as session:
        # Check if tools exist
        result = await session.execute(select(Tool))
        if result.scalars().first():
            print("✓ Sample tools already exist")
            return
        
        tools = [
            # Enhanced Tool #1: Weather Checker
            Tool(
                id=uuid.uuid4(),
                name="Weather Checker",
                description="Get real-time weather information for any location worldwide using the Open-Meteo API. Provides temperature, wind speed, and weather conditions.",
                version="1.0.0",
                tool_type=ToolType.CUSTOM,
                status=ToolStatus.ACTIVE,
                code="""def execute(inputs, context=None):
    import httpx
    from urllib.parse import quote
    
    location = inputs.get('location')
    if not location:
        return {"error": "Location is required"}
    
    try:
        # Get coordinates from location name
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={quote(location)}&count=1&language=en&format=json"
        
        with httpx.Client(timeout=10.0) as client:
            geo_res = client.get(geo_url)
            geo_res.raise_for_status()
            geo_data = geo_res.json()
            
            if not geo_data.get('results'):
                return {"error": f"Location not found: {location}"}
            
            location_data = geo_data['results'][0]
            lat, lon = location_data['latitude'], location_data['longitude']
            location_name = f"{location_data.get('name', '')}, {location_data.get('country', '')}"
            
            # Get weather data
            weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&timezone=auto"
            weather_res = client.get(weather_url)
            weather_res.raise_for_status()
            weather_data = weather_res.json()
            
            current = weather_data['current_weather']
            
            # Weather code descriptions
            weather_codes = {
                0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
                45: "Foggy", 48: "Depositing rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
                55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
                71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 95: "Thunderstorm"
            }
            
            return {
                "success": True,
                "location": location_name,
                "temperature_celsius": current['temperature'],
                "temperature_fahrenheit": round(current['temperature'] * 9/5 + 32, 1),
                "windspeed_kmh": current['windspeed'],
                "weather_code": current['weathercode'],
                "weather_description": weather_codes.get(current['weathercode'], "Unknown"),
                "time": current['time']
            }
    except httpx.HTTPError as e:
        return {"error": f"Weather service error: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}""",
                entry_point="execute",
                input_schema={
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "City name or location (e.g., 'London', 'New York', 'Tokyo')"}
                    },
                    "required": ["location"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "location": {"type": "string"},
                        "temperature_celsius": {"type": "number"},
                        "temperature_fahrenheit": {"type": "number"},
                        "windspeed_kmh": {"type": "number"},
                        "weather_code": {"type": "integer"},
                        "weather_description": {"type": "string"},
                        "time": {"type": "string"},
                        "error": {"type": "string"}
                    }
                },
                category="information",
                tags=["weather", "api", "real-time", "open-meteo"],
                capabilities=["weather_lookup", "location_search"],
                created_by=user_id,
                updated_by=user_id
            ),
            
            # Enhanced Tool #2: Wikipedia Search
            Tool(
                id=uuid.uuid4(),
                name="Wikipedia Search",
                description="Search and retrieve article summaries from Wikipedia. Returns title, extract, and link to the full article.",
                version="1.0.0",
                tool_type=ToolType.CUSTOM,
                status=ToolStatus.ACTIVE,
                code="""def execute(inputs, context=None):
    import httpx
    from urllib.parse import quote
    
    query = inputs.get('query')
    language = inputs.get('language', 'en')
    
    if not query:
        return {"error": "Query is required"}
    
    try:
        # Search for the page
        search_url = f"https://{language}.wikipedia.org/w/api.php"
        search_params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": 1
        }
        
        with httpx.Client(timeout=10.0) as client:
            search_res = client.get(search_url, params=search_params)
            search_res.raise_for_status()
            search_data = search_res.json()
            
            if not search_data.get('query', {}).get('search'):
                return {"error": f"No Wikipedia article found for: {query}"}
            
            page_title = search_data['query']['search'][0]['title']
            
            # Get page summary
            summary_url = f"https://{language}.wikipedia.org/api/rest_v1/page/summary/{quote(page_title)}"
            summary_res = client.get(summary_url)
            summary_res.raise_for_status()
            data = summary_res.json()
            
            return {
                "success": True,
                "title": data.get('title'),
                "summary": data.get('extract'),
                "url": data.get('content_urls', {}).get('desktop', {}).get('page'),
                "thumbnail": data.get('thumbnail', {}).get('source') if data.get('thumbnail') else None,
                "language": language
            }
    except httpx.HTTPError as e:
        return {"error": f"Wikipedia service error: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}""",
                entry_point="execute",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Topic to search for on Wikipedia"},
                        "language": {"type": "string", "description": "Language code (default: 'en')", "default": "en"}
                    },
                    "required": ["query"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "title": {"type": "string"},
                        "summary": {"type": "string"},
                        "url": {"type": "string"},
                        "thumbnail": {"type": "string"},
                        "language": {"type": "string"},
                        "error": {"type": "string"}
                    }
                },
                category="research",
                tags=["wikipedia", "knowledge", "encyclopedia", "research"],
                capabilities=["information_retrieval", "knowledge_base"],
                created_by=user_id,
                updated_by=user_id
            ),
            
            # Enhanced Tool #3: Internet Search
            Tool(
                id=uuid.uuid4(),
                name="Internet Search",
                description="Perform instant answers and web searches using DuckDuckGo API. Get summaries, definitions, and related information.",
                version="1.0.0",
                tool_type=ToolType.CUSTOM,
                status=ToolStatus.ACTIVE,
                code="""def execute(inputs, context=None):
    import httpx
    from urllib.parse import quote
    
    query = inputs.get('query')
    if not query:
        return {"error": "Query is required"}
    
    try:
        url = f"https://api.duckduckgo.com/?q={quote(query)}&format=json&no_html=1"
        
        with httpx.Client(timeout=10.0) as client:
            res = client.get(url)
            res.raise_for_status()
            data = res.json()
            
            abstract = data.get('AbstractText', '')
            related = [
                {
                    "text": topic.get('Text', ''),
                    "url": topic.get('FirstURL', '')
                }
                for topic in data.get('RelatedTopics', [])
                if isinstance(topic, dict) and 'Text' in topic
            ][:5]
            
            return {
                "success": True,
                "query": query,
                "abstract": abstract if abstract else "No instant answer available",
                "abstract_source": data.get('AbstractSource'),
                "abstract_url": data.get('AbstractURL'),
                "related_topics": related,
                "answer": data.get('Answer', ''),
                "definition": data.get('Definition', '')
            }
    except httpx.HTTPError as e:
        return {"error": f"Search service error: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}""",
                entry_point="execute",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query or question"}
                    },
                    "required": ["query"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "query": {"type": "string"},
                        "abstract": {"type": "string"},
                        "abstract_source": {"type": "string"},
                        "abstract_url": {"type": "string"},
                        "related_topics": {"type": "array"},
                        "answer": {"type": "string"},
                        "definition": {"type": "string"},
                        "error": {"type": "string"}
                    }
                },
                category="search",
                tags=["web", "search", "duckduckgo", "internet"],
                capabilities=["web_search", "instant_answers"],
                created_by=user_id,
                updated_by=user_id
            ),
            
            # New Tool #4: Calculator
            Tool(
                id=uuid.uuid4(),
                name="Calculator",
                description="Perform mathematical calculations including arithmetic, scientific functions, and expressions. Supports +, -, *, /, **, sqrt, sin, cos, tan, log, etc.",
                version="1.0.0",
                tool_type=ToolType.CUSTOM,
                status=ToolStatus.ACTIVE,
                code="""def execute(inputs, context=None):
    import math
    import re
    
    expression = inputs.get('expression', '')
    if not expression:
        return {"error": "Expression is required"}
    
    try:
        # Safe math evaluation - allow only math operations
        allowed_names = {
            'sqrt': math.sqrt, 'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
            'log': math.log, 'log10': math.log10, 'exp': math.exp, 'abs': abs,
            'pow': pow, 'pi': math.pi, 'e': math.e, 'floor': math.floor,
            'ceil': math.ceil, 'round': round
        }
        
        # Remove any potentially dangerous characters
        if re.search(r'[^0-9+\-*/().%\s,a-z]', expression, re.I):
            # Check if it's just function names
            clean_expr = re.sub(r'[a-z]+', '', expression, flags=re.I)
            if re.search(r'[^0-9+\-*/().%\s,]', clean_expr):
                return {"error": "Invalid characters in expression"}
        
        # Evaluate safely
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        
        return {
            "success": True,
            "expression": expression,
            "result": float(result) if isinstance(result, (int, float)) else str(result)
        }
    except ZeroDivisionError:
        return {"error": "Division by zero"}
    except SyntaxError:
        return {"error": "Invalid mathematical expression"}
    except Exception as e:
        return {"error": f"Calculation error: {str(e)}"}""",
                entry_point="execute",
                input_schema={
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "Mathematical expression to calculate (e.g., '2+2', 'sqrt(16)', 'sin(pi/2)')"
                        }
                    },
                    "required": ["expression"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "expression": {"type": "string"},
                        "result": {"type": "number"},
                        "error": {"type": "string"}
                    }
                },
                category="utilities",
                tags=["calculator", "math", "arithmetic", "scientific"],
                capabilities=["mathematical_operations", "scientific_functions"],
                created_by=user_id,
                updated_by=user_id
            ),
            
            # New Tool #5: Time & Date
            Tool(
                id=uuid.uuid4(),
                name="Time & Date",
                description="Get current time in any timezone, convert between timezones, format dates, and perform date calculations.",
                version="1.0.0",
                tool_type=ToolType.CUSTOM,
                status=ToolStatus.ACTIVE,
                code="""def execute(inputs, context=None):
    from datetime import datetime, timezone
    import re
    
    action = inputs.get('action', 'current_time')
    tz_name = inputs.get('timezone', 'UTC')
    
    try:
        # Simple timezone offset handling (supports: UTC, EST, PST, GMT+5, etc.)
        offset_match = re.match(r'(UTC|GMT)([+-]\d+)?', tz_name, re.I)
        
        if action == 'current_time':
            now = datetime.now(timezone.utc)
            
            # Handle timezone offset
            if offset_match:
                offset_str = offset_match.group(2) or '+0'
                offset_hours = int(offset_str)
                from datetime import timedelta
                now = now + timedelta(hours=offset_hours)
                tz_display = f"UTC{offset_str}" if offset_str != '+0' else 'UTC'
            else:
                tz_display = tz_name
            
            return {
                "success": True,
                "action": "current_time",
                "timezone": tz_display,
                "datetime": now.strftime('%Y-%m-%d %H:%M:%S'),
                "date": now.strftime('%Y-%m-%d'),
                "time": now.strftime('%H:%M:%S'),
                "iso_format": now.isoformat(),
                "timestamp": int(now.timestamp())
            }
        
        elif action == 'format':
            date_str = inputs.get('date_string')
            fmt = inputs.get('format', '%Y-%m-%d %H:%M:%S')
            
            if not date_str:
                return {"error": "date_string is required for format action"}
            
            # Try to parse common formats
            for parse_fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d', '%d-%m-%Y']:
                try:
                    dt = datetime.strptime(date_str, parse_fmt)
                    return {
                        "success": True,
                        "action": "format",
                        "formatted": dt.strftime(fmt),
                        "iso_format": dt.isoformat()
                    }
                except ValueError:
                    continue
            
            return {"error": "Unable to parse date string. Use format: YYYY-MM-DD or YYYY-MM-DD HH:MM:SS"}
        
        else:
            return {"error": f"Unknown action: {action}. Use 'current_time' or 'format'"}
            
    except Exception as e:
        return {"error": f"Date/time error: {str(e)}"}""",
                entry_point="execute",
                input_schema={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["current_time", "format"],
                            "description": "Action to perform",
                            "default": "current_time"
                        },
                        "timezone": {
                            "type": "string",
                            "description": "Timezone (e.g., 'UTC', 'UTC+5', 'UTC-8')",
                            "default": "UTC"
                        },
                        "date_string": {
                            "type": "string",
                            "description": "Date string to format (for 'format' action)"
                        },
                        "format": {
                            "type": "string",
                            "description": "Output format (for 'format' action)",
                            "default": "%Y-%m-%d %H:%M:%S"
                        }
                    },
                    "required": []
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "action": {"type": "string"},
                        "timezone": {"type": "string"},
                        "datetime": {"type": "string"},
                        "date": {"type": "string"},
                        "time": {"type": "string"},
                        "iso_format": {"type": "string"},
                        "timestamp": {"type": "integer"},
                        "formatted": {"type": "string"},
                        "error": {"type": "string"}
                    }
                },
                category="utilities",
                tags=["time", "date", "timezone", "datetime"],
                capabilities=["time_operations", "date_formatting", "timezone_conversion"],
                created_by=user_id,
                updated_by=user_id
            ),
            
            # New Tool #6: Text Transformer
            Tool(
                id=uuid.uuid4(),
                name="Text Transformer",
                description="Transform text with various operations: case conversion, base64 encoding/decoding, URL encoding, string reversal, and more.",
                version="1.0.0",
                tool_type=ToolType.CUSTOM,
                status=ToolStatus.ACTIVE,
                code="""def execute(inputs, context=None):
    import base64
    from urllib.parse import quote, unquote
    
    text = inputs.get('text', '')
    operation = inputs.get('operation', 'upper')
    
    if not text:
        return {"error": "Text is required"}
    
    try:
        result = None
        
        if operation == 'upper':
            result = text.upper()
        elif operation == 'lower':
            result = text.lower()
        elif operation == 'title':
            result = text.title()
        elif operation == 'reverse':
            result = text[::-1]
        elif operation == 'base64_encode':
            result = base64.b64encode(text.encode()).decode()
        elif operation == 'base64_decode':
            result = base64.b64decode(text.encode()).decode()
        elif operation == 'url_encode':
            result = quote(text)
        elif operation == 'url_decode':
            result = unquote(text)
        elif operation == 'snake_case':
            import re
            result = re.sub(r'(?<!^)(?=[A-Z])', '_', text).lower()
            result = re.sub(r'\s+', '_', result)
        elif operation == 'camel_case':
            import re
            words = re.split(r'[_\s]+', text)
            result = words[0].lower() + ''.join(w.capitalize() for w in words[1:])
        elif operation == 'length':
            result = str(len(text))
        elif operation == 'word_count':
            result = str(len(text.split()))
        else:
            return {"error": f"Unknown operation: {operation}"}
        
        return {
            "success": True,
            "operation": operation,
            "original": text,
            "result": result
        }
    except Exception as e:
        return {"error": f"Transformation error: {str(e)}"}""",
                entry_point="execute",
                input_schema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Text to transform"},
                        "operation": {
                            "type": "string",
                            "enum": ["upper", "lower", "title", "reverse", "base64_encode", "base64_decode", 
                                   "url_encode", "url_decode", "snake_case", "camel_case", "length", "word_count"],
                            "description": "Transformation operation to perform",
                            "default": "upper"
                        }
                    },
                    "required": ["text"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "operation": {"type": "string"},
                        "original": {"type": "string"},
                        "result": {"type": "string"},
                        "error": {"type": "string"}
                    }
                },
                category="utilities",
                tags=["text", "string", "transformation", "encoding"],
                capabilities=["text_manipulation", "encoding", "formatting"],
                created_by=user_id,
                updated_by=user_id
            ),
            
            # New Tool #7: JSON Parser
            Tool(
                id=uuid.uuid4(),
                name="JSON Parser",
                description="Validate, format, prettify, and query JSON data. Parse JSON strings and extract specific values.",
                version="1.0.0",
                tool_type=ToolType.CUSTOM,
                status=ToolStatus.ACTIVE,
                code="""def execute(inputs, context=None):
    import json
    
    json_string = inputs.get('json_string', '')
    operation = inputs.get('operation', 'validate')
    query_path = inputs.get('query_path', '')
    
    if not json_string:
        return {"error": "json_string is required"}
    
    try:
        # Parse JSON
        try:
            data = json.loads(json_string)
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON: {str(e)}", "valid": False}
        
        if operation == 'validate':
            return {
                "success": True,
                "valid": True,
                "message": "JSON is valid"
            }
        
        elif operation == 'format':
            formatted = json.dumps(data, indent=2, sort_keys=True)
            return {
                "success": True,
                "formatted": formatted,
                "compact": json.dumps(data, separators=(',', ':'))
            }
        
        elif operation == 'query':
            if not query_path:
                return {"error": "query_path is required for query operation"}
            
            # Simple JSONPath implementation (supports: key, key.subkey, key[0])
            result = data
            for part in query_path.split('.'):
                if '[' in part:
                    key, index = part.split('[')
                    index = int(index.rstrip(']'))
                    result = result[key][index] if key else result[index]
                else:
                    result = result[part]
            
            return {
                "success": True,
                "query_path": query_path,
                "result": result
            }
        
        elif operation == 'keys':
            if isinstance(data, dict):
                return {
                    "success": True,
                    "keys": list(data.keys())
                }
            else:
                return {"error": "JSON data is not an object"}
        
        else:
            return {"error": f"Unknown operation: {operation}"}
            
    except KeyError as e:
        return {"error": f"Key not found: {str(e)}"}
    except IndexError as e:
        return {"error": f"Index out of range: {str(e)}"}
    except Exception as e:
        return {"error": f"JSON processing error: {str(e)}"}""",
                entry_point="execute",
                input_schema={
                    "type": "object",
                    "properties": {
                        "json_string": {"type": "string", "description": "JSON string to process"},
                        "operation": {
                            "type": "string",
                            "enum": ["validate", "format", "query", "keys"],
                            "description": "Operation to perform",
                            "default": "validate"
                        },
                        "query_path": {
                            "type": "string",
                            "description": "JSON path for query operation (e.g., 'user.name', 'items[0]')"
                        }
                    },
                    "required": ["json_string"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "valid": {"type": "boolean"},
                        "message": {"type": "string"},
                        "formatted": {"type": "string"},
                        "compact": {"type": "string"},
                        "query_path": {"type": "string"},
                        "result": {},
                        "keys": {"type": "array"},
                        "error": {"type": "string"}
                    }
                },
                category="utilities",
                tags=["json", "parsing", "validation", "data"],
                capabilities=["json_processing", "data_validation", "data_extraction"],
                created_by=user_id,
                updated_by=user_id
            ),
            
            # New Tool #8: HTTP Request
            Tool(
                id=uuid.uuid4(),
                name="HTTP Request",
                description="Make HTTP GET and POST requests to external APIs. Supports custom headers, query parameters, and request bodies.",
                version="1.0.0",
                tool_type=ToolType.CUSTOM,
                status=ToolStatus.ACTIVE,
                code="""def execute(inputs, context=None):
    import httpx
    import json as json_module
    
    url = inputs.get('url')
    method = inputs.get('method', 'GET').upper()
    headers = inputs.get('headers', {})
    params = inputs.get('params', {})
    body = inputs.get('body')
    timeout = inputs.get('timeout', 10)
    
    if not url:
        return {"error": "URL is required"}
    
    if method not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
        return {"error": f"Unsupported method: {method}"}
    
    try:
        with httpx.Client(timeout=timeout) as client:
            if method == 'GET':
                response = client.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = client.post(url, headers=headers, params=params, 
                                     json=body if isinstance(body, dict) else None,
                                     content=body if isinstance(body, str) else None)
            elif method == 'PUT':
                response = client.put(url, headers=headers, params=params,
                                    json=body if isinstance(body, dict) else None,
                                    content=body if isinstance(body, str) else None)
            elif method == 'DELETE':
                response = client.delete(url, headers=headers, params=params)
            elif method == 'PATCH':
                response = client.patch(url, headers=headers, params=params,
                                      json=body if isinstance(body, dict) else None,
                                      content=body if isinstance(body, str) else None)
            
            # Try to parse response as JSON
            try:
                response_body = response.json()
            except:
                response_body = response.text
            
            return {
                "success": True,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response_body,
                "url": str(response.url)
            }
    except httpx.TimeoutException:
        return {"error": f"Request timeout after {timeout} seconds"}
    except httpx.HTTPError as e:
        return {"error": f"HTTP error: {str(e)}"}
    except Exception as e:
        return {"error": f"Request error: {str(e)}"}""",
                entry_point="execute",
                input_schema={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to send request to"},
                        "method": {
                            "type": "string",
                            "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                            "description": "HTTP method",
                            "default": "GET"
                        },
                        "headers": {
                            "type": "object",
                            "description": "HTTP headers as key-value pairs",
                            "default": {}
                        },
                        "params": {
                            "type": "object",
                            "description": "Query parameters as key-value pairs",
                            "default": {}
                        },
                        "body": {
                            "description": "Request body (string or object for JSON)",
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in seconds",
                            "default": 10
                        }
                    },
                    "required": ["url"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "status_code": {"type": "integer"},
                        "headers": {"type": "object"},
                        "body": {},
                        "url": {"type": "string"},
                        "error": {"type": "string"}
                    }
                },
                category="integration",
                tags=["http", "api", "request", "web"],
                capabilities=["http_requests", "api_integration", "web_scraping"],
                created_by=user_id,
                updated_by=user_id
            ),
            
            # New Tool #9: File Hash Calculator
            Tool(
                id=uuid.uuid4(),
                name="File Hash Calculator",
                description="Calculate cryptographic hashes (MD5, SHA1, SHA256, SHA512) for text content. Useful for data verification and integrity checks.",
                version="1.0.0",
                tool_type=ToolType.CUSTOM,
                status=ToolStatus.ACTIVE,
                code="""def execute(inputs, context=None):
    import hashlib
    
    content = inputs.get('content', '')
    algorithm = inputs.get('algorithm', 'sha256').lower()
    
    if not content:
        return {"error": "Content is required"}
    
    try:
        # Convert content to bytes
        content_bytes = content.encode('utf-8')
        
        # Calculate hash based on algorithm
        if algorithm == 'md5':
            hash_obj = hashlib.md5(content_bytes)
        elif algorithm == 'sha1':
            hash_obj = hashlib.sha1(content_bytes)
        elif algorithm == 'sha256':
            hash_obj = hashlib.sha256(content_bytes)
        elif algorithm == 'sha512':
            hash_obj = hashlib.sha512(content_bytes)
        else:
            return {"error": f"Unsupported algorithm: {algorithm}. Use md5, sha1, sha256, or sha512"}
        
        hash_hex = hash_obj.hexdigest()
        
        return {
            "success": True,
            "algorithm": algorithm,
            "hash": hash_hex,
            "content_length": len(content)
        }
    except Exception as e:
        return {"error": f"Hash calculation error: {str(e)}"}""",
                entry_point="execute",
                input_schema={
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "Text content to hash"},
                        "algorithm": {
                            "type": "string",
                            "enum": ["md5", "sha1", "sha256", "sha512"],
                            "description": "Hash algorithm to use",
                            "default": "sha256"
                        }
                    },
                    "required": ["content"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "algorithm": {"type": "string"},
                        "hash": {"type": "string"},
                        "content_length": {"type": "integer"},
                        "error": {"type": "string"}
                    }
                },
                category="utilities",
                tags=["hash", "crypto", "md5", "sha256", "checksum"],
                capabilities=["hashing", "data_verification", "cryptography"],
                created_by=user_id,
                updated_by=user_id
            )
        ]
        
        for tool in tools:
            session.add(tool)

        await session.commit()
        print(f"✓ Created {len(tools)} sample tools")


async def create_sample_mcp_servers(user_id: uuid.UUID):
    """Create sample MCP servers"""
    async with AsyncSessionLocal() as session:
        # Check if MCP servers exist
        result = await session.execute(select(MCPServer))
        if result.scalars().first():
            print("✓ Sample MCP servers already exist")
            return

        mcp_servers = [
            MCPServer(
                id=uuid.uuid4(),
                name="GitHub Integration",
                description="Connect to GitHub repositories to manage issues, pull requests, and code.",
                base_url="https://api.github.com",
                version="1.0.0",
                status=MCPServerStatus.CONNECTED,
                capabilities=["access_repositories", "manage_issues", "code_search"],
                created_by=user_id,
                updated_by=user_id
            ),
            MCPServer(
                id=uuid.uuid4(),
                name="Slack Bot",
                description="Integration with Slack workspace for messaging and notifications.",
                base_url="wss://slack.com/mcp",
                version="1.2.0",
                status=MCPServerStatus.CONNECTED,
                capabilities=["send_messages", "read_channels"],
                created_by=user_id,
                updated_by=user_id
            ),
            MCPServer(
                id=uuid.uuid4(),
                name="Weather API",
                description="External weather provider integration.",
                base_url="https://api.weather.com/mcp",
                version="2.1.0",
                status=MCPServerStatus.DISCONNECTED,
                capabilities=["weather_forecast", "historical_data"],
                created_by=user_id,
                updated_by=user_id
            )
        ]
        
        for server in mcp_servers:
            session.add(server)
        
        await session.commit()
        print(f"✓ Created {len(mcp_servers)} sample MCP servers")


async def wait_for_database():
    """Wait for database to be ready with retry logic."""
    from shared.database.connection import async_engine
    from sqlalchemy import text
    import asyncio
    
    max_retries = 10
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            async with async_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            print(f"✅ Database connection established")
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"⏳ Waiting for database... (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(retry_delay)
            else:
                print(f"❌ Failed to connect to database after {max_retries} attempts")
                raise


async def create_interactive_smartphone_guide(admin_id: uuid.UUID):
    """Create interactive smartphone buying guide with specialized agents and workflow."""
    async with AsyncSessionLocal() as session:
        print("Creating Interactive Smartphone Buying Guide...")
        
        # Check if already exists
        result = await session.execute(
            select(Agent).where(Agent.name == "Smartphone Qualifier")
        )
        if result.scalar_one_or_none():
            print("  ✓ Interactive agents already exist")
            return
        
        model_config = {
            "model_name": "llama3.2",
            "llm_provider": "ollama",
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        # 1. Qualifier Agent
        qualifier = Agent(
            name="Smartphone Qualifier",
            description="Asks clarifying questions to understand user needs",
            type=AgentType.CONVERSATIONAL,
            status=AgentStatus.ACTIVE,
            system_prompt="""You are a friendly smartphone shopping assistant. Your goal is to gather information, NOT to recommend phones yet.

PHASE 1: GATHER INFO
Ask questions ONE AT A TIME. Wait for the user's answer before asking the next one.
1. "Hi! I'd be happy to help you find the perfect smartphone. To start, what's your approximate budget?"
2. "Great! What will you mainly use the phone for? (e.g., photography, gaming, business, general use)"
3. "Do you have a preferred brand, or are you open to suggestions?"
4. "Any specific features you need? (e.g., 5G, long battery, small size)"

Do NOT output JSON during this phase. Just chat normally.

PHASE 2: HANDOFF
ONLY after you have answers for ALL 4 questions, output strictly this JSON object to proceed to the next step:

{
  "budget_max": 1000,
  "use_case": "photography",
  "brand_preference": "Samsung",
  "must_have_features": ["good camera", "fast charging"],
  "ready_for_routing": true
}""",
            config=model_config.copy(),
            created_by=admin_id
        )
        session.add(qualifier)
        
        # 2. Router Agent
        router = Agent(
            name="Smartphone Router",
            description="Routes users to appropriate specialist based on needs",
            type=AgentType.CONVERSATIONAL,
            status=AgentStatus.ACTIVE,
            system_prompt="""You are a routing agent. Analyze user preferences and route silently.

Input: User preferences JSON
Output: ONLY this JSON (no explanation):

{
  "route_to": "camera_specialist",
  "user_summary": "Budget: $1000, wants great camera, prefers Samsung, needs fast charging"
}

Routing rules:
- "camera_specialist" if use_case mentions photography/camera
- "gaming_specialist" if use_case mentions gaming
- "business_specialist" if use_case mentions work/business/productivity
- "budget_specialist" if budget < $600 or they emphasize value/price

Keep user_summary brief and natural.""",
            config={**model_config, "temperature": 0.3, "max_tokens": 300},
            created_by=admin_id
        )
        session.add(router)
        
        # 3-6. Specialist Agents
        specialists = [
            ("Budget Phone Specialist", "Recommends best value smartphones within budget", "budget"),
            ("Camera Phone Specialist", "Recommends smartphones with best camera capabilities", "camera"),
            ("Gaming Phone Specialist", "Recommends smartphones optimized for gaming", "gaming"),
            ("Business Phone Specialist", "Recommends smartphones for business and productivity", "business")
        ]
        
        specialist_prompt_template = """You are a {specialty} phone expert. Give direct, helpful recommendations based on what the user told us.

You'll receive: User's budget, preferences, and requirements

Your response should be conversational and helpful:

"Based on what you're looking for, here are my top 3 {specialty} phone recommendations:

**1. [Phone Name] - $[Price]**
This is my top pick for you because [why it matches their needs]. {key_features}. You can find it at [retailer] for $[price].

**2. [Phone Name] - $[Price]**
Great alternative with [key feature]. [Why it's good for them].

**3. [Phone Name] - $[Price]**
Budget-friendly option that still delivers [key benefit].

My recommendation: Go with the [#1 phone] - it hits all your requirements and {specialty_benefit}."

Keep it natural, friendly, and focused on THEIR needs. No follow-up questions."""
        
        for name, desc, specialty in specialists:
            agent = Agent(
                name=name,
                description=desc,
                type=AgentType.CONVERSATIONAL,
                status=AgentStatus.ACTIVE,
                system_prompt=specialist_prompt_template.format(
                    specialty=specialty,
                    key_features="The camera system features" if specialty == "camera" else "Key specs",
                    specialty_benefit="the camera quality is outstanding" if specialty == "camera" else "delivers great performance"
                ),
                config={**model_config, "max_tokens": 1000},
                available_tools=["web_search"],
                created_by=admin_id
            )
            session.add(agent)
        
        # 7. Summarizer Agent
        summarizer = Agent(
            name="Recommendation Summarizer",
            description="Compiles specialist recommendations into final advice",
            type=AgentType.CONVERSATIONAL,
            status=AgentStatus.ACTIVE,
            system_prompt="""You are wrapping up the conversation with a final, friendly recommendation.

You'll receive: Specialist's recommendations

Your job: Present the TOP choice in a warm, conversational way:

"Perfect! Based on everything you've told me, I'd recommend the **[Phone Name]** for $[price].

Here's why it's perfect for you:
✓ [Reason 1 specific to their needs]
✓ [Reason 2 specific to their needs]  
✓ [Reason 3 specific to their needs]

You can grab it at [retailer] - they currently have [deal if any].

If that's a bit over budget, the [Alternative] at $[price] is also excellent and gives you [key benefit].

Want me to tell you more about any of these phones?"

Keep it friendly, concise, and action-oriented. Make them feel confident in the choice.""",
            config={**model_config, "max_tokens": 800},
            created_by=admin_id
        )
        session.add(summarizer)
        
        await session.flush()
        
        # Get agent IDs for workflow
        result = await session.execute(
            select(Agent).where(Agent.name.in_([
                "Smartphone Qualifier", "Smartphone Router",
                "Budget Phone Specialist", "Camera Phone Specialist",
                "Gaming Phone Specialist", "Business Phone Specialist",
                "Recommendation Summarizer"
            ]))
        )
        agents_dict = {agent.name: agent for agent in result.scalars().all()}
        
        # Create the workflow/chain
        chain = Chain(
            name="Interactive Smartphone Buying Guide",
            description="An interactive, conversational smartphone buying guide that asks questions and routes to specialized agents",
            status=ChainStatus.ACTIVE,
            category="Shopping Assistant",
            tags=["smartphone", "shopping", "interactive", "conversational"],
            input_schema={
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "User's message"}
                }
            },
            created_by=admin_id
        )
        session.add(chain)
        await session.flush()
        
        # Create nodes
        positions = {
            "start": (100, 300), "qualifier": (300, 300), "router": (500, 300),
            "budget": (700, 100), "camera": (700, 200), "gaming": (700, 400),
            "business": (700, 500), "summarizer": (900, 300), "end": (1100, 300)
        }
        
        nodes = {}
        node_configs = [
            ("start", ChainNodeType.START, None, "Start", 0),
            ("qualifier", ChainNodeType.AGENT, agents_dict["Smartphone Qualifier"].id, "Ask Questions", 1),
            ("router", ChainNodeType.AGENT, agents_dict["Smartphone Router"].id, "Route to Specialist", 2),
            ("budget", ChainNodeType.AGENT, agents_dict["Budget Phone Specialist"].id, "Budget Specialist", 3),
            ("camera", ChainNodeType.AGENT, agents_dict["Camera Phone Specialist"].id, "Camera Specialist", 3),
            ("gaming", ChainNodeType.AGENT, agents_dict["Gaming Phone Specialist"].id, "Gaming Specialist", 3),
            ("business", ChainNodeType.AGENT, agents_dict["Business Phone Specialist"].id, "Business Specialist", 3),
            ("summarizer", ChainNodeType.AGENT, agents_dict["Recommendation Summarizer"].id, "Compile Recommendation", 4),
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
            nodes[node_id] = node
        
        await session.flush()
        
        # Create edges with conditional routing
        edges = [
            ("start_to_qualifier", "start", "qualifier", "Begin", None),
            ("qualifier_to_router", "qualifier", "router", "Preferences Gathered",
             {"type": "json_contains", "field": "ready_for_routing", "value": True}),
            ("router_to_budget", "router", "budget", "Budget Priority",
             {"type": "json_contains", "field": "route_to", "value": "budget_specialist"}),
            ("router_to_camera", "router", "camera", "Camera Priority",
             {"type": "json_contains", "field": "route_to", "value": "camera_specialist"}),
            ("router_to_gaming", "router", "gaming", "Gaming Priority",
             {"type": "json_contains", "field": "route_to", "value": "gaming_specialist"}),
            ("router_to_business", "router", "business", "Business Priority",
             {"type": "json_contains", "field": "route_to", "value": "business_specialist"}),
            ("budget_to_summarizer", "budget", "summarizer", "Recommendations", None),
            ("camera_to_summarizer", "camera", "summarizer", "Recommendations", None),
            ("gaming_to_summarizer", "gaming", "summarizer", "Recommendations", None),
            ("business_to_summarizer", "business", "summarizer", "Recommendations", None),
            ("summarizer_to_end", "summarizer", "end", "Final Advice", None)
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
        print("  ✓ Created 7 specialized agents and interactive workflow")



async def main():
    print("🌱 Seeding database with sample data...\n")
    
    try:
        # Wait for database to be ready
        await wait_for_database()
        
        # Create admin user
        admin_user = await create_admin_user()
        
        # Create sample data
        await create_sample_agents(admin_user.id)
        await create_sample_workflows(admin_user.id)
        await create_sample_chains(admin_user.id)
        await create_sample_tools(admin_user.id)
        await create_sample_mcp_servers(admin_user.id)
        await create_interactive_smartphone_guide(admin_user.id)
        
        # Import and create enhanced workflows
        from scripts.create_architecture_planner import create_enterprise_architecture_planner
        from scripts.create_career_optimizer import create_career_path_optimizer
        await create_enterprise_architecture_planner(admin_user.id)
        await create_career_path_optimizer(admin_user.id)
        
        print("\n✅ Database seeding completed successfully!")
        print("\n📝 Login credentials:")
        print("   Email: admin@example.com")
        print("   Password: admin")
        
    except Exception as e:
        print(f"\n❌ Error seeding database: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
