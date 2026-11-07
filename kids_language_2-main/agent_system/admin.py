from django.contrib import admin
from .models import (
    Conversation,
    LongTermMemory,
    AiMood,
    Message,
    PresetObjectIdentification,
    AgentSystemPrompt,
)

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    """Conversationadmin."""
    list_display = ['user', 'device_id', 'object_name', 'object_identification', 'island_type', 'is_active', 'created_at']
    list_filter = ['is_active', 'island_type', 'created_at']
    search_fields = ['user__username', 'device_id', 'object_name', 'object_identification']
    readonly_fields = ['id', 'created_at']

@admin.register(LongTermMemory)
class LongTermMemoryAdmin(admin.ModelAdmin):
    """Longtermmemoryadmin."""
    list_display = ['user', 'device_id', 'object_name', 'object_identification', 'island_type', 'conversation_num', 'created_at']
    list_filter = ['island_type', 'created_at']
    search_fields = ['user__username', 'device_id', 'object_name', 'object_identification']
    readonly_fields = ['id', 'created_at']

@admin.register(AiMood)
class AiMoodAdmin(admin.ModelAdmin):
    """Aimoodadmin."""
    list_display = ['mood', 'description_preview']
    search_fields = ['mood', 'description']
    
    def description_preview(self, obj):
        """Description preview."""
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_preview.short_description = '描述预览'

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Messageadmin."""
    list_display = ['user', 'conversation', 'sender', 'message_preview', 'mood_id', 'created_at']
    list_filter = ['sender', 'created_at', 'mood_id']
    search_fields = ['user__username', 'message', 'device_id']
    readonly_fields = ['id', 'created_at']
    
    def message_preview(self, obj):
        """Message preview."""
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = '消息预览'

@admin.register(PresetObjectIdentification)
class PresetObjectIdentificationAdmin(admin.ModelAdmin):
    """Presetobjectidentificationadmin."""
    list_display = ['island_type', 'object_name', 'object_identification', 'description_preview']
    list_filter = ['island_type']
    search_fields = ['island_type', 'object_name', 'object_identification', 'description']
    
    def description_preview(self, obj):
        """Description preview."""
        if obj.description:
            return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
        return '-'
    description_preview.short_description = '描述预览'

@admin.register(AgentSystemPrompt)
class AgentSystemPromptAdmin(admin.ModelAdmin):
    """Agentsystempromptadmin."""
    list_display = ['island_type', 'created_at', 'updated_at']
    search_fields = ['island_type']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = (
        ('基本信息', {
            'fields': ('island_type',)
        }),
        ('提示词配置', {
            'fields': ('system_prompt_1', 'system_prompt_2', 'system_prompt_3', 'system_prompt_4'),
            'classes': ('wide',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
        }),
    )
