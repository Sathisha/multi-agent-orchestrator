
import asyncio
from typing import List, Optional, Any, Dict
from pyzeebe import ZeebeClient, ZeebeWorker, create_insecure_channel, Job
from shared.config.settings import get_settings
from shared.logging.structured_logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

class ZeebeService:
    def __init__(self):
        self.channel = create_insecure_channel(hostname=settings.zeebe_gateway_host, port=settings.zeebe_gateway_port)
        self.client = ZeebeClient(self.channel)
        self.worker = ZeebeWorker(self.channel)
        logger.info(f"ZeebeService initialized with gateway: {settings.zeebe_gateway_host}:{settings.zeebe_gateway_port}")

    async def deploy_workflow(self, bpmn_file_path: str) -> str:
        """
        Deploy a BPMN workflow file to Zeebe.
        """
        try:
            logger.info(f"Deploying workflow from file: {bpmn_file_path}")
            # ZeebeClient.deploy_process returns a tuple, usually (deployment_key, processes) 
            # or a DeployProcessResponse object depending on version.
            # Assuming pyzeebe returns response object.
            
            # Note: pyzeebe's deploy_process is synchronous in some versions or async in others. 
            # `pyzeebe` 4.7.0 client methods are usually async.
            response = await self.client.deploy_process(bpmn_file_path)
            logger.info(f"Top-level deployment successful. Response: {response}")
            return str(response)
        except Exception as e:
            logger.error(f"Failed to deploy workflow: {str(e)}")
            raise

    async def run_workflow(self, bpmn_process_id: str, variables: Dict[str, Any] = {}) -> int:
        """
        Start a new workflow instance.
        """
        try:
            logger.info(f"Starting workflow instance: {bpmn_process_id} with variables: {variables}")
            # This returns a unique instance key
            instance_key = await self.client.run_process(bpmn_process_id, variables)
            logger.info(f"Started workflow instance key: {instance_key}")
            return instance_key
        except Exception as e:
            logger.error(f"Failed to start workflow instance: {str(e)}")
            raise

    async def publish_message(self, message_name: str, correlation_key: str, variables: Dict[str, Any] = {}) -> None:
        """
        Publish a message to Zeebe.
        """
        try:
            logger.info(f"Publishing message: {message_name}, correlation_key: {correlation_key}")
            await self.client.publish_message(message_name, correlation_key, variables)
        except Exception as e:
            logger.error(f"Failed to publish message: {str(e)}")
            raise

    def create_worker(self, task_type: str, task_handler):
        """
        Register a worker for a specific task type.
        """
        logger.info(f"Registering worker for task type: {task_type}")
        self.worker.task(task_type)(task_handler)

    async def start_worker(self):
        """
        Start the worker poll loop.
        """
        logger.info("Starting Zeebe worker...")
        # work() returns a coroutine that runs forever
        await self.worker.work()

# Global instance to be used by the app
zeebe_service = ZeebeService()
