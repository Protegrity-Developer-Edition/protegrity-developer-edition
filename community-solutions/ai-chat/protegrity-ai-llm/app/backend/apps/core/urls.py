# backend/apps/core/urls.py
from django.urls import path

from .views import health, chat, poll_conversation, get_models, get_agents, get_tools, CurrentUserView
from .conversation_views import (
    conversation_list_create,
    conversation_detail,
    conversation_messages_create
)

urlpatterns = [
    # Health & Configuration
    path("health/", health, name="health"),
    path("models/", get_models, name="get_models"),
    path("agents/", get_agents, name="get_agents"),
    path("tools/", get_tools, name="get_tools"),
    
    # User
    path("me/", CurrentUserView.as_view(), name="current_user"),
    
    # Chat (legacy endpoint - integrates with DB)
    path("chat/", chat, name="chat"),
    path("chat/poll/<str:conversation_id>/", poll_conversation, name="poll_conversation"),
    
    # Conversations (RESTful endpoints)
    path("conversations/", conversation_list_create, name="conversation_list_create"),
    path("conversations/<uuid:conversation_id>/", conversation_detail, name="conversation_detail"),
    path("conversations/<uuid:conversation_id>/messages/", conversation_messages_create, name="conversation_messages_create"),
]
