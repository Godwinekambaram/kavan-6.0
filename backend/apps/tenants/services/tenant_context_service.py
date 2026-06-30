import threading

_thread_locals = threading.local()

class TenantContextService:
    @classmethod
    def set_current_tenant(cls, tenant):
        _thread_locals.tenant = tenant
        
    @classmethod
    def get_current_tenant(cls):
        return getattr(_thread_locals, 'tenant', None)
        
    @classmethod
    def clear(cls):
        if hasattr(_thread_locals, 'tenant'):
            del _thread_locals.tenant
