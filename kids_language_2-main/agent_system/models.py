"""Models."""
from django.db import models
from user_system.models import User

class Conversation(models.Model):
    """Conversation."""
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
    device_id = models.CharField(max_length=100, db_index=True)
    object_name = models.CharField(max_length=100, db_index=True)
    object_identification = models.CharField(max_length=100, blank=True, null=True)
    conversation_summary = models.TextField(blank=True, null=True)
    island_type = models.CharField(max_length=20, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'conversations'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['device_id']),
            models.Index(fields=['object_name']),
            models.Index(fields=['is_active']),
            models.Index(fields=['island_type']),
        ]
        verbose_name = '对话会话'
        verbose_name_plural = '对话会话'
    
    def __str__(self):
        return f"{self.user.username} - {self.object_name} ({self.device_id})"

class LongTermMemory(models.Model):
    """Longtermmemory."""
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memories')
    device_id = models.CharField(max_length=100, db_index=True)
    object_name = models.CharField(max_length=100)
    object_identification = models.CharField(max_length=100, blank=True, null=True)
    island_type = models.CharField(max_length=20)
    conversation_num = models.IntegerField(default=1)
    last_conversation_summary = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'long_term_memory'
        unique_together = ['user', 'device_id', 'island_type', 'object_name']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['device_id']),
            models.Index(fields=['user', 'device_id', 'island_type', 'object_name']),
        ]
        verbose_name = '长期记忆'
        verbose_name_plural = '长期记忆'
    
    def __str__(self):
        return f"{self.user.username} - {self.object_name} ({self.island_type})"

class AiMood(models.Model):
    """Aimood."""
    id = models.BigAutoField(primary_key=True)
    mood = models.CharField(max_length=50, unique=True, db_index=True)
    description = models.TextField()
    
    class Meta:
        db_table = 'ai_mood'
        verbose_name = 'AI心情'
        verbose_name_plural = 'AI心情'
    
    def __str__(self):
        return f"{self.mood} - {self.description}"

class Message(models.Model):
    """Message."""
    SENDER_CHOICES = [
        ('ai', 'AI'),
        ('human', 'Human'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages')
    device_id = models.CharField(max_length=100)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES, db_index=True)
    message = models.TextField()
    words_used = models.JSONField(blank=True, null=True)
    mood_id = models.ForeignKey(AiMood, on_delete=models.SET_NULL, null=True, blank=True, db_index=True, db_column='mood_id')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'messages'
        indexes = [
            models.Index(fields=['conversation']),
            models.Index(fields=['user']),
            models.Index(fields=['sender']),
            models.Index(fields=['created_at']),
            models.Index(fields=['mood_id']),
        ]
        verbose_name = '消息'
        verbose_name_plural = '消息'
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.sender} - {self.message[:50]}..."

class PresetObjectIdentification(models.Model):
    """Presetobjectidentification."""
    id = models.BigAutoField(primary_key=True)
    island_type = models.CharField(max_length=20, db_index=True)
    object_name = models.CharField(max_length=100, db_index=True)
    object_identification = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'preset_object_identification'
        unique_together = ['island_type', 'object_name']
        indexes = [
            models.Index(fields=['island_type']),
            models.Index(fields=['object_name']),
        ]
        verbose_name = '预设物体身份'
        verbose_name_plural = '预设物体身份'
    
    def __str__(self):
        return f"{self.island_type} - {self.object_name} -> {self.object_identification}"

class AgentSystemPrompt(models.Model):
    """Agentsystemprompt."""
    id = models.BigAutoField(primary_key=True)
    island_type = models.CharField(max_length=20, unique=True)
    system_prompt_1 = models.TextField(blank=True, null=True)
    system_prompt_2 = models.TextField(blank=True, null=True)
    system_prompt_3 = models.TextField(blank=True, null=True)
    system_prompt_4 = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'agent_system_prompt'
        verbose_name = 'Agent 系统提示词'
        verbose_name_plural = 'Agent 系统提示词'
    
    def __str__(self):
        return f"{self.island_type} - 系统提示词配置"
