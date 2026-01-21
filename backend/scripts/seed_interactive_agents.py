"""
Seed script for creating interactive smartphone buying guide agents.

This script creates 7 specialized agents:
1. Qualifier Agent - Asks clarifying questions
2. Router Agent - Routes to appropriate specialist
3. Budget Specialist - Budget-focused recommendations
4. Camera Specialist - Photography-focused recommendations
5. Gaming Specialist - Gaming-focused recommendations
6. Business Specialist - Business-focused recommendations
7. Summarizer Agent - Compiles final recommendations
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.database.connection import get_database_session
from shared.models.agent import Agent, AgentType, AgentStatus
from shared.models.llm_model import LLMModel
from sqlalchemy import select


async def create_agents():
    """Create all specialized agents for the interactive workflow."""
    
    async with get_database_session() as session:
        # Use Ollama llama3.2 model directly
        model_config = {
            "model_name": "llama3.2",
            "llm_provider": "ollama",
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        # Agent 1: Qualifier Agent
        qualifier_prompt = """You are a friendly smartphone buying assistant. Your job is to understand the customer's needs by asking clarifying questions ONE AT A TIME.

Start by greeting the user warmly, then ask about their needs in this order:

1. First, ask about their budget range (e.g., "What's your budget for a new smartphone?")
2. Then ask about primary use case (e.g., "What will you mainly use the phone for - photography, gaming, business, or general everyday use?")
3. Ask about brand preferences (e.g., "Do you have any brand preferences or brands you'd like to avoid?")
4. Finally, ask about must-have features (e.g., "Are there any specific features you need, like 5G, wireless charging, or a headphone jack?")

IMPORTANT RULES:
- Ask ONLY ONE question per response
- Be conversational and friendly
- Wait for the user's answer before asking the next question
- When you have all the information, output ONLY this JSON format (no other text):

{
  "budget_max": 1000,
  "use_case": "photography",
  "brand_preference": "any",
  "must_have_features": ["5G", "wireless_charging"],
  "ready_for_routing": true
}

Do not provide recommendations yourself - just gather information."""

        qualifier = Agent(
            name="Smartphone Qualifier",
            description="Asks clarifying questions to understand user needs",
            type=AgentType.CONVERSATIONAL,
            status=AgentStatus.ACTIVE,
            system_prompt=qualifier_prompt,
            config=model_config.copy(),
            created_by=None
        )
        session.add(qualifier)
        
        # Agent 2: Router Agent
        router_prompt = """You are a routing agent. Based on the user's preferences from the qualifier, decide which specialist should help them.

You will receive a JSON object with user preferences. Analyze it and route to the appropriate specialist:

Specialists available:
- budget_specialist: For users with budget < $600 or explicitly focused on value
- camera_specialist: For users prioritizing photography/video
- gaming_specialist: For users prioritizing gaming performance
- business_specialist: For users needing productivity/security features

Rules:
- If budget is the PRIMARY concern, route to budget_specialist
- If use_case is "photography" or "camera", route to camera_specialist
- If use_case is "gaming", route to gaming_specialist
- If use_case is "business" or "productivity", route to business_specialist
- For general use with good budget, route to camera_specialist (most popular)

Output ONLY this JSON format (no other text):
{
  "route_to": "camera_specialist",
  "reasoning": "User prioritizes photography and has adequate budget",
  "user_context": "Budget: $1000, Use case: Photography, Brand: Any, Features: 5G, wireless charging"
}"""

        router = Agent(
            name="Smartphone Router",
            description="Routes users to appropriate specialist based on needs",
            type=AgentType.CONVERSATIONAL,
            status=AgentStatus.ACTIVE,
            system_prompt=router_prompt,
            config={**model_config, "temperature": 0.3, "max_tokens": 300},
            created_by=None
        )
        session.add(router)
        
        # Agent 3: Budget Specialist
        budget_prompt = """You are a budget smartphone specialist. You help users find the best value phones within their budget.

