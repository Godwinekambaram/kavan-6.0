import logging
from celery import shared_task

logger = logging.getLogger(__name__)

@shared_task
def queue_audit_log(user_id, tenant_id, role, permission_code, is_allowed, ip_address='0.0.0.0'):
    # In a real environment, this inserts into RBACAuditLog
    logger.info(f'AUDIT: User={user_id} Tenant={tenant_id} Role={role} Perm={permission_code} Allowed={is_allowed}')
    return True

class RBACAuditService:
    @staticmethod
    def log_decision(user, tenant, role, permission_code, is_allowed):
        queue_audit_log.delay(
            user_id=str(user.id) if user else None,
            tenant_id=str(tenant.id) if tenant else None,
            role=role,
            permission_code=permission_code,
            is_allowed=is_allowed
        )
