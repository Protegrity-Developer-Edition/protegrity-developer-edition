"""
Django REST Framework views for conversation management.

API Architecture:
- RESTful design following Django best practices
- Efficient queries with select_related/prefetch_related
- Soft deletes for data retention
- Pagination for scalability
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db import models
from django.db.models import Count, Prefetch, Q
from django.utils import timezone

from .models import Conversation, Message
from .serializers import (
    ConversationListSerializer,
    ConversationDetailSerializer,
    ConversationCreateSerializer,
    MessageSerializer
)
from .utils import error_response


class ConversationPagination(PageNumberPagination):
    """
    Pagination for conversation lists.
    Defaults to 50 conversations per page for performance.
    """
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def conversation_list_create(request):
    """
    GET /api/conversations/
    List all active conversations ordered by most recent.
    
    Query parameters:
    - page: Page number (default: 1)
    - page_size: Results per page (default: 50, max: 100)
    
    Response:
    {
      "count": 150,
      "next": "http://localhost:8000/api/conversations/?page=2",
      "previous": null,
      "results": [
        {
          "id": "uuid",
          "title": "Chat title",
                    "model_id": "azure-gpt-4o",
          "message_count": 5,
          "created_at": "2025-12-10T...",
          "updated_at": "2025-12-10T..."
        },
        ...
      ]
    }
    
    POST /api/conversations/
    Create a new conversation.
    
    Request:
    {
      "title": "New chat",  # optional
            "model_id": "azure-gpt-4o"     # required
    }
    
    Response: 201 Created
    {
      "id": "uuid",
      "title": "New chat",
            "model_id": "azure-gpt-4o",
      "messages": [],
      "created_at": "2025-12-10T...",
      "updated_at": "2025-12-10T..."
    }
    """
    
    if request.method == 'GET':
        # Efficient query: only active conversations, annotate message count
        conversations = Conversation.objects.filter(
            deleted_at__isnull=True
        ).select_related('primary_agent', 'primary_llm').annotate(
            message_count=Count('messages', filter=Q(messages__deleted_at__isnull=True))
        ).order_by('-updated_at')
        
        # Paginate results
        paginator = ConversationPagination()
        page = paginator.paginate_queryset(conversations, request)
        
        if page is not None:
            serializer = ConversationListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = ConversationListSerializer(conversations, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        serializer = ConversationCreateSerializer(data=request.data)
        if serializer.is_valid():
            conversation = serializer.save()
            # Return full detail including empty messages array
            detail_serializer = ConversationDetailSerializer(conversation)
            return Response(detail_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def conversation_detail(request, conversation_id):
    """
    GET /api/conversations/{id}/
    Retrieve a single conversation with all messages.
    
    Response: 200 OK
    {
      "id": "uuid",
      "title": "Chat title",
            "model_id": "azure-gpt-4o",
      "messages": [
        {
          "id": "uuid",
          "role": "user",
          "content": "Hello",
          "protegrity_data": {...},
          "pending": false,
          "blocked": false,
          "created_at": "2025-12-10T..."
        },
        ...
      ],
      "created_at": "2025-12-10T...",
      "updated_at": "2025-12-10T..."
    }
    
    PATCH /api/conversations/{id}/
    Update conversation (e.g., change title).
    
    Request:
    {
      "title": "Updated title"
    }
    
    Response: 200 OK (same as GET)
    
    DELETE /api/conversations/{id}/
    Soft delete a conversation and all its messages.
    
    Response: 204 No Content
    """
    
    try:
        # Efficient query with prefetch_related for messages
        conversation = Conversation.objects.select_related(
            'primary_agent', 'primary_llm'
        ).prefetch_related(
            Prefetch(
                'messages',
                queryset=Message.objects.filter(deleted_at__isnull=True).select_related(
                    'agent', 'llm_provider'
                ).order_by('created_at')
            )
        ).get(id=conversation_id, deleted_at__isnull=True)
    except Conversation.DoesNotExist:
        return error_response(
            "Conversation not found",
            code="conversation_not_found",
            http_status=404
        )
    
    if request.method == 'GET':
        serializer = ConversationDetailSerializer(conversation)
        return Response(serializer.data)
    
    elif request.method == 'PATCH':
        serializer = ConversationDetailSerializer(
            conversation,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        conversation.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def conversation_messages_create(request, conversation_id):
    """
    POST /api/conversations/{id}/messages/
    Add a message to a conversation.
    
    Note: This is used internally by the chat endpoint.
    The main chat endpoint handles message creation + LLM interaction.
    
    Request:
    {
      "role": "user" | "assistant" | "system",
      "content": "Message text",
      "protegrity_data": {...},  # optional
      "pending": false,          # optional
      "blocked": false           # optional
    }
    
    Response: 201 Created
    {
      "id": "uuid",
      "role": "user",
      "content": "Message text",
      "protegrity_data": {...},
      "pending": false,
      "blocked": false,
      "created_at": "2025-12-10T..."
    }
    """
    
    try:
        conversation = Conversation.objects.get(
            id=conversation_id,
            deleted_at__isnull=True
        )
    except Conversation.DoesNotExist:
        return error_response(
            "Conversation not found",
            code="conversation_not_found",
            http_status=404
        )
    
    serializer = MessageSerializer(data=request.data)
    if serializer.is_valid():
        message = serializer.save(conversation=conversation)
        
        # Update conversation's updated_at timestamp
        conversation.updated_at = timezone.now()
        conversation.save(update_fields=['updated_at'])
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Import for annotations
from django.db import models