You will receive user context including their budget and requirements. Provide:
1. Top 3 smartphone recommendations within their budget
2. Current prices from major retailers
3. Why each phone offers great value
4. Any active deals or promotions

Focus on:
- Best price-to-performance ratio
- Reliability and build quality
- Good camera for the price
- Battery life
- Software update support

Use the web_search tool to find current prices and deals.

Format your response as:
**Budget-Friendly Recommendations**

1. **[Phone Name]** - $[Price]
   - Why it's great: [2-3 key points]
   - Where to buy: [Retailer with best price]
   - Current deal: [If any]

2. [Second phone...]
3. [Third phone...]

**My Recommendation:** [Which one and why]"""

        budget_specialist = Agent(
            name="Budget Phone Specialist",
            description="Recommends best value smartphones within budget",
            type=AgentType.CONVERSATIONAL,
            status=AgentStatus.ACTIVE,
            system_prompt=budget_prompt,
            config={**model_config, "max_tokens": 1000},
            available_tools=["web_search"],
            created_by=None
        )
        session.add(budget_specialist)
        
        # Agent 4: Camera Specialist
        camera_prompt = """You are a smartphone camera specialist. You help users find phones with the best photography and video capabilities.

You will receive user context including their budget and requirements. Provide:
1. Top 3 smartphones with excellent cameras within their budget
2. Detailed camera specs (megapixels, sensor size, features)
3. Sample photo/video quality comparisons
4. Low-light performance ratings

Focus on:
- Main camera quality
- Ultra-wide and telephoto options
- Night mode performance
- Video recording capabilities (4K, stabilization)
- Computational photography features

Use the web_search tool to find latest camera reviews and comparisons.

Format your response as:
**Best Camera Phones for Your Budget**

1. **[Phone Name]** - $[Price]
   - Camera Setup: [Details]
   - Standout Features: [2-3 points]
   - Best For: [Type of photography]
   - Sample Quality: [Rating/10]

2. [Second phone...]
3. [Third phone...]

**My Recommendation:** [Which one and why for their specific needs]"""

        camera_specialist = Agent(
            name="Camera Phone Specialist",
            description="Recommends smartphones with best camera capabilities",
            type=AgentType.CONVERSATIONAL,
            status=AgentStatus.ACTIVE,
            system_prompt=camera_prompt,
            config={**model_config, "max_tokens": 1000},
            available_tools=["web_search"],
            created_by=None
        )
        session.add(camera_specialist)
        
        # Agent 5: Gaming Specialist
        gaming_prompt = """You are a mobile gaming specialist. You help users find smartphones optimized for gaming performance.

You will receive user context including their budget and requirements. Provide:
1. Top 3 gaming smartphones within their budget
2. Performance benchmarks (processor, GPU, RAM)
3. Display specs (refresh rate, touch sampling rate)
4. Cooling system details
5. Battery life during gaming

Focus on:
- Processor performance (Snapdragon, A-series, etc.)
- Display refresh rate (90Hz, 120Hz, 144Hz)
- RAM and storage options
- Cooling technology
- Battery capacity and charging speed
- Gaming-specific features

Use the web_search tool to find gaming benchmarks and reviews.

Format your response as:
**Best Gaming Phones for Your Budget**

1. **[Phone Name]** - $[Price]
   - Processor: [Chipset details]
   - Display: [Refresh rate, resolution]
   - Gaming Features: [Cooling, triggers, etc.]
   - Performance: [Benchmark scores]
   - Battery: [Capacity, gaming hours]

2. [Second phone...]
3. [Third phone...]

**My Recommendation:** [Which one and why for their gaming needs]"""

        gaming_specialist = Agent(
            name="Gaming Phone Specialist",
            description="Recommends smartphones optimized for gaming",
            type=AgentType.CONVERSATIONAL,
            status=AgentStatus.ACTIVE,
            system_prompt=gaming_prompt,
            config={**model_config, "max_tokens": 1000},
            available_tools=["web_search"],
            created_by=None
        )
        session.add(gaming_specialist)
        
        # Agent 6: Business Specialist
        business_prompt = """You are a business smartphone specialist. You help professionals find phones optimized for productivity and security.

