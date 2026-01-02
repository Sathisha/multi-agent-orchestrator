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
from shared.models.tool import Tool, ToolType, ToolStatus
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
        user.is_system_admin = True
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
                system_prompt="You are a helpful customer support assistant. Be polite, professional, and solve customer issues efficiently.",
                config={
                    "model": "gpt-4",
                    "temperature": 0.7,
                    "max_tokens": 2000
                },
                available_tools=["Weather Checker", "Wikipedia Search"],
                created_by=user_id,
                updated_by=user_id
            ),
            Agent(
                id=uuid.uuid4(),
                name="Code Review Assistant",
                description="Analyzes code and provides detailed reviews with suggestions",
                type=AgentType.TASK,
                status=AgentStatus.ACTIVE,
                version="1.0",
                system_prompt="You are an expert code reviewer. Analyze code for bugs, performance issues, and best practices.",
                config={
                    "model": "gpt-4",
                    "temperature": 0.3,
                    "max_tokens": 3000
                },
                available_tools=["Code Reviewer", "Linter"],
                capabilities=["code_review", "bug_detection", "refactoring"],
                tags=["development", "code-quality"],
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
                available_tools=["Wikipedia Search"],
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
                available_tools=["Internet Search", "Weather Checker"],
                capabilities=["data_analysis", "visualization", "reporting"],
                tags=["analytics", "data"],
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
                process_definition_key="customer_onboarding",
                bpmn_xml='<?xml version="1.0" encoding="UTF-8"?><definitions></definitions>',
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
                process_definition_key="content_review",
                bpmn_xml='<?xml version="1.0" encoding="UTF-8"?><definitions></definitions>',
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
                process_definition_key="data_pipeline",
                bpmn_xml='<?xml version="1.0" encoding="UTF-8"?><definitions></definitions>',
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


async def create_sample_tools(user_id: uuid.UUID):
    """Create sample tools"""
    async with AsyncSessionLocal() as session:
        # Check if tools exist
        result = await session.execute(select(Tool))
        if result.scalars().first():
            print("✓ Sample tools already exist")
            return
        
        tools = [
            Tool(
                id=uuid.uuid4(),
                name="Weather Checker",
                description="Get real-time weather information for any location worldwide using the Open-Meteo API.",
                version="1.0.0",
                tool_type=ToolType.CUSTOM,
                status=ToolStatus.ACTIVE,
                code="""def execute(inputs, context=None):
    import httpx
    location = inputs.get('location', 'London')
    # Get coordinates
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1&language=en&format=json"
    with httpx.Client(timeout=10.0) as client:
        geo_res = client.get(geo_url)
        if geo_res.status_code != 200 or not geo_res.json().get('results'):
            return {"error": f"Could not find location: {location}"}
        
        res = geo_res.json()['results'][0]
        lat, lon = res['latitude'], res['longitude']
        
        # Get weather
        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        w_res = client.get(w_url)
        if w_res.status_code != 200:
            return {"error": "Weather service unavailable"}
        
        w_data = w_res.json()['current_weather']
        return {
            "location": f"{res['name']}, {res.get('country', '')}",
            "temperature": w_data['temperature'],
            "windspeed": w_data['windspeed'],
            "condition_code": w_data['weathercode']
        }""",
                entry_point="execute",
                input_schema={
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "The city and country to check weather for"}
                    },
                    "required": ["location"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"},
                        "temperature": {"type": "number"},
                        "windspeed": {"type": "number"},
                        "condition_code": {"type": "integer"}
                    }
                },
                category="information",
                tags=["weather", "api", "real-time"],
                capabilities=["weather_lookup"],
                created_by=user_id,
                updated_by=user_id
            ),
            Tool(
                id=uuid.uuid4(),
                name="Wikipedia Search",
                description="Search for and retrieve summaries of articles from Wikipedia.",
                version="1.0.0",
                tool_type=ToolType.CUSTOM,
                status=ToolStatus.ACTIVE,
                code="""def execute(inputs, context=None):
    import httpx
    query = inputs.get('query')
    if not query: return {"error": "No query provided"}
    
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{query.replace(' ', '_')}"
    with httpx.Client(timeout=10.0) as client:
        res = client.get(url)
        if res.status_code == 404:
            return {"error": "Wikipedia page not found"}
        if res.status_code != 200:
            return {"error": "Wikipedia service error"}
        
        data = res.json()
        return {
            "title": data.get('title'),
            "summary": data.get('extract'),
            "url": data.get('content_urls', {}).get('desktop', {}).get('page')
        }""",
                entry_point="execute",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The topic to search for on Wikipedia"}
                    },
                    "required": ["query"]
                },
                category="research",
                tags=["wiki", "knowledge", "encyclopedia"],
                capabilities=["information_retrieval"],
                created_by=user_id,
                updated_by=user_id
            ),
            Tool(
                id=uuid.uuid4(),
                name="Internet Search",
                description="Perform a web search using DuckDuckGo to find information, news, and answers.",
                version="1.0.0",
                tool_type=ToolType.CUSTOM,
                status=ToolStatus.ACTIVE,
                code="""def execute(inputs, context=None):
    import httpx
    query = inputs.get('query')
    if not query: return {"error": "No query provided"}
    
    url = f"https://api.duckduckgo.com/?q={query}&format=json"
    with httpx.Client(timeout=10.0) as client:
        res = client.get(url)
        if res.status_code != 200:
            return {"error": "Search service error"}
        
        data = res.json()
        return {
            "abstract": data.get('AbstractText'),
            "source": data.get('AbstractSource'),
            "related": [t.get('Text') for t in data.get('RelatedTopics', []) if 'Text' in t][:3]
        }""",
                entry_point="execute",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query"}
                    },
                    "required": ["query"]
                },
                category="search",
                tags=["web", "search", "duckduckgo"],
                capabilities=["web_search"],
                created_by=user_id,
                updated_by=user_id
            ),
            Tool(
                id=uuid.uuid4(),
                name="Code Reviewer",
                description="Mock tool for code analysis",
                version="1.0.0",
                tool_type=ToolType.CUSTOM,
                status=ToolStatus.ACTIVE,
                code="""def execute(inputs, context=None):
    code = inputs.get('code', '')
    return {
        "score": 85,
        "issues": ["Unused import at line 5", "Function too long at line 20"],
        "suggestions": ["Refactor execute into smaller functions"]
    }""",
                entry_point="execute",
                input_schema={"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]},
                category="development",
                created_by=user_id,
                updated_by=user_id
            ),
            Tool(
                id=uuid.uuid4(),
                name="Linter",
                description="Mock linter tool",
                version="1.0.0",
                tool_type=ToolType.CUSTOM,
                status=ToolStatus.ACTIVE,
                code="""def execute(inputs, context=None):
    return {"errors": [], "warnings": ["Line too long"]}""",
                entry_point="execute",
                input_schema={"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]},
                category="development",
                created_by=user_id,
                updated_by=user_id
            )
        ]
        
        for tool in tools:
            session.add(tool)
        
        await session.commit()
        print(f"✓ Created {len(tools)} sample tools")


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
        await create_sample_tools(admin_user.id)
        
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
