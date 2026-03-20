"""
Tool Routing and Execution System

This module handles the execution of tool calls requested by LLM providers.
It validates that agents have permission to use requested tools, then dispatches
to the appropriate execution handlers (Protegrity SDK, custom functions, etc).

Architecture:
- execute_tool_calls(): Main entry point, validates agent permissions
- _execute_protegrity_tool(): Dispatcher for Protegrity-specific tools
- Tool results are returned in a standard format for LLM consumption

Tool Call Format (from LLM provider):
{
    "tool_name": "protegrity-redact",   # matches Tool.id in database
    "arguments": {...},                  # JSON-serializable parameters
    "call_id": "tool_call_1",            # unique identifier for this call
}

Tool Result Format (returned to orchestrator):
{
    "call_id": "tool_call_1",
    "tool_name": "protegrity-redact",
    "output": {...},                     # result from tool execution
    "error": "...",                      # present only if execution failed
}
"""

from typing import List, Dict, Any
import logging
from .models import Tool
from .protegrity_service import get_protegrity_service

logger = logging.getLogger(__name__)


def execute_tool_calls(agent, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Execute tool calls for a given agent, validating permissions.
    
    Only tools assigned to the agent (via agent.tools M2M) and marked as active
    will be executed. Unauthorized or inactive tools return an error result.
    
    Args:
        agent: Agent model instance (may be None for no agent)
        tool_calls: List of tool call dicts from LLM provider
    
    Returns:
        List of tool result dicts with call_id, tool_name, output/error
    
    Example:
        >>> tool_calls = [
        ...     {"tool_name": "protegrity-redact", "call_id": "1", "arguments": {"text": "SSN: 123-45-6789"}},
        ... ]
        >>> results = execute_tool_calls(agent, tool_calls)
        >>> results[0]["output"]["redacted_text"]
        'SSN: [SSN]'
    """
    if not tool_calls:
        return []
    
    # Pre-fetch agent tools for quick lookup
    agent_tools = {}
    if agent:
        agent_tools = {t.id: t for t in agent.tools.all()}
        logger.info(f"Agent '{agent.name}' has access to {len(agent_tools)} tool(s): {list(agent_tools.keys())}")
    else:
        logger.warning("No agent provided, tool execution will be restricted")
    
    results = []
    
    for call in tool_calls:
        tool_name = call.get("tool_name")
        call_id = call.get("call_id", "unknown")
        args = call.get("arguments", {}) or {}
        
        logger.info(f"Processing tool call {call_id}: {tool_name}")
        
        # Validate tool exists and agent has permission
        tool = agent_tools.get(tool_name)
        if not tool:
            error_msg = f"Tool '{tool_name}' not found or not authorized for this agent"
            logger.warning(f"{error_msg} (call_id: {call_id})")
            results.append({
                "call_id": call_id,
                "tool_name": tool_name,
                "error": error_msg,
            })
            continue
        
        if not tool.is_active:
            error_msg = f"Tool '{tool_name}' is currently disabled"
            logger.warning(f"{error_msg} (call_id: {call_id})")
            results.append({
                "call_id": call_id,
                "tool_name": tool_name,
                "error": error_msg,
            })
            continue
        
        # Dispatch based on tool type
        try:
            logger.info(f"Executing {tool.tool_type} tool: {tool_name}")
            
            if tool.tool_type == "protegrity":
                output = _execute_protegrity_tool(tool, args)
            else:
                # Future: support other tool types (custom, api, etc.)
                output = {"warning": f"Tool type '{tool.tool_type}' not yet implemented"}
                logger.warning(f"Unsupported tool type: {tool.tool_type}")
            
            results.append({
                "call_id": call_id,
                "tool_name": tool_name,
                "output": output,
            })
            logger.info(f"Successfully executed tool call {call_id}")
            
        except Exception as exc:
            error_msg = str(exc)
            logger.error(f"Tool execution failed for {call_id} ({tool_name}): {error_msg}", exc_info=True)
            results.append({
                "call_id": call_id,
                "tool_name": tool_name,
                "error": error_msg,
            })
    
    return results


def _execute_protegrity_tool(tool: Tool, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a Protegrity-specific tool by calling the appropriate SDK method.
    
    Maps tool IDs to protegrity_service.py functions:
    - protegrity-redact -> redact_data()
    - protegrity-classify -> discover_entities()
    - protegrity-guardrails -> check_guardrails()
    - protegrity-protect -> protect_data()
    - protegrity-unprotect -> unprotect_data()
    
    Args:
        tool: Tool model instance (tool_type must be "protegrity")
        args: Arguments dict from LLM tool call
    
    Returns:
        Dict with tool execution results
    
    Raises:
        NotImplementedError: If tool ID mapping is not defined
        Exception: If Protegrity SDK call fails
    """
    tool_id = tool.id
    protegrity = get_protegrity_service()
    
    # Get text parameter (common to most tools)
    text = args.get("text", "")
    
    if not text and tool_id not in ["protegrity-guardrails"]:
        logger.warning(f"No text provided for {tool_id}, using empty string")
    
    # Dispatch to appropriate Protegrity service method
    if tool_id == "protegrity-redact":
        logger.info(f"Calling protegrity.redact_data() with {len(text)} chars")
        redacted_text, metadata = protegrity.redact_data(text)
        return {
            "redacted_text": redacted_text,
            "original_length": len(text),
            "redacted_length": len(redacted_text),
            "metadata": metadata,
        }
    
    elif tool_id == "protegrity-classify":
        logger.info(f"Calling protegrity.discover_entities() with {len(text)} chars")
        entities = protegrity.discover_entities(text)
        
        # Count total entities found
        total_entities = sum(len(v) for v in entities.values())
        
        return {
            "entities": entities,
            "entity_types": list(entities.keys()),
            "total_entities": total_entities,
            "original_text": text,
        }
    
    elif tool_id == "protegrity-guardrails":
        logger.info(f"Calling protegrity.check_guardrails() with {len(text)} chars")
        guardrail_result = protegrity.check_guardrails(text)
        return guardrail_result
    
    elif tool_id == "protegrity-protect":
        logger.info(f"Calling protegrity.protect_data() with {len(text)} chars")
        protected_text, metadata = protegrity.protect_data(text)
        return {
            "protected_text": protected_text,
            "success": protected_text is not None,
            "metadata": metadata,
        }
    
    elif tool_id == "protegrity-unprotect":
        logger.info(f"Calling protegrity.unprotect_data() with {len(text)} chars")
        unprotected_text, metadata = protegrity.unprotect_data(text)
        return {
            "unprotected_text": unprotected_text,
            "success": unprotected_text is not None,
            "metadata": metadata,
        }
    
    else:
        raise NotImplementedError(
            f"No handler defined for Protegrity tool '{tool_id}'. "
            f"Update _execute_protegrity_tool() to add support."
        )
