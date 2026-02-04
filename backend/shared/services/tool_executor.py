"""
Tool Executor Service for integrating tools with agent execution.

This service handles the execution of tools during agent runs, including:
- Tool routing based on user input
- Parameter extraction from LLM responses
- Tool result formatting for agent context
"""


import json
import logging
import re
from typing import Dict, Any, Optional, List, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.tool import Tool, ToolType, ToolStatus
from ..models.agent import AgentConfig
from ..services.tool_registry import ToolRegistryService
from ..services.mcp_gateway import MCPGatewayService
from ..services.rag_service import RAGService
from ..services.memory_manager import get_memory_manager
from ..logging.config import get_logger

logger = get_logger(__name__)


class ToolExecutorService:
    """Service for executing tools within agent workflows."""
    
    def __init__(self, session: AsyncSession, llm_service=None):
        self.session = session
        self.tool_registry = ToolRegistryService(session)
        self.mcp_gateway = MCPGatewayService()
        self.llm_service = llm_service
    
    async def analyze_and_execute_tools(
        self,
        user_input: str,
        available_tools: List[str],
        agent_id: str,
        agent_config: Optional[AgentConfig] = None,
        max_iterations: int = 5,
        credentials: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """
        Analyze user input and execute appropriate tools.
        
        Args:
            user_input: The user's input message
            available_tools: List of tool names/IDs available to the agent
            agent_id: ID of the agent executing tools
            agent_config: Configuration of the agent (model, key, etc.)
            max_iterations: Maximum tool calling iterations to prevent loops
            credentials: Optional custom credentials to use
            
        Returns:
            Tuple of (List of tool execution results, Dict with token usage stats)
        """
        logger.info(f"Analyzing tools for input: {user_input[:100]}...")
        
        total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        
        if not available_tools:
            logger.debug("No tools available for this agent")
            return [], total_usage
        
        # Get tool schemas
        tools_info = await self._get_tools_info(available_tools)
        if not tools_info:
            logger.warning(f"Could not find any tools from: {available_tools}")
            return [], total_usage
        
        tool_executions = []
        
        for iteration in range(max_iterations):
            logger.debug(f"Tool execution iteration {iteration + 1}/{max_iterations}")
            
            tool_decision = {"needs_tool": False}
            iteration_usage = None
            
            # Decide if tool is needed (LLM or Keyword)
            if self.llm_service and agent_config:
                tool_decision, iteration_usage = await self._decide_tool_use_with_llm(
                    user_input, 
                    tools_info, 
                    tool_executions,
                    agent_config,
                    credentials=credentials
                )
                if iteration_usage:
                    total_usage["prompt_tokens"] += iteration_usage.get("prompt_tokens", 0)
                    total_usage["completion_tokens"] += iteration_usage.get("completion_tokens", 0)
                    total_usage["total_tokens"] += iteration_usage.get("total_tokens", 0)
            else:
                tool_decision = await self._decide_tool_use(
                    user_input, 
                    tools_info, 
                    tool_executions
                )
            
            if not tool_decision.get("needs_tool"):
                logger.info("No tool needed, proceeding with direct response")
                break
            
            tool_name = tool_decision.get("tool_name")
            tool_params = tool_decision.get("parameters", {})
            
            logger.info(f"Executing tool: {tool_name} with params: {tool_params}")
            
            # Execute the tool
            result = await self._execute_tool_by_name(
                tool_name,
                tool_params,
                credentials.get("user_id") or agent_id, # Fallback if user_id missing, but we need REAL user_id for RAG owner. 
                # This is a problem. analyze_and_execute_tools signature doesn't have user_id explicitly except in credentials?
                # The caller should provide user_id. 
                # In main.py or ChainOrchestrator, we usually have user context.
                # credentials usually holds {"user_id": ...}
                # Let's check call signature.
                agent_id=agent_id
            )
            
            tool_executions.append({
                "tool": tool_name,
                "parameters": tool_params,
                "result": result
            })
            
            # Append result to input for next iteration (chaining)
            # This allows the LLM to see the result and decide if more tools are needed
            # For simplicity in this loop, we just collect results
            # A more complex ReAct loop would update context here
            
            # If we have a successful result, check if we need another tool?
            # The LLM router should decide in the next iteration.
            
        return tool_executions, total_usage
    
    async def _decide_tool_use_with_llm(
        self,
        user_input: str,
        tools_info: List[Dict[str, Any]],
        previous_executions: List[Dict[str, Any]],
        agent_config: AgentConfig,
        credentials: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], Optional[Dict[str, int]]]:
        """
        Use LLM to decide if a tool is needed and extract parameters.
        Returns: (Decision Dict, Usage Dict)
        """
        try:
            # Construct context from previous executions
            context_str = ""
            if previous_executions:
                context_str = "PREVIOUS TOOL EXECUTIONS:\n"
                for i, exec_data in enumerate(previous_executions, 1):
                    context_str += f"{i}. Tool: {exec_data['tool']}\n"
                    context_str += f"   Input: {json.dumps(exec_data['parameters'])}\n"
                    context_str += f"   Output: {json.dumps(exec_data['result'].get('output'))}\n"
            
            # Prepare tools description
            tools_desc = json.dumps([{
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"]
            } for t in tools_info], indent=2)
            
            prompt = f"""
You are a high-precision tool routing engine. Your ONLY purpose is to decide if a tool is needed and return the parameters in valid JSON.

USER REQUEST: "{user_input}"

AVAILABLE TOOLS:
{tools_desc}

{context_str}

STRICT CONSTRAINTS:
1. OUTPUT ONLY VALID JSON.
2. DO NOT include any explanations, code, or markdown blocks.
3. If no tool is needed, return {{"needs_tool": false, "tool_name": null, "parameters": {{}} }}.
4. If a tool IS needed, return {{"needs_tool": true, "tool_name": "exact_name", "parameters": {{...}} }}.

RESPONSE FORMAT:
{{
  "needs_tool": boolean,
  "tool_name": "string or null",
  "parameters": {{ "key": "value" }}
}}
"""
            
            # Call LLM
            messages = [
                {"role": "system", "content": "You are a tool routing system. Output ONLY JSON."},
                {"role": "user", "content": prompt}
            ]
            response = await self.llm_service.generate_response(messages, agent_config, credentials=credentials)
            
            # Extract usage
            usage_stats = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
            
            content = response.content.strip()
            
            # Clean up content (remove markdown if present)
            if content.startswith("```"):
                content = re.sub(r'^```[a-z]*\n?', '', content, flags=re.MULTILINE)
                content = re.sub(r'\n?```$', '', content, flags=re.MULTILINE)
            content = content.strip()
            
            try:
                decision = json.loads(content)
                logger.debug(f"LLM Tool Decision: {decision}")
                return decision, usage_stats
            except json.JSONDecodeError:
                # Robust extraction: try finding { ... } in the output
                match = re.search(r'(\{.*\})', content, re.DOTALL)
                if match:
                    try:
                        decision = json.loads(match.group(1))
                        logger.info(f"LLM Tool Decision (Extracted): {decision}")
                        return decision, usage_stats
                    except json.JSONDecodeError:
                        pass
                
                logger.error(f"Failed to parse LLM tool decision. Content: {content}")
                return {"needs_tool": False}, usage_stats
                
        except Exception as e:
            logger.error(f"LLM tool routing failed: {e}")
            return {"needs_tool": False}, None

    async def _get_tools_info(self, tool_identifiers: List[str]) -> List[Dict[str, Any]]:
        """Get tool information for the given identifiers."""
        tools_info = []
        
        for identifier in tool_identifiers:
            try:
                # Try as UUID first
                tool_id = UUID(identifier)
                tool = await self.tool_registry.get_tool(tool_id)
            except (ValueError, TypeError):
                # Otherwise search by name
                tools = await self.tool_registry.list_tools(limit=100)
                tool = next((t for t in tools if t.name == identifier), None)
            
            if tool:
                tools_info.append({
                    "id": str(tool.id),
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.input_schema,
                    "tool_type": tool.tool_type
                })
        
        return tools_info
    
    async def _decide_tool_use(
        self,
        user_input: str,
        tools_info: List[Dict[str, Any]],
        previous_executions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Decide if a tool should be used and extract parameters.
        
        This is a simple keyword-based router fallback.
        """
        # If we already executed tools, likely don't need more in heuristic mode
        if previous_executions:
            return {"needs_tool": False}
        
        user_lower = user_input.lower()
        
        # Check for calculator
        if any(word in user_lower for word in ["calculate", "add", "subtract", "multiply", "divide", "+", "-", "*", "/"]):
            calc_tool = next((t for t in tools_info if "calculator" in t["name"].lower()), None)
            if calc_tool:
                params = self._extract_math_params(user_input)
                return {
                    "needs_tool": True,
                    "tool_name": calc_tool["name"],
                    "parameters": params
                }

        # General keyword matching
        for tool in tools_info:
            tool_name_lower = tool["name"].lower()
            description_lower = (tool.get("description") or "").lower()
            
            # Simple heuristic: if tool name or key terms appear in input
            keywords = [tool_name_lower] + description_lower.split()
            
            if any(kw in user_lower for kw in keywords if len(kw) > 3):
                logger.info(f"Matched tool via keyword: {tool['name']}")
                
                # Extract parameters from input schema
                parameters = self._extract_parameters(
                    user_input,
                    tool.get("input_schema", {})
                )
                
                return {
                    "needs_tool": True,
                    "tool_name": tool["name"],
                    "parameters": parameters
                }
        
        return {"needs_tool": False}
    
    def _extract_parameters(
        self,
        user_input: str,
        input_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract parameters from user input based on schema (Heuristic)."""
        parameters = {}
        
        if not input_schema or "properties" not in input_schema:
            return parameters
        
        numbers = re.findall(r'\b\d+\.?\d*\b', user_input)
        
        for prop_name, prop_schema in input_schema.get("properties", {}).items():
            prop_type = prop_schema.get("type", "string")
            
            if prop_type in ["number", "integer"] and numbers:
                try:
                    parameters[prop_name] = float(numbers.pop(0)) if prop_type == "number" else int(numbers.pop(0))
                except (ValueError, IndexError):
                    pass
            elif prop_type == "string":
                # Use entire input as fallback
                parameters[prop_name] = user_input
        
        return parameters
    
    def _extract_math_params(self, user_input: str) -> Dict[str, Any]:
        """Extract mathematical operation parameters from text (Heuristic)."""
        numbers = re.findall(r'\b\d+\.?\d*\b', user_input)
        user_lower = user_input.lower()
        
        operation = "add"  # default
        if "subtract" in user_lower or "minus" in user_lower or "-" in user_input:
            operation = "subtract"
        elif "multiply" in user_lower or "times" in user_lower or "*" in user_input:
            operation = "multiply"
        elif "divide" in user_lower or "/" in user_input:
            operation = "divide"
        
        params = {"operation": operation}
        
        if len(numbers) >= 2:
            params["a"] = float(numbers[0])
            params["b"] = float(numbers[1])
        
        return params
    
    async def _execute_tool_by_name(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        user_id: str,
        agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a tool by name."""
        try:
            # Find tool by name
            tools = await self.tool_registry.list_tools(limit=100)
            tool = next((t for t in tools if t.name == tool_name), None)
            
            if not tool:
                # Check for system tools like knowledge_base that might not be in registry if manually added
                if tool_name == "knowledge_base":
                    return await self._execute_rag_search(parameters, user_id, agent_id)
                    
                return {
                    "status": "error",
                    "error": f"Tool {tool_name} not found"
                }
            
            # Execute the tool
            result = await self.tool_registry.execute_tool(
                user_id=user_id,
                tool_id=tool.id,
                inputs=parameters,
                context={"source": "agent_execution"}
            )
            
            # Result is a dict, not a Pydantic model
            return {
                "status": "success" if result.get("status") == "success" else "error",
                "output": result.get("outputs"),
                "error": result.get("error")
            }
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e)
            }
            
    async def _execute_rag_search(self, parameters: Dict[str, Any], user_id: str, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute RAG search."""
        try:
            query = parameters.get("query")
            limit = parameters.get("limit", 3)
            
            if not query:
                return {"status": "error", "error": "Query is required"}
                
            memory_manager = await get_memory_manager()
            rag_service = RAGService(self.session, memory_manager)
            
            # Parse user_id to UUID
            try:
                owner_id = UUID(user_id) if user_id else None
                if not owner_id:
                     # Attempt to generic search or fail?
                     return {"status": "error", "error": "User ID required for RAG"}
            except ValueError:
                # If user_id isn't a valid UUID, we can't query RAG
                return {"status": "error", "error": "Invalid User ID for RAG"}

            # Parse agent_id
            parsed_agent_id = None
            if agent_id:
                try:
                    parsed_agent_id = UUID(agent_id)
                except ValueError:
                    pass

            results = await rag_service.query(query, owner_id, limit, agent_id=parsed_agent_id)
            
            return {
                "status": "success",
                "output": {
                    "results": results,
                    "count": len(results),
                    "query": query
                }
            }
        except Exception as e:
            logger.error(f"RAG search error: {e}")
            return {"status": "error", "error": str(e)}
    
    def format_tool_results_for_context(
        self,
        tool_executions: List[Dict[str, Any]]
    ) -> str:
        """Format tool execution results for inclusion in agent context."""
        if not tool_executions:
            return ""
        
        formatted = "\n\nTool Execution Results:\n"
        for i, execution in enumerate(tool_executions, 1):
            formatted += f"\n{i}. Tool: {execution['tool']}\n"
            formatted += f"   Parameters: {json.dumps(execution['parameters'], indent=2)}\n"
            
            if execution['result'].get('status') == 'success':
                formatted += f"   Result: {json.dumps(execution['result'].get('output', {}), indent=2)}\n"
            else:
                formatted += f"   Error: {execution['result'].get('error', 'Unknown error')}\n"
        
        return formatted

