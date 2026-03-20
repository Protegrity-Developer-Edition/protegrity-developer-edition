# backend/apps/core/views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import os
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.exceptions import ImproperlyConfigured

from .models import Conversation, Message, LLMProvider, Agent, Tool
from .serializers import CurrentUserSerializer
from .utils import error_response
from .llm_config import (
    filter_enabled_llm_provider_queryset,
    get_enabled_llm_providers,
    validate_llm_provider_configuration,
)


def health(request):
    """
    Simple health check endpoint used by tests and the frontend.
    """
    return JsonResponse({"status": "ok"})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_models(request):
    """
    Returns the list of available LLM models from database.
    Filtered by user's role - PROTEGRITY sees all, STANDARD sees only min_role="STANDARD" models.
    Requires authentication.
    
    GET /api/models/
    
    Returns:
      {
        "models": [
          {"id": "azure-gpt-4o", "name": "GPT-4o (Azure)", "description": "...", "provider": "azure"},
          ...
        ]
      }
    """
    # Import filtering helper
    from .permissions import filter_by_role
    
    # Fetch LLM providers, filtered by user's role
    llm_providers_qs = LLMProvider.objects.all().order_by('display_order', 'name')
    llm_providers_qs = filter_enabled_llm_provider_queryset(llm_providers_qs)
    llm_providers = filter_by_role(llm_providers_qs, request.user)
    
    models = [
        {
            "id": llm.id,
            "name": llm.name,
            "description": llm.description,
            "provider": llm.provider_type,
            "requires_polling": llm.requires_polling,
            "supports_streaming": llm.supports_streaming,
            "max_tokens": llm.max_tokens
        }
        for llm in llm_providers
    ]
    
    return JsonResponse({"models": models})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_agents(request):
    """
    Returns the list of available AI agents from database.
    Filtered by user's role - PROTEGRITY sees agents, STANDARD sees none (all agents min_role="PROTEGRITY").
    Requires authentication.
    
    GET /api/agents/
    
    Returns:
      {
        "agents": [
          {
            "id": "data-protection-expert",
            "name": "Data Protection Expert",
            "description": "...",
            "default_llm": "dummy",
            "icon": "shield",
            "color": "#FA5A25"
          },
          ...
        ]
      }
    """
    # Import filtering helper
    from .permissions import filter_by_role
    
    # Fetch agents, filtered by user's role
    agents_qs = Agent.objects.all().select_related('default_llm').order_by('display_order', 'name')
    agents_qs = filter_by_role(agents_qs, request.user)
    
    agents = [
        {
            "id": agent.id,
            "name": agent.name,
            "description": agent.description,
            "default_llm": agent.default_llm.id if agent.default_llm else None,
            "icon": agent.icon,
            "color": agent.color,
            "system_prompt": agent.system_prompt
        }
        for agent in agents_qs
    ]
    
    return JsonResponse({"agents": agents})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_tools(request):
    """
    Returns the list of available tools from database.
    Filtered by user's role - PROTEGRITY sees tools, STANDARD sees none (all tools min_role="PROTEGRITY").
    Requires authentication.
    
    GET /api/tools/
    
    Returns:
      {
        "tools": [
          {
            "id": "protegrity-redact",
            "name": "Protegrity Data Redaction",
            "tool_type": "protegrity",
            "description": "...",
            "requires_auth": true
          },
          ...
        ]
      }
    """
    # Import filtering helper
    from .permissions import filter_by_role
    
    # Fetch tools, filtered by user's role
    tools_qs = Tool.objects.all().order_by('name')
    tools_qs = filter_by_role(tools_qs, request.user)
    
    tools = [
        {
            "id": tool.id,
            "name": tool.name,
            "tool_type": tool.tool_type,
            "description": tool.description,
            "requires_auth": tool.requires_auth,
            "function_schema": tool.function_schema
        }
        for tool in tools_qs
    ]
    
    return JsonResponse({"tools": tools})


