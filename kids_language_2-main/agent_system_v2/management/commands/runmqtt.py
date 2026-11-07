"""Run one MQTT consumer and its review scheduler per deployment."""
import time
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Start the v2 MQTT worker with MQTT_ENABLED=true."

    def handle(self, *args, **options):
        from django.conf import settings
        from agent_system_v2 import apps
        from agent_system_v2.mqtt_client import mqtt_client_v2
        if not settings.MQTT_ENABLED or not apps._initialized:
            raise CommandError("Set MQTT_ENABLED=true and check the broker connection.")
        self.stdout.write("MQTT worker running. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            mqtt_client_v2.disconnect()
