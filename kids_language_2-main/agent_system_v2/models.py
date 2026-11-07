"""Models."""
from django.db import models
from user_system.models import User

class Conversation(models.Model):
    """Conversation."""
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations_v2')
    device_id = models.CharField(max_length=100, db_index=True)
    object_name = models.CharField(max_length=100, db_index=True)
    object_identification = models.CharField(max_length=100, blank=True, null=True)
    object_description = models.TextField(blank=True, null=True)
    object_identification_english = models.CharField(max_length=100, blank=True, null=True)
    description_english = models.TextField(blank=True, null=True)
    object_persona = models.IntegerField(blank=True, null=True)

    chapter_type = models.CharField(max_length=20, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    meet_count = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'conversations'
        indexes = [
            models.Index(fields=['user'], name='v2_conv_user_idx'),
            models.Index(fields=['device_id'], name='v2_conv_device_idx'),
            models.Index(fields=['object_name'], name='v2_conv_objname_idx'),
            models.Index(fields=['is_active'], name='v2_conv_active_idx'),
            models.Index(fields=['chapter_type'], name='v2_conv_chapter_idx'),
        ]
        verbose_name = '对话会话'
        verbose_name_plural = '对话会话'

    def __str__(self):
        return f"{self.user.username} - {self.object_name} ({self.device_id})"

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
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages_v2')
    device_id = models.CharField(max_length=100)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES, db_index=True)
    message = models.TextField()
    words_used_id = models.JSONField(blank=True, null=True)
    mood_id = models.ForeignKey(
        AiMood, on_delete=models.SET_NULL, null=True, blank=True,
        db_index=True, db_column='mood_id'
    )
    meet_count = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'messages'
        indexes = [
            models.Index(fields=['conversation'], name='v2_msg_conv_idx'),
            models.Index(fields=['user'], name='v2_msg_user_idx'),
            models.Index(fields=['sender'], name='v2_msg_sender_idx'),
            models.Index(fields=['created_at'], name='v2_msg_created_idx'),
            models.Index(fields=['mood_id'], name='v2_msg_mood_idx'),
        ]
        verbose_name = '消息'
        verbose_name_plural = '消息'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender} - {self.message[:50]}..."

class PresetObjectIdentification(models.Model):
    """Presetobjectidentification."""
    id = models.BigAutoField(primary_key=True)
    chapter_type = models.CharField(max_length=20, db_index=True)
    object_name = models.CharField(max_length=100, db_index=True)
    object_identification = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    object_identification_english = models.CharField(max_length=100, blank=True, null=True)
    description_english = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'preset_object_identification'
        unique_together = ['chapter_type', 'object_name']
        indexes = [
            models.Index(fields=['chapter_type'], name='v2_preset_chapter_idx'),
            models.Index(fields=['object_name'], name='v2_preset_objname_idx'),
        ]
        verbose_name = '预设物体身份'
        verbose_name_plural = '预设物体身份'

    def __str__(self):
        return f"{self.chapter_type} - {self.object_name} -> {self.object_identification}"

class AgentSystemPrompt(models.Model):
    """Agentsystemprompt."""
    id = models.BigAutoField(primary_key=True)
    chapter_name = models.CharField(max_length=20, unique=True)
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
        return f"{self.chapter_name} - 系统提示词配置"

class LongtermMemory(models.Model):
    """Longtermmemory."""
    ENGLISH_LEVEL_CHOICES = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D'),
    ]

    id = models.BigAutoField(primary_key=True)
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name='longterm_memories'
    )
    personality_traits = models.JSONField(blank=True, null=True)
    interest_topics = models.JSONField(blank=True, null=True)
    motivation_triggers = models.JSONField(blank=True, null=True)
    english_level = models.CharField(
        max_length=1, choices=ENGLISH_LEVEL_CHOICES, blank=True, null=True
    )
    updated_time = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'longterm_memories'
        indexes = [
            models.Index(fields=['conversation'], name='v2_ltmem_conv_idx'),
        ]
        verbose_name = '长期记忆'
        verbose_name_plural = '长期记忆'

    def __str__(self):
        return f"Memory for conversation {self.conversation_id}"

class WordsMastery(models.Model):
    """Wordsmastery."""
    id = models.BigAutoField(primary_key=True)
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name='words_mastery'
    )
    cognition = models.FloatField(default=0.0)
    usage = models.FloatField(default=0.0)
    fluency = models.FloatField(default=0.0)
    mastery = models.FloatField(default=0.0)
    confidence = models.FloatField(default=0.0)
    is_passed = models.BooleanField(default=False)
    meet_count = models.BigIntegerField(default=0)
    created_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'words_mastery'
        indexes = [
            models.Index(fields=['conversation'], name='v2_wm_conv_idx'),
            models.Index(fields=['is_passed'], name='v2_wm_passed_idx'),
        ]
        verbose_name = '单词掌握度'
        verbose_name_plural = '单词掌握度'

    def __str__(self):
        return f"Mastery for conversation {self.conversation_id} (mastery={self.mastery})"
