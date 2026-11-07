"""Models."""
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
import uuid

class UserManager(BaseUserManager):
    """Usermanager."""
    
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('用户名必须提供')
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username, password, **extra_fields)

class User(AbstractUser):
    """User."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device_id = models.CharField(max_length=100, unique=True, db_index=True, null=True, blank=True)
    chapter_type = models.CharField(max_length=20, db_index=True, blank=True, null=True)
    device_battery = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()
    
    class Meta:
        db_table = 'user'
        indexes = [
            models.Index(fields=['device_id']),
            models.Index(fields=['chapter_type']),
        ]
        verbose_name = '用户'
        verbose_name_plural = '用户'
    
    def __str__(self):
        return f"{self.username} ({self.device_id or 'No Device'})"

class Dictionary(models.Model):
    """Dictionary."""
    id = models.BigAutoField(primary_key=True)
    dict_name = models.CharField(max_length=100, db_index=True)
    dict_num = models.IntegerField(default=0)
    cover_url = models.CharField(max_length=500, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    chapter_num = models.IntegerField(default=0)
    updated_time = models.DateTimeField(auto_now=True)
    created_time = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'dictionaries'
        indexes = [
            models.Index(fields=['dict_name']),
        ]
        verbose_name = '词典'
        verbose_name_plural = '词典'
    
    def __str__(self):
        return self.dict_name

class Word(models.Model):
    """Word."""
    id = models.BigAutoField(primary_key=True)
    words = models.CharField(max_length=100, unique=True, db_index=True)
    created_time = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'words'
        verbose_name = '单词'
        verbose_name_plural = '单词'
    
    def __str__(self):
        return self.words

class WordMeaning(models.Model):
    """Wordmeaning."""
    id = models.BigAutoField(primary_key=True)
    word = models.ForeignKey(Word, on_delete=models.CASCADE, related_name='meanings')
    part_of_speech = models.CharField(max_length=20)
    inner_id = models.SmallIntegerField()
    chinese_translation = models.TextField()
    created_time = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'words_meanings'
        unique_together = ['word', 'part_of_speech', 'inner_id']
        indexes = [
            models.Index(fields=['word']),
        ]
        verbose_name = '单词释义'
        verbose_name_plural = '单词释义'
    
    def __str__(self):
        return f"{self.word.words} - {self.part_of_speech} - {self.chinese_translation}"

class DictWordMeaning(models.Model):
    """Dictwordmeaning."""
    id = models.BigAutoField(primary_key=True)
    dictionary = models.ForeignKey(Dictionary, on_delete=models.CASCADE, related_name='word_meanings')
    word = models.ForeignKey(Word, on_delete=models.CASCADE)
    meaning = models.ForeignKey(WordMeaning, on_delete=models.CASCADE)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'dict_word_meanings'
        unique_together = ['dictionary', 'word', 'meaning']
        indexes = [
            models.Index(fields=['dictionary']),
            models.Index(fields=['word']),
            models.Index(fields=['dictionary', 'sort_order']),
        ]
        verbose_name = '词典单词映射'
        verbose_name_plural = '词典单词映射'
    
    def __str__(self):
        return f"{self.dictionary.dict_name} - {self.word.words}"

class DictChapter(models.Model):
    """Dictchapter."""
    id = models.BigAutoField(primary_key=True)
    dictionary = models.ForeignKey(Dictionary, on_delete=models.CASCADE, related_name='chapters')
    dict_word_meaning = models.ForeignKey(DictWordMeaning, on_delete=models.CASCADE, related_name='chapter_entries')
    chapter_inner_id = models.IntegerField(db_index=True)
    created_time = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'dict_chapter'
        indexes = [
            models.Index(fields=['dictionary']),
            models.Index(fields=['dict_word_meaning']),
            models.Index(fields=['chapter_inner_id']),
            models.Index(fields=['dictionary', 'chapter_inner_id']),
        ]
        verbose_name = '词典章节'
        verbose_name_plural = '词典章节'
    
    def __str__(self):
        return f"{self.dictionary.dict_name} - 章节{self.chapter_inner_id}"

class UserStudyPlan(models.Model):
    """Userstudyplan."""
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='study_plans')
    dictionary = models.ForeignKey(Dictionary, on_delete=models.CASCADE)
    chapter_inner_id = models.IntegerField(db_index=True, default=1)
    is_activated = models.BooleanField(default=False, db_index=True)
    is_locked = models.BooleanField(default=True)
    learned_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_study_plan'
        unique_together = ['user', 'dictionary', 'chapter_inner_id']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['dictionary']),
            models.Index(fields=['chapter_inner_id']),
            models.Index(fields=['is_activated']),
            models.Index(fields=['is_locked']),
            models.Index(fields=['user', 'dictionary']),
        ]
        verbose_name = '用户学习计划'
        verbose_name_plural = '用户学习计划'
    
    def __str__(self):
        return f"{self.user.username} - {self.dictionary.dict_name} - 章节{self.chapter_inner_id}"

class UserOngoingPlan(models.Model):
    """Userongoingplan."""
    
    LEARNED_TYPE_CHOICES = [
        ('not_started', '未开始'),
        ('learning', '学习中'),
        ('review_due', '待复习'),
        ('mastered', '已掌握'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ongoing_words')
    plan = models.ForeignKey(UserStudyPlan, on_delete=models.CASCADE, related_name='words')
    dict_chapter = models.ForeignKey('DictChapter', on_delete=models.SET_NULL, null=True, blank=True, related_name='ongoing_words')
    words = models.CharField(max_length=100, db_index=True)
    part_of_speech = models.CharField(max_length=20)
    chinese_translation = models.TextField()
    learned_type = models.CharField(
        max_length=20, choices=LEARNED_TYPE_CHOICES, default='not_started', db_index=True
    )
    is_frozen = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_ongoing_plan'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['plan']),
            models.Index(fields=['dict_chapter']),
            models.Index(fields=['learned_type']),
            models.Index(fields=['is_frozen']),
            models.Index(fields=['words']),
        ]
        verbose_name = '用户学习计划详情'
        verbose_name_plural = '用户学习计划详情'
    
    def __str__(self):
        return f"{self.user.username} - {self.words}"
