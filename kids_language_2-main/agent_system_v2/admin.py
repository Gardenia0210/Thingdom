from django.contrib import admin
from .models import (
    Conversation,
    AiMood,
    Message,
    PresetObjectIdentification,
    AgentSystemPrompt,
    LongtermMemory,
    WordsMastery,
)

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    """Conversationadmin."""
    list_display = ['user', 'device_id', 'object_name', 'object_identification', 'object_identification_english', 'object_persona', 'chapter_type', 'is_active', 'meet_count', 'created_at', 'updated_at']
    list_filter = ['is_active', 'chapter_type', 'created_at']
    search_fields = ['user__username', 'device_id', 'object_name', 'object_identification', 'object_identification_english']
    readonly_fields = ['id', 'created_at', 'updated_at']

@admin.register(AiMood)
class AiMoodAdmin(admin.ModelAdmin):
    """Aimoodadmin."""
    list_display = ['mood', 'description_preview']
    search_fields = ['mood', 'description']

    def description_preview(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_preview.short_description = '描述预览'

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Messageadmin."""
    list_display = ['user', 'conversation', 'sender', 'message_preview', 'mood_id', 'meet_count', 'created_at']
    list_filter = ['sender', 'created_at', 'mood_id']
    search_fields = ['user__username', 'message', 'device_id']
    readonly_fields = ['id', 'created_at']

    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = '消息预览'

@admin.register(PresetObjectIdentification)
class PresetObjectIdentificationAdmin(admin.ModelAdmin):
    """Presetobjectidentificationadmin."""
    list_display = ['chapter_type', 'object_name', 'object_identification_english', 'object_identification', 'description_preview']
    list_filter = ['chapter_type']
    search_fields = ['chapter_type', 'object_name', 'object_identification_english', 'object_identification', 'description']

    def description_preview(self, obj):
        if obj.description:
            return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
        return '-'
    description_preview.short_description = '描述预览'

@admin.register(AgentSystemPrompt)
class AgentSystemPromptAdmin(admin.ModelAdmin):
    """Agentsystempromptadmin."""
    list_display = ['chapter_name', 'created_at', 'updated_at']
    search_fields = ['chapter_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = (
        ('基本信息', {
            'fields': ('chapter_name',)
        }),
        ('提示词配置', {
            'fields': ('system_prompt_1', 'system_prompt_2', 'system_prompt_3', 'system_prompt_4'),
            'classes': ('wide',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
        }),
    )

@admin.register(LongtermMemory)
class LongtermMemoryAdmin(admin.ModelAdmin):
    """Longtermmemoryadmin."""
    list_display = ['conversation', 'english_level', 'updated_time']
    list_filter = ['english_level']
    search_fields = ['conversation__user__username']
    readonly_fields = ['id', 'updated_time']

@admin.register(WordsMastery)
class WordsMasteryAdmin(admin.ModelAdmin):
    """Wordsmasteryadmin."""
    list_display = ['conversation', 'cognition', 'usage', 'fluency', 'mastery', 'confidence', 'is_passed', 'meet_count', 'created_time']
    list_filter = ['is_passed', 'created_time']
    search_fields = ['conversation__user__username']
    readonly_fields = ['id', 'created_time']
