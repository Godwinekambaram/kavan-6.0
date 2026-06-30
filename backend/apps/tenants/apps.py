from django.apps import AppConfig

class TenantsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.apps.tenants'
    
    def ready(self):
        import backend.apps.tenants.signals
