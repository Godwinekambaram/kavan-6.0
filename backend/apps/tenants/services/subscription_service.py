from django.utils import timezone

class SubscriptionService:
    @classmethod
    def check_quota(cls, tenant, quota_type):
        sub = getattr(tenant, 'subscription', None)
        if not sub:
            return False
            
        if quota_type == 'users':
            return sub.current_users < sub.user_quota
        elif quota_type == 'storage':
            return sub.current_storage_mb < sub.storage_quota_mb
        elif quota_type == 'api':
            return sub.api_quota == -1 or sub.api_quota > 0 # Simple example logic
        return False
        
    @classmethod
    def update_usage(cls, tenant, quota_type, amount=1):
        sub = getattr(tenant, 'subscription', None)
        if not sub: return
        
        if quota_type == 'users':
            sub.current_users += amount
        elif quota_type == 'storage':
            sub.current_storage_mb += amount
        sub.save()
        
    @classmethod
    def expire_subscription(cls, tenant):
        sub = getattr(tenant, 'subscription', None)
        if sub:
            sub.plan = 'EXPIRED'
            sub.save()
