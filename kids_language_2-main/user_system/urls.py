"""Urls."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()

urlpatterns = [

    path("auth/register/", views.register, name="register"),
    path("auth/login/", views.login, name="login"),
    path("auth/logout/", views.logout, name="logout"),
    path("auth/me/", views.get_current_user, name="get_current_user"),

    path("device/bind/", views.bind_device, name="bind_device"),

    path("dictionaries/", views.get_dictionaries, name="get_dictionaries"),
    path("dictionaries/<int:dict_id>/words/", views.get_dictionary_words, name="get_dictionary_words"),
    path("dictionaries/<int:dict_id>/chapters/words/", views.get_dictionary_chapter_words, name="get_dictionary_chapter_words"),

    path("study-plan/select/", views.select_study_plan, name="select_study_plan"),
    path("study-plan/delete/", views.delete_study_plan, name="delete_study_plan"),
    path("study-plan/progress/", views.get_study_plan_progress, name="get_study_plan_progress"),
    path("study-plan/update-percentage/", views.update_learned_percentage_view, name="update_learned_percentage"),

    path("", include(router.urls)),
]
