"""Db router."""

LEGACY_APPS = {"agent_system"}

DEFAULT_APPS = {"user_system", "agent_system_v2"}

class DatabaseRouter:
    """Databaserouter."""

    def db_for_read(self, model, **hints):
        if model._meta.app_label in LEGACY_APPS:
            return "legacy"
        return "default"

    def db_for_write(self, model, **hints):
        if model._meta.app_label in LEGACY_APPS:
            return "legacy"
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        """Allow relation."""
        db1 = "legacy" if obj1._meta.app_label in LEGACY_APPS else "default"
        db2 = "legacy" if obj2._meta.app_label in LEGACY_APPS else "default"
        return db1 == db2

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Allow migrate."""
        if app_label in LEGACY_APPS:
            return db == "legacy"

        return db == "default"
