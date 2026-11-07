"""Views."""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .serializers import (
    UserRegisterSerializer, 
    UserLoginSerializer, 
    DeviceBindSerializer,
    DictionarySerializer,
    DictWordDetailSerializer,
    StudyPlanSelectSerializer,
    StudyPlanDeleteSerializer,
    StudyPlanProgressSerializer
)
from .models import User, Dictionary, DictWordMeaning, DictChapter, UserStudyPlan, UserOngoingPlan
from .utils import update_learned_percentage

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """Register."""
    serializer = UserRegisterSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        
        return Response({
            "message": "注册成功",
            "user": {
                "id": str(user.id),
                "username": user.username,
                "device_id": user.device_id or None,
                "chapter_type": user.chapter_type or None,
                "device_battery": float(user.device_battery) if user.device_battery is not None else None
            },
            "tokens": {
                "access": str(refresh.access_token),
                "refresh": str(refresh)
            }
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """Login."""
    serializer = UserLoginSerializer(data=request.data)
    
    if serializer.is_valid():
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        
        user = authenticate(username=username, password=password)
        
        if user is not None:
            if user.is_active:

                refresh = RefreshToken.for_user(user)
                
                return Response({
                    "message": "登录成功",
                    "user": {
                        "id": str(user.id),
                        "username": user.username,
                        "device_id": user.device_id or None,
                        "chapter_type": user.chapter_type or None,
                        "device_battery": float(user.device_battery) if user.device_battery is not None else None
                    },
                    "tokens": {
                        "access": str(refresh.access_token),
                        "refresh": str(refresh)
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "error": "账户已被禁用"
                }, status=status.HTTP_403_FORBIDDEN)
        else:
            return Response({
                "error": "用户名或密码错误"
            }, status=status.HTTP_401_UNAUTHORIZED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    """Get current user."""
    user = request.user
    return Response({
        "id": str(user.id),
        "username": user.username,
        "device_id": user.device_id or None,
        "chapter_type": user.chapter_type or None,
        "device_battery": float(user.device_battery) if user.device_battery is not None else None
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """Logout."""
    try:
        refresh_token = request.data.get("refresh_token")
        
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                try:
                    token.blacklist()
                except AttributeError:
                    pass
            except Exception:
                pass
        
        return Response({
            "message": "登出成功"
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            "error": "登出失败",
            "detail": str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bind_device(request):
    """Bind device."""
    serializer = DeviceBindSerializer(data=request.data)
    
    if serializer.is_valid():
        user = request.user
        device_id = serializer.validated_data['device_id']

        if User.objects.filter(device_id=device_id).exclude(id=user.id).exists():
            return Response({
                "error": "该设备已被其他用户绑定"
            }, status=status.HTTP_400_BAD_REQUEST)

        user.device_id = device_id
        user.save()
        
        return Response({
            "message": "设备绑定成功",
            "user": {
                "id": str(user.id),
                "username": user.username,
                "device_id": user.device_id
            }
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dictionaries(request):
    """Get dictionaries."""
    dictionaries = Dictionary.objects.all()
    serializer = DictionarySerializer(dictionaries, many=True)
    
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dictionary_words(request, dict_id):
    """Get dictionary words."""
    try:
        dictionary = Dictionary.objects.get(id=dict_id)
    except Dictionary.DoesNotExist:
        return Response({
            "error": "字典不存在"
        }, status=status.HTTP_404_NOT_FOUND)
    
    dict_word_meanings = DictWordMeaning.objects.filter(
        dictionary_id=dict_id
    ).select_related('word', 'meaning').order_by('sort_order')

    words_dict = {}
    for dwm in dict_word_meanings:
        word_id = dwm.word.id
        word_text = dwm.word.words
        
        if word_id not in words_dict:
            words_dict[word_id] = {
                'word': word_text,
                'meanings': []
            }
        
        words_dict[word_id]['meanings'].append({
            'part_of_speech': dwm.meaning.part_of_speech,
            'chinese_translation': dwm.meaning.chinese_translation,
            'sort_order': dwm.sort_order
        })
    
    result = list(words_dict.values())
    serializer = DictWordDetailSerializer(result, many=True)
    
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dictionary_chapter_words(request, dict_id):
    """Get dictionary chapter words."""
    try:
        dictionary = Dictionary.objects.get(id=dict_id)
    except Dictionary.DoesNotExist:
        return Response({
            "error": "字典不存在"
        }, status=status.HTTP_404_NOT_FOUND)
    
    chapter_entries = DictChapter.objects.filter(
        dictionary_id=dict_id
    ).select_related(
        'dict_word_meaning__word',
        'dict_word_meaning__meaning'
    ).order_by('chapter_inner_id', 'dict_word_meaning__sort_order')

    chapters_dict = {}
    for entry in chapter_entries:
        chapter_id = entry.chapter_inner_id
        dwm = entry.dict_word_meaning
        word_id = dwm.word.id
        word_text = dwm.word.words
        
        if chapter_id not in chapters_dict:
            chapters_dict[chapter_id] = {
                'chapter_inner_id': chapter_id,
                'words_dict': {}
            }
        
        if word_id not in chapters_dict[chapter_id]['words_dict']:
            chapters_dict[chapter_id]['words_dict'][word_id] = {
                'word': word_text,
                'meanings': []
            }
        
        chapters_dict[chapter_id]['words_dict'][word_id]['meanings'].append({
            'part_of_speech': dwm.meaning.part_of_speech,
            'chinese_translation': dwm.meaning.chinese_translation,
            'sort_order': dwm.sort_order
        })
    
    result = []
    for chapter_id in sorted(chapters_dict.keys()):
        chapter_data = chapters_dict[chapter_id]
        result.append({
            'chapter_inner_id': chapter_data['chapter_inner_id'],
            'words': list(chapter_data['words_dict'].values())
        })
    
    return Response(result, status=status.HTTP_200_OK)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def select_study_plan(request):
    """Select study plan."""
    serializer = StudyPlanSelectSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    user = request.user
    dict_id = serializer.validated_data['dict_id']
    
    try:
        dictionary = Dictionary.objects.get(id=dict_id)
    except Dictionary.DoesNotExist:
        return Response({
            "error": "字典不存在"
        }, status=status.HTTP_404_NOT_FOUND)

    existing_plans = UserStudyPlan.objects.filter(user=user, dictionary=dictionary)
    
    if existing_plans.exists():

        existing_plans.update(is_activated=True)

        UserStudyPlan.objects.filter(user=user).exclude(dictionary=dictionary).update(is_activated=False)
        
        plans_data = list(existing_plans.order_by('chapter_inner_id').values(
            'id', 'chapter_inner_id', 'is_activated', 'is_locked', 'learned_percentage'
        ))
        
        for p in plans_data:
            p['learned_percentage'] = str(p['learned_percentage'])
        
        return Response({
            "message": "学习计划已激活",
            "dict_id": dictionary.id,
            "dict_name": dictionary.dict_name,
            "chapter_num": dictionary.chapter_num,
            "plans": plans_data
        }, status=status.HTTP_200_OK)

    chapter_ids = DictChapter.objects.filter(
        dictionary_id=dict_id
    ).values_list('chapter_inner_id', flat=True).distinct().order_by('chapter_inner_id')
    
    if not chapter_ids:
        return Response({
            "error": "该字典尚未配置章节数据"
        }, status=status.HTTP_400_BAD_REQUEST)

    UserStudyPlan.objects.filter(user=user).update(is_activated=False)

    chapter_ids_list = list(chapter_ids)
    first_chapter_id = min(chapter_ids_list) if chapter_ids_list else None
    
    study_plans = []
    for chapter_id in chapter_ids_list:
        study_plans.append(
            UserStudyPlan(
                user=user,
                dictionary=dictionary,
                chapter_inner_id=chapter_id,
                is_activated=True,
                is_locked=(chapter_id != first_chapter_id),
                learned_percentage=0.00
            )
        )
    
    created_plans = UserStudyPlan.objects.bulk_create(study_plans)

    plan_map = {p.chapter_inner_id: p for p in created_plans}

    chapter_entries = DictChapter.objects.filter(
        dictionary_id=dict_id
    ).select_related('dict_word_meaning__word', 'dict_word_meaning__meaning')

    ongoing_plans = []
    for entry in chapter_entries:
        dwm = entry.dict_word_meaning
        plan = plan_map.get(entry.chapter_inner_id)
        if plan:
            ongoing_plans.append(
                UserOngoingPlan(
                    user=user,
                    plan=plan,
                    dict_chapter=entry,
                    words=dwm.word.words,
                    part_of_speech=dwm.meaning.part_of_speech,
                    chinese_translation=dwm.meaning.chinese_translation,
                    learned_type='not_started',
                    is_frozen=False
                )
            )
    
    UserOngoingPlan.objects.bulk_create(ongoing_plans)

    plans_data = [{
        'id': p.id,
        'chapter_inner_id': p.chapter_inner_id,
        'is_activated': p.is_activated,
        'is_locked': p.is_locked,
        'learned_percentage': str(p.learned_percentage)
    } for p in created_plans]
    
    return Response({
        "message": "学习计划已创建并激活",
        "dict_id": dictionary.id,
        "dict_name": dictionary.dict_name,
        "chapter_num": dictionary.chapter_num,
        "plans": plans_data
    }, status=status.HTTP_200_OK)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def delete_study_plan(request):
    """Delete study plan."""
    dict_id = request.data.get('dict_id')
    
    if not dict_id:
        return Response({
            "error": "dict_id 参数必需"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        dict_id = int(dict_id)
    except ValueError:
        return Response({
            "error": "dict_id 必须是整数"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    user = request.user
    
    study_plans = UserStudyPlan.objects.filter(user=user, dictionary_id=dict_id)
    
    if not study_plans.exists():
        return Response({
            "error": "学习计划不存在或无权访问"
        }, status=status.HTTP_404_NOT_FOUND)
    
    plan_ids = list(study_plans.values_list('id', flat=True))

    UserOngoingPlan.objects.filter(plan_id__in=plan_ids).delete()
    
    deleted_count = study_plans.count()
    study_plans.delete()
    
    return Response({
        "message": "学习计划已删除",
        "deleted_plans": deleted_count
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_study_plan_progress(request):
    """Get study plan progress."""
    dict_id = request.query_params.get('dict_id')
    
    if not dict_id:
        return Response({
            "error": "dict_id 参数必需"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        dict_id = int(dict_id)
    except ValueError:
        return Response({
            "error": "dict_id 必须是整数"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    user = request.user
    
    try:
        dictionary = Dictionary.objects.get(id=dict_id)
    except Dictionary.DoesNotExist:
        return Response({
            "error": "字典不存在"
        }, status=status.HTTP_404_NOT_FOUND)
    
    study_plans = UserStudyPlan.objects.filter(
        user=user, 
        dictionary=dictionary
    ).order_by('chapter_inner_id')
    
    if not study_plans.exists():
        return Response({
            "error": "学习计划不存在，请先创建学习计划"
        }, status=status.HTTP_404_NOT_FOUND)
    
    plan_map = {p.id: p for p in study_plans}
    plan_ids = list(plan_map.keys())
    
    ongoing_plans = UserOngoingPlan.objects.filter(
        plan_id__in=plan_ids
    ).order_by('plan_id', 'words', 'part_of_speech')

    chapters_data = {}
    for plan in study_plans:
        chapters_data[plan.id] = {
            'chapter_inner_id': plan.chapter_inner_id,
            'plan_id': plan.id,
            'is_activated': plan.is_activated,
            'is_locked': plan.is_locked,
            'learned_percentage': str(plan.learned_percentage),
            'words_dict': {}
        }
    
    for op in ongoing_plans:
        plan_id = op.plan_id
        word_text = op.words
        
        if plan_id not in chapters_data:
            continue
        
        if word_text not in chapters_data[plan_id]['words_dict']:
            chapters_data[plan_id]['words_dict'][word_text] = {
                'word': word_text,
                'meanings': []
            }
        
        chapters_data[plan_id]['words_dict'][word_text]['meanings'].append({
            'part_of_speech': op.part_of_speech,
            'chinese_translation': op.chinese_translation,
            'learned_type': op.learned_type,
            'is_frozen': op.is_frozen
        })

    chapters_list = []
    for plan_id in [p.id for p in study_plans]:
        chapter_data = chapters_data[plan_id]
        chapters_list.append({
            'chapter_inner_id': chapter_data['chapter_inner_id'],
            'plan_id': chapter_data['plan_id'],
            'is_activated': chapter_data['is_activated'],
            'is_locked': chapter_data['is_locked'],
            'learned_percentage': chapter_data['learned_percentage'],
            'words': list(chapter_data['words_dict'].values())
        })
    
    return Response({
        "dict_id": dictionary.id,
        "dict_name": dictionary.dict_name,
        "chapter_num": dictionary.chapter_num,
        "chapters": chapters_list
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_learned_percentage_view(request):
    """Update learned percentage view."""
    user = request.user
    
    try:
        updated_count = update_learned_percentage(user_id=user.id)
        
        return Response({
            "message": "学习进度已更新",
            "updated_plans": updated_count
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            "error": "更新学习进度失败",
            "detail": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
