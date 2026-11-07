"""Keep legacy database models available without starting legacy workers."""
from django.apps import AppConfig

class AgentSystemConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "agent_system"
