# Standard Agent Communication Protocol (SACP) Specification

This document defines the standard protocol for agent communication within the Multi-Agent Orchestrator. It establishes a schema for agent responses, a method for enforcing this schema via system prompts, and a mechanism for handling orchestration logic based on structured data.

## 1. Objective

To enable seamless, deterministic, and powerful chaining of AI agents by standardizing their input/output format. This allows the system to:
- **Parse responses reliably**: No more regex guessing.
- **Pass structured data**: Agents can output lists, objects, and flags that downstream agents can consume directly.
- **Control flow**: Agents can signal status (`success`, `failure`, `needs_input`) to trigger edge conditions in the workflow.

## 2. Standard JSON Response Schema

All agents participating in a Chain or Workflow MUST return a valid JSON object in their response `content`.

### 2.1 Schema Definition

```json
{
  "type": "object",
  "properties": {
    "thought": {
      "type": "string",
      "description": "Internal reasoning process. Visible to humans but ignored by the next agent programmatically."
    },
    "status": {
      "type": "string",
      "enum": ["success", "failure", "clarification_needed", "completed"],
      "description": "The execution status of the task. Used for routing edge conditions."
    },
    "data": {
      "type": "object",
      "description": "The structured payload to be passed to the next agent or consumed by the system. Keys can be arbitrary based on the task."
    },
    "message": {
      "type": "string",
      "description": "A human-readable summary or final response to be shown to the user."
    },
    "next_step_hint": {
      "type": "string",
      "description": "Optional suggestion for the orchestrator on what to do next (if dynamic routing is enabled)."
    }
  },
  "required": ["thought", "status", "data", "message"]
}
```

### 2.2 Fields

*   **`thought`**: The "Chain of Thought". Agents should use this to plan before acting. It helps improve reasoning quality.
*   **`status`**: Critical for control flow.
    *   `success`: Proceed to the default next node.
    *   `failure`: Preroute to an error handling node or stop.
    *   `clarification_needed`: Pause and ask the user for input.
*   **`data`**: The "context" carrier.
    *   Example: `{ "extracted_names": ["Alice", "Bob"], "sentiment_score": 0.9 }`
*   **`message`**: The "chat" output. This is what the user sees in the chat interface.

## 3. Instruction Injection Strategy

To ensure agents achieve this format, we inject a **Standard System Protocol** into their system prompt. This is appended to any user-defined system prompt.

### 3.1 The Protocol Template

```markdown
### SYSTEM PROTOCOL: RESPONSE FORMAT INSTRUCTIONS
You are a highly organized AI agent integrated into a larger workflow.
CRITICAL: You MUST provide your response in a valid JSON format.
DO NOT include any text outside the JSON block.
DO NOT use markdown code blocks (```json ... ```) unless specifically asked, but the raw response MUST be parseable JSON.

Your response schema is:
{
    "thought": "Your reasoning process here...",
    "status": "success" | "failure" | "clarification_needed",
    "data": {
        "key": "value"
        // Any structured data extracted or generated
    },
    "message": "The final human-readable answer."
}

Example:
{
    "thought": "I need to calculate the sum. 5+5 is 10.",
    "status": "success",
    "data": { "result": 10 },
    "message": "The result is 10."
}
```

### 3.2 Implementation
The `AgentService` or `PromptBuilder` will automatically append this block to the `system_prompt` of any agent configured with `response_format="json_standard"`.

## 4. Edge Conditions & Routing

The workflow engine (`ChainOrchestrator`) will be updated to read the `status` and `data` fields.

### 4.1 Conditional Edges
Edges in the workflow graph can now define conditions based on JSON paths:

*   **Condition**: `response.status == "success"` -> Go to Node B
*   **Condition**: `response.status == "failure"` -> Go to Node C (Error Handler)
*   **Condition**: `response.data.score > 0.8` -> Go to Node D (High Confidence)

### 4.2 Data Mapping
Input mapping for the next node becomes precise:
*   Node B Input: `{{node_A.data.extracted_names}}`
*   Node B Input: `{{node_A.message}}`

## 5. Development Steps

1.  **Update Agent Model**: Add a flag `use_standard_protocol` (boolean) to `AgentConfig`.
2.  **Prompt Injection**: Modify `LLMService` or `AgentService` to append the protocol template if the flag is true.
3.  **Response Parser**: Update `ChainOrchestrator` to parse the JSON content from `LLMResponse`.
    *   If parsing fails, treat as a `failure` status or wrap the raw text in a default JSON wrapper.