@csrf_exempt
@api_view(['POST'])
def chat(request):
    """
    Chat endpoint that integrates with multiple LLM providers.
    Now includes Protegrity Developer Edition processing and agent/LLM tracking.

    Expects:
      POST /api/chat/
      {
        "conversation_id": "optional-uuid",  # If omitted, creates new conversation
        "message": "user message",
        "model_id": "azure-gpt-4o" | "bedrock-claude",  # Optional, sets primary_llm
        "agent_id": "data-protection-expert" | "general-assistant",  # Optional, sets primary_agent
        "protegrity_mode": "redact" | "protect" | "none"  # Optional, default: "redact"
      }
    
    Note: agent_id and model_id are only used when creating a new conversation.
    For existing conversations, the primary_agent and primary_llm are used.

    Returns:
      {
        "conversation_id": "conversation-id",
        "status": "pending" | "completed" | "blocked",
        "messages": [
          {"role": "user", "content": "..."},
          {"role": "assistant", "content": "..."},
        ],
        "protegrity_data": {
          "input_processing": {...},  # Protegrity processing of user input
          "output_processing": {...}  # Protegrity processing of LLM response
        }
      }
    """
    data = request.data if hasattr(request, 'data') else {}

    message = data.get("message", "") or ""
    conversation_id = data.get("conversation_id") or None
    model_id = data.get("model_id") or None  # No hardcoded default model; allow fallback to agent/user default
    agent_id = data.get("agent_id") or None
    protegrity_mode = data.get("protegrity_mode", "redact")  # "redact", "protect", or "none"

    if not message.strip():
        return error_response("Message is required", code="message_required", http_status=400)

    raw_enabled_list = os.getenv("ENABLED_LLM_PROVIDERS", "").strip()
    try:
        if raw_enabled_list:
            enabled_provider_types = validate_llm_provider_configuration()
        else:
            enabled_provider_types = set()
    except ImproperlyConfigured as exc:
        return error_response(
            str(exc),
            code="llm_provider_configuration_error",
            http_status=500,
        )

    # Get or create conversation in database
    conversation = None
    if conversation_id:
        try:
            conversation = Conversation.objects.filter(id=conversation_id, deleted_at__isnull=True).first()
            
            # If conversation exists and model_id/agent_id are provided, update them for this turn
            if conversation:
                # Import permission checker
                from .permissions import check_resource_access
                
                # Update agent if provided
                if agent_id:
                    try:
                        agent = Agent.objects.get(id=agent_id, is_active=True)
                        if check_resource_access(request.user, agent):
                            conversation.primary_agent = agent
                    except Agent.DoesNotExist:
                        pass  # Keep existing agent
                
                # Update LLM if provided
                if model_id:
                    try:
                        llm_qs = LLMProvider.objects.filter(id=model_id, is_active=True)
                        if enabled_provider_types:
                            llm_qs = llm_qs.filter(provider_type__in=enabled_provider_types)
                        llm_provider = llm_qs.get()
                        if check_resource_access(request.user, llm_provider):
                            conversation.primary_llm = llm_provider
                            conversation.model_id = model_id
                    except LLMProvider.DoesNotExist:
                        pass  # Keep existing LLM
                
                # Save updated conversation
                conversation.save()
        except Exception:
            pass  # Invalid UUID or not found, will create new
    
    if not conversation:
        # Import permission checker
        from .permissions import check_resource_access
        
        # Look up agent first
        agent = None
        if agent_id:
            try:
                agent = Agent.objects.get(id=agent_id, is_active=True)
                
                # Permission check: Can user access this agent?
                if not check_resource_access(request.user, agent):
                    return error_response(
                        "You are not allowed to use this agent.",
                        code="forbidden_agent",
                        http_status=403
                    )
            except Agent.DoesNotExist:
                return error_response(f"Invalid agent_id: {agent_id}", code="invalid_agent", http_status=400)
        
        # Look up LLM provider (or fall back to agent's default)
        llm_provider = None
        if model_id:
            try:
                llm_qs = LLMProvider.objects.filter(id=model_id, is_active=True)
                if enabled_provider_types:
                    llm_qs = llm_qs.filter(provider_type__in=enabled_provider_types)
                llm_provider = llm_qs.get()
                
                # Permission check: Can user access this model?
                if not check_resource_access(request.user, llm_provider):
                    return error_response(
                        "You are not allowed to use this model.",
                        code="forbidden_model",
                        http_status=403
                    )
            except LLMProvider.DoesNotExist:
                return error_response(f"Invalid model_id: {model_id}", code="invalid_model", http_status=400)
        elif agent and agent.default_llm:
            # Fallback: use agent's default LLM (with permission check)
            from .permissions import check_resource_access
            if check_resource_access(request.user, agent.default_llm):
                llm_provider = agent.default_llm
                model_id = llm_provider.id
            else:
                llm_provider = None
        
        # Final fallback: get default LLM for user based on role
        if not llm_provider:
            from .utils import get_default_llm_for_user
            llm_provider = get_default_llm_for_user(request.user)
            
            if not llm_provider:
                return error_response(
                    "No LLM providers are available for your account. Please contact an administrator.",
                    code="no_available_llm",
                    http_status=400
                )
            
            model_id = llm_provider.id
        
        # Create new conversation with agent and LLM tracking
        conversation = Conversation.objects.create(
            title="New chat",
            model_id=model_id,
            primary_agent=agent,
            primary_llm=llm_provider
        )
        conversation_id = str(conversation.id)

    if enabled_provider_types and conversation.primary_llm and conversation.primary_llm.provider_type not in enabled_provider_types:
        return error_response(
            f"Conversation model '{conversation.primary_llm.name}' is not enabled by current backend provider configuration.",
            code="provider_not_enabled",
            http_status=400,
        )

    # Save user message to database
    user_message = Message.objects.create(
        conversation=conversation,
        role="user",
        content=message,
        protegrity_data={}
    )

    # Use ChatOrchestrator to handle the message processing
    from .orchestrator import ChatOrchestrator
    
    orchestrator = ChatOrchestrator()
    result = orchestrator.handle_user_message(
        conversation,
        user_message,
        protegrity_mode=protegrity_mode,
    )
    
    assistant_msg = result.get("assistant_message")
    tool_results = result.get("tool_results", [])
    status = result.get("status")
    input_processing = (user_message.protegrity_data or {}).get("input_processing", {})
    
    # Update conversation title if new
    if conversation.title == "New chat":
        conversation.title = message[:50] + ("..." if len(message) > 50 else "")
        conversation.save(update_fields=["title"])
    
    # Build response payload
    if status == "completed":
        messages = [
            {"role": "user", "content": message},
            {
                "role": "assistant", 
                "content": assistant_msg.content if assistant_msg else "",
                "agent": assistant_msg.agent.name if assistant_msg and assistant_msg.agent else None,
                "llm": assistant_msg.llm_provider.name if assistant_msg and assistant_msg.llm_provider else None
            }
        ]
        
        # Extract output_processing from assistant message's protegrity_data
        output_processing = {}
        if assistant_msg and assistant_msg.protegrity_data:
            output_processing = assistant_msg.protegrity_data.get("output_processing", {})
        
        return JsonResponse({
            "conversation_id": str(conversation.id),
            "status": "completed",
            "messages": messages,
            "tool_results": tool_results,
            "protegrity_data": {
                "input_processing": input_processing,
                "output_processing": output_processing
            }
        })
    
    elif status == "pending":
        messages = [
            {"role": "user", "content": message},
            {"role": "assistant", "content": "", "pending": True}
        ]
        
        return JsonResponse({
            "conversation_id": str(conversation.id),
            "status": "pending",
            "messages": messages,
            "tool_results": [],
            "protegrity_data": {
                "input_processing": input_processing,
                "output_processing": None
            }
        })

    elif status == "blocked":
        messages = [
            {"role": "user", "content": message},
            {
                "role": "system",
                "content": assistant_msg.content if assistant_msg else "This prompt was blocked by security guardrails due to policy violations.",
                "blocked": True,
            },
        ]

        return JsonResponse({
            "conversation_id": str(conversation.id),
            "status": "blocked",
            "messages": messages,
            "tool_results": [],
            "protegrity_data": {
                "input_processing": input_processing,
                "output_processing": None
            }
        })
    
    elif status == "error":
        messages = [
            {"role": "user", "content": message},
            {
                "role": "assistant", 
                "content": assistant_msg.content if assistant_msg else "Error processing request",
            }
        ]
        
        # Extract output_processing from assistant message's protegrity_data (if exists)
        output_processing = {}
        if assistant_msg and assistant_msg.protegrity_data:
            output_processing = assistant_msg.protegrity_data.get("output_processing", {})
        
        return JsonResponse({
            "conversation_id": str(conversation.id),
            "status": "error",
            "messages": messages,
            "tool_results": [],
            "protegrity_data": {
                "input_processing": input_processing,
                "output_processing": output_processing
            }
        })
    
    # Unexpected status
    return JsonResponse({"detail": "Unexpected orchestrator response"}, status=500)


