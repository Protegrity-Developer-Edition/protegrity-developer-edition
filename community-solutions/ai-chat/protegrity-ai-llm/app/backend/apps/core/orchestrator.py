"""
Chat Orchestrator

Central coordination layer for chat interactions that handles:
- Agent and LLM selection/resolution
- Provider routing and message sending
- Tool call execution (Protegrity and future tools)
- Message persistence with proper tracking

This orchestrator sits between the API endpoints and the provider/tool layers,
managing the complete flow of a chat turn from user input to assistant response.

Architecture Flow:
1. User message arrives via API endpoint
2. Orchestrator resolves which agent/LLM to use
3. Provider sends message to LLM
4. If LLM requests tools, orchestrator executes them
5. Assistant message is persisted with agent/llm tracking
6. Response returned to API endpoint

Usage:
    orchestrator = ChatOrchestrator()
    result = orchestrator.handle_user_message(conversation, user_message)
    # Returns: {
    #     "assistant_message": Message instance,
    #     "tool_results": [...],
    #     "status": "completed" | "pending"
    # }
"""

from typing import Optional, Dict, Any
from django.db import transaction
import logging
from .models import Conversation, Message, Agent, LLMProvider
from .providers import get_provider
from .tool_router import execute_tool_calls
from .protegrity_service import get_protegrity_service

logger = logging.getLogger(__name__)