4.  **Edge Logic**: enhance `evaluate_condition` in the orchestrator to support JSON path querying (e.g., using `jsonpath-ng` or simple dict access).

## 6. Example Flow

**User**: "Find the email of the CEO of Acme Corp."

**Agent 1 (Researcher)**:
*   **Input**: "Find email..."
*   **Output**:
    ```json
    {
        "thought": "I found the CEO is John Doe, but no direct email. I will guess standard formats.",
        "status": "success",
        "data": {
            "ceo_name": "John Doe",
            "domain": "acme.com",
            "guesses": ["john.doe@acme.com", "jdoe@acme.com"]
        },
        "message": "I identified the CEO as John Doe."
    }
    ```

**Agent 2 (Email Validator)** (Receives `data.guesses`):
*   **Input**: `["john.doe@acme.com", ...]`
*   **Output**:
    ```json
    {
        "thought": "Pinged servers. jdoe@acme.com is valid.",
        "status": "success",
        "data": {
            "valid_email": "jdoe@acme.com"
        },
        "message": "The valid email is jdoe@acme.com"
    }
    ```

## 7. Handling Parsing Failures & Robustness

LLMs may occasionally fail to return valid JSON or may include conversational filler. The system implements a multi-stage fallback mechanism.

### 7.1 Sanitization
Before parsing, the system:
1.  Searches for markdown JSON blocks (````json ... ````).
2.  If not found, it attempts to find the first `{` and last `}` to extract a potential JSON object.
3.  Removes any leading/trailing whitespace or non-JSON characters.

### 7.2 Fallback Schema
If parsing still fails, the `ChainOrchestrator` MUST wrap the raw output in a valid SACP object to prevent workflow breakage:
```json
{
    "thought": "System Note: LLM failed to provide structured JSON output.",
    "status": "failure",
    "data": { "raw_output": "The actual raw text from the LLM..." },
    "message": "The LLM returned an invalid response format."
}
```

## 8. Integration with Tool Execution

When an agent is configured with both `tools` and `use_standard_protocol`, the execution follows this lifecycle:

1.  **Phase 1 (Tool Loop)**: The agent may call multiple tools. These interactions do NOT necessarily follow SACP.
2.  **Phase 2 (Final Synthesis)**: Once the agent decides it has enough information, it generates its final response. THIS final response must strictly adhere to SACP.

### 8.1 Data Mapping from Tools
Agents are encouraged to include relevant tool outputs in the `data` object:
```json
{
    "thought": "I used the search tool and found the weather.",
    "status": "success",
    "data": {
        "city": "London",
        "temp": 15,
        "tool_used": "get_weather"
    },
    "message": "The weather in London is 15°C."
}
```

## 9. Guardrails & Compliance

The SACP structure facilitates automated monitoring and guardrail enforcement.

### 9.1 Status-Based Guardrails
*   **Redaction**: If `status == "failure"` and contains sensitive data in `data`, the system can automatically redact the `message` shown to the user while keeping `data` for the orchestrator (if secured).
*   **Intervention**: If a guardrail service detects a violation in the `message`, it can force-update the `status` to `failure` before the next agent receives the payload.

### 9.2 Audit Trails
Every SACP response is logged in the `AuditLog` table. The `thought` field is particularly valuable for "Explainable AI" (XAI) requirements, allowing auditors to see the reasoning behind a specific automated decision.

## 10. Best Practices for Agent Authors

To maximize the effectiveness of SACP, follow these guidelines when writing system prompts:

1.  **Be Explicit about `data`**: Define in the agent's specific instructions what keys should be in the `data` object. (e.g., "Always include 'order_id' in your data output").
2.  **Use `thought` for Planning**: Encourage the agent to use the `thought` field to think step-by-step.
3.  **Status Integrity**: Only use `success` if the task is truly completed. Use `clarification_needed` if you have multiple options and need the user to choose.
4.  **Avoid Bloat**: Keep the `data` object focused on what downstream agents or the UI actually need. Do not dump entire raw API responses into `data` unless necessary.

## 11. Future Roadmap

*   **Binary Data Support**: Exploring base64 encoding or signed URL references in the `data` field for image/document processing chains.
*   **Negotiation Protocol**: Allowing agents to return a `retry_with_instruction` status to "talk back" to the previous agent in the chain if validation fails.
*   **Schema Enforcement (Pydantic-style)**: Integrating JSON Schema validation at the orchestrator level to reject responses that don't match a *per-agent* defined data schema.



