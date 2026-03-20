"""
Core models for chat conversations and messages.

Database Design Philosophy:
- PostgreSQL recommended for production (supports JSON fields efficiently)
- Indexed fields for fast queries on conversation retrieval
- JSON fields for flexible metadata storage without schema changes
- Soft deletes for data retention and recovery
- Timestamps for audit trails and analytics
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
import uuid
import secrets


# Role choices - used by UserProfile and resource models
ROLE_CHOICES = [
    ("PROTEGRITY", "Protegrity Employee / Admin"),
    ("STANDARD", "Standard User"),
]


class UserProfile(models.Model):
    """
    User profile extending Django's default User model with role-based access control.
    
    Design Notes:
    - OneToOne with User model for clean separation
    - Auto-created via post_save signal
    - Role governs access to LLMs, Agents, and Tools
    - PROTEGRITY role: full access to active resources
    - STANDARD role: limited to Fin AI, no agents/tools
    """
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        help_text="Associated Django user"
    )
    
    role = models.CharField(
        max_length=32,
        choices=ROLE_CHOICES,
        default="STANDARD",
        db_index=True,
        help_text="Role governs access to LLMs, Agents, and Tools"
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_profiles'
        ordering = ['user__username']
    
    def __str__(self):
        return f"{self.user.username} ({self.role})"


# Signal to auto-create UserProfile when User is created
@receiver(post_save, sender=get_user_model())
def create_user_profile(sender, instance, created, **kwargs):
    """Auto-create UserProfile for new users."""
    if created:
        UserProfile.objects.create(user=instance)


class Conversation(models.Model):
    """
    Represents a chat conversation thread.
    
    Design Notes:
    - UUID primary key prevents enumeration attacks
    - title auto-generated from first message, editable by user
    - model_id tracks which LLM was used (for analytics/billing)
    - deleted_at enables soft deletes (data retention policy)
    """
    
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False,
        help_text="Unique conversation identifier"
    )
    
    title = models.CharField(
        max_length=255, 
        default="New chat",
        db_index=True,
        help_text="Conversation title, typically first user message"
    )
    
    model_id = models.CharField(
        max_length=50,
        db_index=True,
        help_text="LLM model identifier (fin, bedrock-claude, etc.)"
    )
    
    primary_agent = models.ForeignKey(
        'Agent',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='conversations',
        help_text="Default agent for this conversation"
    )
    
    primary_llm = models.ForeignKey(
        'LLMProvider',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='conversations',
        help_text="Default LLM provider for this conversation"
    )
    
    created_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="Conversation creation timestamp"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        db_index=True,
        help_text="Last message timestamp"
    )
    
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Soft delete timestamp (NULL if active)"
    )
    
    class Meta:
        db_table = 'conversations'
        ordering = ['-updated_at']
        indexes = [
            # Composite index for active conversations query
            models.Index(fields=['-updated_at', 'deleted_at'], name='conv_active_idx'),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.id})"
    
    def soft_delete(self):
        """Soft delete the conversation and all its messages."""
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])
        self.messages.update(deleted_at=timezone.now())


class Message(models.Model):
    """
    Represents a single message in a conversation.
    
    Design Notes:
    - ForeignKey with CASCADE for data integrity
    - role field for user/assistant/system messages
    - JSON field for Protegrity metadata (flexible, no schema changes needed)
    - pending flag for async LLM responses
    - Indexed for fast conversation message retrieval
    """
    
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique message identifier"
    )
    
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
        db_index=True,
        help_text="Parent conversation"
    )
    
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        db_index=True,
        help_text="Message role: user, assistant, or system"
    )
    
    content = models.TextField(
        help_text="Message content"
    )
    
    agent = models.ForeignKey(
        'Agent',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='messages',
        help_text="Agent that generated this message (assistant messages)"
    )
    
    llm_provider = models.ForeignKey(
        'LLMProvider',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='messages',
        help_text="LLM provider/model used for this message"
    )
    
    protegrity_data = models.JSONField(
        null=True,
        blank=True,
        help_text="""Protegrity processing metadata (PII detections, redactions, etc.)
        
        Schema for user messages (input protection):
        {
            "original_text": "raw user input",
            "processed_text": "text sent to LLM (redacted/protected)",
            "should_block": bool,
            "guardrails": {"outcome": "accepted"|"rejected", "risk_score": float, ...},
            "discovery": {"EMAIL": [{"entity_text": "...", "score": 0.99, ...}], ...},
            "redaction": {"success": bool, "method": "redact"},
            "mode": "redact"|"protect"
        }
        
        Schema for assistant messages (output protection):
        {
            "original_response": "raw LLM output",
            "processed_response": "text shown to user (redacted if needed)",
            "should_filter": bool,
            "guardrails": {"outcome": "accepted"|"rejected", "risk_score": float, ...},
            "discovery": {"EMAIL": [{...}], ...},
            "redaction": {"success": bool, "method": "redact"}
        }
        
        May also contain {"tool_results": [...]} for tool execution tracking.
        """
    )
    
    pending = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True if awaiting LLM response (for async models)"
    )
    
    blocked = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True if message was blocked by guardrails"
    )
    
    created_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="Message creation timestamp"
    )
    
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Soft delete timestamp"
    )
    
    class Meta:
        db_table = 'messages'
        ordering = ['created_at']
        indexes = [
            # Composite index for conversation messages query
            models.Index(
                fields=['conversation', 'created_at'],
                name='msg_conv_time_idx'
            ),
            # Index for LLM provider analytics/billing
            models.Index(
                fields=['llm_provider', 'created_at'],
                name='msg_llm_time_idx'
            ),
            # Index for agent analytics
            models.Index(
                fields=['agent', 'created_at'],
                name='msg_agent_time_idx'
            ),
        ]
    
    def __str__(self):
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"{self.role}: {content_preview}"


class LLMProvider(models.Model):
    """
    LLM (Large Language Model) providers and configurations.
    
    Design Notes:
    - Centralized configuration for all AI models
    - Enables/disables models without code changes
    - Tracks pricing, limits, and capabilities
    - Supports future multi-tenancy with per-user model access
    """
    
    PROVIDER_TYPES = [
        ('openai', 'OpenAI'),
        ('anthropic', 'Anthropic'),
        ('bedrock', 'Amazon Bedrock'),
        ('intercom', 'Intercom Fin'),
        ('azure', 'Azure OpenAI'),
        ('google', 'Google AI'),
        ('custom', 'Custom'),
    ]
    
    id = models.CharField(
        max_length=50,
        primary_key=True,
        help_text="Unique identifier (e.g., 'fin', 'bedrock-claude')"
    )
    
    name = models.CharField(
        max_length=100,
        help_text="Display name (e.g., 'Fin AI', 'Claude 3.5 Sonnet')"
    )
    
    provider_type = models.CharField(
        max_length=20,
        choices=PROVIDER_TYPES,
        help_text="Provider category"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Model description and capabilities"
    )
    
    model_identifier = models.CharField(
        max_length=200,
        blank=True,
        help_text="Provider-specific model ID (e.g., 'anthropic.claude-3-5-sonnet-v2')"
    )
    
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Enable/disable model for selection"
    )
    
    requires_polling = models.BooleanField(
        default=False,
        help_text="True for async models (Fin AI), False for sync (Bedrock)"
    )
    
    max_tokens = models.IntegerField(
        default=4096,
        help_text="Maximum context window size"
    )
    
    supports_streaming = models.BooleanField(
        default=False,
        help_text="Supports streaming responses"
    )
    
    cost_per_1k_input_tokens = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Pricing: USD per 1K input tokens"
    )
    
    cost_per_1k_output_tokens = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Pricing: USD per 1K output tokens"
    )
    
    configuration = models.JSONField(
        default=dict,
        blank=True,
        help_text="Model-specific config (API keys, endpoints, parameters)"
    )
    
    min_role = models.CharField(
        max_length=32,
        choices=ROLE_CHOICES,
        default="PROTEGRITY",
        db_index=True,
        help_text="Minimum user role required to see/use this model"
    )
    
    display_order = models.IntegerField(
        default=0,
        help_text="Sort order in UI (lower = higher priority)"
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'llm_providers'
        ordering = ['display_order', 'name']
        verbose_name = 'LLM Provider'
        verbose_name_plural = 'LLM Providers'
    
    def __str__(self):
        status = "✓" if self.is_active else "✗"
        return f"{status} {self.name} ({self.id})"


class Agent(models.Model):
    """
    AI agents with specific capabilities and tool access.
    
    Design Notes:
    - Agents are pre-configured AI assistants with specific roles
    - Can use multiple LLM providers
    - Have access to specific tools
    - System prompts define behavior and personality
    """
    
    id = models.CharField(
        max_length=50,
        primary_key=True,
        help_text="Unique identifier (e.g., 'data-protection-expert')"
    )
    
    name = models.CharField(
        max_length=100,
        help_text="Display name (e.g., 'Data Protection Expert')"
    )
    
    description = models.TextField(
        help_text="Agent purpose and capabilities"
    )
    
    system_prompt = models.TextField(
        help_text="Base system instructions for the agent"
    )
    
    default_llm = models.ForeignKey(
        LLMProvider,
        on_delete=models.SET_NULL,
        null=True,
        related_name='default_for_agents',
        help_text="Default LLM for this agent"
    )
    
    allowed_llms = models.ManyToManyField(
        LLMProvider,
        blank=True,
        related_name='agents',
        help_text="LLMs this agent can use"
    )
    
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Enable/disable agent"
    )
    
    min_role = models.CharField(
        max_length=32,
        choices=ROLE_CHOICES,
        default="PROTEGRITY",
        db_index=True,
        help_text="Minimum user role required to see/use this agent"
    )
    
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text="Icon identifier for UI"
    )
    
    color = models.CharField(
        max_length=7,
        default='#FA5A25',
        help_text="Hex color for UI theme"
    )
    
    display_order = models.IntegerField(
        default=0,
        help_text="Sort order in UI"
    )
    
    configuration = models.JSONField(
        default=dict,
        blank=True,
        help_text="Agent-specific settings (temperature, max_tokens, etc.)"
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'agents'
        ordering = ['display_order', 'name']
    
    def __str__(self):
        status = "✓" if self.is_active else "✗"
        return f"{status} {self.name}"


class Tool(models.Model):
    """
    External tools/APIs that agents can access.
    
    Design Notes:
    - Function calling / tool use capabilities
    - Protegrity data protection tools
    - External API integrations
    - Per-tool permissions and rate limits
    """
    
    TOOL_TYPES = [
        ('protegrity', 'Protegrity Data Protection'),
        ('api', 'External API'),
        ('function', 'Function Call'),
        ('database', 'Database Query'),
        ('search', 'Search/Retrieval'),
        ('custom', 'Custom Tool'),
    ]
    
    id = models.CharField(
        max_length=50,
        primary_key=True,
        help_text="Unique identifier (e.g., 'protegrity-redact')"
    )
    
    name = models.CharField(
        max_length=100,
        help_text="Display name"
    )
    
    tool_type = models.CharField(
        max_length=20,
        choices=TOOL_TYPES,
        help_text="Tool category"
    )
    
    description = models.TextField(
        help_text="What this tool does"
    )
    
    function_schema = models.JSONField(
        default=dict,
        help_text="OpenAI function calling schema / tool definition"
    )
    
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Enable/disable tool"
    )
    
    min_role = models.CharField(
        max_length=32,
        choices=ROLE_CHOICES,
        default="PROTEGRITY",
        db_index=True,
        help_text="Minimum user role required to see/use this tool"
    )
    
    requires_auth = models.BooleanField(
        default=True,
        help_text="Requires API key or authentication"
    )
    
    configuration = models.JSONField(
        default=dict,
        blank=True,
        help_text="Tool-specific config (API endpoints, credentials, etc.)"
    )
    
    agents = models.ManyToManyField(
        Agent,
        blank=True,
        related_name='tools',
        help_text="Agents that can use this tool"
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tools'
        ordering = ['name']
    
    def __str__(self):
        status = "✓" if self.is_active else "✗"
        return f"{status} {self.name} ({self.tool_type})"


class ApiKey(models.Model):
    """
    API keys for programmatic access to the chat API.
    
    Design Notes:
    - Per-user API keys with role-based access control
    - Keys are hashed using Django's password hashers (never stored plaintext)
    - Prefix stored for efficient lookup (first 8 chars)
    - Full key shown only once at creation time
    - Revocable via is_active flag
    - Expiration support for time-limited keys
    - last_used_at for audit and key rotation policies
    - Scopes for future granular permissions
    
    Security:
    - Uses make_password/check_password (same as Django User passwords)
    - Prefix index allows fast lookup without exposing full key
    - No plaintext keys ever touch the database
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique key identifier"
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="api_keys",
        help_text="Key owner - inherits their role and permissions"
    )
    
    name = models.CharField(
        max_length=100,
        help_text="Human-readable label for this key (e.g., 'Production Server')"
    )
    
    prefix = models.CharField(
        max_length=16,
        db_index=True,
        help_text="First 8 chars of key for fast lookup"
    )
    
    hashed_key = models.CharField(
        max_length=128,
        help_text="Hashed full key (never store plaintext)"
    )
    
    scopes = models.JSONField(
        default=list,
        blank=True,
        help_text="List of scopes, e.g. ['chat', 'models'] - for future use"
    )
    
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Revoke key by setting to False"
    )
    
    created_at = models.DateTimeField(
        default=timezone.now,
        help_text="Key creation timestamp"
    )
    
    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last successful authentication with this key"
    )
    
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Optional expiration date"
    )
    
    class Meta:
        db_table = 'api_keys'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['prefix', 'is_active'], name='apikey_lookup_idx'),
        ]
    
    def __str__(self):
        status = "✓" if self.is_active else "✗"
        return f"{status} {self.name} ({self.prefix}...)"
    
    @staticmethod
    def generate_key() -> str:
        """
        Generate a cryptographically secure random API key.
        
        Returns:
            String of 43 URL-safe characters (32 bytes base64-encoded)
        """
        return secrets.token_urlsafe(32)
    
    @classmethod
    def create_for_user(cls, user, name="API Key", scopes=None):
        """
        Create a new API key for a user.
        
        Args:
            user: Django User instance
            name: Human-readable key name
            scopes: List of permission scopes (default: ['chat'])
        
        Returns:
            Tuple of (ApiKey instance, raw_key_string)
            Raw key is returned ONLY here and never stored
        """
        raw_key = cls.generate_key()
        prefix = raw_key[:8]
        
        api_key = cls.objects.create(
            user=user,
            name=name,
            prefix=prefix,
            hashed_key=make_password(raw_key),
            scopes=scopes or ["chat"],
        )
        
        return api_key, raw_key
    
    def check_key(self, raw_key: str) -> bool:
        """
        Verify a raw key against the stored hash.
        
        Args:
            raw_key: The full API key to check
        
        Returns:
            True if key matches, False otherwise
        """
        return check_password(raw_key, self.hashed_key)
