"""
Django admin configuration for conversations and messages.

Admin Features:
- Read-only fields for auto-generated values
- Inline message editing within conversations
- Soft delete actions
- Search and filtering capabilities
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from .models import Conversation, Message, LLMProvider, Agent, Tool, UserProfile


class MessageInline(admin.TabularInline):
    """Inline display of messages within conversation admin."""
    model = Message
    extra = 0
    fields = ('role', 'content_preview', 'pending', 'blocked', 'created_at')
    readonly_fields = ('content_preview', 'created_at')
    can_delete = False
    
    def content_preview(self, obj):
        """Show truncated message content."""
        if obj.content:
            preview = obj.content[:100] + "..." if len(obj.content) > 100 else obj.content
            return format_html('<span style="white-space: pre-wrap;">{}</span>', preview)
        return "-"
    content_preview.short_description = "Content"


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    """Admin interface for Conversation model."""
    
    list_display = ('title', 'model_id', 'message_count', 'created_at', 'updated_at', 'is_deleted')
    list_filter = ('model_id', 'created_at', 'deleted_at')
    search_fields = ('title', 'id')
    readonly_fields = ('id', 'created_at', 'updated_at', 'message_count')
    inlines = [MessageInline]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'title', 'model_id')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('message_count',)
        }),
    )
    
    def message_count(self, obj):
        """Count non-deleted messages."""
        return obj.messages.filter(deleted_at__isnull=True).count()
    message_count.short_description = "Messages"
    
    def is_deleted(self, obj):
        """Show deletion status."""
        if obj.deleted_at:
            return format_html('<span style="color: red;">✗ Deleted</span>')
        return format_html('<span style="color: green;">✓ Active</span>')
    is_deleted.short_description = "Status"
    
    actions = ['soft_delete_selected', 'restore_selected']
    
    def soft_delete_selected(self, request, queryset):
        """Soft delete selected conversations."""
        count = 0
        for conversation in queryset:
            if not conversation.deleted_at:
                conversation.soft_delete()
                count += 1
        self.message_user(request, f"Soft deleted {count} conversation(s).")
    soft_delete_selected.short_description = "Soft delete selected conversations"
    
    def restore_selected(self, request, queryset):
        """Restore soft-deleted conversations."""
        count = queryset.filter(deleted_at__isnull=False).update(deleted_at=None)
        self.message_user(request, f"Restored {count} conversation(s).")
    restore_selected.short_description = "Restore selected conversations"


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Admin interface for Message model."""
    
    list_display = ('short_content', 'role', 'conversation_link', 'pending', 'blocked', 'created_at')
    list_filter = ('role', 'pending', 'blocked', 'created_at')
    search_fields = ('content', 'conversation__title', 'conversation__id')
    readonly_fields = ('id', 'created_at', 'conversation_link')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Message', {
            'fields': ('id', 'conversation_link', 'role', 'content')
        }),
        ('Status', {
            'fields': ('pending', 'blocked', 'deleted_at')
        }),
        ('Metadata', {
            'fields': ('protegrity_data',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def short_content(self, obj):
        """Show truncated content."""
        return obj.content[:75] + "..." if len(obj.content) > 75 else obj.content
    short_content.short_description = "Content"
    
    def conversation_link(self, obj):
        """Link to parent conversation."""
        if obj.conversation:
            url = f'/admin/core/conversation/{obj.conversation.id}/change/'
            return format_html('<a href="{}">{}</a>', url, obj.conversation.title)
        return "-"
    conversation_link.short_description = "Conversation"


@admin.register(LLMProvider)
class LLMProviderAdmin(admin.ModelAdmin):
    """Admin interface for LLM Provider management."""
    
    list_display = ('status_icon', 'name', 'provider_type', 'model_identifier', 'requires_polling', 'cost_display', 'display_order')
    list_filter = ('is_active', 'provider_type', 'requires_polling', 'supports_streaming')
    search_fields = ('name', 'id', 'description')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('display_order',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'provider_type', 'description')
        }),
        ('Model Configuration', {
            'fields': ('model_identifier', 'is_active', 'requires_polling', 'supports_streaming', 'max_tokens')
        }),
        ('Pricing', {
            'fields': ('cost_per_1k_input_tokens', 'cost_per_1k_output_tokens'),
            'classes': ('collapse',)
        }),
        ('Advanced', {
            'fields': ('configuration', 'display_order'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_icon(self, obj):
        """Visual status indicator."""
        if obj.is_active:
            return format_html('<span style="color: green; font-size: 16px;">●</span>')
        return format_html('<span style="color: red; font-size: 16px;">○</span>')
    status_icon.short_description = ""
    
    def cost_display(self, obj):
        """Display pricing info."""
        if obj.cost_per_1k_input_tokens and obj.cost_per_1k_output_tokens:
            return f"${obj.cost_per_1k_input_tokens}/{obj.cost_per_1k_output_tokens} per 1K"
        return "N/A"
    cost_display.short_description = "Cost (In/Out)"
    
    actions = ['activate_selected', 'deactivate_selected']
    
    def activate_selected(self, request, queryset):
        """Activate selected LLM providers."""
        count = queryset.update(is_active=True)
        self.message_user(request, f"Activated {count} LLM provider(s).")
    activate_selected.short_description = "✓ Activate selected providers"
    
    def deactivate_selected(self, request, queryset):
        """Deactivate selected LLM providers."""
        count = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {count} LLM provider(s).")
    deactivate_selected.short_description = "✗ Deactivate selected providers"


class ToolInline(admin.TabularInline):
    """Inline display of tools for agents."""
    model = Tool.agents.through
    extra = 1
    verbose_name = "Tool Access"
    verbose_name_plural = "Tool Access"


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    """Admin interface for Agent management."""
    
    list_display = ('status_icon', 'name', 'default_llm', 'tool_count', 'display_order')
    list_filter = ('is_active', 'default_llm')
    search_fields = ('name', 'id', 'description')
    readonly_fields = ('created_at', 'updated_at', 'tool_count')
    list_editable = ('display_order',)
    filter_horizontal = ('allowed_llms',)
    inlines = [ToolInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'description', 'is_active')
        }),
        ('LLM Configuration', {
            'fields': ('default_llm', 'allowed_llms')
        }),
        ('Behavior', {
            'fields': ('system_prompt',)
        }),
        ('UI Settings', {
            'fields': ('icon', 'color', 'display_order'),
            'classes': ('collapse',)
        }),
        ('Advanced', {
            'fields': ('configuration',),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('tool_count',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_icon(self, obj):
        """Visual status indicator."""
        if obj.is_active:
            return format_html('<span style="color: green; font-size: 16px;">●</span>')
        return format_html('<span style="color: red; font-size: 16px;">○</span>')
    status_icon.short_description = ""
    
    def tool_count(self, obj):
        """Count tools available to agent."""
        return obj.tools.filter(is_active=True).count()
    tool_count.short_description = "Active Tools"
    
    actions = ['activate_selected', 'deactivate_selected']
    
    def activate_selected(self, request, queryset):
        """Activate selected agents."""
        count = queryset.update(is_active=True)
        self.message_user(request, f"Activated {count} agent(s).")
    activate_selected.short_description = "✓ Activate selected agents"
    
    def deactivate_selected(self, request, queryset):
        """Deactivate selected agents."""
        count = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {count} agent(s).")
    deactivate_selected.short_description = "✗ Deactivate selected agents"


@admin.register(Tool)
class ToolAdmin(admin.ModelAdmin):
    """Admin interface for Tool management."""
    
    list_display = ('status_icon', 'name', 'tool_type', 'requires_auth', 'agent_count')
    list_filter = ('is_active', 'tool_type', 'requires_auth')
    search_fields = ('name', 'id', 'description')
    readonly_fields = ('created_at', 'updated_at', 'agent_count')
    filter_horizontal = ('agents',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'tool_type', 'description', 'is_active')
        }),
        ('Function Definition', {
            'fields': ('function_schema',)
        }),
        ('Security', {
            'fields': ('requires_auth',)
        }),
        ('Agent Access', {
            'fields': ('agents',)
        }),
        ('Configuration', {
            'fields': ('configuration',),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('agent_count',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_icon(self, obj):
        """Visual status indicator."""
        if obj.is_active:
            return format_html('<span style="color: green; font-size: 16px;">●</span>')
        return format_html('<span style="color: red; font-size: 16px;">○</span>')
    status_icon.short_description = ""
    
    def agent_count(self, obj):
        """Count agents using this tool."""
        return obj.agents.filter(is_active=True).count()
    agent_count.short_description = "Active Agents"
    
    actions = ['activate_selected', 'deactivate_selected']
    
    def activate_selected(self, request, queryset):
        """Activate selected tools."""
        count = queryset.update(is_active=True)
        self.message_user(request, f"Activated {count} tool(s).")
    activate_selected.short_description = "✓ Activate selected tools"
    
    def deactivate_selected(self, request, queryset):
        """Deactivate selected tools."""
        count = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {count} tool(s).")
    deactivate_selected.short_description = "✗ Deactivate selected tools"


# User Profile Inline for User Admin
class UserProfileInline(admin.StackedInline):
    """Inline display of UserProfile within User admin."""
    model = UserProfile
    can_delete = False
    verbose_name = "User Profile"
    verbose_name_plural = "User Profile"
    fields = ('role_display',)
    readonly_fields = ('role_display',)
    
    def role_display(self, obj):
        """Display user's role based on group membership."""
        user = obj.user
        if user.groups.filter(name="Protegrity Users").exists():
            return format_html('<strong style="color: green;">PROTEGRITY</strong> (Full Access)')
        elif user.groups.filter(name="Standard Users").exists():
            return format_html('<strong style="color: blue;">STANDARD</strong> (Limited Access)')
        return format_html('<em style="color: gray;">No Role Assigned</em>')
    role_display.short_description = "Access Role (via Groups)"


# Extend the default User admin to include UserProfile inline
class CustomUserAdmin(BaseUserAdmin):
    """Extended User admin with UserProfile inline and group-based role display."""
    inlines = (UserProfileInline,)
    
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_role', 'get_groups')
    list_filter = BaseUserAdmin.list_filter + ('groups',)
    
    def get_role(self, obj):
        """Display user's role from group membership."""
        if obj.groups.filter(name="Protegrity Users").exists():
            return "PROTEGRITY"
        elif obj.groups.filter(name="Standard Users").exists():
            return "STANDARD"
        return "None"
    get_role.short_description = "Role"
    
    def get_groups(self, obj):
        """Display user's groups."""
        groups = obj.groups.all()
        if groups:
            return ", ".join(g.name for g in groups)
        return "-"
    get_groups.short_description = "Groups"


# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
