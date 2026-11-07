"""Serializers."""
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, Dictionary

class UserRegisterSerializer(serializers.ModelSerializer):
    """Userregisterserializer."""
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirmed = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = ['username', 'password', 'password_confirmed']
    
    def validate(self, attrs):
        """Validate."""
        if attrs['password'] != attrs['password_confirmed']:
            raise serializers.ValidationError({
                "password_confirmed": "两次输入的密码不一致"
            })
        return attrs
    
    def create(self, validated_data):
        """Create."""
        validated_data.pop('password_confirmed')
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password']
        )
        return user

class UserLoginSerializer(serializers.Serializer):
    """Userloginserializer."""
    username = serializers.CharField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )

class DeviceBindSerializer(serializers.Serializer):
    """Devicebindserializer."""
    device_id = serializers.CharField(max_length=100, required=True)

class DictionarySerializer(serializers.ModelSerializer):
    """Dictionaryserializer."""
    class Meta:
        model = Dictionary
        fields = ['id', 'dict_name', 'dict_num', 'cover_url', 'description', 'chapter_num']

class WordMeaningSerializer(serializers.Serializer):
    """Wordmeaningserializer."""
    part_of_speech = serializers.CharField()
    chinese_translation = serializers.CharField()
    sort_order = serializers.IntegerField()

class DictWordDetailSerializer(serializers.Serializer):
    """Dictworddetailserializer."""
    word = serializers.CharField()
    meanings = WordMeaningSerializer(many=True)

class StudyPlanSelectSerializer(serializers.Serializer):
    """Studyplanselectserializer."""
    dict_id = serializers.IntegerField(required=True)

class StudyPlanDeleteSerializer(serializers.Serializer):
    """Studyplandeleteserializer."""
    plan_id = serializers.IntegerField(required=True)

class OngoingPlanMeaningSerializer(serializers.Serializer):
    """Ongoingplanmeaningserializer."""
    part_of_speech = serializers.CharField()
    chinese_translation = serializers.CharField()
    learned_type = serializers.CharField()
    is_frozen = serializers.BooleanField()

class StudyPlanProgressSerializer(serializers.Serializer):
    """Studyplanprogressserializer."""
    word = serializers.CharField()
    meanings = OngoingPlanMeaningSerializer(many=True)