@csrf_exempt
def poll_conversation(request, conversation_id):
    """
    Poll for async LLM response when selected provider requires polling.
    Uses ChatOrchestrator to handle tool execution and message persistence.
    
    GET /api/chat/poll/<conversation_id>/
    
    Args:
        conversation_id: Conversation UUID
    
    Returns:
      {
        "status": "pending" | "completed",
        "response": "LLM response text" (if completed),
        "tool_results": [...],  (Tool execution results if any)
        "protegrity_output": {...}  (Protegrity processing of response)
      }
    """
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    
    try:
        # Get conversation by UUID
        conversation = Conversation.objects.get(id=conversation_id, deleted_at__isnull=True)
    except Conversation.DoesNotExist:
        return error_response("Conversation not found", code="conversation_not_found", http_status=404)
    
    try:
        # Use ChatOrchestrator to poll for response
        from .orchestrator import ChatOrchestrator
        
        orchestrator = ChatOrchestrator()
        result = orchestrator.poll(conversation)
        
        status = result.get("status")
        assistant_msg = result.get("assistant_message")
        tool_results = result.get("tool_results", [])
        
        if status == "pending":
            return JsonResponse({"status": "pending"})
        
        if status == "completed" and assistant_msg:
            output_processing = {}
            if assistant_msg.protegrity_data:
                output_processing = assistant_msg.protegrity_data.get("output_processing", {})
            
            # Update conversation timestamp
            conversation.updated_at = timezone.now()
            conversation.save(update_fields=["updated_at"])
            
            return JsonResponse({
                "status": "completed",
                "response": assistant_msg.content,
                "tool_results": tool_results,
                "protegrity_output": output_processing,
                "agent": assistant_msg.agent.name if assistant_msg.agent else None,
                "llm": assistant_msg.llm_provider.name if assistant_msg.llm_provider else None
            })
        
        # If status is error or assistant_msg is None
        return JsonResponse({
            "status": "error",
            "detail": "Failed to get response from orchestrator"
        }, status=500)
    
    except Exception as e:
        return JsonResponse(
            {"status": "error", "detail": f"Unexpected error: {str(e)}"},
            status=500
        )


class CurrentUserView(APIView):
    """
    Returns information about the currently authenticated user.
    
    Used by the frontend to display user name, role, and permissions
    in the user menu and settings panel.
    
    GET /api/me/
    
    Returns:
        {
            "id": 1,
            "username": "user@example.com",
            "email": "user@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "role": "PROTEGRITY" | "STANDARD",
            "is_protegrity": true | false
        }
    
    Authentication:
        Requires valid JWT token or API key.
        Returns 401 if not authenticated.
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Return current user's profile data."""
        serializer = CurrentUserSerializer(request.user)
        return Response(serializer.data)
