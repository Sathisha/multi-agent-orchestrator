
import asyncio
from typing import Dict, Any
from pyzeebe import Job
from shared.logging.structured_logging import get_logger
from shared.core.workflow import zeebe_service

logger = get_logger(__name__)

async def run_agent_task(job: Job) -> Dict[str, Any]:
    """
    Worker for 'agent-task'.
    Expects 'agent_id' and 'input_text' in job variables.
    Returns 'output_text' in result variables.
    """
    try:
        agent_id = job.variables.get("agent_id")
        input_data = job.variables.get("input_data") or {"input": job.variables.get("input_text", "")}
        
        logger.info(f"Worker received agent-task for agent: {agent_id}")
        
        from shared.database.connection import AsyncSessionLocal
        from shared.services.agent_executor import lifecycle_manager, AgentExecutorService, ExecutionStatus

        execution_id = None
        async with AsyncSessionLocal() as session:
            executor = lifecycle_manager.get_executor(session)
            execution_id = await executor.start_agent_execution(
                agent_id=agent_id,
                input_data=input_data,
                created_by="system-workflow"
            )
            logger.info(f"Started agent execution {execution_id} for workflow job {job.key}")

        # Poll for completion
        # We need a new session for polling as the previous one is closed
        timeout_seconds = 300
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout_seconds:
            await asyncio.sleep(2)
            async with AsyncSessionLocal() as session:
                executor = lifecycle_manager.get_executor(session)
                status = await executor.get_execution_status(execution_id)
                
                if status and status["status"] in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED, ExecutionStatus.TIMEOUT]:
                    if status["status"] == ExecutionStatus.COMPLETED:
                         output = status.get("output_data", {})
                         # Flatten output for compatibility if needed, or just return as dict
                         return {"output_data": output, "output_text": output.get("content", "")}
                    else:
                        raise Exception(f"Agent execution failed with status {status['status']}: {status.get('error_message')}")
        
        raise Exception("Agent execution timed out")

    except Exception as e:
        logger.error(f"Worker failed for agent-task: {str(e)}")
        raise e

def register_workers():
    """
    Register all workers with the Zeebe service.
    """
    zeebe_service.create_worker("agent-task", run_agent_task)
    logger.info("Registered 'agent-task' worker")
