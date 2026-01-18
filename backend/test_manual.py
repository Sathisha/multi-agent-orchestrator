import sys
import asyncio
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Ensure we can import
sys.path.append('/app')

from shared.models.chain import Chain, ChainNode, ChainEdge, ChainNodeType, ChainStatus, ChainExecutionStatus
from shared.models.agent import Agent, AgentType, AgentStatus
from shared.services.chain_orchestrator import ChainOrchestratorService
from shared.database.connection import get_db

async def run_manual_test():
    print("Starting Manual Test...")
    
    # Setup DB connection
    # Assuming environment variables set or defaults work
    # We can use the get_db dependency or create session manually
    # Use DATABASE_ASYNC_URL from env or hardcoded default for docker
    import os
    db_url = os.getenv("DATABASE_ASYNC_URL", "postgresql+asyncpg://postgres:postgres@postgres:5432/ai_agent_framework")
    engine = create_async_engine(db_url, echo=False)
    AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        try:
            # Create Agent
            print("Creating Agent...")
            agent = Agent(
                name=f"Manual Agent {uuid4()}",
                description="Manual Test Agent",
                type=AgentType.CHATBOT,
                status=AgentStatus.ACTIVE,
                config={
                    "name": "Echo Agent",
                    "model": "mock-model-v1",
                    "llm_provider": "mock",
                    "temperature": 0.0
                }
            )
            session.add(agent)
            await session.commit()
            await session.refresh(agent)
            print(f"Agent Created: {agent.id}")
            
            # Create Chain
            print("Creating Chain...")
            chain = Chain(name="Manual Data Passing Chain", status=ChainStatus.ACTIVE)
            session.add(chain)
            await session.flush()
            
            # Nodes
            node1 = ChainNode(
                chain_id=chain.id,
                node_id="node1",
                node_type=ChainNodeType.AGENT,
                agent_id=str(agent.id),
                label="Node 1",
                config={"input_map": {}}
            )
            
            node2 = ChainNode(
                chain_id=chain.id,
                node_id="node2",
                node_type=ChainNodeType.AGENT,
                agent_id=str(agent.id),
                label="Node 2",
                config={"input_map": {"message": "{{node1.content}}"}}
            )
            session.add(node1)
            session.add(node2)
            
            # Edge
            edge = ChainEdge(
                chain_id=chain.id,
                edge_id="e1",
                source_node_id="node1",
                target_node_id="node2"
            )
            session.add(edge)
            await session.commit()
            
            # Execute
            print("Executing Chain...")
            orchestrator = ChainOrchestratorService()
            execution = await orchestrator.execute_chain(
                session,
                chain.id,
                input_data={"message": "Hello World"}
            )
            
            print(f"Execution Status: {execution.status}")
            print(f"Node Results: {execution.node_results}")
            
            if execution.status == ChainExecutionStatus.COMPLETED:
                print("SUCCESS: Chain Completed")
                # Verify passed data
                res = execution.node_results
                node1_out = res["node1"]["output"]
                node2_in = res["node2"]["input"]
                print(f"Node 1 Output: {node1_out}")
                print(f"Node 2 Input: {node2_in}")
                
                # Check mapping
                val1 = node1_out.get('content') if isinstance(node1_out, dict) else str(node1_out)
                val2 = node2_in.get('message')
                if val1 == val2:
                     print("VERIFICATION: SUCCESS - Data passed correctly")
                else:
                     print(f"VERIFICATION: FAILURE - Mismatch {val1} != {val2}")

            else:
                print("FAILURE: Chain did not complete")
                
        except Exception as e:
            print(f"EXCEPTION: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_manual_test())
