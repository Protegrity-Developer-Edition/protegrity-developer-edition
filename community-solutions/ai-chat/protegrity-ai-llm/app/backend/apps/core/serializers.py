"""
Django REST Framework serializers for conversations, messages, and users.

Serialization Strategy:
- Nested serialization for complete conversation data
- Read-only fields for auto-generated values
- Validation for required fields
- Efficient queries with select_related/prefetch_related
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Conversation, Message
from .permissions import filter_by_role
from .llm_config import filter_enabled_llm_provider_queryset

User = get_user_model()


class MessageSerializer(serializers.ModelSerializer):
    """
    Serializer for Message model.
    
    Used for:
    - Nested in conversation responses
    - Message creation
    """
    
    agent = serializers.SlugRelatedField(
        slug_field='id',
        read_only=True
    )
    llm_provider = serializers.SlugRelatedField(
        slug_field='id',
        read_only=True
    )
    
    class Meta:
        model = Message
        fields = [
            'id',
            'role',
            'content',
            'protegrity_data',
            'pending',
            'blocked',
            'agent',
            'llm_provider',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']
    
    def to_representation(self, instance):
        """
        Customize output representation.
        Only include protegrity_data if it exists.
        """
        data = super().to_representation(instance)
        if not data.get('protegrity_data'):
            data.pop('protegrity_data', None)
        return data


class ConversationListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for conversation lists.
    
    Used for:
    - GET /api/conversations/ (list endpoint)
    - Minimal data for sidebar rendering
    """
    
    message_count = serializers.SerializerMethodField()
    primary_agent = serializers.SlugRelatedField(
        slug_field='id',
        read_only=True
    )
    primary_llm = serializers.SlugRelatedField(
        slug_field='id',
        read_only=True
    )
    
    class Meta:
        model = Conversation
        fields = [
            'id',
            'title',
            'model_id',
            'primary_agent',
            'primary_llm',
            'message_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_message_count(self, obj):
        """Return count of non-deleted messages."""
        return obj.messages.filter(deleted_at__isnull=True).count()


class ConversationDetailSerializer(serializers.ModelSerializer):
    """
    Complete serializer for conversation detail.
    
    Used for:
    - GET /api/conversations/{id}/ (detail endpoint)
    - Includes all messages
    """
    
    messages = MessageSerializer(many=True, read_only=True)
    primary_agent = serializers.SlugRelatedField(
        slug_field='id',
        read_only=True
    )
    primary_llm = serializers.SlugRelatedField(
        slug_field='id',
        read_only=True
    )
    
    class Meta:
        model = Conversation
        fields = [
            'id',
            'title',
            'model_id',
            'primary_agent',
            'primary_llm',
            'messages',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def to_representation(self, instance):
        """
        Filter out soft-deleted messages in response.
        """
        data = super().to_representation(instance)
        # Filter messages in Python to avoid N+1 queries
        if 'messages' in data:
            data['messages'] = [
                msg for msg in data['messages']
                if not Message.objects.get(id=msg['id']).deleted_at
            ]
        return data


class ConversationCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new conversations.
    
    Used for:
    - POST /api/conversations/
    """
    
    class Meta:
        model = Conversation
        fields = ['title', 'model_id']
    
    def validate_model_id(self, value):
        """Validate that model_id is accessible for the current user and env config."""
        from .models import LLMProvider

        request = self.context.get("request")
        qs = LLMProvider.objects.filter(is_active=True)
        qs = filter_enabled_llm_provider_queryset(qs)
        if request is not None:
            qs = filter_by_role(qs, request.user)

        valid_models = set(qs.values_list("id", flat=True))
        if value not in valid_models:
            available = ", ".join(sorted(valid_models)) if valid_models else "none"
            raise serializers.ValidationError(
                f"Invalid model_id. Available models: {available}"
            )
        return value


class CurrentUserSerializer(serializers.ModelSerializer):
    """
    Serializer for current authenticated user.
    
    Returns user profile information including role and permissions.
    Used by /api/me/ endpoint for user settings and display.
    """
    
    role = serializers.SerializerMethodField()
    is_protegrity = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'role',
            'is_protegrity',
        ]
    
    def get_role(self, obj):
        """Get user's role from Django Groups."""
        from .utils import get_user_role
        return get_user_role(obj)
    
    def get_is_protegrity(self, obj):
        """Check if user has PROTEGRITY role via Django Groups."""
        from .utils import get_user_role
        return get_user_role(obj) == 'PROTEGRITY'
