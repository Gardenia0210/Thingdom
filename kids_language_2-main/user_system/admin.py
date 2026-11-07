from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User,
    Dictionary,
    Word,
    WordMeaning,
    DictWordMeaning,
    DictChapter,
    UserStudyPlan,
    UserOngoingPlan,
)

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Useradmin."""
    list_display = ['username', 'device_id', 'chapter_type', 'is_active', 'created_at']
    list_filter = ['is_active', 'chapter_type', 'created_at']
    search_fields = ['username', 'device_id', 'email']
    readonly_fields = ['id', 'created_at', 'date_joined', 'last_login']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('扩展信息', {
            'fields': ('device_id', 'chapter_type', 'created_at')
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('扩展信息', {
            'fields': ('device_id', 'chapter_type')
        }),
    )

@admin.register(Dictionary)
class DictionaryAdmin(admin.ModelAdmin):
    """Dictionaryadmin."""
    list_display = ['dict_name', 'dict_num', 'chapter_num', 'created_time', 'updated_time']
    list_filter = ['created_time']
    search_fields = ['dict_name', 'description']
    readonly_fields = ['id', 'created_time', 'updated_time']

@admin.register(Word)
class WordAdmin(admin.ModelAdmin):
    """Wordadmin."""
    list_display = ['words', 'created_time']
    search_fields = ['words']
    readonly_fields = ['id', 'created_time']

@admin.register(WordMeaning)
class WordMeaningAdmin(admin.ModelAdmin):
    """Wordmeaningadmin."""
    list_display = ['word', 'part_of_speech', 'inner_id', 'chinese_translation']
    list_filter = ['part_of_speech']
    search_fields = ['word__words', 'chinese_translation']
    readonly_fields = ['id', 'created_time']

@admin.register(DictWordMeaning)
class DictWordMeaningAdmin(admin.ModelAdmin):
    """Dictwordmeaningadmin."""
    list_display = ['dictionary', 'word', 'meaning', 'sort_order']
    list_filter = ['dictionary']
    search_fields = ['dictionary__dict_name', 'word__words']
    readonly_fields = ['id', 'created_at']

@admin.register(DictChapter)
class DictChapterAdmin(admin.ModelAdmin):
    """Dictchapteradmin."""
    list_display = ['dictionary', 'chapter_inner_id', 'dict_word_meaning', 'created_time']
    list_filter = ['dictionary', 'chapter_inner_id']
    search_fields = ['dictionary__dict_name']
    readonly_fields = ['id', 'created_time']

@admin.register(UserStudyPlan)
class UserStudyPlanAdmin(admin.ModelAdmin):
    """Userstudyplanadmin."""
    list_display = ['user', 'dictionary', 'chapter_inner_id', 'is_activated', 'is_locked', 'learned_percentage', 'created_at', 'updated_at']
    list_filter = ['is_activated', 'is_locked', 'dictionary', 'created_at']
    search_fields = ['user__username', 'dictionary__dict_name']
    readonly_fields = ['id', 'created_at', 'updated_at']

@admin.register(UserOngoingPlan)
class UserOngoingPlanAdmin(admin.ModelAdmin):
    """Userongoingplanadmin."""
    list_display = ['user', 'plan', 'dict_chapter', 'words', 'part_of_speech', 'learned_type', 'is_frozen', 'created_at']
    list_filter = ['learned_type', 'is_frozen', 'part_of_speech', 'created_at']
    search_fields = ['user__username', 'words', 'chinese_translation']
    readonly_fields = ['id', 'created_at', 'updated_at']
