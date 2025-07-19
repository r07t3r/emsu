from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    def ready(self):
        import core.signals  # You have to just Ensure signals are imported when the app is ready bro 

