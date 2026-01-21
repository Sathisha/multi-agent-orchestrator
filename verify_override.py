
import asyncio
import uuid
import logging
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from shared.database.connection import get_database_session, init_db
from shared.services.chain_orchestrator import ChainOrchestratorService
from shared.models.agent import Agent, AgentType, AgentStatus
from shared.models.chain import Chain, ChainNode, ChainNodeType
from shared.services.agent import AgentService

# Configure logging to stdout
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    logger.info("Starting Model Override Verification")
    
    # Initialize DB (assumes running in environment with working DB connection)
    # await init_db() 
    
    async with get_database_session() as session:
        # 1. Create Test Agent
        agent_service = AgentService(session)
        agent = await agent_service.create_agent(
            name="Override Test Agent",
            config={"model_name": "DEFAULT_MODEL", "llm_provider": "ollama"},
            agent_type=AgentType.CONVERSATIONAL,
            created_by="test_script"
        )
        logger.info(f"Created Agent: {agent.id} with default model: DEFAULT_MODEL")
        
        # 2. Create Chain
        chain = Chain(
            name="Override Test Chain",
            status="active",
            created_by="test_script"
        )
        session.add(chain)
        await session.flush()
        
        node = ChainNode(
            chain_id=chain.id,
            node_id="agent_step",
            node_type=ChainNodeType.AGENT,
            agent_id=agent.id,
            label="Agent Step",
            order_index=0
        )
        session.add(node)
        await session.commit()
        logger.info(f"Created Chain: {chain.id}")
        
        # 3. Execute with Override
        orchestrator = ChainOrchestratorService()
        override_model = "OVERRIDE_TARGET_MODEL"
        
        logger.info(f"Executing chain with model_override={{'model_name': '{override_model}'}}")
        
        try:
            # We use synchronous execute_chain which waits for background logic if we passed it correctly? 
            # execution = await orchestrator.execute_chain(...) runs logic inline in current impl of 'execute_chain' (legacy)
            # wait, my update to execute_chain passes it to create_execution then runs _run_execution_logic.
            
            execution = await orchestrator.execute_chain(
                session=session,
                chain_id=chain.id,
                input_data={"input": "Hello"},
                model_override={"model_name": override_model}
            )
            
            logger.info(f"Execution finished with status: {execution.status}")
            
            # 4. Verify Variables
            if execution.variables and '_model_override' in execution.variables:
                stored_override = execution.variables['_model_override']
                logger.info(f"VERIFICATION 1: Found _model_override in execution variables: {stored_override}")
                if stored_override.get('model_name') == override_model:
                    logger.info("PASS: Variable storage matches.")
                else:
                    logger.error("FAIL: Variable storage mismatch.")
            else:
                logger.error("FAIL: _model_override not found in execution variables.")
                
            # 5. Verify Logs (Indirectly via output if we could, but agent might fail if model invalid)
            # If the agent failed because "OVERRIDE_TARGET_MODEL" doesn't exist, that actually proves it TRIED to use it!
            # The AgentExecutor logs: "Looking for model with provider='...' and name='...'"
            # failing that, let's check logs if possible.
            
        except Exception as e:
            logger.error(f"Execution failed with error: {e}")
            # Even if it failed provided it failed for the right reason (model not found) it is a pass.

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
