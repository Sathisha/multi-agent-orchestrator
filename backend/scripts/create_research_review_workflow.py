
import asyncio
import sys
import os
import uuid

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.database.connection import get_database_session
from shared.models.agent import Agent, AgentType, AgentStatus
from shared.models.chain import Chain, ChainNode, ChainEdge, ChainNodeType, ChainStatus
from sqlalchemy import select


async def create_research_review_workflow(admin_id: uuid.UUID):
    """Create a research and review workflow with 4 specialized agents."""
    async with get_database_session() as session:
        print("Creating Research and Review Workflow...")
        
        # Check if already exists
        result = await session.execute(
            select(Agent).where(Agent.name == "Research Agent pro")
        )
        if result.scalar_one_or_none():
            print("  ✓ Research agents already exist")
            return
        
        model_config = {
            "model_name": "llama3.2",
            "llm_provider": "ollama",
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        # 1. Research Agent
        research_agent = Agent(
            name="Research Agent pro",
            description="Performs in-depth research using RAG and writes comprehensive articles.",
            type=AgentType.TASK,
            status=AgentStatus.ACTIVE,
            system_prompt="""You are a professional research assistant. 
Your task is to conduct thorough research on the given topic. 
You have access to a RAG (Retrieval-Augmented Generation) system which will provide you with relevant context from internal documents.

Guidelines:
1. Carefully analyze the research request.
2. Synthesize the information provided in the RAG context with your general knowledge.
3. Write a comprehensive, well-structured, and long article (at least 500 words).
4. Use clear headings and bullet points where appropriate.
5. Provide a deep dive into the subject matter.

Your output should be a structured article.""",
            config={
                **model_config,
                "memory_enabled": True,
                "rag_enabled": True # RAG is handled based on user_id in executor
            },
            created_by=admin_id
        )
        session.add(research_agent)
        
        # 2. Completeness Reviewer
        completeness_reviewer = Agent(
            name="Reviewer - Completeness",
            description="Checks if the research article covers all aspects of the user's request.",
            type=AgentType.TASK,
            status=AgentStatus.ACTIVE,
            system_prompt="""You are an editorial reviewer specializing in content completeness.
You will receive the original user research request and the research article produced by the Research Agent.

Your task:
1. Compare the research article against the original user request.
2. Identify any missing aspects or topics that were requested but not covered.
3. Evaluate if the depth of coverage is sufficient for each topic.
4. Provide a summary of your assessment.
5. Give a confidence rating (1-10) for the research material based on how well it satisfies the original request.

Respond in JSON format:
{
  "summary": "Your assessment of completeness...",
  "missing_aspects": ["list", "of", "missing", "items"],
  "confidence_rating": 8
}""",
            config={**model_config, "temperature": 0.3, "max_tokens": 500},
            created_by=admin_id
        )
        session.add(completeness_reviewer)
        
        # 3. Correctness Reviewer
        correctness_reviewer = Agent(
            name="Reviewer - Correctness",
            description="Checks the factual accuracy and logical consistency of the research article.",
            type=AgentType.TASK,
            status=AgentStatus.ACTIVE,
            system_prompt="""You are a fact-checker and technical reviewer.
You will receive the original user research request and the research article produced by the Research Agent.

Your task:
1. Verify the factual accuracy of the claims made in the article.
2. Check for logical consistency and internal contradictions.
3. Identify any potentially misleading information.
4. Provide a summary of your findings.
5. Give a confidence rating (1-10) for the research material based on its accuracy and reliability.

Respond in JSON format:
{
  "summary": "Your assessment of correctness...",
  "errors_found": ["list", "of", "inaccuracies", "or", "issues"],
  "confidence_rating": 9
}""",
            config={**model_config, "temperature": 0.2, "max_tokens": 500},
            created_by=admin_id
        )
        session.add(correctness_reviewer)
        
        # 4. Aggregation Agent
        aggregator = Agent(
            name="Research Aggregator",
            description="Collects feedback and creates the final research report.",
            type=AgentType.TASK,
            status=AgentStatus.ACTIVE,
            system_prompt="""You are a Chief Editor. Your task is to compile the final research report.
You will receive:
1. The original research article from the Research Agent.
2. Feedback from the Completeness Reviewer.
3. Feedback from the Correctness Reviewer.

Your task:
1. Synthesize the article and the feedback.
2. Create a final version of the research report.
3. Include a section on "Areas for Improvement" based on reviewer feedback.
4. Summarize the overall quality and provide a final combined confidence rating.

Final Report Structure:
# FINAL RESEARCH REPORT: [Topic]

[The Research Article]

---
## Reviewer Feedback Summary
- **Completeness**: [Summary and rating]
- **Correctness**: [Summary and rating]

## Areas for Improvement
- [Points based on reviewer feedback]

## Overall Confidence Rating
[Final Rating]/10
""",
            config={**model_config, "temperature": 0.5, "max_tokens": 2500},
            created_by=admin_id
        )
        session.add(aggregator)
        
        await session.flush()
        
        # Get agent IDs
        result = await session.execute(
            select(Agent).where(Agent.name.in_([
                "Research Agent pro", "Reviewer - Completeness",
                "Reviewer - Correctness", "Research Aggregator"
            ]))
        )
        agents_dict = {agent.name: agent for agent in result.scalars().all()}
        
        # Create the Chain
        chain = Chain(
            name="Professional Research & Review Pipeline",
            description="A high-quality research workflow involving RAG-powered research, followed by parallel completeness and correctness reviews, concluding with a synthesized final report.",
            status=ChainStatus.ACTIVE,
            category="Research",
            tags=["research", "rag", "review", "parallel"],
            input_schema={
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "The topic to research"}
                },
                "required": ["topic"]
            },
            created_by=admin_id
        )
        session.add(chain)
        await session.flush()
        
        # Create nodes
        positions = {
            "start": (100, 300),
            "research": (300, 300),
            "reviewer_completeness": (550, 150),
            "reviewer_correctness": (550, 450),
            "aggregator": (800, 300),
            "end": (1000, 300)
        }
        
        node_configs = [
            ("start", ChainNodeType.START, None, "Start", 0),
            ("research", ChainNodeType.AGENT, agents_dict["Research Agent pro"].id, "Research (RAG)", 1),
            ("reviewer_completeness", ChainNodeType.AGENT, agents_dict["Reviewer - Completeness"].id, "Completeness Review", 2),
            ("reviewer_correctness", ChainNodeType.AGENT, agents_dict["Reviewer - Correctness"].id, "Correctness Review", 2),
            ("aggregator", ChainNodeType.AGENT, agents_dict["Research Aggregator"].id, "Final Aggregation", 3),
            ("end", ChainNodeType.END, None, "End", 4)
        ]
        
        for node_id, node_type, agent_id, label, order in node_configs:
            # Add input mapping for reviewers to get original input
            config = {}
            if node_id in ["reviewer_completeness", "reviewer_correctness"]:
                config = {
                    "input_map": {
                        "original_request": "{{input.topic}}",
                        "article": "{{research.content}}"
                    }
                }
            elif node_id == "aggregator":
                 # Aggregator will receive inputs list by default, but we can make it explicit
                 config = {
                     "input_map": {
                         "article": "{{research.content}}",
                         "completeness_feedback": "{{reviewer_completeness.content}}",
                         "correctness_feedback": "{{reviewer_correctness.content}}"
                     }
                 }

            node = ChainNode(
                chain_id=chain.id,
                node_id=node_id,
                node_type=node_type,
                agent_id=agent_id,
                label=label,
                position_x=positions[node_id][0],
                position_y=positions[node_id][1],
                order_index=order,
                config=config,
                created_by=admin_id
            )
            session.add(node)
        
        await session.flush()
        
        # Create edges
        edges = [
            ("start_to_research", "start", "research", "Start Research", None),
            ("research_to_completeness", "research", "reviewer_completeness", "Review Completeness", None),
            ("research_to_correctness", "research", "reviewer_correctness", "Review Correctness", None),
            ("completeness_to_aggregator", "reviewer_completeness", "aggregator", "Completeness Feedback", None),
            ("correctness_to_aggregator", "reviewer_correctness", "aggregator", "Correctness Feedback", None),
            ("aggregator_to_end", "aggregator", "end", "Final Report", None)
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
        print("  ✓ Created research & review workflow with 4 agents")


if __name__ == "__main__":
    admin_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(create_research_review_workflow(admin_id))
