from django.core.exceptions import ValidationError
import re

class TenantValidator:
    @staticmethod
    def validate_code(code):
        if not re.match(r'^[a-z0-9-]+$', code):
            raise ValidationError('Tenant code must contain only lowercase letters, numbers, and hyphens.')
        if len(code) < 3 or len(code) > 63:
            raise ValidationError('Tenant code must be between 3 and 63 characters.')

class DomainValidator:
    @staticmethod
    def validate_domain(domain):
        if not re.match(r'^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$', domain):
            raise ValidationError('Invalid domain format.')

class QuotaValidator:
    @staticmethod
    def validate_usage(current, maximum):
        if maximum != -1 and current >= maximum:
            raise ValidationError('Quota exceeded.')
