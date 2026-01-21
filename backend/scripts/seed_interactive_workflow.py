"""
Seed script for creating the Interactive Smartphone Buying Guide workflow.

This workflow connects the 7 specialized agents with conditional routing:
1. Qualifier asks questions
2. Router determines which specialist to consult
3. Specialist provides recommendations
4. Summarizer compiles final advice
"""

import asyncio
import sys
import os
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.database.connection import get_database_session
from shared.models.chain import Chain, ChainNode, ChainEdge, ChainNodeType, ChainStatus
from shared.models.agent import Agent
from sqlalchemy import select


async def create_workflow():
    """Create the interactive smartphone buying guide workflow."""
    
    async with get_database_session() as session:
        # Get all the agents we created
        result = await session.execute(
            select(Agent).where(Agent.name.in_([
                "Smartphone Qualifier",
                "Smartphone Router",
                "Budget Phone Specialist",
                "Camera Phone Specialist",
                "Gaming Phone Specialist",
                "Business Phone Specialist",
                "Recommendation Summarizer"
            ]))
        )
        agents = {agent.name: agent for agent in result.scalars().all()}
        
        if len(agents) != 7:
            print(f"Error: Expected 7 agents, found {len(agents)}")
            print(f"Found agents: {list(agents.keys())}")
            return
        
        # Create the chain
        chain = Chain(
            name="Interactive Smartphone Buying Guide",
            description="An interactive, conversational smartphone buying guide that asks questions and routes to specialized agents",
            status=ChainStatus.ACTIVE,
            category="Shopping Assistant",
            tags=["smartphone", "shopping", "interactive", "conversational"],
            input_schema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "User's message or question"
                    }
                }
            },
            created_by=None
        )
        session.add(chain)
        await session.flush()
        
        # Node positions for visual layout
        positions = {
            "start": (100, 300),
            "qualifier": (300, 300),
            "router": (500, 300),
            "budget": (700, 100),
            "camera": (700, 200),
            "gaming": (700, 400),
            "business": (700, 500),
            "summarizer": (900, 300),
            "end": (1100, 300)
        }
        
        # Create nodes
        nodes = {}
        
        # Start node
        start_node = ChainNode(
            chain_id=chain.id,
            node_id="start",
            node_type=ChainNodeType.START,
            label="Start",
            position_x=positions["start"][0],
            position_y=positions["start"][1],
            order_index=0,
            created_by=None
        )
        session.add(start_node)
        nodes["start"] = start_node
        
        # Qualifier Agent node
        qualifier_node = ChainNode(
            chain_id=chain.id,
            node_id="qualifier",
            node_type=ChainNodeType.AGENT,
            agent_id=agents["Smartphone Qualifier"].id,
            label="Ask Questions",
            position_x=positions["qualifier"][0],
            position_y=positions["qualifier"][1],
            order_index=1,
            config={
                "description": "Asks clarifying questions to understand user needs"
            },
            created_by=None
        )
        session.add(qualifier_node)
        nodes["qualifier"] = qualifier_node
        
        # Router Agent node
        router_node = ChainNode(
            chain_id=chain.id,
            node_id="router",
            node_type=ChainNodeType.AGENT,
            agent_id=agents["Smartphone Router"].id,
            label="Route to Specialist",
            position_x=positions["router"][0],
            position_y=positions["router"][1],
            order_index=2,
            config={
                "description": "Determines which specialist to consult"
            },
            created_by=None
        )
        session.add(router_node)
        nodes["router"] = router_node
        
        # Specialist nodes
        budget_node = ChainNode(
            chain_id=chain.id,
            node_id="budget_specialist",
            node_type=ChainNodeType.AGENT,
            agent_id=agents["Budget Phone Specialist"].id,
            label="Budget Specialist",
            position_x=positions["budget"][0],
            position_y=positions["budget"][1],
            order_index=3,
            created_by=None
        )
        session.add(budget_node)
        nodes["budget"] = budget_node
        
        camera_node = ChainNode(
            chain_id=chain.id,
            node_id="camera_specialist",
            node_type=ChainNodeType.AGENT,
            agent_id=agents["Camera Phone Specialist"].id,
            label="Camera Specialist",
            position_x=positions["camera"][0],
            position_y=positions["camera"][1],
            order_index=3,
            created_by=None
        )
        session.add(camera_node)
        nodes["camera"] = camera_node
        
        gaming_node = ChainNode(
            chain_id=chain.id,
            node_id="gaming_specialist",
            node_type=ChainNodeType.AGENT,
            agent_id=agents["Gaming Phone Specialist"].id,
            label="Gaming Specialist",
            position_x=positions["gaming"][0],
            position_y=positions["gaming"][1],
            order_index=3,
            created_by=None
        )
        session.add(gaming_node)
        nodes["gaming"] = gaming_node
        
        business_node = ChainNode(
            chain_id=chain.id,
            node_id="business_specialist",
            node_type=ChainNodeType.AGENT,
            agent_id=agents["Business Phone Specialist"].id,
            label="Business Specialist",
            position_x=positions["business"][0],
            position_y=positions["business"][1],
            order_index=3,
            created_by=None
        )
        session.add(business_node)
        nodes["business"] = business_node
        
        # Summarizer node
        summarizer_node = ChainNode(
            chain_id=chain.id,
            node_id="summarizer",
            node_type=ChainNodeType.AGENT,
            agent_id=agents["Recommendation Summarizer"].id,
            label="Compile Recommendation",
            position_x=positions["summarizer"][0],
            position_y=positions["summarizer"][1],
            order_index=4,
            created_by=None
        )
        session.add(summarizer_node)
        nodes["summarizer"] = summarizer_node
        
        # End node
        end_node = ChainNode(
            chain_id=chain.id,
            node_id="end",
            node_type=ChainNodeType.END,
            label="End",
            position_x=positions["end"][0],
            position_y=positions["end"][1],
            order_index=5,
            created_by=None
        )
        session.add(end_node)
        nodes["end"] = end_node
        
        await session.flush()
        
        # Create edges with conditional routing
        edges = []
        
        # Start -> Qualifier
        edges.append(ChainEdge(
            chain_id=chain.id,
            edge_id="start_to_qualifier",
            source_node_id="start",
            target_node_id="qualifier",
            label="Begin",
            created_by=None
        ))
        
        # Qualifier -> Router
        edges.append(ChainEdge(
            chain_id=chain.id,
            edge_id="qualifier_to_router",
            source_node_id="qualifier",
            target_node_id="router",
            label="User Preferences Gathered",
            condition={
                "type": "json_contains",
                "field": "ready_for_routing",
                "value": True
            },
            created_by=None
        ))
        
        # Router -> Budget Specialist (conditional)
        edges.append(ChainEdge(
            chain_id=chain.id,
            edge_id="router_to_budget",
            source_node_id="router",
            target_node_id="budget_specialist",
            label="Budget Priority",
            condition={
                "type": "json_contains",
                "field": "route_to",
                "value": "budget_specialist"
            },
            created_by=None
        ))
        
        # Router -> Camera Specialist (conditional)
        edges.append(ChainEdge(
            chain_id=chain.id,
            edge_id="router_to_camera",
            source_node_id="router",
            target_node_id="camera_specialist",
            label="Camera Priority",
            condition={
                "type": "json_contains",
                "field": "route_to",
                "value": "camera_specialist"
            },
            created_by=None
        ))
        
        # Router -> Gaming Specialist (conditional)
        edges.append(ChainEdge(
            chain_id=chain.id,
            edge_id="router_to_gaming",
            source_node_id="router",
            target_node_id="gaming_specialist",
            label="Gaming Priority",
            condition={
                "type": "json_contains",
                "field": "route_to",
                "value": "gaming_specialist"
            },
            created_by=None
        ))
        
        # Router -> Business Specialist (conditional)
        edges.append(ChainEdge(
            chain_id=chain.id,
            edge_id="router_to_business",
            source_node_id="router",
            target_node_id="business_specialist",
            label="Business Priority",
            condition={
                "type": "json_contains",
                "field": "route_to",
                "value": "business_specialist"
            },
            created_by=None
        ))
        
        # All specialists -> Summarizer
        for specialist in ["budget_specialist", "camera_specialist", "gaming_specialist", "business_specialist"]:
            edges.append(ChainEdge(
                chain_id=chain.id,
                edge_id=f"{specialist}_to_summarizer",
                source_node_id=specialist,
                target_node_id="summarizer",
                label="Recommendations",
                created_by=None
            ))
        
        # Summarizer -> End
        edges.append(ChainEdge(
            chain_id=chain.id,
            edge_id="summarizer_to_end",
            source_node_id="summarizer",
            target_node_id="end",
            label="Final Advice",
            created_by=None
        ))
        
        for edge in edges:
            session.add(edge)
        
        await session.commit()
        
        print("✅ Successfully created Interactive Smartphone Buying Guide workflow!")
        print(f"   Chain ID: {chain.id}")
        print(f"   Nodes: {len(nodes)}")
        print(f"   Edges: {len(edges)}")
        print("\nWorkflow Flow:")
        print("  1. Start → Qualifier (asks questions)")
        print("  2. Qualifier → Router (analyzes preferences)")
        print("  3. Router → [Budget|Camera|Gaming|Business] Specialist (conditional)")
        print("  4. Specialist → Summarizer (compiles recommendations)")
        print("  5. Summarizer → End (final advice)")
        print("\nYou can now test this workflow in the Chat interface!")


if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(create_workflow())
