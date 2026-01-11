@router.post("/refine-prompt", response_model=PromptRefinementResponse)
async def refine_agent_prompt(
    request: PromptRefinementRequest,
    session: AsyncSession = Depends(get_async_db)
):
    """Refine an agent's system prompt using AI."""
    from ..services.llm_service import LLMService
    from ..services.llm_model import LLMModelService
    from ..models.agent import AgentConfig, LLMProvider
    
    try:
        # Get LLM model if specified
        llm_service = LLMService()
        model_config = None
        
        if request.llm_model_id:
            model_service = LLMModelService(session)
            llm_model = await model_service.get_llm_model(str(request.llm_model_id))
            
            if llm_model:
                # Create agent config for this model
                model_config = AgentConfig(
                    name="prompt_refiner",
                    model=llm_model.name,
                    temperature=0.3,  # Lower temperature for more focused refinement
                    max_tokens=1500,
                    llm_provider=llm_model.provider
                )
                
                # Set up credentials if available
                credentials = {}
                if llm_model.api_key:
                    credentials["api_key"] = llm_model.api_key
                if llm_model.api_base:
                    credentials["base_url"] = llm_model.api_base
        
        # Fallback to default config if no model specified
        if not model_config:
            model_config = AgentConfig(
                name="prompt_refiner",
                model="tinyllama",
                temperature=0.3,
                max_tokens=1500,
                llm_provider=LLMProvider.OLLAMA
            )
            credentials = {}
        
        # Create refinement prompt
        refinement_system_prompt = """You are an expert in crafting effective system prompts for AI agents. 
Your task is to refine and improve system prompts to make them:
- More specific and clear
- Better structured
- Include relevant constraints and guidelines
- Use best practices in prompt engineering

Provide your response in this exact JSON format:
{
  "refined_prompt": "the improved prompt here",
  "improvements": ["improvement 1", "improvement 2", ...],
  "confidence": 0.0-1.0 (your confidence in the improvement)
}"""
        
        user_prompt = f"""Original prompt: "{request.original_prompt}"
Agent type: {request.agent_type or 'general'}

Please refine this prompt following best practices. Output ONLY valid JSON."""
        
        messages = [
            {"role": "system", "content": refinement_system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Call LLM
        response = await llm_service.generate_response(messages, model_config, credentials=credentials if credentials else None)
        
        # Parse response
        import json
        import re
        
        content = response.content.strip()
        
        # Clean up markdown code blocks if present
        if content.startswith("```"):
            content = re.sub(r'^```[a-z]*\n?', '', content, flags=re.MULTILINE)
            content = re.sub(r'\n?```$', '', content, flags=re.MULTILINE)
        content = content.strip()
        
        # Try to parse JSON
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            # Try to find JSON in the response
            match = re.search(r'(\{.*\})', content, re.DOTALL)
            if match:
                result = json.loads(match.group(1))
            else:
                # Fallback: return improved version with basic formatting
                improved = request.original_prompt.strip()
                if not improved.endswith('.'):
                    improved += '.'
                result = {
                    "refined_prompt": improved,
                    "improvements": ["Ensured proper punctuation"],
                    "confidence": 0.5
                }
        
        return PromptRefinementResponse(
            refined_prompt=result.get("refined_prompt", request.original_prompt),
            improvements=result.get("improvements", []),
            confidence=min(max(result.get("confidence", 0.7), 0.0), 1.0)
        )
        
    except Exception as e:
        logger.error(f"Prompt refinement failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Prompt refinement failed: {str(e)}")