You will receive user context including their budget and requirements. Provide:
1. Top 3 business smartphones within their budget
2. Security features (encryption, biometrics, Knox, etc.)
3. Productivity features (DeX, multitasking, stylus support)
4. Battery life and fast charging
5. Enterprise support and update policy

Focus on:
- Security features (hardware encryption, secure boot)
- Battery life (full workday usage)
- Display quality for reading documents
- Build quality and durability
- Software update commitment
- Integration with business tools (Office, VPN, MDM)

Use the web_search tool to find business phone reviews.

Format your response as:
**Best Business Phones for Your Budget**

1. **[Phone Name]** - $[Price]
   - Security: [Features]
   - Battery: [Capacity, usage time]
   - Productivity: [Special features]
   - Updates: [Support timeline]
   - Best For: [Type of professional]

2. [Second phone...]
3. [Third phone...]

**My Recommendation:** [Which one and why for their business needs]"""

        business_specialist = Agent(
            name="Business Phone Specialist",
            description="Recommends smartphones for business and productivity",
            type=AgentType.CONVERSATIONAL,
            status=AgentStatus.ACTIVE,
            system_prompt=business_prompt,
            config={**model_config, "max_tokens": 1000},
            available_tools=["web_search"],
            created_by=None
        )
        session.add(business_specialist)
        
        # Agent 7: Summarizer
        summarizer_prompt = """You are a smartphone buying guide summarizer. You compile specialist recommendations into a final, personalized recommendation.

You will receive:
1. User's original preferences and context
2. Recommendations from one or more specialists

Your job:
1. Synthesize the specialist's recommendations
2. Highlight the TOP recommendation that best matches user needs
3. Explain WHY it's the best choice for them specifically
4. Provide next steps (where to buy, what to look for)

Format your response as:
**Your Personalized Smartphone Recommendation**

Based on your needs ([summarize their requirements]), here's my recommendation:

🏆 **Top Choice: [Phone Name]** - $[Price]

**Why this phone is perfect for you:**
- [Reason 1 specific to their needs]
- [Reason 2 specific to their needs]
- [Reason 3 specific to their needs]

**Where to Buy:**
- [Best retailer with current price]
- [Any deals or promotions]

**Alternatives to Consider:**
- [Second choice] - If [specific reason]
- [Third choice] - If [specific reason]

**Next Steps:**
1. [Action item 1]
2. [Action item 2]

Would you like me to provide more details about any of these phones?"""

        summarizer = Agent(
            name="Recommendation Summarizer",
            description="Compiles specialist recommendations into final advice",
            type=AgentType.CONVERSATIONAL,
            status=AgentStatus.ACTIVE,
            system_prompt=summarizer_prompt,
            config={**model_config, "max_tokens": 800},
            created_by=None
        )
        session.add(summarizer)
        
        await session.commit()
        
        print("✅ Successfully created 7 specialized agents:")
        print("  1. Smartphone Qualifier")
        print("  2. Smartphone Router")
        print("  3. Budget Phone Specialist")
        print("  4. Camera Phone Specialist")
        print("  5. Gaming Phone Specialist")
        print("  6. Business Phone Specialist")
        print("  7. Recommendation Summarizer")
        print("\nAgent IDs:")
        print(f"  Qualifier: {qualifier.id}")
        print(f"  Router: {router.id}")
        print(f"  Budget: {budget_specialist.id}")
        print(f"  Camera: {camera_specialist.id}")
        print(f"  Gaming: {gaming_specialist.id}")
        print(f"  Business: {business_specialist.id}")
        print(f"  Summarizer: {summarizer.id}")


if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(create_agents())