class ChatOrchestrator:
    """
    Orchestrates the complete flow of a chat interaction.
    
    Responsibilities:
    - Resolve agent and LLM for the conversation
    - Route messages to appropriate provider
    - Execute tool calls when requested by LLM
    - Persist assistant messages with tracking metadata
    - Handle both synchronous and asynchronous provider flows
    """
    
    def _resolve_agent_and_llm(self, conversation: Conversation) -> tuple[Optional[Agent], Optional[LLMProvider]]:
        """
        Determine which agent and LLM to use for this conversation.
        
        Resolution logic:
        1. Use conversation.primary_agent (set by user)
        2. Use conversation.primary_llm (set by user)
        3. If primary_llm is None, fallback to agent.default_llm
        4. Update conversation if fallback was used
        
        Args:
            conversation: Conversation instance
        
        Returns:
            Tuple of (agent, llm_provider) - both may be None
        """
        agent = conversation.primary_agent
        llm = conversation.primary_llm
        
        # Fallback: use agent's default LLM if primary_llm is unset
        if llm is None and agent and agent.default_llm:
            llm = agent.default_llm
            conversation.primary_llm = llm
            conversation.model_id = llm.id
            conversation.save(update_fields=["primary_llm", "model_id"])
            logger.info(f"Using agent '{agent.name}' default LLM: {llm.name}")
        
        if agent:
            logger.info(f"Resolved agent: {agent.name} (ID: {agent.id})")
        if llm:
            logger.info(f"Resolved LLM: {llm.name} (ID: {llm.id})")
        
        return agent, llm
    
    @transaction.atomic
    def handle_user_message(
        self,
        conversation: Conversation,
        user_message: Message,
        protegrity_mode: str = "redact",
    ) -> Dict[str, Any]:
        """
        Process a new user message through the complete chat pipeline.
        
        Steps:
        1. Resolve agent and LLM
        2. Get conversation history
        3. Send to LLM provider
        4. Execute any requested tool calls
        5. Create assistant message with results
        
        Args:
            conversation: Conversation instance
            user_message: User Message instance (already saved)
        
        Returns:
            Dict with:
            {
                "assistant_message": Message instance (None if pending),
                "tool_results": List of tool execution results,
                "status": "completed" | "pending"
            }
        """
        logger.info(f"Handling user message for conversation {conversation.id}")
        
        # Step 1: Run Protegrity input protection on user message
        protegrity_service = get_protegrity_service()
        input_result = protegrity_service.process_full_pipeline(
            user_message.content,
            mode=protegrity_mode or "redact"
        )
        # Wrap input protection data in input_processing key (matching frontend expectations)
        user_message.protegrity_data = {
            "input_processing": input_result
        }
        user_message.save(update_fields=["protegrity_data"])
        logger.info(f"Input protection: should_block={input_result.get('should_block')}")
        
        # If input is blocked, return early with blocked message
        if input_result.get("should_block"):
            logger.warning("User input blocked by Protegrity guardrails")
            blocked_msg = Message.objects.create(
                conversation=conversation,
                role="assistant",
                content="Your message was blocked due to policy violations. Please rephrase and try again.",
                pending=False,
                blocked=True,
                agent=conversation.primary_agent,
                llm_provider=conversation.primary_llm,
            )
            return {
                "assistant_message": blocked_msg,
                "tool_results": [],
                "status": "blocked"
            }
        
        # Step 2: Resolve agent and LLM
        agent, llm = self._resolve_agent_and_llm(conversation)
        
        if not llm:
            logger.error("No LLM available for conversation")
            # Create error message
            error_msg = Message.objects.create(
                conversation=conversation,
                role="assistant",
                content="Error: No LLM provider configured for this conversation.",
                pending=False,
                blocked=False,
                agent=agent,
                llm_provider=None,
            )
            return {
                "assistant_message": error_msg,
                "tool_results": [],
                "status": "error"
            }
        
        # Step 3: Get provider and send message with protected text
        provider = get_provider(llm)
        history = list(conversation.messages.order_by("created_at"))
        
        # Replace last user message content with protected text for LLM
        protected_text = input_result.get("processed_text") or user_message.content
        for msg in reversed(history):
            if msg.id == user_message.id:
                msg.content = protected_text
                break
        
        logger.info(f"Sending message to provider: {provider.__class__.__name__}")
        result = provider.send_message(conversation, history, agent=agent)
        
        tool_results = []
        assistant_msg = None
        
        # Step 4: Handle completed responses
        if result.status == "completed":
            logger.info(f"Provider returned completed response")
            
            # Step 5: Execute tool calls if requested
            if result.tool_calls:
                logger.info(f"Executing {len(result.tool_calls)} tool call(s)")
                tool_results = execute_tool_calls(agent, result.tool_calls)
                
                # Log tool execution summary
                for tr in tool_results:
                    if "error" in tr:
                        logger.warning(f"Tool {tr['tool_name']} failed: {tr['error']}")
                    else:
                        logger.info(f"Tool {tr['tool_name']} succeeded")
            
            # Step 6: Run Protegrity output protection on LLM response
            raw_llm_output = result.content or ""
            output_result = protegrity_service.process_llm_response(raw_llm_output)
            safe_content = output_result.get("processed_response") or raw_llm_output
            
            # Optionally append tool summary to content for visibility
            if tool_results:
                tool_summary = "\n\n---\n**Tools Used:**\n"
                for tr in tool_results:
                    if "error" in tr:
                        tool_summary += f"- ❌ {tr['tool_name']}: {tr['error']}\n"
                    else:
                        tool_summary += f"- ✅ {tr['tool_name']}: Success\n"
                safe_content += tool_summary
            
            # Wrap output protection data in output_processing key (matching frontend expectations)
            protegrity_data = {
                "output_processing": output_result
            }
            if tool_results:
                protegrity_data["tool_results"] = tool_results
            
            # Determine if message should be blocked
            is_blocked = output_result.get("should_filter", False)
            if is_blocked:
                safe_content = "This response was blocked due to policy violations."
            
            logger.info(f"Output protection: should_filter={is_blocked}")
            
            # Step 7: Create assistant message
            assistant_msg = Message.objects.create(
                conversation=conversation,
                role="assistant",
                content=safe_content,
                protegrity_data=protegrity_data,
                pending=False,
                blocked=is_blocked,
                agent=agent,
                llm_provider=llm,
            )
            
            logger.info(f"Created assistant message {assistant_msg.id}")
        
        elif result.status == "pending":
            # For async providers, create a pending message placeholder
            logger.info(f"Provider returned pending status")
            assistant_msg = Message.objects.create(
                conversation=conversation,
                role="assistant",
                content="",
                pending=True,
                blocked=False,
                agent=agent,
                llm_provider=llm,
            )
        
        return {
            "assistant_message": assistant_msg,
            "tool_results": tool_results,
            "status": result.status,
        }
    
    def poll(self, conversation: Conversation) -> Dict[str, Any]:
        """
        Poll for async provider results for a conversation.
        
        Used by /api/chat/poll/ endpoint to check if an async LLM
        has completed its response.
        
        Args:
            conversation: Conversation instance
        
        Returns:
            Dict with:
            {
                "status": "completed" | "pending",
                "assistant_message": Message instance (if completed),
                "tool_results": List of tool execution results
            }
        """
        logger.info(f"Polling conversation {conversation.id}")
        
        # Step 1: Resolve agent and LLM
        agent, llm = self._resolve_agent_and_llm(conversation)
        
        if not llm:
            logger.error("No LLM available for polling")
            return {"status": "error", "assistant_message": None, "tool_results": []}
        
        # Step 2: Poll provider
        provider = get_provider(llm)
        result = provider.poll_response(conversation)
        
        if result is None or result.status == "pending":
            logger.info("Provider still pending")
            return {"status": "pending", "assistant_message": None, "tool_results": []}
        
        # Step 3: Process completed response
        tool_results = []
        if result.tool_calls:
            logger.info(f"Executing {len(result.tool_calls)} tool call(s) from poll")
            tool_results = execute_tool_calls(agent, result.tool_calls)
        
        # Step 4: Run Protegrity output protection on LLM response
        protegrity_service = get_protegrity_service()
        raw_llm_output = result.content or ""
        output_result = protegrity_service.process_llm_response(raw_llm_output)
        safe_content = output_result.get("processed_response") or raw_llm_output
        
        # Append tool summary if applicable
        if tool_results:
            tool_summary = "\n\n---\n**Tools Used:**\n"
            for tr in tool_results:
                if "error" in tr:
                    tool_summary += f"- ❌ {tr['tool_name']}: {tr['error']}\n"
                else:
                    tool_summary += f"- ✅ {tr['tool_name']}: Success\n"
            safe_content += tool_summary
        
        # Wrap output protection data in output_processing key (matching frontend expectations)
        protegrity_data = {
            "output_processing": output_result
        }
        if tool_results:
            protegrity_data["tool_results"] = tool_results
        
        # Determine if message should be blocked
        is_blocked = output_result.get("should_filter", False)
        if is_blocked:
            safe_content = "This response was blocked due to policy violations."
        
        logger.info(f"Poll output protection: should_filter={is_blocked}")
        
        # Step 5: Create assistant message
        assistant_msg = Message.objects.create(
            conversation=conversation,
            role="assistant",
            content=safe_content,
            protegrity_data=protegrity_data,
            pending=False,
            blocked=is_blocked,
            agent=agent,
            llm_provider=llm,
        )
        
        logger.info(f"Poll completed, created assistant message {assistant_msg.id}")
        
        return {
            "status": "completed",
            "assistant_message": assistant_msg,
            "tool_results": tool_results,
        }
